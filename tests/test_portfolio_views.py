"""Tests dédiés à core/portfolio_views.py (reporting : positions, P&L,
allocation, dividendes, bêta net).

Ce module est lecture pure (aucune modification d'état). On construit des
scénarios réalistes via core.portfolio (buy/sell/short/cover) puis on
appelle directement core.portfolio_views.xxx pour vérifier les calculs.
"""
import pytest

from core import portfolio as pf
from core import portfolio_views as pv
from core.game_state import PlayerState
from core.market import Market


def _setup(grade_index=8, cash=1_000_000.0):
    m = Market(seed=999)
    p = PlayerState()
    p.grade_index = grade_index
    p.cash = cash
    return p, m


def _set_price(m, tk, price):
    m.price[m.ticker_idx[tk]] = price


# --------------------------------------------------------------- holdings
def test_holdings_returns_expected_fields_for_long_position():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.buy(p, m, tk, 50)
    avg = p.portfolio[tk]["avg"]   # prix d'exécution réel (spread + impact inclus)
    _set_price(m, tk, 120.0)
    hs = pv.holdings(p, m)
    assert len(hs) == 1
    h = hs[0]
    assert h["ticker"] == tk
    assert h["shares"] == 50
    assert h["avg"] == pytest.approx(avg)
    assert h["price"] == pytest.approx(120.0)
    assert h["value"] == pytest.approx(120.0 * 50)
    assert h["pnl"] == pytest.approx((120.0 - avg) * 50)
    assert h["pnl_pct"] == pytest.approx((120.0 / avg - 1) * 100)
    assert h["short"] is False


def test_holdings_pnl_pct_sign_correct_for_short():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.short(p, m, tk, 50)
    avg = p.portfolio[tk]["avg"]
    _set_price(m, tk, 80.0)        # le cours baisse -> le short gagne
    h = pv.holdings(p, m)[0]
    assert h["short"] is True
    assert h["pnl"] == pytest.approx((80.0 - avg) * (-50))
    assert h["pnl"] > 0
    assert h["pnl_pct"] == pytest.approx((avg / 80.0 - 1) * 100)
    assert h["pnl_pct"] > 0


def test_holdings_sorted_by_absolute_value_descending():
    p, m = _setup(cash=10_000_000.0)
    tk_small = m.companies[0]["ticker"]
    tk_big = m.companies[1]["ticker"]
    _set_price(m, tk_small, 10.0)
    _set_price(m, tk_big, 10.0)
    pf.buy(p, m, tk_small, 5)
    pf.buy(p, m, tk_big, 500)
    hs = pv.holdings(p, m)
    assert hs[0]["ticker"] == tk_big
    assert hs[1]["ticker"] == tk_small


def test_holdings_empty_when_no_positions():
    p, m = _setup()
    assert pv.holdings(p, m) == []


# --------------------------------------------------------------- unrealized_pnl
def test_unrealized_pnl_matches_price_diff_times_shares_long():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 50.0)
    pf.buy(p, m, tk, 200)
    avg = p.portfolio[tk]["avg"]
    _set_price(m, tk, 65.0)
    assert pv.unrealized_pnl(p, m) == pytest.approx((65.0 - avg) * 200)


def test_unrealized_pnl_sign_correct_for_short():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 50.0)
    pf.short(p, m, tk, 200)
    avg = p.portfolio[tk]["avg"]
    _set_price(m, tk, 65.0)         # le cours monte -> le short perd
    assert pv.unrealized_pnl(p, m) == pytest.approx((65.0 - avg) * (-200))
    assert pv.unrealized_pnl(p, m) < 0


def test_unrealized_pnl_aggregates_across_positions():
    p, m = _setup(cash=1_000_000.0)
    tk1 = m.companies[0]["ticker"]
    tk2 = m.companies[1]["ticker"]
    _set_price(m, tk1, 100.0)
    _set_price(m, tk2, 50.0)
    pf.buy(p, m, tk1, 10)
    pf.short(p, m, tk2, 20)
    avg1 = p.portfolio[tk1]["avg"]
    avg2 = p.portfolio[tk2]["avg"]
    _set_price(m, tk1, 110.0)
    _set_price(m, tk2, 40.0)
    expected = (110.0 - avg1) * 10 + (40.0 - avg2) * (-20)
    assert pv.unrealized_pnl(p, m) == pytest.approx(expected)


def test_unrealized_pnl_zero_when_no_positions():
    p, m = _setup()
    assert pv.unrealized_pnl(p, m) == pytest.approx(0.0)


# --------------------------------------------------------------- allocation_by
def test_allocation_by_sector_sums_to_gross_exposure():
    p, m = _setup(cash=1_000_000.0)
    tk1 = m.companies[0]["ticker"]
    tk2 = m.companies[1]["ticker"]
    _set_price(m, tk1, 100.0)
    _set_price(m, tk2, 50.0)
    pf.buy(p, m, tk1, 30)
    pf.short(p, m, tk2, 10)
    agg = pv.allocation_by(p, m, "sector")
    assert sum(agg.values()) == pytest.approx(pf.gross_exposure(p, m))


def test_allocation_by_groups_correctly_per_key():
    p, m = _setup(cash=1_000_000.0)
    tk1 = m.companies[0]["ticker"]
    tk2 = m.companies[1]["ticker"]
    sector1 = m.companies[0]["sector"]
    sector2 = m.companies[1]["sector"]
    _set_price(m, tk1, 100.0)
    _set_price(m, tk2, 50.0)
    pf.buy(p, m, tk1, 30)   # 3000 d'expo
    pf.buy(p, m, tk2, 20)   # 1000 d'expo
    agg = pv.allocation_by(p, m, "sector")
    if sector1 == sector2:
        assert agg[sector1] == pytest.approx(4000.0)
    else:
        assert agg[sector1] == pytest.approx(3000.0)
        assert agg[sector2] == pytest.approx(1000.0)


def test_allocation_by_region_uses_absolute_exposure_for_shorts():
    p, m = _setup(cash=1_000_000.0)
    tk = m.companies[0]["ticker"]
    region = m.companies[0]["region"]
    _set_price(m, tk, 100.0)
    pf.short(p, m, tk, 25)
    agg = pv.allocation_by(p, m, "region")
    assert agg[region] == pytest.approx(100.0 * 25)


def test_allocation_by_empty_when_no_positions():
    p, m = _setup()
    assert pv.allocation_by(p, m, "sector") == {}


# --------------------------------------------------------------- sector_heatmap
def test_sector_heatmap_aggregates_value_and_pnl_per_sector():
    p, m = _setup(cash=1_000_000.0)
    tk1 = m.companies[0]["ticker"]
    tk2 = m.companies[1]["ticker"]
    sector1 = m.companies[0]["sector"]
    sector2 = m.companies[1]["sector"]
    _set_price(m, tk1, 100.0)
    _set_price(m, tk2, 50.0)
    pf.buy(p, m, tk1, 10)
    pf.buy(p, m, tk2, 10)
    avg1, avg2 = p.portfolio[tk1]["avg"], p.portfolio[tk2]["avg"]
    _set_price(m, tk1, 120.0)
    _set_price(m, tk2, 40.0)
    exp_value1, exp_pnl1 = 120.0 * 10, (120.0 - avg1) * 10
    exp_value2, exp_pnl2 = 40.0 * 10, (40.0 - avg2) * 10
    heat = pv.sector_heatmap(p, m)
    by_sector = {a["sector"]: a for a in heat}
    if sector1 == sector2:
        a = by_sector[sector1]
        assert a["value"] == pytest.approx(exp_value1 + exp_value2)
        assert a["pnl"] == pytest.approx(exp_pnl1 + exp_pnl2)
    else:
        assert by_sector[sector1]["value"] == pytest.approx(exp_value1)
        assert by_sector[sector1]["pnl"] == pytest.approx(exp_pnl1)
        assert by_sector[sector2]["value"] == pytest.approx(exp_value2)
        assert by_sector[sector2]["pnl"] == pytest.approx(exp_pnl2)


def test_sector_heatmap_sorted_by_absolute_value_descending():
    p, m = _setup(cash=1_000_000.0)
    tk1, tk2, tk3 = (m.companies[i]["ticker"] for i in range(3))
    _set_price(m, tk1, 100.0)
    _set_price(m, tk2, 100.0)
    _set_price(m, tk3, 100.0)
    pf.buy(p, m, tk1, 5)
    pf.buy(p, m, tk2, 30)
    pf.buy(p, m, tk3, 10)
    heat = pv.sector_heatmap(p, m)
    values = [abs(a["value"]) for a in heat]
    assert values == sorted(values, reverse=True)


def test_sector_heatmap_handles_short_positions():
    p, m = _setup(cash=1_000_000.0)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.short(p, m, tk, 10)
    avg = p.portfolio[tk]["avg"]
    _set_price(m, tk, 80.0)  # le short gagne quand le prix baisse
    heat = pv.sector_heatmap(p, m)
    a = heat[0]
    assert a["value"] == pytest.approx(-800.0)
    assert a["pnl"] == pytest.approx((avg - 80.0) * 10)
    assert a["pnl"] > 0


def test_sector_heatmap_empty_when_no_positions():
    p, m = _setup()
    assert pv.sector_heatmap(p, m) == []


# ------------------------------------------------------- holdings_correlation
def test_holdings_correlation_empty_when_no_positions():
    p, m = _setup()
    labels, corr = pv.holdings_correlation(p, m)
    assert labels == []
    assert corr.shape == (0, 0)


def test_holdings_correlation_empty_with_single_position():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.buy(p, m, tk, 10)
    labels, corr = pv.holdings_correlation(p, m)
    assert labels == []
    assert corr.shape == (0, 0)


def test_holdings_correlation_returns_matrix_for_two_equity_positions():
    p, m = _setup()
    for _ in range(5):
        m.step()
    tk1, tk2 = m.companies[0]["ticker"], m.companies[1]["ticker"]
    _set_price(m, tk1, 100.0)
    _set_price(m, tk2, 50.0)
    pf.buy(p, m, tk1, 10)
    pf.buy(p, m, tk2, 10)
    labels, corr = pv.holdings_correlation(p, m)
    assert set(labels) == {tk1, tk2}
    assert corr.shape == (2, 2)
    assert corr[0, 0] == pytest.approx(1.0)
    assert corr[1, 1] == pytest.approx(1.0)
    assert corr[0, 1] == pytest.approx(corr[1, 0])


# --------------------------------------------------------------- dividends
def test_dividends_long_position_receives_expected_payout():
    p, m = _setup(cash=1_000_000.0)
    tk = next(c["ticker"] for c in m.companies if c["div_yield"] > 0)
    div_yield = next(c["div_yield"] for c in m.companies if c["ticker"] == tk)
    _set_price(m, tk, 100.0)
    pf.buy(p, m, tk, 100)
    d = pv.dividends(p, m, days=90)
    expected = 100.0 * 100 * div_yield * (90 / 365.0)
    assert d == pytest.approx(expected)
    assert d > 0


def test_dividends_short_position_pays_negative():
    p, m = _setup(cash=1_000_000.0)
    tk = next(c["ticker"] for c in m.companies if c["div_yield"] > 0)
    _set_price(m, tk, 100.0)
    pf.short(p, m, tk, 100)
    d = pv.dividends(p, m, days=90)
    assert d < 0


def test_dividends_zero_when_no_positions():
    p, m = _setup()
    assert pv.dividends(p, m, days=90) == pytest.approx(0.0)


def test_dividends_scale_with_days():
    p, m = _setup(cash=1_000_000.0)
    tk = next(c["ticker"] for c in m.companies if c["div_yield"] > 0)
    _set_price(m, tk, 100.0)
    pf.buy(p, m, tk, 100)
    d30 = pv.dividends(p, m, days=30)
    d60 = pv.dividends(p, m, days=60)
    assert d60 == pytest.approx(d30 * 2, rel=1e-9)


# --------------------------------------------------------------- portfolio_beta
def test_portfolio_beta_zero_when_no_positions():
    p, m = _setup()
    assert pv.portfolio_beta(p, m) == pytest.approx(0.0)


def test_portfolio_beta_matches_single_position_weighted_beta():
    p, m = _setup(cash=1_000_000.0)
    tk = m.companies[0]["ticker"]
    beta = m.companies[0]["beta"]
    _set_price(m, tk, 100.0)
    pf.buy(p, m, tk, 50)
    eq = pf.net_worth(p, m)
    expected = (100.0 * 50 / eq) * beta
    assert pv.portfolio_beta(p, m) == pytest.approx(expected)


def test_portfolio_beta_short_reduces_net_market_exposure():
    p, m = _setup(cash=1_000_000.0)
    tk1 = m.companies[0]["ticker"]
    tk2 = m.companies[1]["ticker"]
    _set_price(m, tk1, 100.0)
    _set_price(m, tk2, 100.0)
    pf.buy(p, m, tk1, 50)
    beta_long_only = pv.portfolio_beta(p, m)
    pf.short(p, m, tk2, 50)
    beta_with_short = pv.portfolio_beta(p, m)
    # ajouter un short de poids comparable réduit le bêta net (vers 0, voire négatif)
    assert beta_with_short < beta_long_only


def test_portfolio_beta_is_weighted_average_across_positions():
    p, m = _setup(cash=1_000_000.0)
    tk1 = m.companies[0]["ticker"]
    tk2 = m.companies[1]["ticker"]
    beta1 = m.companies[0]["beta"]
    beta2 = m.companies[1]["beta"]
    _set_price(m, tk1, 100.0)
    _set_price(m, tk2, 50.0)
    pf.buy(p, m, tk1, 30)
    pf.buy(p, m, tk2, 20)
    eq = pf.net_worth(p, m)
    expected = (100.0 * 30 / eq) * beta1 + (50.0 * 20 / eq) * beta2
    assert pv.portfolio_beta(p, m) == pytest.approx(expected)
