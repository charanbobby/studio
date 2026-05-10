from datetime import datetime
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict

JobStatus = Literal[
    "queued", "recording", "captioning", "awaiting_review",
    "voice_generating", "muxing", "done", "failed", "voice_failed",
]

class Job(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    job_id: str
    status: JobStatus
    workdir: Path
    created_at: datetime
    error: str | None = None
    estimate_usd: float | None = None
    actual_usd: float | None = None
