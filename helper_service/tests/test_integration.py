import io, tarfile, pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from helper_service.api import app

FIX = Path(__file__).parent / "fixtures" / "tiny_demo"

def make_tar() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        tf.add(FIX, arcname=".")
    return buf.getvalue()

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HELPER_AUTH_KEY", "k")
    monkeypatch.setenv("DAILY_BUDGET_USD", "5")

@patch("helper_service.runner._run_probes")
@patch("helper_service.runner._record_beats")
@patch("helper_service.runner._concat_silent")
@patch("helper_service.runner._burn_captions")
@patch("helper_service.runner._generate_voice", return_value=0.0044)
@patch("helper_service.runner._final_mux")
def test_happy_path_silent_then_voice(mux, voice, burn, concat, rec, probes):
    client = TestClient(app)
    auth = {"X-Helper-Key": "k"}
    r = client.post("/helper/jobs", files={"project": ("p.tar.gz", make_tar())},
                    headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "awaiting_review"
    assert "estimate_usd" in body
    jid = body["job_id"]

    r2 = client.post(f"/helper/jobs/{jid}/voice", headers=auth)
    assert r2.status_code == 200
    assert r2.json()["status"] == "done"
