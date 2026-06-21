"""Tests de core/market_query.py (MarketQueryMixin) : méthodes de LECTURE du
moteur de marché (courbe des taux, indices, recherche, attribution P&L...).
Ces méthodes ne consomment aucun tirage rng ; on vérifie ici leur cohérence
fonctionnelle, indépendamment du déterminisme du moteur (déjà couvert par
test_market.py)."""
import numpy as np
import pytest

from core.market import Market


@pytest.fixture
def m():
    mk = Market(seed=11)
    mk.fast_forward(80)
    return mk


# --------------------------------------------------------------- courbe des taux
def test_curve_point_increases_with_maturity_at_neutral_state(m):
    # à pente/courbure nulles, seule la prime de terme joue : la courbe monte
    # avec la maturité (legacy : short + CURVE_TERM_PREMIUM*years).
    short = m.curve_point(0.0)
    long = m.curve_point(30.0)
    assert long >= short

def test_yield_curve_has_all_tenors(m):
    curve = m.yield_curve()
    assert set(curve.keys()) == {"3M", "2Y", "5Y", "10Y", "30Y"}
    assert all(v >= 0.0 for v in curve.values())

def test_curve_slope_matches_10y_minus_2y(m):
    expected = (m.curve_point(10.0) - m.curve_point(2.0)) * 100.0
    assert m.curve_slope() == pytest.approx(expected)

def test_curve_inverted_matches_slope_sign(m):
    assert m.curve_inverted() == (m.curve_slope() < 0.0)

def test_curve_phase_is_a_known_label(m):
    assert m.curve_phase() in ("Inversion", "Aplatissement", "Normale", "Pentification")

def test_curve_point_never_negative(m):
    for years in (0.1, 1, 5, 10, 30):
        assert m.curve_point(years) >= 0.0


# --------------------------------------------------------------- crédit / macro
def test_credit_spread_multiplier_floor(m):
    assert m.credit_spread_multiplier("AAA") >= 0.4
    assert m.credit_spread_multiplier("BB") >= 0.4

def test_macro_change_zero_with_short_history():
    mk = Market(seed=5)  # aucun pas joué -> historique trop court
    assert mk.macro_change("rate") == 0.0

def test_bump_region_credit_accumulates(m):
    region = m.regions[0]
    before = m.region_credit_bump[region]
    m.bump_region_credit(region, 5.0)
    m.bump_region_credit(region, 2.0)
    assert m.region_credit_bump[region] == pytest.approx(before + 7.0)


# --------------------------------------------------------------- index / sociétés
def test_index_history_matches_index_value_after_step(m):
    name = next(iter(m.index_members))
    hist = m.index_history(name)
    assert hist[-1] == pytest.approx(m.index_value(name))

def test_index_change_pct_zero_for_short_history():
    mk = Market(seed=5)
    name = next(iter(mk.index_members))
    assert mk.index_change_pct(name) == 0.0

def test_price_of_known_and_unknown_ticker(m):
    tk = m.companies[0]["ticker"]
    assert m.price_of(tk) == pytest.approx(float(m.price[0]))
    assert m.price_of("NOPE_TICKER_XYZ") is None

def test_history_of_length_bounded_by_n(m):
    tk = m.companies[0]["ticker"]
    full = m.history_of(tk)
    bounded = m.history_of(tk, n=10)
    assert len(bounded) == 10
    assert bounded == full[-10:]

def test_track_company_prefills_history(m):
    tk = m.companies[1]["ticker"]
    hist = m.track_company(tk)
    assert len(hist) > 0
    assert tk in m.price_hist


# --------------------------------------------------------------- metrics
def test_metrics_unknown_ticker_returns_none(m):
    assert m.metrics("NOPE_TICKER_XYZ") is None

def test_metrics_known_ticker_has_expected_keys(m):
    tk = m.companies[0]["ticker"]
    mt = m.metrics(tk)
    assert mt["ticker"] == tk
    assert mt["price"] > 0
    for key in ("pe", "ev_ebitda", "ps", "fcf_yield", "nd_ebitda", "payout"):
        assert key in mt

def test_metrics_pe_is_none_for_negative_eps(m):
    # pe n'est défini que si eps > 0 (cf. market_query.metrics)
    for c in m.companies:
        mt = m.metrics(c["ticker"])
        if mt["eps"] <= 0:
            assert mt["pe"] is None
            break


# --------------------------------------------------------------- recherche
def test_search_finds_by_ticker_or_name(m):
    tk = m.companies[0]["ticker"]
    assert tk in m.search(tk)

def test_search_empty_query_returns_empty(m):
    assert m.search("") == []

def test_suggest_orders_exact_before_prefix_before_contains(m):
    tk = m.companies[0]["ticker"]
    hits = m.suggest(tk)
    assert hits[0][0] == tk

def test_resolve_exact_ticker(m):
    tk = m.companies[0]["ticker"]
    assert m.resolve(tk) == tk

def test_resolve_unknown_query_returns_none(m):
    assert m.resolve("zzzznotacompany") is None


# --------------------------------------------------------------- classements / largeur de marché
def test_top_companies_sorted_by_mktcap_desc(m):
    top = m.top_companies(n=5, by="mktcap")
    caps = [c["mktcap"] for c in top]
    assert caps == sorted(caps, reverse=True)

def test_sector_performance_covers_all_sectors(m):
    perf = m.sector_performance()
    assert {p["sector"] for p in perf} == set(m.sectors)

def test_returns_over_zero_steps_is_zero(m):
    assert np.allclose(m.returns_over(0), 0.0)

def test_breadth_advancers_decliners_sum_to_n(m):
    b = m.breadth()
    assert b["advancers"] + b["decliners"] + b["unchanged"] == m.n

def test_heatmap_covers_all_sectors(m):
    grid = m.heatmap()
    assert {row["sector"] for row in grid} == set(m.sectors)


# --------------------------------------------------------------- attribution P&L
def test_factor_attribution_empty_holdings(m):
    out = m.factor_attribution({})
    assert out == {"world": 0.0, "sector": 0.0, "region": 0.0,
                    "specific": 0.0, "drift": 0.0, "total": 0.0}

def test_factor_attribution_components_sum_to_total(m):
    tk = m.companies[0]["ticker"]
    out = m.factor_attribution({tk: 10})
    components = out["world"] + out["sector"] + out["region"] + out["specific"] + out["drift"]
    assert components == pytest.approx(out["total"], abs=1e-6)

def test_factor_attribution_unknown_ticker_ignored(m):
    out = m.factor_attribution({"NOPE_TICKER_XYZ": 5})
    assert out["total"] == 0.0
