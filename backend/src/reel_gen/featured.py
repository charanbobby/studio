"""Featured-runs selection for the homepage.

Pure helper module: walks the runs directory, applies filters, returns a
small list of FeaturedRun records. No FastAPI imports so unit tests stay
fast and don't need the app context.
"""
from __future__ import annotations

from pydantic import BaseModel


class FeaturedRun(BaseModel):
    run_id: str
    brief: str
    reel_url: str
    completed_at: str | None = None
    pinned: bool = False
