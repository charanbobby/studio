"""
probe_01_openrouter_claude_cached.py

Verify Claude Sonnet via OpenRouter honors cache_control: ephemeral on the
system block. Two consecutive calls with the same system prompt; call #2
should show cached_input_tokens > 0.

Pass: PROBE OK with cache hit rate, cost numbers.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

API_KEY = os.environ["OPENROUTER_API_KEY"]
MODEL = os.environ.get("PLAN_MODEL", "anthropic/claude-sonnet-4-6")

# Long system prompt so caching makes a measurable difference.
SYSTEM = (
    "You are a video script planner for short-form vertical reels. "
    "Output a JSON object with: hook, scenes, voiceover_text, voice_style, "
    "music_mood, aspect_ratio. Each scene has scene_idx, duration_s, "
    "visual_prompt, voiceover_excerpt, motion. "
) * 80  # padded so the system block exceeds the cache-eligible threshold


def call(user_msg: str) -> dict:
    body = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            },
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 200,
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "https://studio.sshub.dev",
        "X-Title": "Sri Studio probe_01",
    }
    t0 = time.time()
    r = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=body,
        timeout=60,
    )
    r.raise_for_status()
    payload = r.json()
    payload["_latency_s"] = round(time.time() - t0, 3)
    return payload


def main() -> int:
    r1 = call("Plan a 5s reel about coffee.")
    time.sleep(1)
    r2 = call("Plan a 5s reel about a sunset.")
    transcript = {"first": r1, "second": r2}
    (OUT / "probe_01.json").write_text(json.dumps(transcript, indent=2))

    u1 = r1.get("usage", {})
    u2 = r2.get("usage", {})
    cached_2 = u2.get("prompt_tokens_details", {}).get("cached_tokens", 0)
    if cached_2 == 0:
        # OpenRouter sometimes nests cache info under the provider's shape;
        # look in usage directly too.
        cached_2 = u2.get("cache_read_input_tokens", 0)

    print("PROBE 01")
    print(f"  call1 input/output/latency: {u1.get('prompt_tokens')} / "
          f"{u1.get('completion_tokens')} / {r1['_latency_s']}s")
    print(f"  call2 input/output/latency: {u2.get('prompt_tokens')} / "
          f"{u2.get('completion_tokens')} / {r2['_latency_s']}s")
    print(f"  call2 cached_input_tokens: {cached_2}")
    if cached_2 <= 0:
        print("PROBE FAIL: no cache hit on call 2.")
        return 1
    print("PROBE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
