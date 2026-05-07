"""
probe_02_elevenlabs_voiceclone_tts.py

Verify the user's cloned voice ID accepts text and returns MP3 plus
alignment timestamps that we can use for burn-in captions.

Pass: PROBE OK; mp3 file written; alignment array length matches text;
total alignment span is within 0.5s of the audio file's duration.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

API_KEY = os.environ["ELEVENLABS_API_KEY"]
VOICE_ID = os.environ["ELEVENLABS_VOICE_ID"]
TEXT = "Sri Studio is a tiny tool that makes vertical reels in my own voice."


def main() -> int:
    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        f"/with-timestamps?output_format=mp3_44100_128"
    )
    body = {
        "text": TEXT,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    headers = {"xi-api-key": API_KEY, "Content-Type": "application/json"}
    r = httpx.post(url, json=body, headers=headers, timeout=60)
    r.raise_for_status()
    payload = r.json()

    audio_b64 = payload["audio_base64"]
    alignment = payload.get("alignment") or {}
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []

    import base64
    mp3_path = OUT / "probe_02.mp3"
    mp3_path.write_bytes(base64.b64decode(audio_b64))

    # Duration via ffprobe.
    dur = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(mp3_path)
    ]).decode().strip()
    audio_dur = float(dur)
    align_span = ends[-1] if ends else 0.0

    transcript = {
        "text": TEXT,
        "char_count": len(chars),
        "audio_duration_s": audio_dur,
        "alignment_span_s": align_span,
        "alignment_chars_first_10": chars[:10],
        "starts_first_10": starts[:10],
        "ends_first_10": ends[:10],
    }
    (OUT / "probe_02.json").write_text(json.dumps(transcript, indent=2))

    print("PROBE 02")
    print(f"  text length:        {len(TEXT)}")
    print(f"  alignment chars:    {len(chars)}")
    print(f"  audio duration:     {audio_dur:.3f}s")
    print(f"  alignment span:     {align_span:.3f}s")
    print(f"  delta:              {abs(audio_dur - align_span):.3f}s")
    if abs(audio_dur - align_span) > 0.5:
        print("PROBE FAIL: alignment span vs audio duration off by > 0.5s.")
        return 1
    if len(chars) < len(TEXT) - 5:
        print("PROBE FAIL: alignment chars far short of text length.")
        return 1
    print("PROBE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
