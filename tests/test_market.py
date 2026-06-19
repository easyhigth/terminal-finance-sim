"""Tests du moteur de marché (core/market.py).

Le marché est DÉTERMINISTE : (graine, nombre de pas) doit reconstruire l'état
exact. C'est l'invariant le plus important du jeu (sauvegardes minuscules).
On vérifie aussi la calibration (rendement/volatilité annualisés plausibles),
l'émergence des indices et l'effet des crises.
"""
import numpy as np
import pytest

from core.market import REGIMES, Crisis, Market

STEPS_PER_YEAR = 52  # un pas de marché ≈ une semaine (cf. market.py)


# --------------------------------------------------------------- déterminisme
def test_same_seed_same_prices():
    a = Market(seed=42); a.fast_forward(60)
    b = Market(seed=42); b.fast_forward(60)
    assert np.allclose(a.price, b.price)
    assert a.macro["rate"]["v"] == pytest.approx(b.macro["rate"]["v"])


def test_different_seed_diverges():
    a = Market(seed=1); a.fast_forward(60)
    b = Market(seed=2); b.fast_forward(60)
    assert not np.allclose(a.price, b.price)


def test_sync_to_reconstructs_exact_state():
    # avancer d'un coup jusqu'au pas N == avancer pas à pas jusqu'à N
    ref = Market(seed=7); ref.fast_forward(40)
    rebuilt = Market(seed=7); rebuilt.sync_to(40)
    assert rebuilt.step_count == 40
    assert np.allclose(ref.price, rebuilt.price)


def test_sync_to_is_noop_when_already_ahead():
    m = Market(seed=7); m.fast_forward(40)
    snapshot = m.price.copy()
    m.sync_to(10)  # demande inférieure : ne doit rien faire
    assert np.allclose(m.price, snapshot)
    assert m.step_count == 40


# --------------------------------------------------------------- robustesse
def test_prices_stay_finite_and_positive():
    m = Market(seed=123)
    m.fast_forward(500)  # long horizon : pas de NaN/inf ni de prix négatif
    assert np.all(np.isfinite(m.price))
    assert np.all(m.price > 0)


def test_macro_stays_within_bounds():
    m = Market(seed=99)
    m.fast_forward(300)
    macro = m.macro
    assert 0.0 <= macro["rate"]["v"] <= 12.0
    assert -2.0 <= macro["inflation"]["v"] <= 15.0
    assert 50.0 <= macro["confidence"]["v"] <= 140.0
    assert 20.0 <= macro["credit_ig"]["v"] <= 400.0
    assert 100.0 <= macro["credit_hy"]["v"] <= 1500.0
    assert 10.0 <= macro["liquidity"]["v"] <= 100.0


# --------------------------------------------------------------- courbe des taux
def test_yield_curve_is_increasing_at_neutral_regime():
    m = Market(seed=3)
    curve = m.yield_curve()
    tenors = ["3M", "2Y", "5Y", "10Y", "30Y"]
    values = [curve[t] for t in tenors]
    assert values == sorted(values)   # pentue/normale par défaut (régime Calme)


def test_curve_point_matches_legacy_term_premium_at_neutral_state():
    """À l'état neutre (régime Calme, croissance == mean macro 2.0), la courbe se
    réduit à l'ancienne prime de terme fixe (0.15%/an) : pas de régression sur
    les niveaux de rendement déjà calibrés."""
    m = Market(seed=3)
    m.macro["growth"]["v"] = 2.0
    short = m.macro["rate"]["v"] / 100.0
    for years in (0.25, 2.0, 10.0, 30.0):
        assert m.curve_point(years) == pytest.approx(short + 0.0015 * years)


def test_curve_inverts_under_recession_conditions():
    m = Market(seed=3)
    m.regime = "Récession"
    m.macro["growth"]["v"] = -4.0
    assert m.curve_slope() < 0.0
    assert m.curve_inverted()
    assert m.curve_phase() == "Inversion"


def test_curve_steepens_under_expansion_conditions():
    m = Market(seed=3)
    m.regime = "Expansion"
    m.macro["growth"]["v"] = 5.0
    assert m.curve_slope() > 1.0
    assert m.curve_phase() == "Pentification"


# --------------------------------------------------------- crédit & liquidité
def test_credit_spreads_widen_under_recession_stress():
    m = Market(seed=11)
    base_ig, base_hy = m.macro["credit_ig"]["v"], m.macro["credit_hy"]["v"]
    m.macro["growth"]["v"] = -3.0
    m.macro["unemployment"]["v"] = 9.0
    for _ in range(40):
        m._step_credit_liquidity()
    assert m.macro["credit_ig"]["v"] > base_ig
    assert m.macro["credit_hy"]["v"] > base_hy
    # le HY se tend toujours plus que l'IG en conditions de stress
    assert (m.macro["credit_hy"]["v"] - base_hy) > (m.macro["credit_ig"]["v"] - base_ig)


def test_liquidity_drops_when_credit_hy_widens():
    m = Market(seed=11)
    base_liq = m.macro["liquidity"]["v"]
    m.macro["growth"]["v"] = -3.0
    m.macro["unemployment"]["v"] = 9.0
    m.regime = "Volatil"
    for _ in range(150):
        m._step_credit_liquidity()
    assert m.macro["liquidity"]["v"] < base_liq


def test_credit_spread_multiplier_reacts_to_macro_state():
    m = Market(seed=11)
    assert m.credit_spread_multiplier("AAA") == pytest.approx(1.0, abs=1e-6)
    assert m.credit_spread_multiplier("B") == pytest.approx(1.0, abs=1e-6)
    m.macro["credit_hy"]["v"] = 760.0   # double du niveau de référence
    assert m.credit_spread_multiplier("B") == pytest.approx(2.0, abs=1e-6)
    assert m.credit_spread_multiplier("AAA") == pytest.approx(1.0, abs=1e-6)   # IG inchangé


def test_step_macro_does_not_consume_extra_rng_draws_for_credit():
    """Le crédit/la liquidité sont dérivés sans tirage rng propre : deux marchés
    de même graine doivent rester synchronisés sur les autres indicateurs."""
    a, b = Market(seed=55), Market(seed=55)
    a.fast_forward(10)
    b.fast_forward(10)
    assert a.macro["rate"]["v"] == pytest.approx(b.macro["rate"]["v"])
    assert a.macro["credit_hy"]["v"] == pytest.approx(b.macro["credit_hy"]["v"])


# --------------------------------------------------------------- indices
def test_index_emerges_from_constituents():
    m = Market(seed=5)
    name = m.index_defs[0][0]
    members = m.index_members[name]
    # la valeur de l'indice == somme capi des membres × échelle
    cap = float(np.sum(m.price[members] * m.shares[members]))
    assert m.index_value(name) == pytest.approx(cap * m.index_scale[name])


def test_index_history_grows_with_steps():
    m = Market(seed=5)
    name = m.index_defs[0][0]
    before = len(m.index_history(name))
    m.fast_forward(10)
    assert len(m.index_history(name)) == before + 10


# --------------------------------------------------------------- calibration
def test_annualized_return_and_vol_in_target_range():
    """Le marché doit produire un rendement/volatilité plausibles.

    Cible annoncée : ~+10-15 %/an, ~19 % de vol. On laisse des bornes larges
    pour rester robuste, mais on attrape toute dérive grossière (bull infini,
    vol absurde) qui casserait l'équilibrage.
    """
    m = Market(seed=2024)
    n_steps = 5 * STEPS_PER_YEAR
    # collecte des rendements log agrégés (moyenne des sociétés par pas)
    step_rets = []
    prev = m.price.copy()
    for _ in range(n_steps):
        m.step()
        step_rets.append(np.mean(np.log(m.price / prev)))
        prev = m.price.copy()
    step_rets = np.array(step_rets)

    ann_ret = step_rets.mean() * STEPS_PER_YEAR
    ann_vol = step_rets.std() * np.sqrt(STEPS_PER_YEAR)

    assert 0.0 < ann_ret < 0.35, f"rendement annualisé hors cible: {ann_ret:.2%}"
    assert 0.05 < ann_vol < 0.40, f"volatilité annualisée hors cible: {ann_vol:.2%}"


def test_equity_risk_premium_positive_across_seeds():
    """Invariant d'équilibrage : en MOYENNE sur plusieurs graines, l'action
    rapporte nettement plus que le cash (~3%) — prime de risque positive, sans
    sur-bull (équités > obligations > cash)."""
    rets = []
    for seed in (1, 7, 42, 99, 123, 256, 2024, 555):
        m = Market(seed=seed)
        prev = m.price.copy()
        srs = []
        for _ in range(8 * STEPS_PER_YEAR):
            m.step()
            srs.append(np.mean(np.log(m.price / prev)))
            prev = m.price.copy()
        rets.append(np.mean(srs) * STEPS_PER_YEAR)
    avg = sum(rets) / len(rets)
    assert avg > 0.045, f"prime de risque actions trop faible: {avg:.2%}"
    assert avg < 0.15, f"marché trop haussier (sur-bull): {avg:.2%}"


# --------------------------------------------------------------- crises
def test_crisis_depresses_prices():
    base = Market(seed=321); base.fast_forward(20)
    shocked = Market(seed=321); shocked.fast_forward(20)
    # un choc mondial fortement négatif sur plusieurs pas
    shocked.add_crisis(Crisis("krach test", steps=5, world=-0.05, vol_mult=2.0))
    base.fast_forward(5)
    shocked.fast_forward(5)
    # en moyenne, le marché choqué vaut nettement moins que le marché de base
    assert shocked.price.mean() < base.price.mean()


def test_crisis_expires():
    m = Market(seed=321)
    m.add_crisis(Crisis("court", steps=3, world=-0.02))
    assert len(m.crises) == 1
    m.fast_forward(3)
    assert len(m.crises) == 0  # la crise a expiré


# --------------------------------------------------------------- attribution
def test_factor_attribution_sums_to_total():
    m = Market(seed=77)
    m.fast_forward(10)
    # un panier de 3 sociétés
    tickers = [m.companies[i]["ticker"] for i in (0, 50, 150)]
    holdings = {tk: 100 for tk in tickers}
    m.step()
    attr = m.factor_attribution(holdings)
    parts = attr["world"] + attr["sector"] + attr["region"] + attr["specific"] + attr["drift"]
    # la somme des composantes égale exactement le P&L total
    assert parts == pytest.approx(attr["total"], rel=1e-9, abs=1e-6)
    # le P&L total == variation de valeur des positions sur le pas
    expected = sum(100 * (m.price[m.ticker_idx[tk]] - m.prev_price[m.ticker_idx[tk]])
                   for tk in tickers)
    assert attr["total"] == pytest.approx(expected, rel=1e-9, abs=1e-6)


def test_factor_attribution_empty_before_any_step():
    m = Market(seed=77)
    attr = m.factor_attribution({m.companies[0]["ticker"]: 10})
    assert attr["total"] == 0.0  # aucun pas joué -> pas d'attribution


# --------------------------------------------------------------- régimes
def test_regime_always_valid_and_reconstructed():
    a = Market(seed=8); a.fast_forward(80)
    b = Market(seed=8); b.sync_to(80)
    assert a.regime in REGIMES
    assert a.regime == b.regime  # régime reconstruit via (graine, pas)


def test_regimes_visited_over_long_horizon():
    m = Market(seed=2024)
    seen = set()
    for _ in range(3000):
        m.step()
        seen.add(m.regime)
    # sur un long horizon, plusieurs régimes différents apparaissent
    assert len(seen) >= 2


# --------------------------------------------------------------- earnings
def test_earnings_season_is_staggered_and_quarterly():
    m = Market(seed=44)
    reporters = set()
    for _ in range(13):  # un trimestre = 13 pas (EARN_PERIOD)
        m.step()
        # chaque pas, une fraction des sociétés publie (~ n/13)
        assert 0 < len(m.last_earnings) <= m.n
        reporters.update(r["ticker"] for r in m.last_earnings)
    # sur un trimestre complet (13 pas), toutes les sociétés ont publié une fois
    assert len(reporters) == m.n


def test_earnings_are_deterministic():
    a = Market(seed=44); a.fast_forward(30)
    b = Market(seed=44); b.fast_forward(30)
    assert a.earnings_log == b.earnings_log


def test_earnings_evolve_fundamentals_and_margins_bounded():
    m = Market(seed=44)
    tk = m.companies[0]["ticker"]
    i = m.ticker_idx[tk]
    rev0 = float(m.revenue[i])
    m.fast_forward(40)
    assert float(m.revenue[i]) != rev0  # le CA a bougé via les résultats
    # les marges restent dans les bornes autour du profil de base
    assert (0.4 * m._base_net_margin[i] - 1e-9
            <= m.net_margin[i] <= 1.6 * m._base_net_margin[i] + 1e-9)


def test_metrics_reflect_dynamic_fundamentals():
    m = Market(seed=44)
    tk = m.companies[0]["ticker"]
    m.fast_forward(40)
    mt = m.metrics(tk)
    assert mt["revenue"] == pytest.approx(float(m.revenue[m.ticker_idx[tk]]))
    assert "last_earnings" in mt


# --------------------------------------------------------------- requêtes
def test_metrics_and_price_lookup():
    m = Market(seed=11)
    tk = m.companies[0]["ticker"]
    assert m.price_of(tk) == pytest.approx(float(m.price[m.ticker_idx[tk]]))
    mt = m.metrics(tk)
    assert mt["ticker"] == tk
    assert mt["mktcap"] > 0
    # un ticker inconnu renvoie None proprement
    assert m.price_of("ZZZINEXISTANT") is None
    assert m.metrics("ZZZINEXISTANT") is None


# --------------------------------------------------------------- recherche
def test_resolve_exact_ticker():
    m = Market(seed=3)
    tk = m.companies[0]["ticker"]
    assert m.resolve(tk) == tk
    assert m.resolve(tk.lower()) == tk


def test_resolve_by_name_fragment():
    m = Market(seed=3)
    c = m.companies[10]
    frag = c["name"].split()[0][:4]          # fragment du nom
    assert m.resolve(frag) is not None       # résout vers une société


def test_resolve_unknown_returns_none():
    m = Market(seed=3)
    assert m.resolve("zzzznope") is None
    assert m.resolve("") is None


def test_suggest_ranks_exact_first():
    m = Market(seed=3)
    tk = m.companies[5]["ticker"]
    sug = m.suggest(tk)
    assert sug and sug[0][0] == tk
    assert len(sug) <= 8


# --------------------------------------------------------------- secteurs / top
def test_sector_performance_covers_all_sectors_and_sums_companies():
    m = Market(seed=3); m.fast_forward(5)
    perf = m.sector_performance()
    assert {p["sector"] for p in perf} == set(m.sectors)
    assert sum(p["n"] for p in perf) == m.n
    # trié du plus fort au plus faible
    assert all(perf[i]["change_pct"] >= perf[i + 1]["change_pct"] for i in range(len(perf) - 1))


def test_top_companies_filters_by_sector():
    m = Market(seed=3)
    sector = m.companies[0]["sector"]
    out = m.top_companies(sector=sector, n=50)
    assert out
    assert all(c["sector"] == sector for c in out)
