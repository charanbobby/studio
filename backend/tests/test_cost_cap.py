from datetime import date

import pytest

from reel_gen.llm.cost_cap import (
    DailyCostCapExceeded,
    add_to_today,
    check_cap,
    today_total_usd,
)


def test_add_and_total(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_COST_CAP_USD", "5.00")
    add_to_today(0.10)
    add_to_today(0.05)
    assert abs(today_total_usd() - 0.15) < 1e-6


def test_check_cap_under(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_COST_CAP_USD", "5.00")
    add_to_today(1.00)
    check_cap(prospective_cost_usd=0.10)


def test_check_cap_over_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_COST_CAP_USD", "1.00")
    add_to_today(0.95)
    with pytest.raises(DailyCostCapExceeded):
        check_cap(prospective_cost_usd=0.10)
