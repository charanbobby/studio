import pytest, io, tarfile, json
from fastapi.testclient import TestClient
from helper_service.api import app

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HELPER_AUTH_KEY", "test-key")
    monkeypatch.setenv("DAILY_BUDGET_USD", "5.0")

@pytest.fixture
def client(): return TestClient(app)

@pytest.fixture
def auth(): return {"X-Helper-Key": "test-key"}

def test_health_returns_ok_status(client, auth):
    r = client.get("/helper/health", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "daily_budget_remaining_usd" in body

def test_skill_returns_markdown(client, auth, tmp_path, monkeypatch):
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text("# Test SKILL\n")
    monkeypatch.setenv("HELPER_SKILL_PATH", str(skill_path))
    r = client.get("/helper/skill", headers=auth)
    assert r.status_code == 200
    assert "Test SKILL" in r.text

def test_samples_returns_empty_list_initially(client):
    # public endpoint, no auth header
    r = client.get("/helper/samples")
    assert r.status_code == 200
    assert r.json() == []

def test_post_jobs_requires_auth(client):
    r = client.post("/helper/jobs", files={"project": ("p.tar.gz", b"x")})
    assert r.status_code == 401
