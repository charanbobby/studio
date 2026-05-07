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
    if motion == "static":
        return f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    direction = {
        "zoom_in":  "z='min(zoom+0.0008,1.15)'",
        "zoom_out": "z='if(eq(on,0),1.15,max(zoom-0.0008,1.0))'",
        "pan_left": "z='1.1'",
        "pan_right": "z='1.1'",
    }.get(motion, "z='min(zoom+0.0008,1.15)'")
    pan_x = {
        "pan_left":  "x='iw-(iw/zoom)-on*((iw-iw/zoom)/" + str(frames) + ")'",
        "pan_right": "x='on*((iw-iw/zoom)/" + str(frames) + ")'",
    }.get(motion, "x='iw/2-(iw/zoom/2)'")
    pan_y = "y='ih/2-(ih/zoom/2)'"
    return (
        f"scale=2160:3840,zoompan={direction}:d={frames}:{pan_x}:{pan_y}:s=1080x1920:fps={FPS}"
    )


def stitch_reel(
    *,
    plan: ScriptPlan,
    image_paths: list[Path],
    voiceover: Path,
    music: Path | None,
    captions: list[CaptionWord] | None,
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent
    inputs: list[str] = []
    filter_parts: list[str] = []

    for i, scene in enumerate(plan.scenes):
        img = image_paths[i]
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
        filter_parts.append(f"[vbase]copy[vout]")

    voice_idx = len(plan.scenes)
    inputs += ["-i", str(voiceover)]

    if music is not None:
        music_idx = voice_idx + 1
        inputs += ["-i", str(music)]
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
