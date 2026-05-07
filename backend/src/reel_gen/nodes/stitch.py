"""Stitch node: assemble final reel.mp4 from generated assets.

Thin async wrapper around ``ffmpeg_stitch.stitch_reel`` that:
- emits ``stitch_start`` / ``stitch_end`` SSE events via the run registry
- runs the blocking ffmpeg subprocess in a worker thread
- records fatal errors on the state object instead of raising

Note: the ``with_span`` decorator from ``reel_gen.tracing.langfuse_client`` is
sync-only (it calls the wrapped function directly inside a context manager).
Decorating an ``async def`` would only span the coroutine construction, not
its execution, so we omit it here. The peer ``execute_node`` does the same.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from reel_gen.media.ffmpeg_stitch import stitch_reel
from reel_gen.runs import REGISTRY
from reel_gen.state import NodeError, ReelState


def _run_dir(run_id: str) -> Path:
    return Path(os.environ.get("RUNS_DIR", "./runs")) / run_id


async def stitch_node(state: ReelState) -> ReelState:
    if not state.plan or not state.voiceover_path or not state.image_paths:
        state.errors.append(NodeError(
            node="stitch",
            message="missing plan / voiceover / images",
            fatal=True,
        ))
        return state

    out = _run_dir(state.run_id) / "reel.mp4"
    try:
        await REGISTRY.publish(state.run_id, {"event": "stitch_start"})
        await asyncio.to_thread(
            stitch_reel,
            plan=state.plan,
            image_paths=state.image_paths,
            voiceover=state.voiceover_path,
            music=state.music_path,
            captions=state.captions,
            out=out,
        )
        state.reel_path = out
        await REGISTRY.publish(
            state.run_id, {"event": "stitch_end", "reel": out.name}
        )
    except Exception as e:
        state.errors.append(NodeError(node="stitch", message=str(e), fatal=True))
    return state
