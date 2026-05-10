import pytest
from unittest.mock import patch
from helper_service.runner import run_silent_phases

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))

@patch("helper_service.runner._run_probes", return_value=None)
@patch("helper_service.runner._record_beats", return_value=None)
@patch("helper_service.runner._concat_silent", return_value=None)
@patch("helper_service.runner._burn_captions", return_value=None)
def test_silent_phases_set_status_to_awaiting_review(probes, rec, concat, burn, tmp_path):
    from helper_service.jobs import create_job, load_job
    jid = create_job()
    run_silent_phases(jid, beats=[{"name": "intro", "voiceover": "hi"}])
    assert load_job(jid).status == "awaiting_review"
    assert load_job(jid).estimate_usd is not None
