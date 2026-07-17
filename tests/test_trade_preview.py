"""Tests du simulateur avant→après (core/trade_preview.py) : clonage sans
effet de bord, grille de snapshot, flux par tour mesuré sur les vrais
accruals, preview d'actions variées, coût d'exécution, stress avant/après."""
import pytest

from core import bonds, cds
from core import portfolio as pf
from core import trade_preview as tp
from core.game_state import GameState
from core.market import Market


def _setup(cash=5_000_000.0):
    gs = GameState()
    p = gs.player
    p.grade_index = 8
    p.cash = cash
    m = Market(seed=8)   # époque normale
    for _ in range(10):
        m.step()
    return p, m


def test_clone_is_deep_and_independent():
    p, m = _setup()
    pf.buy(p, m, m.companies[0]["ticker"], 10)
    q = tp.clone_player(p)
    q.cash = 1.0
    q.portfolio[m.companies[0]["ticker"]]["shares"] = 999
    assert p.cash != 1.0
    assert p.portfolio[m.companies[0]["ticker"]]["shares"] == 10


def test_preview_does_not_touch_the_real_player():
    p, m = _setup()
    cash0 = p.cash
    pv = tp.preview(p, m, lambda q, mk: pf.buy(q, mk, m.companies[0]["ticker"], 50),
                    with_var=False)
    assert pv["result"]["ok"]
    assert p.cash == cash0 and not p.portfolio
    assert pv["after"]["cash"] < pv["before"]["cash"]
    assert pv["after"]["nw"] == pytest.approx(pv["before"]["nw"],
                                              rel=0.01)   # ~inchangée (frais près)


def test_failed_action_reports_reason_without_after():
    p, m = _setup(cash=100.0)
    pv = tp.preview(p, m, lambda q, mk: pf.buy(q, mk, m.companies[0]["ticker"], 10_000),
                    with_var=False)
    assert not pv["result"].get("ok")
    assert pv["after"] is None and pv["flux_after"] is None


def test_flux_reflects_bond_coupons():
    p, m = _setup()
    pv = tp.preview(p, m,
                    lambda q, mk: bonds.buy_bond(q, mk, bonds.all_quotes(mk)[0]["id"], 50),
                    with_var=False)
    assert pv["result"].get("ok")
    assert pv["flux_after"] > pv["flux_before"]   # les coupons tombent chaque tour


def test_flux_reflects_cds_premium_cost():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    pv = tp.preview(p, m,
                    lambda q, mk: cds.buy_protection(q, mk, tk, 500_000, 3),
                    with_var=False)
    if not pv["result"].get("ok"):
        pytest.skip("achat CDS refusé sur cette graine")
    assert pv["flux_after"] < pv["flux_before"]   # la prime coûte chaque tour


def test_snapshot_var_vs_limit():
    p, m = _setup()
    pf.buy(p, m, m.companies[0]["ticker"], 200)
    snap = tp.snapshot(p, m)
    assert snap["var"] is not None and snap["var"] >= 0
    assert snap["var_limit"] > 0


def test_execution_cost_breakdown():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    c = tp.execution_cost(p, m, tk, 100)
    assert c["fill"] >= c["mid"]            # un achat paie le demi-spread
    assert c["total"] == pytest.approx(c["spread_impact"] + c["fee"])
    assert c["total_pct"] > 0


def test_position_weight_after():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    w = tp.position_weight_after(p, m, tk, 100)
    assert 0 < w < 100


def test_stress_compare_before_after():
    p, m = _setup()
    pv = tp.preview(p, m, lambda q, mk: pf.buy(q, mk, m.companies[0]["ticker"], 400),
                    with_var=False)
    rows = tp.stress_compare(p, m, pv["player_after"])
    assert [r["key"] for r in rows] == ["eq", "rates", "vol"]
    eq = rows[0]
    # sans position, le choc actions ne coûte rien ; avec, il coûte
    assert eq["before"] == pytest.approx(0.0, abs=1.0)
    assert eq["after"] < eq["before"]
