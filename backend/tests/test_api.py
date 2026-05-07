from fastapi.testclient import TestClient

from reel_gen.api import app


def test_post_runs_returns_id(monkeypatch, tmp_path):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    client = TestClient(app)
    r = client.post("/api/runs", json={"prompt": "hi", "duration_s": 5, "with_music": False})
    assert r.status_code == 200
    body = r.json()
    assert "run_id" in body


def test_get_runs_lists(monkeypatch, tmp_path):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    client = TestClient(app)
    client.post("/api/runs", json={"prompt": "a", "duration_s": 5, "with_music": False})
    r = client.get("/api/runs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
