"""Featured-runs selection for the homepage.

Pure helper module: walks the runs directory, applies filters, returns a
small list of FeaturedRun records. No FastAPI imports so unit tests stay
fast and don't need the app context.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel


class FeaturedRun(BaseModel):
    run_id: str
    brief: str
    reel_url: str
    completed_at: str | None = None
    pinned: bool = False


def _runs_dir() -> Path:
    """Mirror api.py's RUNS_DIR convention so tests can monkeypatch it."""
    return Path(os.environ.get("RUNS_DIR", "./runs"))


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def list_featured_runs(pin: str | None, limit: int) -> list[FeaturedRun]:
    candidates: list[FeaturedRun] = []
    base = _runs_dir()
    if not base.exists():
        return []

    for run_dir in sorted(base.iterdir()):
        if not run_dir.is_dir():
            continue
        state = _load_json(run_dir / "state.json", default={})
        if state.get("status") != "completed":
            continue
        feedback = _load_json(run_dir / "reel_feedback.json", default=None)
        if not feedback or not feedback.get("would_ship"):
            continue
        intent = _load_json(run_dir / "intent.json", default={})
        candidates.append(
            FeaturedRun(
                run_id=run_dir.name,
                brief=intent.get("topic", ""),
                reel_url=f"/api/runs/{run_dir.name}/reel.mp4",
                completed_at=feedback.get("submitted_at"),
                pinned=False,
            )
        )

    return candidates[: max(0, limit)]
