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


def test_recovery_time_no_drawdown():
    assert analytics.recovery_time([]) == 0
    assert analytics.recovery_time([100]) == 0
    assert analytics.recovery_time([100, 110, 120]) == 0


def test_recovery_time_measures_steps_to_new_peak():
    # pic à 120 (index 1), creux à 90 (index 2), récupération à 130 (index 4)
    assert analytics.recovery_time([100, 120, 90, 110, 130]) == 2


def test_recovery_time_none_when_not_recovered():
    assert analytics.recovery_time([100, 120, 90, 110]) is None


def test_tracking_error_zero_with_short_history():
    p, m = _mk()
    assert analytics.tracking_error(p, m) == 0.0


def test_tracking_error_in_summary():
    p, m = _mk()
    p.cash_history = [500_000.0 + i * 1000 for i in range(10)]
    s = analytics.summary(p, m)
    assert "tracking_error" in s
    assert s["tracking_error"] >= 0.0


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


def test_holdings_table_has_avg_liquidity_and_contributions():
    p, m = _mk()
    for c in m.companies[:2]:
        p.portfolio[c["ticker"]] = {"shares": 100, "avg": m.price_of(c["ticker"])}
    bonds.buy_bond(p, m, "CORP_HY", 10)
    rows = analytics.holdings_table(p, m)
    for r in rows:
        assert "avg" in r and "liquidity" in r
        assert r["liquidity"] in ("Liquide", "Peu liquide", "Illiquide")
        assert "risk_contribution_pct" in r and "perf_contribution_pct" in r
    assert abs(sum(r["risk_contribution_pct"] for r in rows) - 100.0) < 1e-6


def test_summary_has_net_exposure_and_by_liquidity():
    p, m = _mk()
    for c in m.companies[:3]:
        p.portfolio[c["ticker"]] = {"shares": 200, "avg": m.price_of(c["ticker"])}
    s = analytics.summary(p, m)
    assert "net_exposure" in s and "by_liquidity" in s
    assert s["net_exposure"] > 0   # tout long ici
    assert sum(s["by_liquidity"].values()) > 0
