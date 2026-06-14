"""Tests du marché obligataire (core/bonds.py)."""
import pytest

from core.market import Market
from core.game_state import PlayerState
from core import bonds as B
from core import portfolio as pf


def _setup():
    m = Market(seed=2024)
    p = PlayerState()
    p.cash = 1_000_000.0
    return p, m


def test_quotes_have_sensible_fields():
    _, m = _setup()
    for q in B.all_quotes(m):
        assert q["price"] > 0
        assert 0 < q["ytm"] < 0.20
        assert q["mod_duration"] > 0
        assert q["convexity"] > 0


def test_high_yield_yields_more_than_sovereign():
    _, m = _setup()
    hy = B.quote(m, "CORP_HY")["ytm"]
    sov = B.quote(m, "UST10")["ytm"]
    assert hy > sov   # le spread crédit gonfle le rendement exigé


def test_price_falls_when_rates_rise():
    _, m = _setup()
    p0 = B.quote(m, "UST10")["price"]
    m.macro["rate"]["v"] += 2.0          # +200 bps
    p1 = B.quote(m, "UST10")["price"]
    assert p1 < p0                       # relation inverse prix/taux


def test_longer_duration_more_sensitive():
    _, m = _setup()
    short_d = B.quote(m, "UST2")["mod_duration"]
    long_d = B.quote(m, "UST10")["mod_duration"]
    assert long_d > short_d


def test_buy_and_sell_bond():
    p, m = _setup()
    r = B.buy_bond(p, m, "UST10", 100)
    assert r["ok"] and p.bonds["UST10"]["qty"] == 100
    assert B.holdings_value(p, m) > 0
    s = B.sell_bond(p, m, "UST10", "ALL")
    assert s["ok"] and "UST10" not in p.bonds


def test_coupons_paid():
    p, m = _setup()
    B.buy_bond(p, m, "CORP_HY", 100)     # coupon 9%
    coup = B.coupons(p, m, days=90)
    assert coup > 0


def test_net_worth_includes_bonds():
    p, m = _setup()
    nw0 = pf.net_worth(p, m)
    B.buy_bond(p, m, "UST10", 100)
    nw1 = pf.net_worth(p, m)
    # la valeur nette est conservée (cash -> obligations) à la commission près
    assert nw1 == pytest.approx(nw0, rel=2e-3)
