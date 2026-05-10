import pytest
from helper_service.jobs import create_job, load_job, set_status

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))

def test_create_job_returns_id_and_creates_workdir():
    jid = create_job()
    assert isinstance(jid, str) and len(jid) >= 8
    job = load_job(jid)
    assert job.status == "queued"
    assert job.workdir.exists()

def test_set_status_persists():
    jid = create_job()
    set_status(jid, "recording")
    assert load_job(jid).status == "recording"
