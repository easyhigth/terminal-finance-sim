"""Tests des produits structurés (core/structured.py) : payoffs non linéaires."""
import pytest

from core import structured as S
from core.game_state import PlayerState
from core.market import Market


def _prod(ti, notional=100_000.0, start=1000.0):
    p = dict(S.TEMPLATES[ti])
    p["notional"] = notional
    p["start_level"] = start
    return p


def test_capital_guaranteed_protects_downside():
    p = _prod(0)                                   # capital garanti + 60% hausse
    assert S.payoff(p, 500.0) == pytest.approx(100_000.0)        # -50% -> capital protégé
    assert S.payoff(p, 1200.0) == pytest.approx(100_000 * (1 + 0.6 * 0.2))  # +20% -> participation


def test_reverse_convertible_coupon_and_barrier():
    p = _prod(1)                                   # 10%/an, 2 ans, barrière 70%
    coupons = 100_000 * 0.10 * 2
    # au-dessus de la barrière : capital + coupons
    assert S.payoff(p, 900.0) == pytest.approx(coupons + 100_000)
    # sous la barrière (final < 700) : perte sur le capital
    assert S.payoff(p, 600.0) == pytest.approx(coupons + 100_000 * 0.6)


def test_autocallable_paths():
    p = _prod(2)                                   # 8%/an, 3 ans, barrière 60%
    assert S.payoff(p, 1100.0) == pytest.approx(100_000 * (1 + 0.08 * 3))   # hausse -> rappelé
    assert S.payoff(p, 800.0) == pytest.approx(100_000.0)                   # entre barrière et 0
    assert S.payoff(p, 500.0) == pytest.approx(100_000 * 0.5)              # sous barrière -> perte


def test_invest_and_evaluate_due():
    m = Market(seed=2024)
    p = PlayerState(); p.cash = 500_000.0; p.continent = "USA"
    r = S.invest(p, m, 0, 100_000.0)
    assert r["ok"] and len(p.structured) == 1 and p.cash == pytest.approx(400_000.0)
    # pas encore à échéance
    assert S.evaluate_due(p, m) == []
    # force l'échéance
    p.structured[0]["maturity_step"] = m.step_count
    res = S.evaluate_due(p, m)
    assert len(res) == 1 and not p.structured       # dénoué, retiré


def test_invest_refused_without_cash():
    m = Market(seed=2024)
    p = PlayerState(); p.cash = 1000.0; p.continent = "USA"
    assert S.invest(p, m, 0, 100_000.0)["reason"] == "cash"
