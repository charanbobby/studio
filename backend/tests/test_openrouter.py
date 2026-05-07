import json

import respx
from httpx import Response

from reel_gen.llm.openrouter import call_claude_cached


@respx.mock
def test_call_claude_cached_includes_cache_control(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")

    captured: dict = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return Response(
            200,
            json={
                "id": "x",
                "choices": [{"message": {"role": "assistant", "content": "hi"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 5,
                          "prompt_tokens_details": {"cached_tokens": 80}},
            },
        )

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(side_effect=handler)

    result = call_claude_cached(
        model="anthropic/claude-sonnet-4-6",
        system="SYSTEM",
        user="USER",
        max_tokens=10,
        phase="test",
    )

    sys_block = captured["body"]["messages"][0]["content"][0]
    assert sys_block.get("cache_control") == {"type": "ephemeral"}
    assert result.text == "hi"
    assert result.cost_entry.cached_input_tokens == 80
