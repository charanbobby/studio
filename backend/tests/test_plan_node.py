import json
from pathlib import Path

import respx
from httpx import Response

from reel_gen.nodes.plan import plan_node
from reel_gen.state import ExtractedIntent, ReelState


@respx.mock
def test_plan_node_writes_plan_json(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("PLAN_MODEL", "anthropic/claude-sonnet-4-6")
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_COST_CAP_USD", "100")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")

    plan_json = json.dumps({
        "hook": "Spring is here.",
        "scenes": [
            {"scene_idx": 0, "duration_s": 5.0,
             "visual_prompt": "spring market vertical 9:16 cinematic",
             "voiceover_excerpt": "Spring is here.", "motion": "zoom_in"}
        ],
        "voiceover_text": "Spring is here.",
        "voice_style": "warm",
        "music_mood": None,
        "aspect_ratio": "9:16",
    })
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json={
            "choices": [{"message": {"content": plan_json}}],
            "usage": {"prompt_tokens": 500, "completion_tokens": 200,
                      "prompt_tokens_details": {"cached_tokens": 400}},
        })
    )

    state = ReelState(
        run_id="rxx",
        brief="spring sale",
        duration_s=5,
        intent=ExtractedIntent(topic="spring sale", tone="energetic", audience="general"),
    )
    new_state = plan_node(state)
    assert new_state.plan is not None
    assert len(new_state.plan.scenes) == 1
    assert (Path(tmp_path) / "rxx" / "plan.json").exists()
