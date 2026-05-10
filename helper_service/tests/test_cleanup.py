import time, pytest
from pathlib import Path
from helper_service.cleanup import sweep_expired

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JOB_TTL_DAYS", "0")  # immediate expiry

def test_sweep_deletes_expired_jobs(tmp_path):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    old = jobs_dir / "old"; old.mkdir()
    (old / "x").write_text("x")
    sweep_expired()
    assert not old.exists()
