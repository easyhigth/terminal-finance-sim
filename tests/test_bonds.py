"""Tests du marché obligataire (core/bonds.py)."""
import pytest

from core import bonds as B
from core import portfolio as pf
from core.game_state import PlayerState
from core.market import Market


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


def test_high_yield_ytm_rises_when_credit_hy_spread_widens():
    """Un High Yield doit coûter plus cher à émettre (rendement exigé plus haut)
    quand le spread de crédit HY macro se tend, alors qu'un AAA y est insensible."""
    _, m = _setup()
    sov_before = B.quote(m, "UST10")["ytm"]
    hy_before = B.quote(m, "CORP_HY")["ytm"]
    m.macro["credit_hy"]["v"] = 760.0   # double du niveau de référence
    hy_after = B.quote(m, "CORP_HY")["ytm"]
    sov_after = B.quote(m, "UST10")["ytm"]
    assert hy_after > hy_before
    assert sov_after == pytest.approx(sov_before, abs=1e-9)   # AAA insensible au spread HY


def test_buy_fill_price_above_mid_high_yield_more_than_sovereign():
    """L'exécution coûte plus cher (spread/impact) qu'un high yield illiquide
    qu'un souverain noté liquide, pour un même ordre (item 25/26)."""
    _, m = _setup()
    sov_mid = B.quote(m, "UST10")["price"]
    hy_mid = B.quote(m, "CORP_HY")["price"]
    sov_fill = B.fill_price(m, "UST10", 10, "buy")
    hy_fill = B.fill_price(m, "CORP_HY", 10, "buy")
    sov_cost_frac = sov_fill / sov_mid - 1
    hy_cost_frac = hy_fill / hy_mid - 1
    assert sov_fill > sov_mid
    assert hy_cost_frac > sov_cost_frac
    assert B.quote(m, "UST10")["liquidity"] == "Liquide"
    assert B.quote(m, "CORP_HY")["liquidity"] == "Illiquide"


def test_bond_yield_curve_term_premium_matches_market_curve():
    """La prime de terme d'une obligation doit suivre la courbe du marché (et
    non plus une prime fixe) : une courbe inversée réduit le rendement exigé
    des maturités longues par rapport au court terme."""
    _, m = _setup()
    m.regime = "Récession"
    m.macro["growth"]["v"] = -4.0
    long_premium = B.term_premium(m, 10.0)
    short_premium = B.term_premium(m, 2.0)
    assert long_premium < short_premium   # courbe inversée


def test_bond_fill_price_costs_more_under_market_stress():
    """Pour un même ordre obligataire, un marché en plein stress (last_stress_level
    proche de 1.0 — régime volatil/récession) doit coûter plus cher à l'exécution
    qu'un marché calme (item 9/15 : coût d'exécution varie avec le régime)."""
    _, m = _setup()
    m.last_stress_level = 0.0
    calm = B.fill_price(m, "CORP_HY", 50, "buy")
    m.last_stress_level = 1.0
    stressed = B.fill_price(m, "CORP_HY", 50, "buy")
    assert stressed > calm


def test_bond_fill_price_deterministic_for_same_market_state():
    """Même état de marché (même stress, mêmes taux/spreads) -> même prix
    d'exécution, à chaque appel (aucun aléa non reproductible)."""
    _, m = _setup()
    m.last_stress_level = 0.42
    a = B.fill_price(m, "UST10", 30, "sell")
    b = B.fill_price(m, "UST10", 30, "sell")
    assert a == b
