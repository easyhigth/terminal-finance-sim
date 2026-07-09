"""Tests du lot « crédit + taux avancé + crise » : core/credit_risk.py
(Merton structurel : PD monotone au levier et au cours de l'action),
waterfall de titrisation (ordre de la cascade), forwards/rotation DV01
(core/rates_analytics) et core/crisis_lab.py (corrélations → 1 coûte plus
cher que le choc diversifié, les puts amortissent)."""
import math

import pytest

from core import bonds as B
from core import credit_risk as CR
from core import crisis_lab as CL
from core import hedging as H
from core import portfolio as pf
from core import rates_analytics as RT
from core import securitisation as SEC
from core.game_state import PlayerState
from core.market import Market


@pytest.fixture()
def market():
    m = Market(seed=13)
    for _ in range(60):
        m.step()
    return m


@pytest.fixture()
def player():
    p = PlayerState()
    p.grade_index = 9
    p.cash = 5_000_000.0
    return p


# ============================================================ Merton crédit
def test_merton_credit_fields_plausible(market):
    tk = market.top_companies(n=1)[0]["ticker"]
    f = CR.merton_credit(market, tk)
    assert f is not None
    assert f["assets"] == pytest.approx(f["equity"] + f["debt"])
    assert 0.0 <= f["pd"] <= 1.0
    assert f["spread_bps"] >= 0.0
    assert f["sigma_v"] <= f["sigma_e"] + 1e-12      # dé-levier : vol actifs ≤ vol actions


def test_merton_pd_rises_when_equity_falls(market):
    """Le lien actions ↔ crédit : une action qui chute rapproche du défaut."""
    row = CR.market_scan(market, n=1)[0]              # société la plus endettée
    curve = CR.pd_vs_equity_curve(market, row["ticker"])
    assert len(curve) >= 4
    pds = [pd for _s, pd in curve]                    # chocs croissants (−60 % → +20 %)
    assert pds[0] >= pds[-1]                          # PD décroît quand l'action monte
    assert pds[0] > row["pd"] - 1e-12                 # crash → PD au moins aussi haute


def test_market_scan_sorted_by_pd(market):
    scan = CR.market_scan(market, n=8)
    assert len(scan) == 8
    pds = [r["pd"] for r in scan]
    assert pds == sorted(pds, reverse=True)


# ================================================================ Waterfall
def test_waterfall_order_equity_first_senior_last():
    (eq_id, _n1, a1, d1, _c1, _r1) = SEC.TRANCHES[0]
    (mz_id, _n2, a2, d2, _c2, _r2) = SEC.TRANCHES[1]
    (sr_id, _n3, a3, d3, _c3, _r3) = SEC.TRANCHES[2]
    # perte de pool 5 % : l'equity (0-10 %) prend, les autres rien
    assert SEC.tranche_loss_fraction(0.05, a1, d1) == pytest.approx(0.5)
    assert SEC.tranche_loss_fraction(0.05, a2, d2) == 0.0
    assert SEC.tranche_loss_fraction(0.05, a3, d3) == 0.0
    # 15 % : equity anéantie, mezzanine entamée, senior indemne
    assert SEC.tranche_loss_fraction(0.15, a1, d1) == 1.0
    assert 0.0 < SEC.tranche_loss_fraction(0.15, a2, d2) < 1.0
    assert SEC.tranche_loss_fraction(0.15, a3, d3) == 0.0
    # les coupons paient le rang : equity > mezz > senior
    coupons = [t[4] for t in SEC.TRANCHES]
    assert coupons == sorted(coupons, reverse=True)


# =================================================== forwards & rotation
def test_forward_rates_recover_flat_and_steep_curves():
    flat = [(1.0, 0.03), (5.0, 0.03), (10.0, 0.03)]
    fwds = RT.forward_rates(flat)
    assert all(f == pytest.approx(0.03) for _t1, _t2, f in fwds)
    steep = [(1.0, 0.02), (10.0, 0.04)]
    (_t1, _t2, f), = RT.forward_rates(steep)
    # forward au-dessus du long : (0,04·10 − 0,02·1)/9 ≈ 4,22 %
    assert f == pytest.approx((0.04 * 10 - 0.02 * 1) / 9)
    assert f > 0.04


def test_dv01_rotation_plan_matches_dv01(market, player):
    quotes = sorted(B.sovereign_quotes(market), key=lambda q: q["years"])
    assert B.buy_bond(player, market, quotes[-1]["id"], 40)["ok"]   # long terme
    plan = RT.dv01_rotation_plan(player, market, "shorten")
    assert plan is not None
    assert plan["sell"]["id"] == quotes[-1]["id"]
    assert plan["buy"]["id"] == quotes[0]["id"]
    assert plan["buy"]["dv01"] == pytest.approx(plan["sell"]["dv01"], rel=0.25)
    r = RT.execute_rotation(player, market, plan)
    assert r["ok"] is True
    assert plan["buy"]["id"] in player.bonds          # la jambe courte est au book


def test_dv01_rotation_none_on_empty_book(market, player):
    assert RT.dv01_rotation_plan(player, market, "shorten") is None


# ================================================================ Labo crise
def _setup_book(player, market):
    for c in market.top_companies(n=3):
        assert pf.buy(player, market, c["ticker"], 60)["ok"]


def test_crisis_crunch_costs_more_than_diversified(market, player):
    _setup_book(player, market)
    normal = CL.reprice(player, market, eq_shock=-0.25, dy=0.0, corr_crunch=False)
    crunch = CL.reprice(player, market, eq_shock=-0.25, dy=0.0, corr_crunch=True)
    assert normal["total"] < 0
    # corrélations → 1 : au moins aussi douloureux que le choc bêta-pondéré
    assert crunch["total"] <= normal["total"] + 1e-6
    assert crunch["total_normal"] == pytest.approx(normal["total"], rel=1e-6)


def test_crisis_protective_put_cushions_the_crash(market, player):
    _setup_book(player, market)
    without = CL.reprice(player, market, eq_shock=-0.30, corr_crunch=True)
    assert H.buy_put(player, market, 500_000.0, 0.95, 0.5)["ok"]
    with_put = CL.reprice(player, market, eq_shock=-0.30, corr_crunch=True)
    put_line = next(x for x in with_put["lines"] if x["kind"] == "Couverture")
    assert put_line["pnl"] > 0                        # le put GAGNE dans le krach
    assert with_put["total"] > without["total"]


def test_crisis_rates_shock_hits_bonds(market, player):
    bid = sorted(B.sovereign_quotes(market), key=lambda q: q["years"])[-1]["id"]
    assert B.buy_bond(player, market, bid, 40)["ok"]
    res = CL.reprice(player, market, eq_shock=0.0, dy=0.02)
    bond_line = next(x for x in res["lines"] if x["kind"] == "Obligation")
    assert bond_line["pnl"] < 0                       # +200 bp : le book de taux souffre


def test_crisis_deterministic(market, player):
    _setup_book(player, market)
    a = CL.reprice(player, market, -0.2, 0.01, True)
    b = CL.reprice(player, market, -0.2, 0.01, True)
    assert a["total"] == b["total"]
