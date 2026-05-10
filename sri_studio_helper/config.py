"""Project-specific constants.

REPLACE the values below for your project. The runner, voice-gen, and
assembly scripts read this module to find the target site, beat durations,
output dir, and any project-specific identifiers (e.g. a rule_id you click
in one of the scenes).

Pattern: do not hardcode anything project-specific in scenes/ or runners.
Always pull from here.
"""
from pathlib import Path

# REPLACE: the site you are recording against.
SITE_URL = "https://example.com"

# REPLACE: any project-specific case ids, run ids, rule ids that scenes need.
# Examples (drop or add as your project requires):
# CASE_ID = "demo-case"
# RUN_ID = "demo-case-001"
# RULE_ID_FOR_PROMOTE = "some-rule-uuid"

# Recording settings. Usually you do not change these.
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
FRAMERATE = 30

# Beat duration budget in seconds. The keys here MUST match the scene module
# names (e.g. "beat1_open" -> sri_studio_helper/scenes/beat1_open.py).
# Total must equal the target video length (e.g. 300 for a 5-minute video).
DURATIONS = {
    # REPLACE with your beats. Example skeleton:
    "beat1_open": 15,
    "beat2_body": 270,
    "beat3_outro": 15,
}
assert sum(DURATIONS.values()) > 0, "DURATIONS dict is empty; define your beats"

# Output directory for generated MP4s, SRT, and voice MP3s. Defaults to
# ../out under this package's parent. Override with env var if needed.
import os
OUT_DIR = Path(os.environ.get(
    "SSH_OUT_DIR",
    str(Path(__file__).resolve().parents[1] / "out"),
))
OUT_DIR.mkdir(parents=True, exist_ok=True)
