"""OpenRouter client wired with prompt caching + cost helpers.

Each call is wrapped in a Langfuse v4 generation observation that records:
- input: full chat messages (system + user blocks, including cache_control hints)
- output: the assistant text returned by the model
- model: the OpenRouter model id
- model_parameters: max_tokens, etc.
- usage_details: input (uncached), cached_input, output token counts
- cost_details: total USD computed via the local rate table
- metadata: phase, plus the raw OpenRouter usage block for forensic depth

The Langfuse import is wrapped in a try/except so the module remains importable
in environments without the SDK or credentials (unit tests use respx and never
talk to the live Langfuse backend).
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

import httpx

from reel_gen.llm.cost import cost_for_llm_usage, llm_cost_post, llm_cost_pre
from reel_gen.llm.cost_cap import add_to_today, check_cap
from reel_gen.state import CostEntry

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class OpenRouterResult:
    text: str
    cost_entry: CostEntry
    raw: dict


@contextmanager
def _generation_observation(
    *, name: str, model: str, input_messages: list[dict[str, Any]], metadata: dict[str, Any]
) -> Iterator[Any]:
    """Yield a Langfuse generation handle, or None if Langfuse is unavailable.

    The handle exposes ``.update(output=..., usage_details=..., cost_details=...)``
    when present. Caller code uses ``if gen is not None`` guards so the path is
    a no-op in test environments without Langfuse credentials.
    """
    try:
        from langfuse import get_client  # local import (optional dep)

        lf = get_client()
    except Exception:
        yield None
        return

    try:
        cm = lf.start_as_current_observation(
            name=name,
            as_type="generation",
            model=model,
            input=input_messages,
            metadata=metadata,
        )
    except Exception:
        # Misconfigured Langfuse client: degrade gracefully, do not break the
        # paid call.
        yield None
        return

    with cm as gen:
        yield gen


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
    to the daily ledger, and emits a Langfuse generation observation with
    the full prompt, response text, model, usage, and cost details.
    """
    api_key = os.environ["OPENROUTER_API_KEY"]
    if estimated_input_tokens == 0:
        estimated_input_tokens = max(len(system) // 4, 1)

    # Conservative pre-cap estimate: assume worst case (no cache hit).
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

    gen_metadata = {
        "phase": phase,
        "max_tokens": max_tokens,
        "estimated_input_tokens": estimated_input_tokens,
    }

    with _generation_observation(
        name=f"openrouter.{phase}",
        model=model,
        input_messages=body["messages"],
        metadata=gen_metadata,
    ) as gen:
        r = httpx.post(OPENROUTER_URL, json=body, headers=headers, timeout=120)
        r.raise_for_status()
        payload = r.json()

        text = payload["choices"][0]["message"]["content"]
        if isinstance(text, list):
            text = "".join(part.get("text", "") for part in text if isinstance(part, dict))

        usage = payload.get("usage", {}) or {}
        cost_entry = llm_cost_post(phase=phase, model=model, usage=usage)
        add_to_today(cost_entry.cost_usd)

        if gen is not None:
            in_tok = cost_entry.input_tokens
            out_tok = cost_entry.output_tokens
            cached = cost_entry.cached_input_tokens
            try:
                gen.update(
                    output=text,
                    model_parameters={"max_tokens": max_tokens},
                    usage_details={
                        "input": max(0, in_tok - cached),
                        "cached_input": cached,
                        "output": out_tok,
                    },
                    cost_details={"total": float(cost_entry.cost_usd)},
                    metadata={**gen_metadata, "raw_usage": usage},
                )
            except Exception:
                # Never let an observation update break the paid call result.
                pass

    return OpenRouterResult(text=text, cost_entry=cost_entry, raw=payload)
