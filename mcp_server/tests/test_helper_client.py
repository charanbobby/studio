import pytest, respx, httpx
from mcp_server.helper_client import HelperClient

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("HELPER_BASE_URL", "http://test.local")
    monkeypatch.setenv("HELPER_AUTH_KEY", "k")
    return HelperClient()

@respx.mock
def test_post_jobs_sends_auth_header(client):
    route = respx.post("http://test.local/helper/jobs").mock(
        return_value=httpx.Response(200, json={"job_id": "abc",
                                                "preview_url": "/p", "estimate_usd": 0.05,
                                                "status": "awaiting_review"}))
    out = client.post_silent(b"fake-tar")
    assert route.called
    assert route.calls[0].request.headers["X-Helper-Key"] == "k"
    assert out["job_id"] == "abc"

@respx.mock
def test_post_voice_returns_final_url(client):
    respx.post("http://test.local/helper/jobs/abc/voice").mock(
        return_value=httpx.Response(200, json={"final_url": "/f", "status": "done"}))
    out = client.post_voice("abc")
    assert out["final_url"] == "/f"

@respx.mock
def test_get_skill_returns_text(client):
    respx.get("http://test.local/helper/skill").mock(
        return_value=httpx.Response(200, text="# SKILL"))
    assert "SKILL" in client.get_skill()

@respx.mock
def test_402_raises_BudgetExceeded(client):
    from mcp_server.helper_client import BudgetExceeded
    respx.post("http://test.local/helper/jobs/abc/voice").mock(
        return_value=httpx.Response(402, json={"detail": {"reason": "would_exceed_daily_cap",
                                                            "remaining": 0.1, "needed": 0.5}}))
    with pytest.raises(BudgetExceeded) as e:
        client.post_voice("abc")
    assert e.value.remaining == 0.1
