"""
probe_03_replicate_flux_schnell_9x16.py

Verify Flux Schnell on Replicate honors aspect_ratio="9:16" and returns an
image we can pass to ffmpeg.

Pass: PROBE OK; png file written; image dimensions are 9:16-shaped.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
import replicate

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

os.environ["REPLICATE_API_TOKEN"] = os.environ["REPLICATE_API_TOKEN"]


def main() -> int:
    output = replicate.run(
        "black-forest-labs/flux-schnell",
        input={
            "prompt": "a cozy minimalist coffee shop at sunrise, warm light, "
                      "soft focus, vertical composition, cinematic",
            "aspect_ratio": "9:16",
            "num_outputs": 1,
            "output_format": "png",
            "output_quality": 90,
        },
    )

    # replicate.run returns a list of FileOutput objects in newer SDK versions;
    # fall back to URL strings for older shape.
    first = output[0] if isinstance(output, list) else output
    if hasattr(first, "read"):
        png_bytes = first.read()
    else:
        png_bytes = httpx.get(str(first), timeout=60).content

    img_path = OUT / "probe_03.png"
    img_path.write_bytes(png_bytes)

    # Dimensions via ffprobe.
    import subprocess
    info = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0", str(img_path)
    ]).decode().strip()
    w_str, h_str = info.split("x")
    w, h = int(w_str), int(h_str)
    ratio = w / h
    expected = 9 / 16

    transcript = {"width": w, "height": h, "ratio": ratio, "expected": expected}
    (OUT / "probe_03.json").write_text(json.dumps(transcript, indent=2))

    print("PROBE 03")
    print(f"  dimensions: {w}x{h}")
    print(f"  ratio:      {ratio:.4f} (expected {expected:.4f})")
    if abs(ratio - expected) > 0.05:
        print("PROBE FAIL: aspect ratio off by more than 5 percent.")
        return 1
    print("PROBE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
