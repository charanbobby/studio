"""ffmpeg stitching: Ken Burns motion per scene, voiceover + ducked music,
burn-in captions from word-level timestamps. 1080x1920 H.264 AAC mp4 out.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from reel_gen.state import CaptionWord, ScriptPlan

FPS = 30


def _ass_timestamp(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - h * 3600 - m * 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _captions_to_ass(captions: list[CaptionWord], group: int = 3) -> str:
    """Group `group` words at a time into one Dialogue line for readability."""
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        "Style: Caption,DejaVu Sans,72,&H00FFFFFF,&H00000000,&H80000000,"
        "1,0,0,0,100,100,0,0,1,5,2,2,40,40,200,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines: list[str] = []
    i = 0
    while i < len(captions):
        chunk = captions[i:i + group]
        text = " ".join(w.text for w in chunk)
        start = chunk[0].start_s
        end = chunk[-1].end_s
        lines.append(
            f"Dialogue: 0,{_ass_timestamp(start)},{_ass_timestamp(end)},"
            f"Caption,,0,0,0,,{text}"
        )
        i += group
    return header + "\n".join(lines) + "\n"


def _motion_filter(motion: str, frames: int) -> str:
    """Animated crop on a pre-scaled image. Avoids zoompan (which silently
    repeats the first input frame when fed a `-loop 1 -t X -i pic.png`
    stream and broke every multi-scene reel).

    ffmpeg's crop filter evaluates w and h ONCE at init, but x and y are
    evaluated per-frame. So "zoom" cannot be done by animating crop size;
    instead we approximate motion via a pan with directional bias. All
    modes produce visible Ken Burns motion across the scene duration.

    Pipeline: scale source to ~1.4x target (1512x2688), crop a fixed
    1080x1920 window whose x/y animate via `t` (input timestamp seconds).
    `t` ranges 0 to duration_s within each looped input.
    """
    duration_s = frames / FPS
    D = max(duration_s, 0.1)
    # Pre-scale so there's room to pan around without exposing edges.
    SCALE_W, SCALE_H = 1512, 2688  # 1.4x target
    PAN_X = SCALE_W - 1080  # 432 px of horizontal slack
    PAN_Y = SCALE_H - 1920  # 768 px of vertical slack

    if motion == "zoom_in":
        # Diagonal pan from a corner toward center (feels like a zoom-in)
        x = f"{PAN_X}*(1-t/{D})/2"
        y = f"{PAN_Y}*(1-t/{D})/2"
    elif motion == "zoom_out":
        # Pan from center outward (feels like zoom-out)
        x = f"{PAN_X}*(t/{D})/2 + {PAN_X}/4"
        y = f"{PAN_Y}*(t/{D})/2 + {PAN_Y}/4"
    elif motion == "pan_left":
        x = f"{PAN_X}*(1-t/{D})"
        y = f"{PAN_Y}/2"
    elif motion == "pan_right":
        x = f"{PAN_X}*t/{D}"
        y = f"{PAN_Y}/2"
    else:  # static
        x = f"{PAN_X}/2"
        y = f"{PAN_Y}/2"

    crop_expr = f"crop=w=1080:h=1920:x='{x}':y='{y}'"
    return f"scale={SCALE_W}:{SCALE_H},{crop_expr},setsar=1,fps={FPS}"


def stitch_reel(
    *,
    plan: ScriptPlan,
    image_paths: list[Path],
    voiceover: Path,
    music: Path | None,
    captions: list[CaptionWord] | None,
    out: Path,
) -> None:
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent
    inputs: list[str] = []
    filter_parts: list[str] = []

    for i, scene in enumerate(plan.scenes):
        # Resolve to absolute so ffmpeg can find inputs regardless of cwd.
        # cwd is overridden to `work` so the `subtitles=` filter can reference
        # captions.ass by its base name (ASS quoting in filter graphs is fiddly).
        img = Path(image_paths[i]).resolve()
        frames = int(scene.duration_s * FPS)
        inputs += ["-loop", "1", "-t", str(scene.duration_s), "-i", str(img)]
        filter_parts.append(f"[{i}:v]{_motion_filter(scene.motion, frames)}[v{i}]")

    concat = "".join(f"[v{i}]" for i in range(len(plan.scenes)))
    filter_parts.append(f"{concat}concat=n={len(plan.scenes)}:v=1:a=0[vbase]")

    if captions:
        ass_path = work / "captions.ass"
        ass_path.write_text(_captions_to_ass(captions))
        filter_parts.append(f"[vbase]subtitles={ass_path.name}[vout]")
    else:
        filter_parts.append(f"[vbase]null[vout]")

    voice_idx = len(plan.scenes)
    inputs += ["-i", str(Path(voiceover).resolve())]

    if music is not None:
        music_idx = voice_idx + 1
        inputs += ["-i", str(Path(music).resolve())]
        filter_parts.append(
            f"[{music_idx}:a]volume=-18dB[mq];"
            f"[{voice_idx}:a][mq]amix=inputs=2:duration=longest:dropout_transition=2[aout]"
        )
        a_map = "[aout]"
    else:
        a_map = f"{voice_idx}:a"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "[vout]", "-map", a_map,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-shortest", str(out),
    ]
    subprocess.run(cmd, check=True, cwd=str(work))
