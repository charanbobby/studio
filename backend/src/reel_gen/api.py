"""FastAPI app: routes for run lifecycle, SSE streaming, plan approval, file serving."""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from reel_gen.featured import FeaturedRun, list_featured_runs
from reel_gen.runs import REGISTRY
from reel_gen.tracing.langfuse_client import flush as flush_langfuse
from reel_gen.tracing.langfuse_client import run_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Rehydrate past runs from disk so the Past Runs page survives backend
    # restarts. The in-memory registry would otherwise reset to empty on every
    # container restart, hiding all historical runs even though they exist on
    # the runs/ volume.
    try:
        loaded = REGISTRY.rehydrate_from_disk()
        print(f"[startup] rehydrated {loaded} past runs from disk")
    except Exception as e:
        print(f"[startup] rehydrate failed: {e}")
    yield


app = FastAPI(title="Sri Studio API", version="0.1.0", lifespan=lifespan)


class CreateRunRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    duration_s: int = Field(default=5, ge=3, le=120)
    with_music: bool = False


class CreateRunResponse(BaseModel):
    run_id: str


class FieldFeedbackModel(BaseModel):
    rating: Literal["good", "partial", "bad"] | None = None
    note: str = ""


class ApproveRequest(BaseModel):
    approved: bool
    edits: dict[str, Any] | None = None
    feedback: dict[str, FieldFeedbackModel] | None = None


class ReelFeedbackRequest(BaseModel):
    reel_quality: Literal["good", "partial", "bad"] | None = None
    voice_fidelity: Literal["good", "partial", "bad"] | None = None
    brand_voice_match: Literal["good", "partial", "bad"] | None = None
    would_ship: bool | None = None
    note: str = ""


_RATING_TO_NUMERIC = {"good": 1.0, "partial": 0.5, "bad": 0.0}


def _emit_score(
    *,
    session_id: str,
    name: str,
    value: float,
    string_value: str | None = None,
    comment: str | None = None,
) -> None:
    """Emit a single Langfuse score linked to the run's session.

    The v4.5.1 ``Langfuse.create_score`` signature accepts ``session_id``,
    ``name``, ``value`` (float | str), ``data_type``, ``comment``, plus an
    optional ``metadata`` mapping. There is no ``string_value`` kwarg, so we
    fold the categorical label into ``metadata.rating`` and append a "[label]"
    prefix to the comment for at-a-glance scanning in the dashboard.

    Implementation note: in v4.5.1, scores created with only ``session_id``
    (no ``trace_id``) are accepted by the ingest endpoint but do NOT surface
    via ``GET /api/public/scores?sessionId=...`` because the API only joins
    scores back to sessions through their attached trace. To make scores
    visible in the dashboard we wrap the call in a tiny ``feedback_score``
    observation under ``propagate_attributes(session_id=...)`` so a trace
    exists with the right session linkage, and use ``score_current_trace``
    which automatically picks up the active trace_id.

    Best-effort: any failure to construct or call the Langfuse client is
    swallowed and the client is flushed so scores show up in the Langfuse
    session before the next user action races ahead. A flush failure is also
    swallowed.
    """
    try:
        from langfuse import get_client, propagate_attributes  # local import
    except Exception:
        return

    try:
        lf = get_client()
        merged_comment = comment
        metadata: dict[str, Any] = {}
        if string_value is not None:
            metadata["rating"] = string_value
            tag = f"[{string_value}]"
            merged_comment = f"{tag} {comment}" if comment else tag
        score_kwargs: dict[str, Any] = {
            "name": name,
            "value": value,
            "data_type": "NUMERIC",
        }
        if merged_comment:
            score_kwargs["comment"] = merged_comment
        if metadata:
            score_kwargs["metadata"] = metadata

        with propagate_attributes(
            session_id=session_id,
            tags=["sri-studio", "feedback"],
            metadata={"run_id": session_id, "kind": "feedback_score"},
        ):
            with lf.start_as_current_observation(
                name=f"feedback_score.{name}",
                as_type="span",
                input={"score_name": name, "value": value, "rating": string_value},
            ):
                lf.score_current_trace(**score_kwargs)

        try:
            lf.flush()
        except Exception:
            pass
    except Exception:
        pass


@app.get("/healthz")
@app.get("/api/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "sri-studio-backend"}


def _runs_dir() -> Path:
    d = Path(os.environ.get("RUNS_DIR", "./runs"))
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _execute_run(run_id: str, prompt: str, duration_s: int, with_music: bool) -> None:
    """Drives the full LangGraph machine end-to-end. Publishes per-node events."""
    import json

    from reel_gen.graph import build_graph
    from reel_gen.state import ReelState

    state = ReelState(run_id=run_id, brief=prompt, duration_s=duration_s, with_music=with_music)
    await REGISTRY.update(run_id, status="running")
    graph = build_graph()
    try:
        # Wrap the entire graph invocation in a Langfuse session so every span
        # produced by @with_span-decorated node helpers is grouped under the
        # same run_id session in the dashboard. propagate_attributes is the
        # v4.5.1 OTel-baggage mechanism (mirrors the Find Evil pipeline pattern).
        with run_session(run_id=run_id):
            # LangGraph's async invoke is required because approval_gate + execute + stitch use async.
            final = await graph.ainvoke(state)
        final_state = ReelState.model_validate(final) if isinstance(final, dict) else final
        run_dir = _runs_dir() / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "cost.json").write_text(
            json.dumps([c.model_dump() for c in final_state.cost_ledger], indent=2, default=str)
        )
        if final_state.reel_path:
            await REGISTRY.update(run_id, reel_path=str(final_state.reel_path))
        if final_state.approved is False:
            await REGISTRY.complete(run_id, status="rejected")
        elif final_state.errors and any(e.fatal for e in final_state.errors):
            await REGISTRY.complete(run_id, status="error")
        else:
            await REGISTRY.complete(run_id, status="completed")
    except Exception as e:
        await REGISTRY.publish(run_id, {"event": "error", "message": str(e)})
        await REGISTRY.complete(run_id, status="error")
    finally:
        flush_langfuse()


_BACKGROUND_TASKS: set[asyncio.Task] = set()


@app.post("/api/runs", response_model=CreateRunResponse)
async def create_run(req: CreateRunRequest) -> CreateRunResponse:
    run_id = await REGISTRY.create(
        brief=req.prompt, duration_s=req.duration_s, with_music=req.with_music
    )
    # Detached background task; survives the request handler's return so
    # the long-running graph (Extract -> Approval -> Execute -> Stitch) can run
    # without blocking the response. We hold a reference to prevent the GC
    # from collecting the task mid-flight (asyncio docs).
    task = asyncio.create_task(_execute_run(run_id, req.prompt, req.duration_s, req.with_music))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
    return CreateRunResponse(run_id=run_id)


@app.get("/api/runs")
async def list_runs() -> list[dict]:
    return await REGISTRY.list_runs()


@app.get("/api/featured-runs", response_model=list[FeaturedRun])
def get_featured_runs(pin: str | None = None, limit: int = 3) -> list[FeaturedRun]:
    """Return up to `limit` runs that the user marked would_ship.

    The pinned run id (if it qualifies) is forced into slot 0. Remaining
    slots are filled newest-first by reel_feedback.submitted_at.
    """
    return list_featured_runs(pin=pin, limit=limit)


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    snap = await REGISTRY.snapshot(run_id)
    if not snap:
        raise HTTPException(404, "run not found")
    # Always merge the latest plan from disk so the UI reflects post-edit
    # state. plan.json is the source of truth: plan_node writes it, and the
    # approve-plan endpoint rewrites it when the user submits edits. Reading
    # it here keeps the registry snapshot from masking the edited version.
    plan_path = _runs_dir() / run_id / "plan.json"
    if plan_path.exists():
        try:
            snap["plan"] = json.loads(plan_path.read_text())
        except Exception:
            pass
    return snap


@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str):
    snap = await REGISTRY.snapshot(run_id)
    if not snap:
        raise HTTPException(404, "run not found")

    async def gen():
        async for event in REGISTRY.subscribe(run_id):
            yield {"event": event.get("event", "message"), "data": json.dumps(event)}

    return EventSourceResponse(gen())


def _diff_plans(original: dict, edited: dict) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """Per-field diff between two ScriptPlan dicts.

    Returns (fields_changed, diffs) where diffs maps a dotted/indexed path to
    {"before": ..., "after": ...}. Captured paths cover hook, voiceover_text,
    voice_style, music_mood, plus per-scene visual_prompt / voiceover_excerpt
    / motion / duration_s. This is the training-signal shape consumed by Plan
    prompt distillation.
    """
    fields_changed: list[str] = []
    diffs: dict[str, dict[str, Any]] = {}
    top_keys = ["hook", "voiceover_text", "voice_style", "music_mood", "aspect_ratio"]
    for key in top_keys:
        before = original.get(key)
        after = edited.get(key)
        if before != after:
            fields_changed.append(key)
            diffs[key] = {"before": before, "after": after}

    orig_scenes = original.get("scenes") or []
    edit_scenes = edited.get("scenes") or []
    n = max(len(orig_scenes), len(edit_scenes))
    scene_keys = ["visual_prompt", "voiceover_excerpt", "motion", "duration_s", "scene_idx"]
    for i in range(n):
        o = orig_scenes[i] if i < len(orig_scenes) else {}
        e = edit_scenes[i] if i < len(edit_scenes) else {}
        for key in scene_keys:
            before = o.get(key) if isinstance(o, dict) else None
            after = e.get(key) if isinstance(e, dict) else None
            if before != after:
                path = f"scenes[{i}].{key}"
                fields_changed.append(path)
                diffs[path] = {"before": before, "after": after}
    return fields_changed, diffs


@app.post("/api/runs/{run_id}/approve-plan")
async def approve_plan(run_id: str, req: ApproveRequest) -> dict:
    snap = await REGISTRY.snapshot(run_id)
    if not snap:
        raise HTTPException(404, "run not found")

    fields_changed: list[str] = []
    if req.edits is not None:
        run_dir = _runs_dir() / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        plan_path = run_dir / "plan.json"
        original_plan: dict = {}
        if plan_path.exists():
            try:
                original_plan = json.loads(plan_path.read_text())
            except Exception:
                original_plan = {}
        edited_plan = req.edits
        fields_changed, diffs = _diff_plans(original_plan, edited_plan)
        edits_record = {
            "run_id": run_id,
            "edited_at": datetime.now(timezone.utc).isoformat(),
            "original_plan": original_plan,
            "edited_plan": edited_plan,
            "fields_changed": fields_changed,
            "diffs": diffs,
        }
        (run_dir / "plan_edits.json").write_text(
            json.dumps(edits_record, indent=2, default=str)
        )
        # Persist the edited plan so subsequent reads (and the Execute
        # fan-out, which reads through state.plan refreshed in the gate)
        # see the user's edits.
        plan_path.write_text(json.dumps(edited_plan, indent=2, default=str))
        await REGISTRY.set_approval(run_id, approved=req.approved, edited_plan=edited_plan)
    else:
        await REGISTRY.set_approval(run_id, approved=req.approved)

    # Per-field feedback ratings. Auxiliary signal alongside plan_edits.json;
    # written only if the user touched at least one field. Wrapped in try/except
    # so a bad payload never breaks the approve flow.
    feedback_written = False
    if req.feedback:
        try:
            rated = {
                k: v.model_dump()
                for k, v in req.feedback.items()
                if v.rating is not None or (v.note or "").strip() != ""
            }
            if rated:
                run_dir = _runs_dir() / run_id
                run_dir.mkdir(parents=True, exist_ok=True)
                feedback_record = {
                    "run_id": run_id,
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                    "feedback": rated,
                }
                (run_dir / "feedback.json").write_text(
                    json.dumps(feedback_record, indent=2, default=str)
                )
                feedback_written = True

                # Mirror each rated field as a Langfuse Score on the run's
                # session so the dashboard can filter "show me runs where the
                # hook was rated bad". Best-effort: any Langfuse failure is
                # swallowed by _emit_score so it never blocks the user.
                for path, fb in req.feedback.items():
                    rating = fb.rating
                    if rating is None:
                        continue
                    numeric = _RATING_TO_NUMERIC.get(rating)
                    if numeric is None:
                        continue
                    _emit_score(
                        session_id=run_id,
                        name=f"plan.{path}",
                        value=numeric,
                        string_value=rating,
                        comment=(fb.note or None),
                    )
        except Exception:
            feedback_written = False

    # Edit volume as a separate score: useful for "how much did the user
    # rewrite the plan" analyses. Emit even when feedback is empty, as long as
    # edits were submitted.
    if req.edits is not None:
        _emit_score(
            session_id=run_id,
            name="plan.fields_edited_count",
            value=float(len(fields_changed)),
        )

    return {
        "run_id": run_id,
        "approved": req.approved,
        "edited": req.edits is not None,
        "fields_changed": fields_changed,
        "feedback_written": feedback_written,
    }


@app.post("/api/runs/{run_id}/reel-feedback")
async def reel_feedback(run_id: str, req: ReelFeedbackRequest) -> dict:
    """Capture post-reel user feedback after the final reel renders.

    Persists to ``runs/<id>/reel_feedback.json`` and emits one Langfuse Score
    per non-null rating, plus a numeric ``reel.would_ship`` score when set.
    """
    snap = await REGISTRY.snapshot(run_id)
    if not snap:
        raise HTTPException(404, "run not found")

    run_dir = _runs_dir() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "run_id": run_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "reel_quality": req.reel_quality,
        "voice_fidelity": req.voice_fidelity,
        "brand_voice_match": req.brand_voice_match,
        "would_ship": req.would_ship,
        "note": req.note,
    }
    (run_dir / "reel_feedback.json").write_text(
        json.dumps(record, indent=2, default=str)
    )

    # Mirror every non-null rating to Langfuse as a Score linked to the run's
    # session. Field name mirrors the plan.* convention so dashboard filters
    # group neatly (plan.* vs reel.*).
    rating_fields = {
        "reel.quality": req.reel_quality,
        "reel.voice_fidelity": req.voice_fidelity,
        "reel.brand_voice_match": req.brand_voice_match,
    }
    for name, rating in rating_fields.items():
        if rating is None:
            continue
        numeric = _RATING_TO_NUMERIC.get(rating)
        if numeric is None:
            continue
        _emit_score(
            session_id=run_id,
            name=name,
            value=numeric,
            string_value=rating,
            comment=(req.note or None),
        )

    if req.would_ship is not None:
        _emit_score(
            session_id=run_id,
            name="reel.would_ship",
            value=1.0 if req.would_ship else 0.0,
            string_value="yes" if req.would_ship else "no",
            comment=(req.note or None),
        )

    return {"run_id": run_id, "saved": True}


@app.get("/api/runs/{run_id}/plan.json")
async def get_plan(run_id: str):
    p = _runs_dir() / run_id / "plan.json"
    if not p.exists():
        raise HTTPException(404, "plan not found")
    return FileResponse(p, media_type="application/json")


@app.get("/api/runs/{run_id}/reel.mp4")
async def get_reel(run_id: str):
    p = _runs_dir() / run_id / "reel.mp4"
    if not p.exists():
        raise HTTPException(404, "reel not ready")
    return FileResponse(p, media_type="video/mp4", filename=f"{run_id}.mp4")
