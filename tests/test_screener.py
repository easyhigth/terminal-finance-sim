"""Tests du screener actions/ETF et de la vue de comparaison (core/screener.py)."""
from core import screener as S
from core.market import Market


def _setup():
    m = Market(seed=2024)
    m.fast_forward(60)
    return m


def test_screen_stocks_respects_region_and_sector_filters():
    m = _setup()
    region = m.companies[0]["region"]
    sector = m.companies[0]["sector"]
    out = S.screen_stocks(m, region=region, sector=sector, limit=100)
    assert out
    assert all(c["region"] == region and c["sector"] == sector for c in out)


def test_screen_stocks_cap_bounds_are_respected():
    m = _setup()
    out = S.screen_stocks(m, cap_min=10_000.0, cap_max=1_000_000.0, limit=200)
    assert out
    assert all(10_000.0 <= c["mktcap"] <= 1_000_000.0 for c in out)


def test_screen_stocks_pe_max_excludes_expensive_names():
    m = _setup()
    out = S.screen_stocks(m, pe_max=15.0, limit=200)
    assert all(c["pe"] is not None and c["pe"] <= 15.0 for c in out)


def test_screen_stocks_beta_max_excludes_volatile_names():
    m = _setup()
    out = S.screen_stocks(m, beta_max=0.8, limit=200)
    assert all(c["beta"] <= 0.8 for c in out)


def test_screen_etfs_category_filter():
    m = _setup()
    out = S.screen_etfs(m, category="bond", limit=50)
    assert out
    assert all(q["category"] == "bond" for q in out)


def test_screen_etfs_region_filter_only_matches_equity_etfs_in_region():
    m = _setup()
    out = S.screen_etfs(m, region="USA", limit=50)
    assert out
    ids = {q["id"] for q in out}
    assert "USA" in ids


def test_screen_etfs_duration_filters_only_apply_to_bonds():
    m = _setup()
    out = S.screen_etfs(m, duration_min=15.0, limit=50)
    assert out
    assert all(q["category"] == "bond" for q in out)


def test_screen_etfs_rating_min_excludes_high_yield():
    m = _setup()
    out = S.screen_etfs(m, rating_min="A", limit=50)
    assert all(q["id"] != "HYG" for q in out)


def test_screen_etfs_expense_max_filter():
    m = _setup()
    out = S.screen_etfs(m, expense_max=0.0010, limit=50)
    assert out
    assert all(q["expense"] <= 0.0010 for q in out)


def test_compare_stocks_preserves_order_and_skips_unknown():
    m = _setup()
    tickers = [m.companies[0]["ticker"], "INVALID_TICKER", m.companies[1]["ticker"]]
    out = S.compare_stocks(m, tickers)
    assert [c["ticker"] for c in out] == [tickers[0], tickers[2]]


def test_compare_etfs_preserves_order_and_skips_unknown():
    m = _setup()
    out = S.compare_etfs(m, ["SPX", "NOPE", "GOV"])
    assert [q["id"] for q in out] == ["SPX", "GOV"]
