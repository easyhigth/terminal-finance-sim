"""Tests de l'analyse de portefeuille (core/analytics.py)."""
from core import analytics, bonds, market
from core.game_state import PlayerState


def _mk():
    m = market.Market(seed=12345)
    m.sync_to(market.WARMUP_STEPS)
    p = PlayerState(continent="Europe", cash=500_000.0)
    return p, m


def test_empty_portfolio_summary():
    p, m = _mk()
    s = analytics.summary(p, m)
    assert s["n_positions"] == 0
    assert s["invested"] == 0.0
    assert s["rows"] == []


def test_holdings_table_aggregates_classes():
    p, m = _mk()
    for c in m.companies[:3]:
        p.portfolio[c["ticker"]] = {"shares": 100, "avg": m.price_of(c["ticker"])}
    bonds.buy_bond(p, m, bonds.BONDS[0]["id"], 10)
    rows = analytics.holdings_table(p, m)
    classes = {r["cls"] for r in rows}
    assert "Actions" in classes and "Obligations" in classes
    # les poids somment ~100 %
    assert abs(sum(r["weight"] for r in rows) - 100.0) < 1e-6


def test_summary_weights_and_concentration():
    p, m = _mk()
    for c in m.companies[:4]:
        p.portfolio[c["ticker"]] = {"shares": 500, "avg": m.price_of(c["ticker"]) * 0.9}
    s = analytics.summary(p, m)
    assert s["n_positions"] == 4
    assert 0 < s["top_weight"] <= 100
    assert s["effective_positions"] > 1     # diversifié sur plusieurs lignes
    assert "Actions" in s["by_class"]


def test_max_drawdown():
    assert analytics.max_drawdown([100, 120, 90, 110]) == 25.0   # pic 120 -> creux 90
    assert analytics.max_drawdown([]) == 0.0
    assert analytics.max_drawdown([100]) == 0.0


def test_correlation_and_frontier_need_two_equities():
    p, m = _mk()
    p.portfolio[m.companies[0]["ticker"]] = {"shares": 100, "avg": 10}
    labels, _ = analytics.correlation(p, m)
    assert labels == []                       # < 2 actions
    assert analytics.equity_frontier(p, m) is None
    # avec 3 actions : corrélation et frontière disponibles
    for c in m.companies[1:3]:
        p.portfolio[c["ticker"]] = {"shares": 100, "avg": m.price_of(c["ticker"])}
    labels, corr = analytics.correlation(p, m)
    assert len(labels) == 3 and corr.shape == (3, 3)
    fr = analytics.equity_frontier(p, m)
    assert fr is not None and len(fr["vols"]) > 0
