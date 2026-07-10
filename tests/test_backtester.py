"""Tests du backtesteur de stratégies (core/backtester.py) — logique pure,
sans pygame. Vérifie l'absence de biais de future (look-ahead), les cas
limites, et la cohérence des métriques (Sharpe/drawdown/exposition)."""
import numpy as np
import pytest

from core import backtester as bt
from core import market as market_mod
from core.market import Market


def test_buy_hold_matches_benchmark_exactly():
    prices = [100.0, 105.0, 95.0, 110.0, 120.0]
    r = bt.run_backtest(prices, strategy="buy_hold")
    assert r["total_return"] == pytest.approx(r["benchmark_return"])
    assert r["exposure"] == 1.0


def test_short_history_returns_none():
    assert bt.run_backtest([100.0, 101.0], strategy="buy_hold") is None
    assert bt.run_backtest([], strategy="buy_hold") is None


def test_unknown_strategy_returns_none():
    assert bt.run_backtest([100.0, 101.0, 102.0], strategy="nope") is None


def test_sma_crossover_is_flat_before_enough_data():
    # avec slow=20, aucune position n'est prise avant le pas 19
    prices = list(100.0 + np.cumsum(np.random.RandomState(1).normal(0, 1, 30)))
    r = bt.run_backtest(prices, strategy="sma_crossover", fast=5, slow=20)
    assert r["positions"][:18] == [0.0] * 18


def test_momentum_signal_has_no_lookahead_bias():
    """Le signal en t ne doit dépendre QUE des prix jusqu'à t : décaler le
    futur (après t) ne doit rien changer au signal en t."""
    rng = np.random.RandomState(0)
    prices = list(100.0 + np.cumsum(rng.normal(0, 1, 40)))
    sig_full = bt.momentum_signal(prices, lookback=10)
    truncated = prices[:25]
    sig_truncated = bt.momentum_signal(truncated, lookback=10)
    assert list(sig_full[:25]) == list(sig_truncated)


def test_mean_reversion_buys_the_dip():
    # série qui plonge nettement sous sa moyenne récente au dernier point
    prices = [100.0] * 20 + [80.0]
    sig = bt.mean_reversion_signal(prices, z_lookback=20, entry_z=-1.0)
    assert sig[-1] == 1.0


def test_equity_curve_length_matches_positions():
    prices = [100.0, 101.0, 99.0, 103.0, 105.0, 104.0]
    r = bt.run_backtest(prices, strategy="momentum", lookback=2)
    assert len(r["equity"]) == len(r["positions"]) == len(prices) - 1


def test_max_drawdown_is_non_positive():
    prices = [100.0, 120.0, 80.0, 90.0, 130.0]
    r = bt.run_backtest(prices, strategy="buy_hold")
    assert r["max_drawdown"] <= 0.0


def test_flat_strategy_has_zero_sharpe_and_return():
    prices = [100.0, 101.0, 102.0, 103.0]

    def _never(prices, **kw):
        return [0.0] * len(prices)

    bt.STRATEGIES["_never_for_test"] = _never
    try:
        r = bt.run_backtest(prices, strategy="_never_for_test")
        assert r["total_return"] == 0.0
        assert r["sharpe"] == 0.0
        assert r["exposure"] == 0.0
    finally:
        del bt.STRATEGIES["_never_for_test"]


def test_backtest_ticker_uses_real_market_prehistory():
    m = Market(seed=5)
    m.sync_to(market_mod.WARMUP_STEPS)
    tk = m.top_companies(n=1)[0]["ticker"]
    r = bt.backtest_ticker(m, tk, strategy="momentum", lookback=10)
    assert r is not None
    assert r["n"] > 300  # 5 ans de préhistoire (~365 pas) au minimum


def test_backtest_ticker_unknown_ticker_is_none():
    m = Market(seed=5)
    assert bt.backtest_ticker(m, "NOT_A_TICKER", strategy="buy_hold") is None
