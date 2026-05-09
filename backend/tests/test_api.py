import json
from pathlib import Path

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


def _seed_shipped_run(runs_dir: Path, run_id: str, topic: str, submitted_at: str):
    d = runs_dir / run_id
    d.mkdir(parents=True)
    (d / "state.json").write_text(json.dumps({"status": "completed"}))
    (d / "intent.json").write_text(json.dumps({"topic": topic}))
    (d / "reel_feedback.json").write_text(
        json.dumps({"would_ship": True, "submitted_at": submitted_at})
    )


def test_featured_runs_endpoint_returns_pin_first(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    _seed_shipped_run(tmp_path, "pin", "intro", "2026-05-01T00:00:00+00:00")
    _seed_shipped_run(tmp_path, "live1", "live one", "2026-05-09T00:00:00+00:00")

    client = TestClient(app)
    res = client.get("/api/featured-runs?pin=pin&limit=3")
    assert res.status_code == 200
    body = res.json()
    assert [r["run_id"] for r in body] == ["pin", "live1"]
    assert body[0]["pinned"] is True
    assert body[0]["brief"] == "intro"
    assert body[0]["reel_url"] == "/api/runs/pin/reel.mp4"


def test_featured_runs_endpoint_defaults_limit_to_three(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    for i in range(5):
        _seed_shipped_run(
            tmp_path,
            f"r{i}",
            f"brief {i}",
            f"2026-05-0{i+1}T00:00:00+00:00",
        )

    client = TestClient(app)
    res = client.get("/api/featured-runs")
    assert res.status_code == 200
    assert len(res.json()) == 3
