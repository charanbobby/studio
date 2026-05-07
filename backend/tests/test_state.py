from pathlib import Path

import pytest
from pydantic import ValidationError

from reel_gen.state import ExtractedIntent, ReelState, Scene, ScriptPlan


def test_scene_validates_positive_duration():
    s = Scene(scene_idx=0, duration_s=2.5, visual_prompt="x", voiceover_excerpt="y", motion="zoom_in")
    assert s.scene_idx == 0
    with pytest.raises(ValidationError):
        Scene(scene_idx=0, duration_s=-1, visual_prompt="x", voiceover_excerpt="y", motion="zoom_in")


def test_scriptplan_round_trip():
    plan = ScriptPlan(
        hook="A.",
        scenes=[Scene(scene_idx=0, duration_s=5.0, visual_prompt="p", voiceover_excerpt="v", motion="zoom_in")],
        voiceover_text="A.",
        voice_style="warm",
        music_mood=None,
        aspect_ratio="9:16",
    )
    j = plan.model_dump_json()
    plan2 = ScriptPlan.model_validate_json(j)
    assert plan2.scenes[0].motion == "zoom_in"


def test_reelstate_minimum():
    s = ReelState(run_id="abc", brief="hello", duration_s=5, with_music=False)
    assert s.intent is None
    assert s.image_paths == []
    assert s.cost_ledger == []
