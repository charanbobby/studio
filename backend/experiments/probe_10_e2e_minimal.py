"""
probe_10_e2e_minimal.py

Simulate one complete pipeline run with a HARDCODED plan (no LLM call):
- TTS via ElevenLabs
- 2 images via Replicate Flux Schnell
- ffmpeg stitch into a 5s mp4

This is the integration smoke before any LangGraph wiring.

Pass: PROBE OK; experiments/out/probe_10.mp4 exists, plays, is ~5s long
and 1080x1920.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import replicate

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


HARDCODED_PLAN = {
    # ~5s of speech at typical ElevenLabs cadence so the stitched mp4
    # lands inside the 5s +/- 0.4s pass window.
    "voiceover_text": (
        "Sri Studio. Vertical reels in my own voice, generated in just a few "
        "seconds, and ready to post."
    ),
    "scenes": [
        {"idx": 0, "duration_s": 2.5,
         "visual_prompt": "warm minimal coffee shop sunrise, vertical, cinematic"},
        {"idx": 1, "duration_s": 2.5,
         "visual_prompt": "abstract neon studio lights vertical composition cinematic"},
    ],
}


async def gen_image(scene: dict) -> Path:
    # Replicate enforces a 6/min, burst-of-1 rate limit on accounts with
    # less than $5 credit. Retry transient 429s with a small backoff.
    last_err: Exception | None = None
    for attempt in range(5):
        try:
            out = await asyncio.to_thread(
                replicate.run,
                "black-forest-labs/flux-schnell",
                input={
                    "prompt": scene["visual_prompt"],
                    "aspect_ratio": "9:16",
                    "num_outputs": 1,
                    "output_format": "png",
                },
            )
            break
        except replicate.exceptions.ReplicateError as e:
            last_err = e
            if "429" not in str(e):
                raise
            wait = 12 * (attempt + 1)
            print(f"  scene {scene['idx']} 429 throttled, retry in {wait}s")
            await asyncio.sleep(wait)
    else:
        raise RuntimeError(f"replicate retries exhausted: {last_err}")

    first = out[0] if isinstance(out, list) else out
    if hasattr(first, "read"):
        png = first.read()
    else:
        png = httpx.get(str(first), timeout=60).content
    p = OUT / f"probe_10_scene_{scene['idx']:02d}.png"
    p.write_bytes(png)
    return p


def gen_voiceover(text: str) -> Path:
    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/"
        f"{os.environ['ELEVENLABS_VOICE_ID']}"
        f"?output_format=mp3_44100_128"
    )
    r = httpx.post(
        url,
        json={"text": text, "model_id": "eleven_multilingual_v2"},
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        timeout=60,
    )
    r.raise_for_status()
    p = OUT / "probe_10_voice.mp3"
    p.write_bytes(r.content)
    return p


def stitch(images: list[Path], voice: Path, dst: Path, scene_dur: float = 2.5) -> None:
    fps = 30
    frames = int(scene_dur * fps)
    inputs: list[str] = []
    filter_parts: list[str] = []
    for i, img in enumerate(images):
        inputs += ["-loop", "1", "-t", str(scene_dur), "-i", str(img)]
        zoom = 0.0008
        filter_parts.append(
            f"[{i}:v]scale=2160:3840,"
            f"zoompan=z='min(zoom+{zoom},1.15)':d={frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}[v{i}]"
        )
    concat_inputs = "".join(f"[v{i}]" for i in range(len(images)))
    filter_parts.append(f"{concat_inputs}concat=n={len(images)}:v=1:a=0[vout]")
    vf = ";".join(filter_parts)

    voice_idx = len(images)
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-i", str(voice),
        "-filter_complex", vf,
        "-map", "[vout]", "-map", f"{voice_idx}:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(dst)
    ]
    subprocess.run(cmd, check=True)


async def main() -> int:
    print("PROBE 10: starting...")
    # Sequential image generation (Replicate throttles concurrent calls
    # to 1 burst on low-credit accounts; later runs with higher credit
    # can switch to asyncio.gather for parallel generation).
    images: list[Path] = []
    for s in HARDCODED_PLAN["scenes"]:
        images.append(await gen_image(s))
    voice = gen_voiceover(HARDCODED_PLAN["voiceover_text"])

    dst = OUT / "probe_10.mp4"
    stitch(images, voice, dst)

    info = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration",
        "-of", "json", str(dst)
    ]).decode()
    s = json.loads(info)["streams"][0]
    w, h, dur = int(s["width"]), int(s["height"]), float(s.get("duration", 0))
    print(f"  output: {w}x{h}, {dur:.3f}s")
    if (w, h) != (1080, 1920) or abs(dur - 5.0) > 0.4:
        print("PROBE FAIL: dimensions or duration out of bounds.")
        return 1
    print("PROBE OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
