from reel_gen.featured import FeaturedRun


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
