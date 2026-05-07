import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from reel_gen.nodes.execute import execute_node
from reel_gen.state import CaptionWord, CostEntry, ReelState, Scene, ScriptPlan


@pytest.mark.asyncio
async def test_execute_node_runs_tts_and_images_in_parallel(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    plan = ScriptPlan(
        hook="A.", scenes=[
            Scene(scene_idx=0, duration_s=2.5, visual_prompt="p1",
                  voiceover_excerpt="hi", motion="zoom_in"),
            Scene(scene_idx=1, duration_s=2.5, visual_prompt="p2",
                  voiceover_excerpt="bye", motion="zoom_out"),
        ],
        voiceover_text="hi bye", voice_style="warm",
        music_mood=None, aspect_ratio="9:16",
    )
    state = ReelState(run_id="r", brief="x", duration_s=5, plan=plan, approved=True)

    fake_cost = CostEntry(phase="x", provider="x", cost_usd=0.001, timestamp="t")

    def fake_image(*args, **kwargs):
        scene_idx = kwargs.get("scene_idx", args[2] if len(args) > 2 else 0)
        out_dir = kwargs.get("out_dir", args[1] if len(args) > 1 else Path("."))
        p = Path(out_dir) / f"scene_{scene_idx:02d}.png"
        p.write_bytes(b"\x89PNG")
        return p, fake_cost

    def fake_tts(*args, **kwargs):
        out_dir = kwargs.get("out_dir", args[1] if len(args) > 1 else Path("."))
        p = Path(out_dir) / "voiceover.mp3"
        p.write_bytes(b"mp3")
        words = [CaptionWord(text="hi", start_s=0.0, end_s=0.5),
                 CaptionWord(text="bye", start_s=0.5, end_s=1.0)]
        return p, words, fake_cost

    with patch("reel_gen.nodes.execute.generate_image", side_effect=fake_image), \
         patch("reel_gen.nodes.execute.generate_voiceover", side_effect=fake_tts):
        new_state = await execute_node(state)

    assert new_state.voiceover_path is not None
    assert len(new_state.image_paths) == 2
    assert new_state.captions and len(new_state.captions) == 2
