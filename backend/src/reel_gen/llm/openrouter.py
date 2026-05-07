"""OpenRouter client wired with prompt caching + cost helpers."""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from reel_gen.llm.cost import llm_cost_post, llm_cost_pre
from reel_gen.llm.cost_cap import add_to_today, check_cap
from reel_gen.state import CostEntry

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class OpenRouterResult:
    text: str
    cost_entry: CostEntry
    raw: dict


def call_claude_cached(
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 1024,
    phase: str,
    estimated_input_tokens: int = 0,
) -> OpenRouterResult:
    """Single Claude call with cache_control: ephemeral on the system block.

    Pre-call: checks daily cost cap with a conservative estimate, prints
    PRE cost line. Post-call: prints POST cost line, adds actual cost
    to the daily ledger.
    """
    api_key = os.environ["OPENROUTER_API_KEY"]
    if estimated_input_tokens == 0:
        estimated_input_tokens = max(len(system) // 4, 1)

    # Conservative pre-cap estimate: assume worst case (no cache hit).
    from reel_gen.llm.cost import cost_for_llm_usage
    est_cost = cost_for_llm_usage(
        model=model, input_tokens=estimated_input_tokens, output_tokens=max_tokens
    ) or 0.0
    check_cap(prospective_cost_usd=est_cost)

    llm_cost_pre(phase=phase, model=model, input_tokens_estimate=estimated_input_tokens)

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
                ],
            },
            {"role": "user", "content": user},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://studio.sshub.dev",
        "X-Title": "Sri Studio",
    }

    r = httpx.post(OPENROUTER_URL, json=body, headers=headers, timeout=120)
    r.raise_for_status()
    payload = r.json()

    text = payload["choices"][0]["message"]["content"]
    if isinstance(text, list):
        text = "".join(part.get("text", "") for part in text if isinstance(part, dict))

    cost_entry = llm_cost_post(phase=phase, model=model, usage=payload.get("usage", {}))
    add_to_today(cost_entry.cost_usd)

    return OpenRouterResult(text=text, cost_entry=cost_entry, raw=payload)
