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


def test_effective_limits_defaults_to_default_profile():
    p = PlayerState()
    assert risklimits.effective_limits(p) == risklimits.DEFAULT_LIMITS


def test_set_profile_changes_effective_limits():
    p = PlayerState()
    assert risklimits.set_profile(p, "strict") is True
    assert p.risk_limit_profile == "strict"
    assert risklimits.effective_limits(p) == risklimits.LIMIT_PROFILES["strict"]


def test_set_profile_rejects_unknown_name():
    p = PlayerState()
    assert risklimits.set_profile(p, "yolo") is False
    assert p.risk_limit_profile == "default"


def test_strict_profile_breaches_sooner_than_souple():
    p, m = _player_with_concentrated_position()
    risklimits.set_profile(p, "strict")
    strict_result = risklimits.check_limits(p, m)
    risklimits.set_profile(p, "souple")
    souple_result = risklimits.check_limits(p, m)
    assert len(strict_result["breaches"]) >= len(souple_result["breaches"])


def test_persistent_breach_costs_reputation_after_three_steps():
    from core.game_state import GameState

    p, m = _player_with_concentrated_position()
    risklimits.set_profile(p, "strict")
    gs = GameState(player=p)
    for _ in range(3):
        gs.advance_step(market=m)
    assert p.flags.get("risk_breach_streak", 0) >= 3
    assert any(reason == "Dépassement persistant des limites de risque"
               for reason, _ in p.rep_log)
