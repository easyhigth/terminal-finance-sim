"""Tests du lot B v2 : delta-hedge (décomposition Δ/Γ/Θ + aplatir), carry FX
(parité couverte, accrual dans advance_step), GARCH(1,1) (persistance,
convergence de la prévision), inférence de régime (filtre collant) et
immunisation (duration appariée, barbell exécutable)."""
import math

import numpy as np
import pytest

from core import delta_hedge as DH
from core import fx
from core import fx_carry as FXC
from core import garch as G
from core import option_strategies as OS
from core import portfolio as pf
from core import rates_analytics as RT
from core import regime_inference as RI
from core.game_state import GameState, PlayerState
from core.market import Market


@pytest.fixture()
def market():
    m = Market(seed=23)
    for _ in range(120):
        m.step()
    return m


@pytest.fixture()
def player():
    p = PlayerState()
    p.grade_index = 9
    p.cash = 5_000_000.0
    return p


# ============================================================= delta-hedge
def test_flatten_plan_neutralizes_book_delta(market, player):
    tk = market.top_companies(n=1)[0]["ticker"]
    assert OS.execute_strategy(player, market, tk, "call", 0.5, 100)["ok"]
    rows = DH.book_delta_by_underlying(player, market)
    assert rows and abs(rows[0]["net_shares"]) > 1   # un call sec a du delta
    plan = DH.flatten_plan(player, market)
    assert plan
    r = DH.execute_flatten(player, market, plan)
    assert not r["failed"]
    rows2 = DH.book_delta_by_underlying(player, market)
    assert abs(rows2[0]["net_shares"]) <= 1          # net plat au titre près


def test_pnl_decomposition_sums_to_actual(market, player):
    tk = market.top_companies(n=1)[0]["ticker"]
    assert OS.execute_strategy(player, market, tk, "straddle", 0.5, 20)["ok"]
    for _ in range(10):
        market.step()
    pos = player.options[0]
    dec = DH.pnl_decomposition(player, market, pos)
    assert dec is not None and dec["steps"] == 10
    total = dec["delta"] + dec["gamma"] + dec["theta"] + dec["residual"]
    assert total == pytest.approx(dec["actual"], abs=1e-6)   # décomposition exacte
    assert dec["gamma"] >= 0                          # gamma long : toujours ≥ 0
    assert dec["theta"] <= 0                          # le temps coûte


# ================================================================ FX carry
def test_parity_forward_discounts_high_yield_base(market):
    # USD/ZAR : le rand porte ~4,5 pts de plus → long la paire = carry NÉGATIF
    # (long USD, short ZAR) et forward au-DESSUS du spot (base à bas taux)
    r_base, r_quote = FXC.pair_rates(market, "USD/ZAR")
    assert r_quote > r_base
    fwd = FXC.parity_forward(market, "USD/ZAR", 3)
    assert fwd > fx.spot(market, "USD/ZAR")
    assert FXC.carry_annual(market, "USD/ZAR", "long") < 0
    assert FXC.carry_annual(market, "USD/ZAR", "short") > 0


def test_carry_table_sorted_and_consistent(market):
    table = FXC.carry_table(market)
    assert len(table) == len(fx.PAIRS)
    carries = [abs(r["carry_long"]) for r in table]
    assert carries == sorted(carries, reverse=True)
    for r in table:
        assert r["carry_long"] == pytest.approx(r["r_base"] - r["r_quote"])


def test_carry_accrues_through_advance_step(market, player):
    assert fx.open_spot(player, market, "USD/ZAR", "short", 200_000.0)["ok"]
    expected = FXC.accrue(player, market, 5)
    assert expected > 0                               # short USD/ZAR : carry positif
    gs = GameState()
    gs.player = player
    cash0 = player.cash
    gs.advance_step(market=market)
    # le cash a reçu (au moins) le portage — d'autres flux (salaire...) s'ajoutent
    assert player.cash >= cash0 + expected * 0.5


# ================================================================== GARCH
def test_garch_fit_recovers_clustering():
    """Série FABRIQUÉE avec grappes de vol (GARCH simulé) : le fit retrouve
    une persistance élevée ; un bruit blanc en retrouve peu."""
    rng = np.random.default_rng(4)
    n = 400
    a_true, b_true, omega = 0.12, 0.82, 0.0001 * (1 - 0.94)
    sig2, rets = 0.0001, []
    for _ in range(n):
        sig2 = omega + a_true * (rets[-1] ** 2 if rets else 0.0001) + b_true * sig2
        rets.append(rng.normal(0.0, math.sqrt(sig2)))
    model = G.fit(rets)
    assert model is not None
    assert model["persistence"] > 0.75                # grappes détectées


def test_garch_forecast_converges_to_long_run():
    model = {"lr_var": 0.0004, "persistence": 0.9, "sigma2_last": 0.0016,
             "omega": 0.00004, "alpha": 0.1, "beta": 0.8, "loglik": 0.0}
    fc = G.forecast(model, horizon=40)
    assert fc[0][1] > fc[-1][1]                       # décroît vers LR
    assert fc[-1][1] == pytest.approx(0.0004, rel=0.05)


def test_garch_analyze_on_market(market):
    tk = market.top_companies(n=1)[0]["ticker"]
    g = G.analyze(market, tk)
    assert g is not None
    assert 0.0 < g["vol_forecast_ann"] < 2.0
    assert len(g["forecast_curve"]) == 12
    assert g["verdict"]


# ================================================================= régimes
def test_regime_filter_flags_synthetic_stress():
    rng = np.random.default_rng(6)
    calm = rng.normal(0, 0.005, 60)
    stress = rng.normal(0, 0.03, 25)
    rets = np.concatenate([calm, stress])
    probs = RI.filter_probabilities(rets)
    assert probs is not None
    assert probs[-1] > 0.8                            # le stress final est vu
    assert probs[40] < 0.5                            # le calme du début aussi


def test_regime_infer_on_market(market):
    r = RI.infer(market)
    assert r is not None
    assert 0.0 <= r["p_now"] <= 1.0
    assert r["inferred"] in ("CALME", "STRESS")
    assert r["truth"] in ("Expansion", "Calme", "Volatil", "Récession")


# ============================================================ immunisation
def test_immunize_plan_duration_matches_horizon(market, player):
    plan = RT.immunize_plan(player, market, 500_000.0, 5)
    if plan is None:
        pytest.skip("univers n'encadrant pas 5 ans")
    d_barbell = (plan["short"]["weight"] * plan["short"]["dur"]
                 + plan["long"]["weight"] * plan["long"]["dur"])
    assert d_barbell == pytest.approx(5.0, abs=1e-9)  # duration = horizon, exact
    assert 0.0 < plan["short"]["weight"] < 1.0
    chk = RT.immunization_check(plan, dy=0.01)
    # au 1er ordre, actifs et passif bougent pareil
    assert abs(chk["mismatch"]) < 0.02 * plan["pv"]
    r = RT.execute_immunization(player, market, plan)
    assert r["ok"]
    assert plan["short"]["id"] in player.bonds
    assert plan["long"]["id"] in player.bonds
