"""
tests/test_risk_indicator.py — Indicateur de risque unifié (core/risk_indicator.py).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from core import risk_indicator as RI
from core.game_state import PlayerState
from core.market import Market


def _setup(grade_index=5, cash=100_000.0):
    m = Market(seed=999)
    p = PlayerState()
    p.grade_index = grade_index
    p.cash = cash
    return p, m


def _set_price(m, tk, price):
    m.price[m.ticker_idx[tk]] = price


def _first_ticker(m):
    return m.companies[0]["ticker"]


def test_ok_with_no_positions():
    p, m = _setup()
    r = RI.assess(p, m)
    assert r["level"] == RI.LEVEL_OK


def test_warn_on_moderate_concentration():
    p, m = _setup(cash=40_000.0)
    tk = _first_ticker(m)
    _set_price(m, tk, 100.0)
    p.portfolio[tk] = {"shares": 600.0, "avg": 100.0}
    # valeur position = 60,000 ; patrimoine net = 40,000 + 60,000 = 100,000 -> poids 60%
    r = RI.assess(p, m)
    assert r["level"] == RI.LEVEL_WARN


def test_danger_on_heavy_concentration():
    p, m = _setup(cash=5_000.0)
    tk = _first_ticker(m)
    _set_price(m, tk, 100.0)
    p.portfolio[tk] = {"shares": 950.0, "avg": 100.0}
    # valeur position = 95,000 ; patrimoine net = 100,000 -> poids 95%
    r = RI.assess(p, m)
    assert r["level"] == RI.LEVEL_DANGER


def test_danger_on_high_leverage():
    p, m = _setup(grade_index=11, cash=10_000.0)
    tk = _first_ticker(m)
    _set_price(m, tk, 100.0)
    # exposition brute très supérieure à l'equity -> levier > 2x
    p.portfolio[tk] = {"shares": 500.0, "avg": 100.0}
    p.cash = 10_000.0 - 500.0 * 100.0 + 10_000.0   # cash après achat simulé, equity ~10,000
    r = RI.assess(p, m)
    assert r["level"] in (RI.LEVEL_WARN, RI.LEVEL_DANGER)


def test_reasons_non_empty_when_ok():
    p, m = _setup()
    r = RI.assess(p, m)
    assert r["reasons"]


def test_reasons_mention_concentration_when_flagged():
    p, m = _setup(cash=5_000.0)
    tk = _first_ticker(m)
    _set_price(m, tk, 100.0)
    p.portfolio[tk] = {"shares": 950.0, "avg": 100.0}
    r = RI.assess(p, m)
    assert any("concentr" in reason.lower() for reason in r["reasons"])


def test_worse_picks_the_more_severe_level():
    assert RI._worse(RI.LEVEL_OK, RI.LEVEL_WARN) == RI.LEVEL_WARN
    assert RI._worse(RI.LEVEL_DANGER, RI.LEVEL_WARN) == RI.LEVEL_DANGER
    assert RI._worse(RI.LEVEL_OK, RI.LEVEL_OK) == RI.LEVEL_OK


def test_max_position_weight_ignores_ticker_with_no_price():
    p, m = _setup(cash=1_000.0)
    p.portfolio["ZZZZ"] = {"shares": 100.0, "avg": 10.0}   # ticker inexistant
    assert RI._max_position_weight(p, m) == 0.0


def test_high_heat_raises_level():
    p, m = _setup()
    p.heat = 60                       # au-delà du seuil d'enquête (55)
    r = RI.assess(p, m)
    assert r["level"] == RI.LEVEL_DANGER
    assert any("réglementaire" in reason.lower() for reason in r["reasons"])
    p.heat = 45                       # zone de surveillance
    assert RI.assess(p, m)["level"] == RI.LEVEL_WARN


def test_var_ratio_folds_into_assessment():
    p, m = _setup()
    assert RI.assess(p, m, var_ratio=1.1)["level"] == RI.LEVEL_DANGER
    assert RI.assess(p, m, var_ratio=0.8)["level"] == RI.LEVEL_WARN
    assert RI.assess(p, m, var_ratio=0.3)["level"] == RI.LEVEL_OK
    # None = signal ignoré (rétrocompatible)
    assert RI.assess(p, m)["level"] == RI.LEVEL_OK
