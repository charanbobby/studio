"""ElevenLabs voice-clone TTS with alignment-based caption extraction."""
from __future__ import annotations

import base64
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import httpx

from reel_gen.llm.cost import unit_cost_post
from reel_gen.llm.cost_cap import add_to_today, check_cap
from reel_gen.state import CaptionWord, CostEntry


def _chars_to_words(
    chars: list[str], starts: list[float], ends: list[float]
) -> list[CaptionWord]:
    """Group character-level alignment into word-level CaptionWord items."""
    words: list[CaptionWord] = []
    buf = ""
    word_start: float | None = None
    word_end: float | None = None
    for c, s, e in zip(chars, starts, ends):
        if c.isspace():
            if buf:
                words.append(CaptionWord(text=buf, start_s=word_start or 0.0, end_s=word_end or 0.0))
                buf = ""
                word_start = None
                word_end = None
        else:
            if not buf:
                word_start = s
            buf += c
            word_end = e
    if buf:
        words.append(CaptionWord(text=buf, start_s=word_start or 0.0, end_s=word_end or 0.0))
    return words


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
    ``usage_details`` columns in the Langfuse dashboard, which is what we want
    for paid TTS calls. Mirrors the helper in ``llm.openrouter`` so test
    environments without Langfuse credentials degrade to a no-op rather than
    failing the call.
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


def generate_voiceover(*, text: str, out_dir: Path) -> tuple[Path, list[CaptionWord], CostEntry]:
    voice_id = os.environ["ELEVENLABS_VOICE_ID"]
    api_key = os.environ["ELEVENLABS_API_KEY"]
    chars_used = len(text)

    # Pre-cap check (estimate via published per-character rate).
    from reel_gen.llm.cost import cost_for_units
    est = cost_for_units(provider="elevenlabs", unit_label="tts_chars", units=chars_used)
    check_cap(prospective_cost_usd=est)

    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        f"/with-timestamps?output_format=mp3_44100_128"
    )
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

    gen_input = {
        "text": text,
        "voice_id": voice_id,
        "voice_settings": body["voice_settings"],
    }
    gen_metadata = {
        "phase": "tts",
        "provider": "elevenlabs",
        "voice_id": voice_id,
        "chars": chars_used,
        "unit_label": "tts_chars",
    }

    with _media_generation(
        name="elevenlabs.tts",
        model=body["model_id"],
        input_payload=gen_input,
        metadata=gen_metadata,
    ) as gen:
        r = httpx.post(url, json=body, headers=headers, timeout=120)
        r.raise_for_status()
        payload = r.json()

        out_dir.mkdir(parents=True, exist_ok=True)
        mp3 = out_dir / "voiceover.mp3"
        mp3.write_bytes(base64.b64decode(payload["audio_base64"]))

        align = payload.get("alignment") or {}
        words = _chars_to_words(
            align.get("characters", []),
            align.get("character_start_times_seconds", []),
            align.get("character_end_times_seconds", []),
        )

        cost = unit_cost_post(
            phase="tts", provider="elevenlabs", unit_label="tts_chars", units=chars_used
        )
        add_to_today(cost.cost_usd)

        if gen is not None:
            try:
                gen.update(
                    output={
                        "mp3_path": str(mp3),
                        "mp3_bytes": mp3.stat().st_size,
                        "n_words": len(words),
                        "duration_s": (words[-1].end_s if words else 0.0),
                    },
                    usage_details={"tts_chars": chars_used},
                    cost_details={"total": float(cost.cost_usd)},
                    metadata={**gen_metadata, "cost_usd": float(cost.cost_usd)},
                )
            except Exception:
                pass

    return mp3, words, cost
