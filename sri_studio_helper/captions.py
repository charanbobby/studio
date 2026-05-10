"""Per-beat voiceover script. ALSO the source of truth for burned-in captions.

Caption text MUST equal voiceover text. The voice generated in Phase E reads
this same string, so the burned-in caption can never drift from what the
narrator actually says.

REPLACE the BEATS list below for your project. Each entry:
    name           matches a scenes/<name>.py module
    start_s        cumulative offset in seconds (beat1 starts at 0)
    duration_s     beat length, must match config.DURATIONS[name]
    voiceover      the line to be both spoken AND captioned
"""
from __future__ import annotations


BEATS = [
    # REPLACE: your beats. Example skeleton:
    {
        "name": "beat1_open",
        "start_s": 0,
        "duration_s": 15,
        "voiceover": (
            "Replace this voiceover text with your project's opening line. "
            "Keep it under 40 words for a 15-second beat."
        ),
    },
    {
        "name": "beat2_body",
        "start_s": 15,
        "duration_s": 270,
        "voiceover": (
            "Replace this with the body of your demo. Speak conversationally; "
            "the caption text and voice are the same string."
        ),
    },
    {
        "name": "beat3_outro",
        "start_s": 285,
        "duration_s": 15,
        "voiceover": (
            "Replace with your closing line. URLs, credit, thank you."
        ),
    },
]


def _split_into_lines(text: str, max_chars: int = 80) -> list[str]:
    """Greedy word-wrap, preferring 2-line blocks under max_chars each."""
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for w in words:
        candidate = " ".join(current + [w])
        if len(candidate) <= max_chars:
            current.append(w)
        else:
            lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines


def _hms(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(lead_in_s: float = 2.0, max_chars: int = 80) -> str:
    """Build an SRT string covering all beats. Each beat's voiceover is
    split into ~80-char lines and distributed evenly across the beat duration,
    leaving a 0.3s gap between cues so they do not overlap visually.

    The first beat gets a `lead_in_s` second silence at the start so the
    cold open frame has a moment to breathe before the first caption appears.
    """
    cues: list[tuple[float, float, str]] = []
    for beat in BEATS:
        text = beat["voiceover"]
        lines = _split_into_lines(text, max_chars=max_chars)
        windows = [lines[i:i + 2] for i in range(0, len(lines), 2)]
        n = len(windows)
        if n == 0:
            continue
        is_first = (beat is BEATS[0])
        beat_start = beat["start_s"] + (lead_in_s if is_first else 0)
        beat_end = beat["start_s"] + beat["duration_s"]
        avail = max(0.5, beat_end - beat_start - 0.3)
        per = avail / n
        for i, window in enumerate(windows):
            t0 = beat_start + i * per
            t1 = t0 + per - 0.3
            cues.append((t0, t1, "\n".join(window)))

    out_parts: list[str] = []
    for idx, (t0, t1, text) in enumerate(cues, start=1):
        out_parts.append(f"{idx}\n{_hms(t0)} --> {_hms(t1)}\n{text}\n")
    return "\n".join(out_parts)


if __name__ == "__main__":
    from .config import OUT_DIR
    srt_path = OUT_DIR / "captions.srt"
    srt_path.write_text(build_srt(), encoding="utf-8")
    print(f"wrote {srt_path}")
