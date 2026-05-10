import asyncio, os, shutil, time
from pathlib import Path

def _jobs_dir() -> Path:
    """Lazily resolve JOBS_DIR to pick up HELPER_DATA_DIR env var on each call."""
    data_dir = Path(os.environ.get("HELPER_DATA_DIR", "/data"))
    return data_dir / "jobs"

async def cleanup_loop(interval_s: int = 3600):
    while True:
        try:
            sweep_expired()
        except Exception as e:
            print(f"[cleanup] error: {e}")
        await asyncio.sleep(interval_s)

def sweep_expired() -> None:
    jobs_dir = _jobs_dir()
    if not jobs_dir.exists(): return
    ttl_days = float(os.environ.get("JOB_TTL_DAYS", "7"))
    cutoff = time.time() - ttl_days * 86400
    for d in jobs_dir.iterdir():
        if d.is_dir() and d.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)
