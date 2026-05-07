"""
probe_04_replicate_flux_nsfw_behavior.py

Document what Replicate Flux Schnell does on a borderline prompt: does it
raise an exception, return a placeholder URL, or return a blank image?

Output: a transcript JSON we can match against in execute_images.py for
the retry-with-rewrite path. This probe always exits 0; it is documentation.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

import replicate

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

# Borderline-but-legal-content prompt designed to trigger the moderation
# filter without being actively offensive. Adjust if Replicate's filter
# changes shape.
BORDERLINE = "a person in a swimsuit on a beach at sunset, photorealistic"


def main() -> int:
    transcript: dict = {"prompt": BORDERLINE}
    try:
        out = replicate.run(
            "black-forest-labs/flux-schnell",
            input={
                "prompt": BORDERLINE,
                "aspect_ratio": "9:16",
                "num_outputs": 1,
                "output_format": "png",
                "disable_safety_checker": False,
            },
        )
        first = out[0] if isinstance(out, list) else out
        transcript["result"] = "succeeded"
        transcript["first_value"] = str(first)
    except Exception as e:
        transcript["result"] = "raised"
        transcript["exception_class"] = type(e).__name__
        transcript["exception_str"] = str(e)
        transcript["traceback"] = traceback.format_exc()

    (OUT / "probe_04.json").write_text(json.dumps(transcript, indent=2))
    print("PROBE 04 (documentation only)")
    print(json.dumps(transcript, indent=2)[:1000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
