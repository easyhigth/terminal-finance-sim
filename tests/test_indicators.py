"""Tests pour core/indicators.py — indicateurs techniques (logique pure)."""
import math

from core.indicators import sma, ema, bollinger_bands, rsi


# ----------------------------------------------------------------- fixtures
SIMPLE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
CONST = [50.0] * 30
SHORT = [1.0, 2.0, 3.0]


# --------------------------------------------------------------------- sma
def test_sma_values():
    out = sma(SIMPLE, 3)
    assert out[0] is None and out[1] is None
    assert out[2] == 2.0      # (1+2+3)/3
    assert out[3] == 3.0      # (2+3+4)/3
    assert out[-1] == 9.0     # (8+9+10)/3


def test_sma_length_matches_input():
    for period in (1, 3, 5, 20):
        assert len(sma(SIMPLE, period)) == len(SIMPLE)


def test_sma_short_series_no_crash():
    out = sma(SHORT, 14)
    assert len(out) == len(SHORT)
    assert all(v is None for v in out)


# --------------------------------------------------------------------- ema
def test_ema_known_values():
    # EMA(3) sur [1..10] : seed = SMA des 3 premiers = 2.0, puis alpha = 0.5
    out = ema(SIMPLE, 3)
    assert out[0] is None and out[1] is None
    assert out[2] == 2.0
    assert out[3] == (4 * 0.5 + 2.0 * 0.5)   # 3.0
    assert out[4] == (5 * 0.5 + out[3] * 0.5)  # 4.0


def test_ema_length_matches_input():
    for period in (1, 3, 5, 20):
        assert len(ema(SIMPLE, period)) == len(SIMPLE)


def test_ema_short_series_no_crash():
    out = ema(SHORT, 14)
    assert len(out) == len(SHORT)
    assert all(v is None for v in out)


# ------------------------------------------------------------- bollinger
def test_bollinger_length_and_order():
    lower, mid, upper = bollinger_bands(SIMPLE, period=3, num_std=2.0)
    assert len(lower) == len(mid) == len(upper) == len(SIMPLE)
    for lo, m, hi in zip(lower, mid, upper):
        if m is not None:
            assert lo <= m <= hi


def test_bollinger_constant_series_zero_width():
    lower, mid, upper = bollinger_bands(CONST, period=5, num_std=2.0)
    for lo, m, hi in zip(lower, mid, upper):
        if m is not None:
            assert math.isclose(lo, m)
            assert math.isclose(hi, m)


def test_bollinger_short_series_no_crash():
    lower, mid, upper = bollinger_bands(SHORT, period=20, num_std=2.0)
    assert len(lower) == len(mid) == len(upper) == len(SHORT)
    assert all(v is None for v in mid)


# -------------------------------------------------------------------- rsi
def test_rsi_in_range():
    series = [10, 11, 9, 12, 13, 8, 14, 15, 7, 16, 17, 6, 18, 19, 5, 20]
    out = rsi(series, period=14)
    assert len(out) == len(series)
    for v in out:
        if v is not None:
            assert 0.0 <= v <= 100.0


def test_rsi_constant_series_no_division_by_zero():
    out = rsi(CONST, period=14)
    assert len(out) == len(CONST)
    for v in out:
        if v is not None:
            assert v == 50.0
            assert 0.0 <= v <= 100.0


def test_rsi_short_series_no_crash():
    out = rsi(SHORT, period=14)
    assert len(out) == len(SHORT)
    assert all(v is None for v in out)


def test_rsi_uptrend_above_50():
    series = [float(x) for x in range(1, 30)]   # monotone croissant
    out = rsi(series, period=14)
    last = [v for v in out if v is not None][-1]
    assert last > 50.0


def test_rsi_downtrend_below_50():
    series = [float(x) for x in range(30, 1, -1)]   # monotone décroissant
    out = rsi(series, period=14)
    last = [v for v in out if v is not None][-1]
    assert last < 50.0
