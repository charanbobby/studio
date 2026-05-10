"""Centralized filesystem paths used by the service."""
from pathlib import Path
import os

DATA_DIR    = Path(os.environ.get("HELPER_DATA_DIR", "/data"))
JOBS_DIR    = DATA_DIR / "jobs"
SAMPLES_DIR = DATA_DIR / "samples"
SPEND_FILE  = DATA_DIR / "spend.json"
AUDIT_LOG   = DATA_DIR / "audit.log"

def job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id

def sample_dir(job_id: str) -> Path:
    return SAMPLES_DIR / job_id
