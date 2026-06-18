"""Tests du desk crédit / titrisation (core/securitisation.py)."""
import pytest

from core import securitisation as SEC
from core.game_state import PlayerState
from core.market import Market


def test_waterfall_subordination():
    # equity [0,10%], mezz [10,25%], senior [25,100%]
    eq = SEC.TRANCHES[0]; mz = SEC.TRANCHES[1]; sr = SEC.TRANCHES[2]
    # perte pool 5% : l'equity encaisse 50% (5/10), mezz et senior intacts
    assert SEC.tranche_loss_fraction(0.05, eq[2], eq[3]) == pytest.approx(0.5)
    assert SEC.tranche_loss_fraction(0.05, mz[2], mz[3]) == pytest.approx(0.0)
    assert SEC.tranche_loss_fraction(0.05, sr[2], sr[3]) == pytest.approx(0.0)
    # perte pool 15% : equity wipé (100%), mezz à (15-10)/15 = 33%, senior intact
    assert SEC.tranche_loss_fraction(0.15, eq[2], eq[3]) == pytest.approx(1.0)
    assert SEC.tranche_loss_fraction(0.15, mz[2], mz[3]) == pytest.approx((0.15-0.10)/0.15)
    assert SEC.tranche_loss_fraction(0.15, sr[2], sr[3]) == pytest.approx(0.0)
    # perte pool 40% : senior touché à (40-25)/75 = 20%
    assert SEC.tranche_loss_fraction(0.40, sr[2], sr[3]) == pytest.approx((0.40-0.25)/0.75)


def test_equity_coupon_higher_than_senior():
    qs = {q["id"]: q for q in SEC.all_quotes()}
    assert qs["EQUITY"]["coupon"] > qs["MEZZ"]["coupon"] > qs["SENIOR"]["coupon"]
    # la perte attendue est plus forte sur l'equity que sur le senior
    assert qs["EQUITY"]["exp_loss"] > qs["SENIOR"]["exp_loss"]


def test_invest_and_evaluate():
    m = Market(seed=2024)
    p = PlayerState(); p.cash = 500_000.0; p.continent = "USA"
    assert SEC.invest(p, m, "MEZZ", 100_000.0)["ok"]
    assert p.cash == pytest.approx(400_000.0)
    p.securitised[0]["maturity_step"] = m.step_count
    res = SEC.evaluate_due(p, m)
    assert len(res) == 1 and not p.securitised
    assert 0.0 <= res[0]["loss_frac"] <= 1.0


def test_realized_loss_deterministic():
    a, b = Market(seed=9), Market(seed=9)
    assert SEC.realized_pool_loss(a, 0) == pytest.approx(SEC.realized_pool_loss(b, 0))


def test_invest_refused_without_cash():
    m = Market(seed=2024)
    p = PlayerState(); p.cash = 1000.0; p.continent = "USA"
    assert SEC.invest(p, m, "SENIOR", 100_000.0)["reason"] == "cash"
