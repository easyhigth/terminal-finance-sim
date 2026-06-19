"""Tests de l'attribution de performance (core/attribution.py)."""
import pytest

from core import attribution
from core.game_state import PlayerState
from core.market import Market


def _mk():
    m = Market(seed=77)
    m.fast_forward(10)
    p = PlayerState()
    return p, m


def test_sector_and_region_attribution_sum_to_total_price_pnl():
    p, m = _mk()
    tickers = [m.companies[i]["ticker"] for i in (0, 50, 150)]
    for tk in tickers:
        p.portfolio[tk] = {"shares": 100, "avg": m.price_of(tk)}
    m.step()
    sector = attribution.sector_attribution(p, m)
    region = attribution.region_attribution(p, m)
    expected = sum(100 * (m.price[m.ticker_idx[tk]] - m.prev_price[m.ticker_idx[tk]])
                   for tk in tickers)
    assert sum(sector.values()) == pytest.approx(expected, rel=1e-9, abs=1e-6)
    assert sum(region.values()) == pytest.approx(expected, rel=1e-9, abs=1e-6)


def test_style_attribution_buckets_into_growth_and_value():
    p, m = _mk()
    tickers = [m.companies[i]["ticker"] for i in range(20)]
    for tk in tickers:
        p.portfolio[tk] = {"shares": 10, "avg": m.price_of(tk)}
    m.step()
    style = attribution.style_attribution(p, m)
    assert set(style.keys()) <= {"Croissance", "Valeur"}


def test_selection_timing_attribution_matches_factor_attribution():
    p, m = _mk()
    tickers = [m.companies[i]["ticker"] for i in (0, 50, 150)]
    for tk in tickers:
        p.portfolio[tk] = {"shares": 100, "avg": m.price_of(tk)}
    m.step()
    st = attribution.selection_timing_attribution(p, m)
    agg = m.factor_attribution({tk: 100 for tk in tickers})
    assert st["selection"] == pytest.approx(agg["specific"])
    assert st["timing"] == pytest.approx(agg["world"] + agg["drift"])
    assert st["total"] == pytest.approx(agg["total"])


def test_empty_portfolio_attribution_is_empty():
    p, m = _mk()
    assert attribution.sector_attribution(p, m) == {}
    assert attribution.region_attribution(p, m) == {}
    st = attribution.selection_timing_attribution(p, m)
    assert st["total"] == 0.0
