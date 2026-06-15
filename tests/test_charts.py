"""Tests des calculs de graphes (core/charts.py) et de la préhistoire du marché."""
import math
import numpy as np

from core import charts, market


# ----------------------------------------------------------------- préhistoire
def test_warmup_gives_five_years_of_history():
    m = market.Market(seed=4242)
    m.sync_to(market.WARMUP_STEPS)
    assert m.step_count == market.WARMUP_STEPS
    tk = m.companies[0]["ticker"]
    hist = m.history_of(tk)
    # ~5 ans de points disponibles dès le « jour 1 » de carrière
    assert len(hist) >= market.WARMUP_STEPS
    assert all(p > 0 for p in hist)


def test_history_is_deterministic():
    a = market.Market(seed=99); a.sync_to(market.WARMUP_STEPS)
    b = market.Market(seed=99); b.sync_to(market.WARMUP_STEPS)
    tk = a.companies[3]["ticker"]
    assert a.history_of(tk) == b.history_of(tk)


def test_history_capped_at_hist_len():
    m = market.Market(seed=7)
    m.sync_to(market.HIST_LEN + 50)
    assert len(m.price_hist_all) == market.HIST_LEN


def test_history_of_unknown_ticker_is_empty():
    m = market.Market(seed=1)
    assert m.history_of("ZZZ_NOPE") == []


# ------------------------------------------------------------------- normalize
def test_normalize_base_zero():
    out = charts.normalize([100, 110, 90])
    assert out[0] == 0.0
    assert abs(out[1] - 10.0) < 1e-9
    assert abs(out[2] - (-10.0)) < 1e-9


def test_normalize_empty_and_zero_base():
    assert charts.normalize([]) == []
    assert charts.normalize([0, 1, 2]) == [0.0, 0.0, 0.0]


# --------------------------------------------------------------------- returns
def test_simple_returns():
    r = charts.simple_returns([100, 110, 99])
    assert abs(r[0] - 0.1) < 1e-9
    assert abs(r[1] - (-0.1)) < 1e-9
    assert len(r) == 2


# ------------------------------------------------------------------------- vol
def test_rolling_vol_constant_series_is_zero():
    vol = charts.rolling_vol([100] * 30, window=10)
    # aucune variation -> vol nulle là où définie
    assert all(v == 0.0 for v in vol if v is not None)


def test_rolling_vol_alignment_and_positivity():
    series = [100, 101, 99, 103, 98, 105, 97, 106, 96, 108, 95, 110]
    vol = charts.rolling_vol(series, window=5)
    assert len(vol) == len(series)
    assert vol[0] is None
    assert any(v is not None and v > 0 for v in vol)


# ---------------------------------------------------------------------- spread
def test_spread_ratio_and_diff():
    assert charts.spread([10, 20], [2, 4], mode="ratio") == [5.0, 5.0]
    assert charts.spread([10, 20], [2, 4], mode="diff") == [8.0, 16.0]


# ------------------------------------------------------------------------ beta
def test_ols_beta_perfect_linear():
    x = [0.01, -0.02, 0.03, -0.01, 0.02]
    y = [2 * v for v in x]          # beta exact = 2, alpha = 0
    beta, alpha, r2 = charts.ols_beta(y, x)
    assert abs(beta - 2.0) < 1e-9
    assert abs(alpha) < 1e-9
    assert abs(r2 - 1.0) < 1e-9


def test_ols_beta_too_few_points():
    assert charts.ols_beta([0.01], [0.01]) == (0.0, 0.0, 0.0)


# --------------------------------------------------------------- corrélation
def test_correlation_matrix_perfect():
    base = [100, 102, 101, 105, 103, 108]
    labels, corr = charts.correlation_matrix({"A": base, "B": base})
    assert labels == ["A", "B"]
    assert abs(corr[0, 1] - 1.0) < 1e-9


def test_correlation_matrix_diagonal_is_one():
    a = [100, 101, 99, 102, 98]
    b = [50, 49, 51, 48, 52]
    _, corr = charts.correlation_matrix({"A": a, "B": b})
    assert abs(corr[0, 0] - 1.0) < 1e-9
    assert abs(corr[1, 1] - 1.0) < 1e-9


# --------------------------------------------------------------- courbe taux
def test_yield_curve_is_increasing_with_maturity():
    m = market.Market(seed=5)
    m.sync_to(market.WARMUP_STEPS)
    curve = charts.yield_curve(m, "AAA")
    ys = [y for _, y in curve]
    assert ys == sorted(ys)        # prime de terme -> courbe croissante
    assert all(y > 0 for y in ys)
