import json
from pathlib import Path

from reel_gen.featured import FeaturedRun, list_featured_runs


def _seed_run(
    runs_dir: Path,
    run_id: str,
    *,
    status: str = "completed",
    would_ship: bool = True,
    topic: str = "a brief",
    submitted_at: str = "2026-05-09T12:00:00+00:00",
) -> Path:
    """Create a fake run dir with the three JSON files the selector reads."""
    d = runs_dir / run_id
    d.mkdir(parents=True)
    (d / "state.json").write_text(json.dumps({"status": status}))
    (d / "intent.json").write_text(json.dumps({"topic": topic}))
    (d / "reel_feedback.json").write_text(
        json.dumps({"would_ship": would_ship, "submitted_at": submitted_at})
    )
    return d


def test_featured_run_model_round_trips():
    payload = {
        "run_id": "abc123",
        "brief": "A 5-second teaser",
        "reel_url": "/api/runs/abc123/reel.mp4",
        "completed_at": "2026-05-09T16:32:06.334493+00:00",
        "pinned": False,
    }
    fr = FeaturedRun.model_validate(payload)
    assert fr.run_id == "abc123"
    assert fr.pinned is False
    assert fr.model_dump() == payload


def test_featured_run_completed_at_optional():
    fr = FeaturedRun(
        run_id="x",
        brief="b",
        reel_url="/r",
        completed_at=None,
        pinned=True,
    )
    assert fr.completed_at is None


def test_empty_runs_dir_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    assert list_featured_runs(pin=None, limit=3) == []


def test_only_completed_and_would_ship_returned(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    _seed_run(tmp_path, "good", status="completed", would_ship=True)
    _seed_run(tmp_path, "rejected", status="completed", would_ship=False)
    _seed_run(tmp_path, "failed", status="failed", would_ship=True)

    out = list_featured_runs(pin=None, limit=3)
    ids = [r.run_id for r in out]
    assert ids == ["good"]
    assert out[0].brief == "a brief"
    assert out[0].reel_url == "/api/runs/good/reel.mp4"
    assert out[0].pinned is False


def test_missing_feedback_file_excluded(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    d = tmp_path / "no_feedback"
    d.mkdir()
    (d / "state.json").write_text(json.dumps({"status": "completed"}))
    (d / "intent.json").write_text(json.dumps({"topic": "x"}))
    # no reel_feedback.json on purpose

    assert list_featured_runs(pin=None, limit=3) == []


def test_newest_first_by_submitted_at(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    _seed_run(tmp_path, "older", submitted_at="2026-05-01T00:00:00+00:00")
    _seed_run(tmp_path, "newer", submitted_at="2026-05-09T00:00:00+00:00")
    _seed_run(tmp_path, "middle", submitted_at="2026-05-05T00:00:00+00:00")

    out = list_featured_runs(pin=None, limit=3)
    assert [r.run_id for r in out] == ["newer", "middle", "older"]
