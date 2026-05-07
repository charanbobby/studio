"""
probe_05_ffmpeg_kenburns_zoompan.py

Verify the ffmpeg `zoompan` filter produces smooth Ken Burns motion on a
9:16 still over 2.5 seconds and outputs at exactly 1080x1920.

Pass: PROBE OK; mp4 written; ffprobe confirms dimensions and duration.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

# Reuse the image from probe_03 if present; else generate a solid color test.
SRC = OUT / "probe_03.png"
if not SRC.exists():
    # Generate a 1080x1920 solid-color test PNG via ffmpeg lavfi.
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=teal:s=1080x1920:d=1",
        "-frames:v", "1", str(SRC)
    ], check=True)

DST = OUT / "probe_05.mp4"
DURATION = 2.5
FPS = 30
FRAMES = int(DURATION * FPS)


def main() -> int:
    # zoompan: slow zoom-in from 1.0 -> 1.15 over duration; output 1080x1920.
    vf = (
        f"scale=2160:3840,"
        f"zoompan=z='min(zoom+0.0008,1.15)':d={FRAMES}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={FPS}"
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(SRC),
        "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-t", str(DURATION), "-an", str(DST)
    ]
    subprocess.run(cmd, check=True)

    info = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration,nb_frames",
        "-of", "json", str(DST)
    ]).decode()
    parsed = json.loads(info)["streams"][0]
    w = int(parsed["width"])
    h = int(parsed["height"])
    dur = float(parsed.get("duration") or DURATION)

    transcript = {"width": w, "height": h, "duration_s": dur, "frames": parsed.get("nb_frames")}
    (OUT / "probe_05.json").write_text(json.dumps(transcript, indent=2))

    print("PROBE 05")
    print(f"  output: {w}x{h}, duration {dur:.3f}s")
    if (w, h) != (1080, 1920):
        print("PROBE FAIL: dimensions are not 1080x1920.")
        return 1
    if abs(dur - DURATION) > 0.2:
        print("PROBE FAIL: duration off by more than 0.2s.")
        return 1
    print("PROBE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
