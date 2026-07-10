"""Tests du lot « investisseur fondamental » : core/valuation.py (DCF,
sensibilité, SML/CAPM, pont d'IRR LBO avec invariant exact), devis d'impact
TWAP (core/orders.compare_cost) et critère de Kelly (core/kelly.py)."""
import math

import pytest

from core import kelly as K
from core import orders as ORD
from core import valuation as VAL
from core.game_state import PlayerState
from core.market import Market


@pytest.fixture()
def market():
    m = Market(seed=17)
    for _ in range(80):
        m.step()
    return m


# ================================================================== DCF
def _dcf_ticker(market):
    for c in market.companies:
        if VAL.dcf(market, c["ticker"]) is not None:
            return c["ticker"]
    pytest.skip("aucune société DCF-able")


def test_dcf_structure_and_gordon_guard(market):
    tk = _dcf_ticker(market)
    d = VAL.dcf(market, tk)
    assert d["ev"] == pytest.approx(d["pv_explicit"] + d["pv_terminal"])
    assert d["equity"] == pytest.approx(d["ev"] - d["net_debt"])
    assert d["per_share"] > 0
    assert VAL.dcf(market, tk, wacc=0.02, g_term=0.03) is None   # Gordon diverge


def test_dcf_value_falls_when_wacc_rises(market):
    tk = _dcf_ticker(market)
    lo = VAL.dcf(market, tk, wacc=0.07)
    hi = VAL.dcf(market, tk, wacc=0.12)
    assert lo["per_share"] > hi["per_share"]          # actualiser plus fort = moins cher


def test_dcf_sensitivity_grid_monotone(market):
    tk = _dcf_ticker(market)
    s = VAL.dcf_sensitivity(market, tk)
    for row in s["grid"]:
        vals = [v for v in row if v is not None]
        assert vals == sorted(vals, reverse=True)     # WACC ↑ ⇒ valeur ↓


# ================================================================== SML
def test_sml_rows_and_alpha_definition(market):
    s = VAL.sml(market)
    assert s is not None
    assert len(s["rows"]) == len(market.companies)
    r = s["rows"][0]
    assert r["alpha"] == pytest.approx(r["ret"] - (s["rf"] + r["beta"]
                                                   * (s["r_market"] - s["rf"])))
    alphas = [x["alpha"] for x in s["rows"]]
    assert alphas == sorted(alphas, reverse=True)


# ================================================================== LBO
def test_lbo_bridge_invariant_exact():
    b = VAL.lbo_bridge(100.0, 8.0, 0.60, 0.06, 9.0, 5)
    assert b is not None
    total = b["growth_effect"] + b["multiple_effect"] + b["paydown_effect"]
    assert total == pytest.approx(b["gain"], abs=1e-9)  # décomposition EXACTE
    assert b["moic"] > 1.0
    assert b["irr"] == pytest.approx(b["moic"] ** (1 / 5) - 1)


def test_lbo_leverage_amplifies_moic():
    low = VAL.lbo_bridge(100.0, 8.0, 0.30, 0.06, 8.0, 5)
    high = VAL.lbo_bridge(100.0, 8.0, 0.70, 0.06, 8.0, 5)
    assert high["moic"] > low["moic"]                 # l'effet de levier du LBO


def test_lbo_multiple_compression_hurts():
    flat = VAL.lbo_bridge(100.0, 8.0, 0.60, 0.06, 8.0, 5)
    compressed = VAL.lbo_bridge(100.0, 8.0, 0.60, 0.06, 6.0, 5)
    assert compressed["moic"] < flat["moic"]
    assert compressed["multiple_effect"] < 0


# ================================================================== TWAP
def test_twap_compare_cost_slicing_saves_impact(market):
    tk = market.top_companies(n=1)[0]["ticker"]
    est = ORD.compare_cost(market, tk, 50_000, "buy", 10)
    assert est is not None
    assert est["block_cost"] > est["sliced_cost"] > 0  # l'impact est non-linéaire
    assert est["savings"] == pytest.approx(est["block_cost"] - est["sliced_cost"])
    est_sell = ORD.compare_cost(market, tk, 50_000, "sell", 10)
    assert est_sell["savings"] > 0                     # symétrique à la vente


# ================================================================= Kelly
def _fake_journal(player, results):
    player.trade_journal = [{"realized": r} for r in results]


def test_kelly_fraction_textbook():
    # p = 60 %, b = 1 : f* = 0,6 − 0,4/1 = 0,2
    assert K.kelly_fraction(0.6, 1.0) == pytest.approx(0.2)
    assert K.kelly_fraction(0.5, 1.0) == 0.0           # pas d'edge → 0
    assert K.kelly_fraction(0.9, 0.0) == 0.0


def test_kelly_growth_peaks_at_f_star():
    p, b = 0.6, 1.0
    f_star = K.kelly_fraction(p, b)
    g_star = K.growth_rate(f_star, p, b)
    assert g_star > K.growth_rate(f_star / 2, p, b) > 0
    assert g_star > K.growth_rate(min(0.95, f_star * 2), p, b)  # sur-risquer coûte
    assert K.growth_rate(1.0, p, b) == float("-inf")   # tout miser = ruine


def test_kelly_recommendation_from_journal():
    p = PlayerState()
    _fake_journal(p, [100.0] * 12 + [-100.0] * 8)      # 20 trades : p=0,6, b=1
    reco = K.recommendation(p, net_worth=1_000_000.0)
    assert reco["f_star"] == pytest.approx(0.2)
    assert reco["stake_half"] == pytest.approx(100_000.0)
    assert reco["warning"] is None                     # échantillon suffisant
    _fake_journal(p, [100.0] * 3 + [-100.0] * 2)       # 5 trades : bruit
    reco = K.recommendation(p, net_worth=1_000_000.0)
    assert reco["warning"] is not None and "bruit" in reco["warning"]
    _fake_journal(p, [100.0] * 3 + [-200.0] * 17)      # espérance négative
    reco = K.recommendation(p, net_worth=1_000_000.0)
    assert reco["f_star"] == 0.0
    assert "ne pariez pas" in reco["warning"]


def test_kelly_none_without_journal():
    p = PlayerState()
    assert K.recommendation(p, 1_000_000.0) is None
