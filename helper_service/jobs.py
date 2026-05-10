import json
import secrets
import os
from datetime import datetime, timezone
from pathlib import Path
from .models import Job, JobStatus


def _jobs_dir() -> Path:
    """Lazily resolve JOBS_DIR to pick up HELPER_DATA_DIR env var on each call."""
    data_dir = Path(os.environ.get("HELPER_DATA_DIR", "/data"))
    return data_dir / "jobs"


def _state_file(jid: str) -> Path:
    """Return the state.json path for a job, resolving JOBS_DIR lazily."""
    return _jobs_dir() / jid / "state.json"


def create_job() -> str:
    """Create a new job with a random ID and return the job ID."""
    jobs_dir = _jobs_dir()
    jobs_dir.mkdir(parents=True, exist_ok=True)
    jid = secrets.token_hex(6)  # 12-char hex
    wd = jobs_dir / jid
    wd.mkdir()
    job = Job(
        job_id=jid,
        status="queued",
        workdir=wd,
        created_at=datetime.now(timezone.utc),
    )
    _state_file(jid).write_text(job.model_dump_json(indent=2))
    return jid


def load_job(jid: str) -> Job:
    """Load a job from its state.json file."""
    return Job.model_validate_json(_state_file(jid).read_text())


def set_status(jid: str, status: JobStatus, **fields) -> None:
    """Update a job's status and optionally other fields."""
    job = load_job(jid)
    data = job.model_dump()
    data["status"] = status
    data.update(fields)
    _state_file(jid).write_text(Job(**data).model_dump_json(indent=2))
