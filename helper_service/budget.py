import json
import os
from datetime import date
from pathlib import Path
from fastapi import HTTPException

def _spend_file() -> Path:
    """Lazily resolve SPEND_FILE to pick up HELPER_DATA_DIR env var on each call."""
    data_dir = Path(os.environ.get("HELPER_DATA_DIR", "/data"))
    return data_dir / "spend.json"

def _usd_per_char() -> float:
    return float(os.environ.get("ELEVENLABS_USD_PER_CHAR", "0.00044"))

def _daily_budget() -> float:
    return float(os.environ["DAILY_BUDGET_USD"])

def _today() -> str:
    return date.today().isoformat()

def _load() -> dict:
    spend_file = _spend_file()
    if not spend_file.exists():
        return {"date": _today(), "spent_usd": 0.0, "by_job": {}}
    s = json.loads(spend_file.read_text())
    if s.get("date") != _today():
        return {"date": _today(), "spent_usd": 0.0, "by_job": {}}
    return s

def _save(s: dict) -> None:
    spend_file = _spend_file()
    spend_file.parent.mkdir(parents=True, exist_ok=True)
    spend_file.write_text(json.dumps(s, indent=2))

def estimate(beats: list[dict]) -> float:
    chars = sum(len(b["voiceover"]) for b in beats)
    return chars * _usd_per_char()

def remaining_today() -> float:
    return _daily_budget() - _load()["spent_usd"]

def gate_voice(beats: list[dict]) -> None:
    est = estimate(beats)
    rem = remaining_today()
    if est > rem:
        raise HTTPException(
            402,
            detail={"reason": "would_exceed_daily_cap",
                    "remaining": rem, "needed": est},
        )

def record_spend(job_id: str, chars: int, actual_usd: float) -> None:
    s = _load()
    s["spent_usd"] = round(s["spent_usd"] + actual_usd, 6)
    s["by_job"][job_id] = {"chars": chars, "actual_usd": actual_usd}
    _save(s)
