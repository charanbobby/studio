"""FastAPI app: routes for run lifecycle, SSE streaming, plan approval, file serving."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from reel_gen.runs import REGISTRY
from reel_gen.tracing.langfuse_client import flush as flush_langfuse

app = FastAPI(title="Sri Studio API", version="0.1.0")


class CreateRunRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    duration_s: int = Field(default=5, ge=3, le=120)
    with_music: bool = False


class CreateRunResponse(BaseModel):
    run_id: str


class ApproveRequest(BaseModel):
    approved: bool


@app.get("/healthz")
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


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    snap = await REGISTRY.snapshot(run_id)
    if not snap:
        raise HTTPException(404, "run not found")
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


@app.post("/api/runs/{run_id}/approve-plan")
async def approve_plan(run_id: str, req: ApproveRequest) -> dict:
    snap = await REGISTRY.snapshot(run_id)
    if not snap:
        raise HTTPException(404, "run not found")
    await REGISTRY.set_approval(run_id, approved=req.approved)
    return {"run_id": run_id, "approved": req.approved}


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
