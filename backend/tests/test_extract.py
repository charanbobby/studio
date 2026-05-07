import json

import respx
from httpx import Response

from reel_gen.nodes.extract import extract_node
from reel_gen.state import ReelState


@respx.mock
def test_extract_node_parses_intent(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("EXTRACT_MODEL", "anthropic/claude-haiku-4-5")
    # Isolate cost-cap ledger to a tmp dir; raise the cap so the prospective
    # estimate inside call_claude_cached cannot trip it.
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_COST_CAP_USD", "100")
    # Langfuse client is constructed lazily by the with_span decorator; give it
    # dummy creds so it does not crash. The exporter will fail to reach the
    # backend in tests, but that is non-fatal (errors print, do not raise).
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")

    intent_json = json.dumps({
        "topic": "spring kitchen sale",
        "tone": "energetic",
        "audience": "home cooks",
        "brand_voice": "Sur La Table",
        "notes": None,
    })
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json={
            "choices": [{"message": {"content": intent_json}}],
            "usage": {"prompt_tokens": 200, "completion_tokens": 50,
                      "prompt_tokens_details": {"cached_tokens": 0}},
        })
    )

    state = ReelState(run_id="r1", brief="Sur La Table spring kitchen sale, fun energy", duration_s=5)
    new_state = extract_node(state)
    assert new_state.intent is not None
    assert new_state.intent.topic == "spring kitchen sale"
    assert new_state.intent.tone == "energetic"
    assert len(new_state.cost_ledger) == 1
