"""Replicate Flux Schnell client with NSFW + 429 retry-with-backoff."""
from __future__ import annotations

import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import httpx
import replicate

from reel_gen.llm.cost import unit_cost_post
from reel_gen.llm.cost_cap import add_to_today, check_cap
from reel_gen.state import CostEntry

_RISKY = re.compile(r"\b(swimsuit|bikini|nude|naked|skin|body|sensual|sexy)\b", re.IGNORECASE)
_FLUX_MODEL = "black-forest-labs/flux-schnell"


def _safer_prompt(prompt: str) -> str:
    return _RISKY.sub("clothed", prompt)


def _download(out_obj) -> bytes:
    if hasattr(out_obj, "read"):
        return out_obj.read()
    return httpx.get(str(out_obj), timeout=60).content


def _is_nsfw_error(err: Exception) -> bool:
    m = str(err).lower()
    return any(s in m for s in ("nsfw", "moderation", "safety"))


def _is_rate_limit(err: Exception) -> bool:
    m = str(err).lower()
    return ("429" in m) or ("rate limit" in m) or ("too many requests" in m)


def _call(prompt: str):
    return replicate.run(
        _FLUX_MODEL,
        input={
            "prompt": prompt, "aspect_ratio": "9:16",
            "num_outputs": 1, "output_format": "png", "output_quality": 90,
        },
    )


@contextmanager
def _media_generation(
    *,
    name: str,
    model: str,
    input_payload: dict[str, Any],
    metadata: dict[str, Any],
) -> Iterator[Any]:
    """Yield a Langfuse generation handle for paid media calls, or None if unavailable.

    Generation observations (vs span) surface ``cost_details`` and
    ``usage_details`` columns in the Langfuse dashboard.
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
            input=input_payload,
            metadata=metadata,
        )
    except Exception:
        yield None
        return

    with cm as gen:
        yield gen


def generate_image(
    *, prompt: str, out_dir: Path, scene_idx: int, retry_on_nsfw: bool = True,
    rate_limit_retries: int = 5, rate_limit_backoff_s: float = 12.0,
) -> tuple[Path, CostEntry]:
    os.environ["REPLICATE_API_TOKEN"] = os.environ["REPLICATE_API_TOKEN"]

    # Pre-cap check ($0.003 per image).
    from reel_gen.llm.cost import cost_for_units
    est = cost_for_units(provider="replicate", unit_label="images", units=1)
    check_cap(prospective_cost_usd=est)

    gen_input = {
        "prompt": prompt,
        "aspect_ratio": "9:16",
        "scene_idx": scene_idx,
    }
    gen_metadata = {
        "phase": "image",
        "scene_idx": scene_idx,
        "provider": "replicate",
        "unit_label": "images",
    }

    with _media_generation(
        name="replicate.flux_schnell",
        model=_FLUX_MODEL,
        input_payload=gen_input,
        metadata=gen_metadata,
    ) as gen:
        current_prompt = prompt
        last_err: Exception | None = None
        nsfw_retried = False
        for attempt in range(rate_limit_retries + 1):
            try:
                try:
                    out = _call(current_prompt)
                except Exception as e:
                    if retry_on_nsfw and _is_nsfw_error(e):
                        current_prompt = _safer_prompt(current_prompt)
                        nsfw_retried = True
                        out = _call(current_prompt)
                    else:
                        raise
                break
            except Exception as e:
                last_err = e
                if _is_rate_limit(e) and attempt < rate_limit_retries:
                    wait = rate_limit_backoff_s * (1 + attempt)
                    time.sleep(wait)
                    continue
                if gen is not None:
                    try:
                        gen.update(level="ERROR", status_message=repr(e))
                    except Exception:
                        pass
                raise
        else:
            if last_err:
                if gen is not None:
                    try:
                        gen.update(level="ERROR", status_message=repr(last_err))
                    except Exception:
                        pass
                raise last_err

        first = out[0] if isinstance(out, list) else out
        png_bytes = _download(first)

        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / f"scene_{scene_idx:02d}.png"
        p.write_bytes(png_bytes)

        cost = unit_cost_post(phase="image", provider="replicate", unit_label="images", units=1)
        add_to_today(cost.cost_usd)

        if gen is not None:
            try:
                gen.update(
                    output={
                        "png_path": str(p),
                        "size_bytes": p.stat().st_size,
                        "final_prompt": current_prompt,
                        "nsfw_retried": nsfw_retried,
                    },
                    usage_details={"images": 1},
                    cost_details={"total": float(cost.cost_usd)},
                    metadata={**gen_metadata, "cost_usd": float(cost.cost_usd)},
                )
            except Exception:
                pass

    return p, cost
