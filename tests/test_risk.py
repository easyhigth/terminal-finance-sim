"""Tests du risque sur portefeuille réel (core/risk.py)."""
import pytest

from core import bonds as B
from core import portfolio as pf
from core import risk
from core.game_state import PlayerState
from core.market import Market


def _player_with_positions():
    m = Market(seed=2024)
    p = PlayerState()
    p.grade_index = 8
    p.cash = 2_000_000.0
    # quelques actions + une obligation
    for tk in (m.companies[0]["ticker"], m.companies[10]["ticker"], m.companies[20]["ticker"]):
        m.price[m.ticker_idx[tk]] = 100.0
        pf.buy(p, m, tk, 200)
    B.buy_bond(p, m, "UST10", 100)
    return p, m


def test_simulate_produces_positive_var():
    p, m = _player_with_positions()
    r = risk.simulate(p, m, confidence=0.95, n=5000, seed=1)
    assert r["var"] > 0
    assert r["cvar"] >= r["var"]          # la CVaR dépasse la VaR
    assert r["sigma"] > 0
    assert len(r["pnl"]) == 5000


def test_empty_portfolio_has_zero_risk():
    m = Market(seed=2024)
    p = PlayerState()
    r = risk.simulate(p, m, n=2000, seed=1)
    assert r["sigma"] == pytest.approx(0.0, abs=1e-9)
    assert r["var"] == pytest.approx(0.0, abs=1e-9)


def test_exposures_reflect_positions():
    p, m = _player_with_positions()
    exp = risk.exposures(p, m)
    assert exp["Actions (net)"] > 0
    assert exp["Obligations"] > 0
    assert exp["Taux (DV01/100bps)"] > 0


def test_stress_equity_crash_is_a_loss():
    p, m = _player_with_positions()
    s = risk.stress(p, m, "Krach actions")
    assert s["equity"] < 0                 # un krach actions fait perdre
    assert s["total"] == pytest.approx(s["equity"] + s["bond"], rel=1e-9)


def test_rate_shock_hurts_bonds():
    p, m = _player_with_positions()
    s = risk.stress(p, m, "Choc de taux +200bps")
    assert s["bond"] < 0                   # +200 bps fait baisser les obligations


def test_drawdown_from_history():
    p = PlayerState()
    p.cash_history = [100, 120, 90, 110, 70, 130]
    dd = risk.net_worth_drawdown(p)
    assert dd == pytest.approx((120 - 70) / 120, rel=1e-6)
