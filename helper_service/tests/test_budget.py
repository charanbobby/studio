import json, os
import pytest
from helper_service.budget import estimate, remaining_today, gate_voice, record_spend
from fastapi import HTTPException

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_BUDGET_USD", "1.0")
    monkeypatch.setenv("ELEVENLABS_USD_PER_CHAR", "0.001")  # 1000 chars = $1
    yield

def test_estimate_sums_voiceover_chars():
    beats = [{"voiceover": "abc"}, {"voiceover": "defgh"}]
    assert estimate(beats) == pytest.approx(0.008)  # 8 chars * 0.001

def test_remaining_today_starts_at_full_budget():
    assert remaining_today() == pytest.approx(1.0)

def test_record_spend_decrements_remaining():
    record_spend("job1", chars=500, actual_usd=0.5)
    assert remaining_today() == pytest.approx(0.5)

def test_gate_voice_raises_402_if_estimate_exceeds_remaining():
    record_spend("job1", chars=900, actual_usd=0.9)
    with pytest.raises(HTTPException) as exc:
        gate_voice([{"voiceover": "x" * 200}])  # 200 chars = $0.2; remaining = $0.1
    assert exc.value.status_code == 402
