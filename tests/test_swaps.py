"""Tests des swaps de devises (core/swaps.py) : différentiel de taux régional."""
import pytest

from core import swaps as SW
from core.game_state import PlayerState
from core.market import Market


def _player(continent="Europe", cash=0.0):
    p = PlayerState()
    p.continent = continent
    p.cash = cash
    return p


def test_foreign_regions_excludes_home():
    p = _player("Europe")
    regions = SW.foreign_regions(p)
    assert "Europe" not in regions
    assert "USA" in regions


def test_quote_diff_matches_rate_difference():
    m = Market(seed=2024)
    p = _player("Europe")
    q = SW.quote(m, p, "USA")
    assert q["diff"] == pytest.approx(q["foreign_rate"] - q["home_rate"])


def test_enter_swap_rejects_invalid_inputs():
    m = Market(seed=2024)
    p = _player("Europe")
    assert SW.enter_swap(p, m, "Europe", "receive_foreign", 100_000.0, 2)["ok"] is False
    assert SW.enter_swap(p, m, "USA", "bad_direction", 100_000.0, 2)["ok"] is False
    assert SW.enter_swap(p, m, "USA", "receive_foreign", 0.0, 2)["ok"] is False
    assert SW.enter_swap(p, m, "USA", "receive_foreign", 100_000.0, 4)["ok"] is False


def test_enter_swap_does_not_debit_cash():
    m = Market(seed=2024)
    p = _player("Europe", cash=500_000.0)
    r = SW.enter_swap(p, m, "USA", "receive_foreign", 500_000.0, 2)
    assert r["ok"] is True
    assert p.cash == 500_000.0
    assert len(p.currency_swaps) == 1
    assert p.currency_swaps[0]["days_left"] == 2 * 365


def test_accrue_sign_flips_with_direction():
    m = Market(seed=2024)
    m.region_credit_bump["USA"] = 0.02  # force un écart positif clair (étranger > domestique)
    p = _player("Europe")
    SW.enter_swap(p, m, "USA", "receive_foreign", 1_000_000.0, 2)
    flow_foreign, _ = SW.accrue(p, m, 5)

    p2 = _player("Europe")
    SW.enter_swap(p2, m, "USA", "receive_domestic", 1_000_000.0, 2)
    flow_domestic, _ = SW.accrue(p2, m, 5)

    assert flow_foreign == pytest.approx(-flow_domestic)
    assert flow_foreign > 0


def test_accrue_expires_swap_after_tenor():
    m = Market(seed=2024)
    p = _player("Europe")
    SW.enter_swap(p, m, "USA", "receive_foreign", 200_000.0, 2)
    sw = p.currency_swaps[0]
    steps = sw["days_left"] // 5
    expired = []
    for _ in range(steps):
        _, expired = SW.accrue(p, m, 5)
    assert p.currency_swaps == []
    assert len(expired) == 1
    assert expired[0]["days_left"] <= 0


def test_holdings_enriches_with_carry_and_years_left():
    m = Market(seed=2024)
    p = _player("Europe")
    SW.enter_swap(p, m, "USA", "receive_foreign", 300_000.0, 3)
    hold = SW.holdings(p, m)
    assert len(hold) == 1
    h = hold[0]
    assert h["annual_carry"] == pytest.approx(300_000.0 * h["net_rate"])
    assert h["years_left"] == pytest.approx(3.0)
