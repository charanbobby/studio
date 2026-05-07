"""Parallel fan-out: TTS, image gen, captions. Music deferred unless with_music."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from reel_gen.media.elevenlabs_tts import generate_voiceover
from reel_gen.media.replicate_flux import generate_image
from reel_gen.runs import REGISTRY
from reel_gen.state import NodeError, ReelState


def _run_dir(run_id: str) -> Path:
    return Path(os.environ.get("RUNS_DIR", "./runs")) / run_id


async def execute_node(state: ReelState) -> ReelState:
    if not state.plan:
        state.errors.append(NodeError(node="execute", message="missing plan", fatal=True))
        return state
    if state.approved is False:
        state.errors.append(NodeError(node="execute", message="rejected by user", fatal=True))
        return state

    run_dir = _run_dir(state.run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    await REGISTRY.publish(state.run_id, {"event": "execute_start"})

    async def do_tts():
        try:
            mp3, words, cost = await asyncio.to_thread(
                generate_voiceover, text=state.plan.voiceover_text, out_dir=run_dir
            )
            state.voiceover_path = mp3
            state.captions = words
            state.cost_ledger.append(cost)
            await REGISTRY.publish(state.run_id, {"event": "tts_done"})
        except Exception as e:
            state.errors.append(NodeError(node="execute_tts", message=str(e), fatal=True))

    async def do_image(scene):
        try:
            p, cost = await asyncio.to_thread(
                generate_image,
                prompt=scene.visual_prompt,
                out_dir=run_dir,
                scene_idx=scene.scene_idx,
            )
            state.image_paths.append(p)
            state.cost_ledger.append(cost)
            await REGISTRY.publish(
                state.run_id, {"event": "image_done", "scene_idx": scene.scene_idx}
            )
        except Exception as e:
            await _fallback_solid_frame(run_dir, scene)
            fallback_path = run_dir / f"scene_{scene.scene_idx:02d}.png"
            state.image_paths.append(fallback_path)
            state.errors.append(NodeError(
                node="execute_image",
                message=f"scene {scene.scene_idx}: {e}",
                fatal=False,
            ))

    image_tasks = [do_image(s) for s in state.plan.scenes]
    await asyncio.gather(do_tts(), *image_tasks)

    state.image_paths.sort(key=lambda p: int(p.stem.split("_")[-1]))

    await REGISTRY.publish(state.run_id, {"event": "execute_end"})
    return state


async def _fallback_solid_frame(run_dir: Path, scene) -> None:
    import subprocess
    p = run_dir / f"scene_{scene.scene_idx:02d}.png"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=#1a1a2e:s=1080x1920:d=1",
        "-frames:v", "1", str(p),
    ], check=True)
