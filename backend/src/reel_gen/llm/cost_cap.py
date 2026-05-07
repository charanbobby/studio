"""Daily cost cap enforced before any paid API call.

Per spec section 8d: a JSON file in the runs volume tracks cumulative
USD spent today (UTC). Before any paid call, callers invoke check_cap()
with the prospective cost; over-cap raises DailyCostCapExceeded. After
the call, callers call add_to_today() with the actual cost.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class DailyCostCapExceeded(RuntimeError):
    """Raised when the day's cumulative cost would exceed DAILY_COST_CAP_USD."""


def _cap_file() -> Path:
    runs = Path(os.environ.get("RUNS_DIR", "./runs"))
    runs.mkdir(parents=True, exist_ok=True)
    return runs / "_daily_cost.json"


def _today_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _load() -> dict:
    f = _cap_file()
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text())
    except json.JSONDecodeError:
        return {}


def _save(data: dict) -> None:
    _cap_file().write_text(json.dumps(data, indent=2))


def today_total_usd() -> float:
    data = _load()
    return float(data.get(_today_key(), 0.0))


def add_to_today(cost_usd: float) -> None:
    data = _load()
    key = _today_key()
    data[key] = round(float(data.get(key, 0.0)) + float(cost_usd), 6)
    _save(data)


def check_cap(*, prospective_cost_usd: float) -> None:
    cap = float(os.environ.get("DAILY_COST_CAP_USD", "5.00"))
    total = today_total_usd()
    if total + prospective_cost_usd > cap:
        raise DailyCostCapExceeded(
            f"Daily cost cap of ${cap:.2f} would be exceeded "
            f"(today=${total:.4f}, prospective=${prospective_cost_usd:.4f})"
        )
