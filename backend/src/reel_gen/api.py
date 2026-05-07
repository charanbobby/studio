"""FastAPI app: routes for run lifecycle, SSE streaming, plan approval, file serving."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
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
    """Background coroutine: drives the LangGraph machine and publishes SSE events.
    Phase 5 wires the approval gate; Phases 6-7 wire Execute and Stitch.
    """
    from reel_gen.graph import build_graph_until_plan
    from reel_gen.state import ReelState

    state = ReelState(run_id=run_id, brief=prompt, duration_s=duration_s, with_music=with_music)
    await REGISTRY.update(run_id, status="running")
    await REGISTRY.publish(run_id, {"event": "extract_start"})
    graph = build_graph_until_plan()
    try:
        final = await asyncio.to_thread(graph.invoke, state)
        plan = final["plan"] if isinstance(final, dict) else final.plan
        await REGISTRY.publish(run_id, {"event": "plan_end", "plan": plan.model_dump() if plan else None})
        await REGISTRY.update(run_id, plan=plan.model_dump() if plan else None, status="awaiting_approval")
        # Phase 5 will: await REGISTRY.await_approval(run_id) then continue.
        await REGISTRY.complete(run_id, status="awaiting_approval")
    except Exception as e:
        await REGISTRY.publish(run_id, {"event": "error", "message": str(e)})
        await REGISTRY.complete(run_id, status="error")
    finally:
        flush_langfuse()


@app.post("/api/runs", response_model=CreateRunResponse)
async def create_run(req: CreateRunRequest, bg: BackgroundTasks) -> CreateRunResponse:
    run_id = await REGISTRY.create(
        brief=req.prompt, duration_s=req.duration_s, with_music=req.with_music
    )
    bg.add_task(_execute_run, run_id, req.prompt, req.duration_s, req.with_music)
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
