"""Tests des modules purs de la salle des marchés avancée :
core/option_strategies.py (paquets multi-jambes exécutés sur le vrai desk
core/options), core/risk_advanced.py (allocation d'Euler, backtest de
Kupiec) et core/rates_analytics.py (courbe, DV01, chocs de courbe)."""
import numpy as np
import pytest

from core import bonds as B
from core import option_strategies as OS
from core import portfolio as pf
from core import rates_analytics as RT
from core import risk_advanced as RA
from core.game_state import PlayerState
from core.market import Market


@pytest.fixture()
def market():
    m = Market(seed=11)
    for _ in range(60):
        m.step()
    return m


@pytest.fixture()
def player():
    p = PlayerState()
    p.grade_index = 9
    p.cash = 3_000_000.0
    return p


def _tk(market, i=0):
    return market.top_companies(n=i + 1)[i]["ticker"]


# ======================================================= option_strategies
def test_straddle_quote_has_two_legs_and_v_shape(market, player):
    q = OS.quote_strategy(player, market, _tk(market), "straddle", 0.5, 10)
    assert len(q["legs"]) == 2
    assert q["premium"] > 0
    assert len(q["breakevens"]) == 2                 # deux points morts
    # P&L minimal AU strike (≈ spot), gains sur les deux ailes
    i_spot = int(np.argmin(np.abs(q["spots"] - q["spot"])))
    assert q["pnl"][i_spot] == pytest.approx(q["max_loss"], rel=0.05)
    assert q["pnl"][0] > 0 and q["pnl"][-1] > 0


def test_strangle_cheaper_than_straddle(market, player):
    tk = _tk(market)
    straddle = OS.quote_strategy(player, market, tk, "straddle", 0.5, 10)
    strangle = OS.quote_strategy(player, market, tk, "strangle", 0.5, 10)
    assert strangle["premium"] < straddle["premium"]


def test_protective_put_floors_the_loss(market, player):
    tk = _tk(market)
    q = OS.quote_strategy(player, market, tk, "protective_put", 0.5, 10)
    # à gauche de la grille (crash −40 %), la perte est PLANCHONNÉE :
    # bien moindre que la perte de l'action seule
    stock_loss = (q["spots"][0] - q["spot"]) * 10
    assert q["pnl"][0] > stock_loss
    assert q["max_loss"] < 0                          # l'assurance a un coût


def test_execute_strategy_all_or_nothing(market, player):
    tk = _tk(market)
    # put protecteur sans détenir l'action → refus AVANT tout achat
    r = OS.execute_strategy(player, market, tk, "protective_put", 0.5, 10)
    assert r == {"ok": False, "reason": "needs_stock", "held": 0.0}
    assert not getattr(player, "options", [])
    # cash insuffisant → refus avant tout achat
    poor = PlayerState()
    poor.cash = 0.5
    r = OS.execute_strategy(poor, market, tk, "straddle", 0.5, 10)
    assert r["ok"] is False and r["reason"] == "cash"
    assert not getattr(poor, "options", [])
    # exécution normale : 2 jambes au book, prime débitée
    cash0 = player.cash
    r = OS.execute_strategy(player, market, tk, "straddle", 0.5, 10)
    assert r["ok"] and len(r["positions"]) == 2
    assert player.cash == pytest.approx(cash0 - r["premium"], rel=1e-9)


def test_book_greeks_aggregate(market, player):
    tk = _tk(market)
    OS.execute_strategy(player, market, tk, "straddle", 0.5, 10)
    book = OS.book_greeks(player, market)
    assert len(book["rows"]) == 2
    assert book["totals"]["value"] > 0
    assert book["totals"]["theta_day"] < 0            # options longues : theta négatif
    # straddle ATM : delta cash proche de zéro relativement au notionnel
    notionnel = 10 * market.price_of(tk)
    assert abs(book["totals"]["delta_cash"]) < notionnel


# ========================================================== risk_advanced
def test_component_var_sums_to_total(market, player):
    for i in range(3):
        pf.buy(player, market, _tk(market, i), 80)
    comp = RA.component_var(player, market, n=6000)
    assert comp is not None and len(comp["lines"]) == 3
    total_contrib = sum(x["contrib"] for x in comp["lines"])
    assert total_contrib == pytest.approx(comp["var"], rel=0.05)  # Euler


def test_component_var_flags_hedge_as_negative(market, player):
    tk = _tk(market)
    pf.buy(player, market, tk, 100)
    hedge_tk = _tk(market, 1)
    pf.short(player, market, hedge_tk, 60)
    comp = RA.component_var(player, market, n=6000)
    short_line = next(x for x in comp["lines"] if x["label"] == hedge_tk)
    long_line = next(x for x in comp["lines"] if x["label"] == tk)
    assert long_line["contrib"] > 0
    assert short_line["contrib"] < long_line["contrib"]  # la couverture réduit


def test_component_var_none_without_positions(market, player):
    assert RA.component_var(player, market) is None


def test_var_backtest_counts_exceptions(market, player):
    for i in range(3):
        pf.buy(player, market, _tk(market, i), 60)
    bt = RA.var_backtest(player, market, lookback=60)
    assert bt is not None
    assert bt["n"] >= 20
    assert 0 <= bt["exceptions"] <= bt["n"]
    assert bt["expected"] == pytest.approx(0.05 * bt["n"])
    assert bt["lr"] >= 0.0


def test_kupiec_lr_rejects_gross_miscalibration():
    # 20 exceptions sur 100 à 95 % : modèle manifestement faux → rejet
    assert RA._kupiec_lr(100, 20, 0.05) > RA.KUPIEC_CHI2_95
    # 5 exceptions sur 100 : exactement l'attendu → LR ≈ 0
    assert RA._kupiec_lr(100, 5, 0.05) == pytest.approx(0.0, abs=1e-9)


# ======================================================== rates_analytics
def test_yield_curve_sorted_with_multiple_maturities(market):
    curve = RT.yield_curve(market)
    assert len(curve) >= 3
    years = [y for y, _ in curve]
    assert years == sorted(years)
    assert all(0 < v < 0.30 for _, v in curve)        # YTM plausibles


def test_book_lines_and_dv01(market, player):
    bid = B.sovereign_quotes(market)[0]["id"]
    assert B.buy_bond(player, market, bid, 50)["ok"]
    lines = RT.book_lines(player, market)
    assert len(lines) == 1
    x = lines[0]
    assert x["dv01"] == pytest.approx(x["value"] * x["duration"] * 1e-4)
    totals = RT.book_totals(lines)
    assert totals["duration"] == pytest.approx(x["duration"])


def test_parallel_up_shock_loses_money_on_long_book(market, player):
    quotes = sorted(B.sovereign_quotes(market), key=lambda q: q["years"])
    for q in (quotes[0], quotes[-1]):                 # court + long
        assert B.buy_bond(player, market, q["id"], 30)["ok"]
    t = RT.scenario_table(player, market)
    up100 = next(s for s in t["scenarios"] if s["name"] == "+100 bp parallèle")
    down100 = next(s for s in t["scenarios"] if s["name"] == "−100 bp parallèle")
    assert up100["pnl"] < 0 < down100["pnl"]
    # convexité : le gain de −100 bp dépasse la perte de +100 bp
    assert down100["pnl"] > -up100["pnl"]
    # pentification vs aplatissement : signes opposés sur le tri court/long
    steep = next(s for s in t["scenarios"] if "Pentification" in s["name"])
    flat = next(s for s in t["scenarios"] if "Aplatissement" in s["name"])
    assert steep["pnl"] != pytest.approx(flat["pnl"])


def test_scenario_table_empty_book(market, player):
    t = RT.scenario_table(player, market)
    assert t["lines"] == []
    assert all(s["pnl"] == 0.0 for s in t["scenarios"])
