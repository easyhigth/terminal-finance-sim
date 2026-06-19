"""Tests des limites de risque configurables (core/risklimits.py)."""
from core import portfolio as pf
from core import risklimits
from core.game_state import PlayerState
from core.market import Market


def _player_with_concentrated_position():
    m = Market(seed=2024)
    p = PlayerState()
    p.grade_index = 8
    p.cash = 2_000_000.0
    tk = m.companies[0]["ticker"]
    other = m.companies[1]["ticker"]
    m.price[m.ticker_idx[tk]] = 100.0
    m.price[m.ticker_idx[other]] = 100.0
    pf.buy(p, m, tk, 5000)    # grosse ligne concentrée (~83% du brut investi)
    pf.buy(p, m, other, 1000)
    return p, m


def test_no_breach_on_empty_portfolio():
    m = Market(seed=2024)
    p = PlayerState()
    result = risklimits.check_limits(p, m)
    assert result["ok"] is True
    assert result["breaches"] == []


def test_position_limit_breach_detected():
    p, m = _player_with_concentrated_position()
    result = risklimits.check_limits(p, m, {"position_pct": 10.0})
    assert result["ok"] is False
    assert any(b["type"] == "position" for b in result["breaches"])


def test_custom_limits_override_defaults():
    p, m = _player_with_concentrated_position()
    result = risklimits.check_limits(p, m, {"position_pct": 99.0})
    assert not any(b["type"] == "position" for b in result["breaches"])


def test_none_limit_disables_check():
    p, m = _player_with_concentrated_position()
    result = risklimits.check_limits(p, m, {"position_pct": None})
    assert not any(b["type"] == "position" for b in result["breaches"])


def test_beta_limit_breach_detected():
    p, m = _player_with_concentrated_position()
    result = risklimits.check_limits(p, m, {"beta_max": 0.01})
    assert any(b["type"] == "beta" for b in result["breaches"])
