"""Tests du socle quantitatif core/quant_tools.py (logique pure) — le socle
partagé par les apps Sharpe / Z-Score / Couverture / Frontière efficiente.
Vérifie les CHIFFRES (annualisation, poids, conservation du budget), pas
seulement l'absence de crash."""
import math

import numpy as np
import pytest

from core import quant_tools as QT
from core.game_state import PlayerState
from core.market import Market, STEPS_PER_YEAR


@pytest.fixture()
def market():
    m = Market(seed=7)
    for _ in range(90):
        m.step()
    return m


@pytest.fixture()
def player():
    p = PlayerState()
    p.grade_index = 9
    p.cash = 2_000_000.0
    return p


def _buy(p, m, n=3, shares=50):
    from core import portfolio as pf
    tks = [c["ticker"] for c in m.top_companies(n=n)]
    for tk in tks:
        assert pf.buy(p, m, tk, shares)["ok"]
    return tks


# ------------------------------------------------------------ annualisation
def test_period_steps_match_graph_scene():
    from scenes.scene_graph import STEP_PERIODS
    for code, steps in QT.PERIOD_STEPS.items():
        key = code if code in STEP_PERIODS else code.replace("A", "A")
        if code in STEP_PERIODS:
            assert STEP_PERIODS[code] == steps, code


def test_ann_return_and_vol_scale_with_steps_per_year():
    r = np.full(50, 0.001)                      # +0,1 % par pas, constant
    assert QT.ann_return(r) == pytest.approx(0.001 * STEPS_PER_YEAR)
    assert QT.ann_vol(r) == pytest.approx(0.0)  # aucun écart-type
    r2 = np.array([0.01, -0.01] * 25)
    assert QT.ann_vol(r2) == pytest.approx(0.01 * math.sqrt(STEPS_PER_YEAR))


def test_sharpe_sign_and_zero_vol():
    up = np.full(30, 0.005)
    assert QT.sharpe(up, rf_annual=0.0) == 0.0          # vol nulle → 0, pas inf
    noisy = np.array([0.02, -0.005] * 20)               # moyenne positive
    assert QT.sharpe(noisy, rf_annual=0.0) > 0
    assert QT.sharpe(noisy, rf_annual=10.0) < 0         # rf énorme → négatif


def test_rolling_sharpe_length():
    r = np.random.default_rng(0).normal(0.001, 0.01, 60)
    rs = QT.rolling_sharpe(r, window=18)
    assert len(rs) == 60 - 18 + 1
    assert QT.rolling_sharpe(r[:10], window=18).size == 0


def test_beta_of_identical_series_is_one(market):
    b = QT.index_returns(market)
    assert QT.beta(b, b) == pytest.approx(1.0)
    assert QT.beta(2.0 * b, b) == pytest.approx(2.0)


def test_main_index_prefers_player_region(market, player):
    name = QT.main_index(market, player)
    assert name in market.index_region
    assert market.index_region[name] == player.continent


# ------------------------------------------------------------- portefeuille
def test_portfolio_returns_empty_without_positions(market, player):
    r, tks = QT.portfolio_step_returns(player, market)
    assert len(r) == 0 and tks == []


def test_portfolio_returns_with_positions(market, player):
    tks = _buy(player, market)
    r, out_tks = QT.portfolio_step_returns(player, market, 40)
    assert set(out_tks) == set(tks)
    assert len(r) >= QT.MIN_POINTS
    assert np.isfinite(r).all()


def test_current_weights_sum_to_one(market, player):
    tks = _buy(player, market)
    w, total = QT.current_weights(player, market, tks + ["INEXISTANT"])
    assert total > 0
    assert w.sum() == pytest.approx(1.0)
    assert w[-1] == 0.0                                  # non détenu → 0


# ---------------------------------------------------------------- frontière
def test_frontier_returns_weights_per_point(market):
    tks = [c["ticker"] for c in market.top_companies(n=4)]
    fr = QT.frontier(market, tks, n_points=15)
    assert fr is not None
    assert len(fr["vols"]) == len(fr["rets"]) == len(fr["weights"])
    for w in fr["weights"]:
        assert w.sum() == pytest.approx(1.0, abs=1e-6)
        assert (w >= -1e-9).all()                        # long-only
    assert 0 <= fr["i_min_var"] < len(fr["vols"])
    assert 0 <= fr["i_max_sharpe"] < len(fr["vols"])
    # le point min-var a bien la vol minimale de la courbe
    assert fr["vols"][fr["i_min_var"]] == pytest.approx(fr["vols"].min())


def test_frontier_needs_two_tickers(market):
    assert QT.frontier(market, ["MVC"]) is None
    assert QT.frontier(market, []) is None


def test_target_trades_reach_the_target_weights(market, player):
    tks = _buy(player, market, n=3, shares=100)
    fr = QT.frontier(market, tks, n_points=10)
    target_w = fr["weights"][fr["i_min_var"]]
    plan = QT.target_trades(player, market, tks, target_w)
    assert plan["budget"] > 0
    # ventes AVANT achats dans la liste
    sides = [t["side"] for t in plan["trades"]]
    if "sell" in sides and "buy" in sides:
        assert sides.index("buy") > len([s for s in sides if s == "sell"]) - 1
    res = QT.apply_trades(player, market, plan["trades"])
    assert res["done"] == len(plan["trades"])
    assert not res["failed"]
    # après exécution, les poids réels sont proches de la cible
    w_after, _tot = QT.current_weights(player, market, tks)
    assert np.abs(w_after - target_w / target_w.sum()).max() < 0.08


def test_target_trades_from_cash_only(market, player):
    """Sans position, le budget par défaut = 80 % du cash — on peut INVESTIR
    directement sur un point de la frontière."""
    tks = [c["ticker"] for c in market.top_companies(n=3)]
    fr = QT.frontier(market, tks, n_points=10)
    plan = QT.target_trades(player, market, tks, fr["weights"][fr["i_max_sharpe"]])
    assert plan["budget"] == pytest.approx(player.cash * 0.8)
    assert all(t["side"] == "buy" for t in plan["trades"])
    res = QT.apply_trades(player, market, plan["trades"])
    assert res["done"] and not res["failed"]
    assert player.cash < 2_000_000.0


def test_projection_quantiles_are_ordered():
    pr = QT.projection(100_000.0, 0.08, 0.20, years=1.0)
    assert pr["p5"] < pr["p50"] < pr["p95"]
    assert pr["p50"] == pytest.approx(100_000.0 * math.exp(0.08 - 0.5 * 0.04))
    assert QT.projection(0.0, 0.08, 0.2)["p50"] == 0.0


# ----------------------------------------------------------------- z-scores
def test_rolling_zscore_flags_a_spike():
    base = [100.0] * 30 + [100.0 + i * 0.01 for i in range(10)]
    base[-1] = 130.0                                     # pic net
    z = QT.rolling_zscore(np.array(base), window=18)
    assert len(z) == len(base) - 18 + 1
    assert z[-1] > 2.0
    assert abs(z[0]) < 0.5


def test_zscore_last_zero_on_flat_series():
    assert QT.zscore_last([5.0] * 20) == 0.0


def test_rolling_volatility_and_correlation_lengths(market):
    tks = [c["ticker"] for c in market.top_companies(n=2)]
    a = QT.returns_of(market, tks[0], 60)
    b = QT.returns_of(market, tks[1], 60)
    assert len(QT.rolling_volatility(a, 18)) == len(a) - 18 + 1
    rc = QT.rolling_correlation(a, b, 18)
    assert len(rc) == min(len(a), len(b)) - 18 + 1
    assert (np.abs(rc) <= 1.0 + 1e-9).all()


# --------------------------------------------------------------- couverture
def test_hedge_ratio_perfect_hedge():
    a = np.random.default_rng(1).normal(0, 0.01, 60)
    hr = QT.hedge_ratio(a, a)
    assert hr["ratio"] == pytest.approx(1.0)
    assert hr["corr"] == pytest.approx(1.0)
    assert hr["resid_vol_pct"] == pytest.approx(0.0, abs=1e-6)


def test_hedge_ratio_uncorrelated_is_useless():
    rng = np.random.default_rng(2)
    hr = QT.hedge_ratio(rng.normal(0, 0.01, 500), rng.normal(0, 0.01, 500))
    assert abs(hr["corr"]) < 0.2
    assert hr["resid_vol_pct"] > 90.0


def test_hedge_candidates_sorted_by_correlation(market):
    tk = market.top_companies(n=1)[0]["ticker"]
    cands = QT.hedge_candidates(market, tk, n=5)
    assert len(cands) == 5
    assert tk not in [c for c, _ in cands]
    corrs = [c for _, c in cands]
    assert corrs == sorted(corrs, reverse=True)
