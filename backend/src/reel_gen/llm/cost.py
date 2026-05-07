"""Cost helpers per global CLAUDE.md hard rule:
print cost pre/post EVERY paid API call.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from reel_gen.state import CostEntry

# Per 1M tokens, USD. Update when model versions change.
RATES: dict[str, dict[str, float]] = {
    "anthropic/claude-sonnet-4-6": {
        "input_per_mtok": 3.00,
        "output_per_mtok": 15.00,
        "cache_read_per_mtok": 0.30,
    },
    "anthropic/claude-haiku-4-5": {
        "input_per_mtok": 0.80,
        "output_per_mtok": 4.00,
        "cache_read_per_mtok": 0.08,
    },
}

# Per-unit pricing for non-token APIs.
UNIT_RATES: dict[tuple[str, str], float] = {
    ("replicate", "images"): 0.003,
    ("elevenlabs", "tts_chars"): 0.00030,
    ("elevenlabs", "music_seconds"): 0.005,
}


def cost_for_llm_usage(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float | None:
    """Returns USD cost or None when the model is unknown.

    Per global CLAUDE.md: never silently skip an unknown rate.
    """
    rate = RATES.get(model)
    if rate is None:
        return None
    fresh_in = max(0, input_tokens - cached_input_tokens)
    cost = (
        (fresh_in / 1_000_000) * rate["input_per_mtok"]
        + (output_tokens / 1_000_000) * rate["output_per_mtok"]
        + (cached_input_tokens / 1_000_000) * rate.get("cache_read_per_mtok", rate["input_per_mtok"])
    )
    return round(cost, 6)


def cost_for_units(*, provider: str, unit_label: str, units: float) -> float:
    rate = UNIT_RATES.get((provider, unit_label))
    if rate is None:
        return 0.0
    return round(units * rate, 6)


def llm_cost_pre(*, phase: str, model: str, input_tokens_estimate: int) -> None:
    """Print PRE-call cost estimate."""
    rate = RATES.get(model)
    if rate is None:
        print(f"[COST PRE] phase={phase} model={model} rate=unknown "
              f"input_est={input_tokens_estimate}")
        return
    est = (input_tokens_estimate / 1_000_000) * rate["input_per_mtok"]
    print(f"[COST PRE] phase={phase} model={model} input_est={input_tokens_estimate} "
          f"est_cost=${est:.4f}")


def llm_cost_post(
    *,
    phase: str,
    model: str,
    usage: dict[str, Any],
) -> CostEntry:
    """Print POST-call actuals and return a CostEntry for the ledger."""
    in_tok = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    out_tok = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    cached = int(
        (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
        or usage.get("cache_read_input_tokens", 0)
    )
    cost = cost_for_llm_usage(
        model=model, input_tokens=in_tok, output_tokens=out_tok, cached_input_tokens=cached
    )
    cost_str = "rate-unknown" if cost is None else f"${cost:.6f}"
    print(f"[COST POST] phase={phase} model={model} "
          f"in={in_tok} out={out_tok} cached={cached} cost={cost_str}")
    return CostEntry(
        phase=phase,
        provider="openrouter",
        model=model,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cached_input_tokens=cached,
        cost_usd=(cost or 0.0),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def unit_cost_post(
    *,
    phase: str,
    provider: str,
    unit_label: str,
    units: float,
) -> CostEntry:
    cost = cost_for_units(provider=provider, unit_label=unit_label, units=units)
    print(f"[COST POST] phase={phase} provider={provider} "
          f"{unit_label}={units} cost=${cost:.6f}")
    return CostEntry(
        phase=phase,
        provider=provider,
        units=units,
        unit_label=unit_label,
        cost_usd=cost,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
