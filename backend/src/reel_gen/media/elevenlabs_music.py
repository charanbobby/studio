"""ElevenLabs Music generation. Returns MP3 path + CostEntry."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import httpx

from reel_gen.llm.cost import cost_for_units, unit_cost_post
from reel_gen.llm.cost_cap import add_to_today, check_cap
from reel_gen.state import CostEntry


@contextmanager
def _media_generation(
    *,
    name: str,
    model: str,
    input_payload: dict[str, Any],
    metadata: dict[str, Any],
) -> Iterator[Any]:
    """Yield a Langfuse generation handle for paid media calls, or None if unavailable.

    Mirrors the helper in ``elevenlabs_tts`` so test environments without
    Langfuse credentials degrade to a no-op rather than failing the call.
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


def generate_music(
    *, mood: str, duration_s: float, out_dir: Path
) -> tuple[Path, CostEntry] | None:
    """Generate a music bed via ElevenLabs Music. Returns (path, cost) or None on failure.

    Soft-fails (returns None) on auth/plan/availability errors so the pipeline
    degrades to silent. Hard errors (network, 5xx) bubble up to the caller,
    which logs as a non-fatal NodeError.
    """
    api_key = os.environ["ELEVENLABS_API_KEY"]

    # Pre-cap check ($0.005 per second per cost.UNIT_RATES).
    est = cost_for_units(provider="elevenlabs", unit_label="music_seconds", units=duration_s)
    print(
        f"[COST PRE] phase=music provider=elevenlabs music_seconds={duration_s} "
        f"est_cost=${est:.6f}"
    )
    check_cap(prospective_cost_usd=est)

    url = "https://api.elevenlabs.io/v1/music"
    body = {
        "prompt": mood,
        "music_length_ms": int(duration_s * 1000),
        "model_id": "music_v1",
    }
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

    gen_input = {"prompt": mood, "duration_s": duration_s}
    gen_metadata = {
        "phase": "music",
        "provider": "elevenlabs",
        "duration_s": duration_s,
        "unit_label": "music_seconds",
    }

    with _media_generation(
        name="elevenlabs.music",
        model="music_v1",
        input_payload=gen_input,
        metadata=gen_metadata,
    ) as gen:
        try:
            r = httpx.post(url, json=body, headers=headers, timeout=180)
        except httpx.HTTPError as e:
            print(f"[MUSIC] network error, degrading to silent: {e}")
            return None

        # Soft-fail on auth / plan / availability / not-found so reels still ship.
        if r.status_code in (401, 402, 403, 404):
            print(
                f"[MUSIC] gracefully degrading: HTTP {r.status_code} "
                f"body={r.text[:200]!r}"
            )
            return None
        r.raise_for_status()

        out_dir.mkdir(parents=True, exist_ok=True)
        mp3 = out_dir / "music.mp3"
        ctype = r.headers.get("content-type", "")
        if "json" in ctype:
            payload = r.json()
            audio_url = payload.get("audio_url") or payload.get("download_url")
            if not audio_url:
                print(f"[MUSIC] JSON response without audio_url: keys={list(payload)}")
                return None
            r2 = httpx.get(audio_url, timeout=180)
            r2.raise_for_status()
            mp3.write_bytes(r2.content)
        else:
            mp3.write_bytes(r.content)

        cost = unit_cost_post(
            phase="music",
            provider="elevenlabs",
            unit_label="music_seconds",
            units=duration_s,
        )
        add_to_today(cost.cost_usd)

        if gen is not None:
            try:
                gen.update(
                    output={
                        "mp3_path": str(mp3),
                        "mp3_bytes": mp3.stat().st_size,
                    },
                    usage_details={"music_seconds": duration_s},
                    cost_details={"total": float(cost.cost_usd)},
                    metadata={**gen_metadata, "cost_usd": float(cost.cost_usd)},
                )
            except Exception:
                pass

        return mp3, cost
