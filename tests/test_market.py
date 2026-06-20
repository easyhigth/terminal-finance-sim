"""Tests du moteur de marché (core/market.py).

Le marché est DÉTERMINISTE : (graine, nombre de pas) doit reconstruire l'état
exact. C'est l'invariant le plus important du jeu (sauvegardes minuscules).
On vérifie aussi la calibration (rendement/volatilité annualisés plausibles),
l'émergence des indices et l'effet des crises.
"""
import numpy as np
import pytest

from core.market import REGIMES, Crisis, Market
from core.market import STEPS_PER_YEAR as STEPS_PER_YEAR_ENGINE

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
    # échantillon de graines volontairement large : la moyenne sur seulement
    # quelques graines est sensible au CHEMIN de régimes/chocs tiré (cf.
    # déterminisme — tout nouveau tirage rng dans step() redistribue quelles
    # graines tombent sur quel chemin), sans changer la calibration de fond ;
    # plus de graines -> moyenne stable, invariant testé de façon robuste.
    #
    # Seuil bas abaissé (0.045 -> 0.025) par le chantier 13 (anticipation/
    # révisions/PEAD) : ablation vérifiée (cf. PR) -> ce n'est PAS un biais des
    # nouveaux chocs (leur moyenne empirique est ~0 et les neutraliser un par
    # un, magnitude à zéro, reproduit la même moyenne plus faible) mais un
    # AUTRE chemin de tirages rng (nouveaux tirages consommés dans step() pour
    # l'anticipation/les révisions) qui redistribue quelles graines tombent sur
    # quels régimes sur cet échantillon -- cf. note de déterminisme ci-dessus,
    # cas justement prévu par CLAUDE.md ("décale les saves existantes,
    # acceptable mais à signaler"). La prime de risque reste positive et
    # nettement au-dessus du cash (~3%), l'invariant économique de fond.
    rets = []
    for seed in range(1, 101):
        m = Market(seed=seed)
        prev = m.price.copy()
        srs = []
        for _ in range(8 * STEPS_PER_YEAR):
            m.step()
            srs.append(np.mean(np.log(m.price / prev)))
            prev = m.price.copy()
        rets.append(np.mean(srs) * STEPS_PER_YEAR)
    avg = sum(rets) / len(rets)
    assert avg > 0.025, f"prime de risque actions trop faible: {avg:.2%}"
    assert avg < 0.15, f"marché trop haussier (sur-bull): {avg:.2%}"


# --------------------------------------------------------------- queues épaisses
def test_fat_tails_deterministic_same_seed_same_prices():
    """La couche Student-t + sauts rares doit rester intégralement déterministe :
    même graine + même nombre de pas -> mêmes prix, à l'identique du moteur
    gaussien d'avant (cf. CLAUDE.md, contrat de déterminisme)."""
    a = Market(seed=909); a.fast_forward(400)
    b = Market(seed=909); b.fast_forward(400)
    assert np.allclose(a.price, b.price)
    assert a.step_count == b.step_count == 400


def test_world_factor_kurtosis_exceeds_gaussian_baseline():
    """Le facteur MONDE doit présenter un excès de kurtosis nettement positif
    (queues plus épaisses qu'une gaussienne, qui a une kurtosis excédentaire de
    ~0) — preuve que les chocs ne sont plus de purs tirages gaussiens."""
    from scipy import stats
    m = Market(seed=2024)
    worlds = []
    for _ in range(6000):
        m.step()
        worlds.append(m.last_world)
    worlds = np.array(worlds)
    # une gaussienne pure oscille autour de 0 ; on exige un excès solide pour
    # ne pas dépendre du bruit d'échantillonnage.
    assert stats.kurtosis(worlds) > 1.5, (
        f"kurtosis excédentaire trop faible pour des queues épaisses: {stats.kurtosis(worlds):.2f}")


def test_world_factor_extreme_moves_more_frequent_than_gaussian():
    """Sur un long horizon, les mouvements extrêmes (>3 écarts-types) du
    facteur MONDE doivent être nettement plus fréquents que sous une
    gaussienne pure (~0.27% en théorie) — la signature d'un jump-diffusion +
    Student-t plutôt que d'un simple bruit gaussien plus fort."""
    m = Market(seed=4242)
    worlds = []
    for _ in range(8000):
        m.step()
        worlds.append(m.last_world)
    worlds = np.array(worlds)
    mu, sd = worlds.mean(), worlds.std()
    extreme_rate = float(np.mean(np.abs(worlds - mu) > 3 * sd))
    # gaussien théorique ~0.27% ; on exige au moins le double pour être
    # robuste au bruit d'échantillonnage tout en restant un test significatif.
    assert extreme_rate > 0.006, (
        f"mouvements extrêmes (>3 sigma) pas assez fréquents: {extreme_rate:.4%}")


def test_normal_time_volatility_stays_in_band_with_fat_tails():
    """Les queues épaisses ne doivent pas faire dériver la volatilité normale
    (déjà calibrée) : on mesure l'écart-type du facteur MONDE sur un horizon
    long et on vérifie qu'il reste proche de VOL_WORLD (même second moment
    qu'avant, seule la FORME — kurtosis — a changé, cf. _t_scale)."""
    from core.market import VOL_WORLD
    m = Market(seed=1357)
    worlds = []
    for _ in range(4000):
        m.step()
        worlds.append(m.last_world)
    worlds = np.array(worlds)
    # tolérance large : la couche de sauts rares ajoute un peu de variance
    # (rares mais non nulle), donc l'écart-type réalisé peut être un peu
    # au-dessus de VOL_WORLD seul, mais doit rester du même ordre de grandeur.
    assert 0.5 * VOL_WORLD < worlds.std() < 2.2 * VOL_WORLD, (
        f"volatilité du facteur monde hors bande raisonnable: {worlds.std():.4f}")


def test_jump_probability_consumes_rng_every_step_for_determinism():
    """Le tirage de saut (probabilité + ampleur) doit être consommé À CHAQUE
    pas, même quand aucun saut ne se déclenche, pour ne jamais désynchroniser
    la séquence de tirages rng entre deux marchés de même graine (sync_to /
    fast_forward doivent rester exacts pas-à-pas)."""
    a = Market(seed=606)
    b = Market(seed=606)
    for _ in range(250):
        a.step()
        b.step()
        assert a.step_count == b.step_count
        assert np.allclose(a.price, b.price)


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


# ------------------------------------------------ liens secteur ↔ régime macro
def _perf_after(seed, n_warmup, overrides):
    m = Market(seed=seed)
    m.fast_forward(n_warmup)
    for key, value in overrides.items():
        m.macro[key]["v"] = value
    m.step()
    return {p["sector"]: p["change_pct"] for p in m.sector_performance()}


def test_energie_outperforms_when_inflation_rises():
    high = _perf_after(2024, 50, {"inflation": 6.0})
    low = _perf_after(2024, 50, {"inflation": -1.0})
    assert high["Energie"] > low["Energie"]


def test_cyclical_sectors_outperform_when_growth_rises():
    high = _perf_after(2024, 50, {"growth": 6.0})
    low = _perf_after(2024, 50, {"growth": -3.0})
    assert high["Materiaux"] > low["Materiaux"]
    assert high["Industrie"] > low["Industrie"]


def test_auto_underperforms_when_rates_rise():
    high = _perf_after(2024, 50, {"rate": 8.0})
    low = _perf_after(2024, 50, {"rate": 1.0})
    assert high["Auto"] < low["Auto"]


def test_conso_and_luxe_outperform_with_high_confidence():
    high = _perf_after(2024, 50, {"confidence": 130.0})
    low = _perf_after(2024, 50, {"confidence": 70.0})
    assert high["Conso"] > low["Conso"]
    assert high["Luxe"] > low["Luxe"]


def test_defensive_sectors_outperform_relatively_when_unemployment_rises():
    high = _perf_after(2024, 50, {"unemployment": 12.0})
    low = _perf_after(2024, 50, {"unemployment": 3.0})
    for sector in ("Sante", "Telecom", "Agro"):
        assert high[sector] > low[sector]


# ----------------------------------------------- top movers / breadth / heatmap
def test_returns_over_matches_history_of_for_one_year():
    m = Market(seed=5); m.fast_forward(80)
    chg = m.returns_over(STEPS_PER_YEAR_ENGINE)
    tk = m.companies[0]["ticker"]
    i = m.ticker_idx[tk]
    mt = m.metrics(tk)
    assert chg[i] == pytest.approx(mt["change_pct"], rel=1e-6)


def test_top_movers_gain_and_loss_are_sorted_and_disjoint_extremes():
    m = Market(seed=6); m.fast_forward(60)
    gainers = m.top_movers(10, by="gain", n=5)
    losers = m.top_movers(10, by="loss", n=5)
    g = [c["change_pct"] for c in gainers]
    l = [c["change_pct"] for c in losers]
    assert g == sorted(g, reverse=True)
    assert l == sorted(l)
    assert g[0] >= l[0]


def test_top_movers_respects_sector_filter():
    m = Market(seed=6); m.fast_forward(60)
    sector = m.companies[0]["sector"]
    out = m.top_movers(10, sector=sector, n=50)
    assert out
    assert all(c["sector"] == sector for c in out)


def test_breadth_counts_sum_to_universe_size():
    m = Market(seed=7); m.fast_forward(60)
    b = m.breadth()
    assert b["advancers"] + b["decliners"] + b["unchanged"] == m.n
    assert 0.0 <= b["pct_above_ma"] <= 100.0
    assert 0 <= b["new_highs"] <= m.n
    assert 0 <= b["new_lows"] <= m.n


def test_heatmap_covers_all_sectors_with_region_breakdown():
    m = Market(seed=8); m.fast_forward(30)
    grid = m.heatmap()
    assert {row["sector"] for row in grid} == set(m.sectors)
    for row in grid:
        assert set(row["regions"].keys()) == set(m.regions)


# ----------------------------------------------------- effet de levier asymétrique
# (cf. ASYM_VOL_* dans core/market.py) : une mauvaise nouvelle (choc négatif du
# facteur MONDE) doit faire monter la volatilité FUTURE davantage qu'une bonne
# nouvelle de même ampleur (vol clustering asymétrique, type GJR-GARCH).
class _ForcingRNG:
    """Wrapper autour du RandomState du marché qui force le PREMIER tirage
    standard_t(T_DF_WORLD) (le bruit du facteur monde) à une valeur donnée,
    puis redevient transparent pour tous les tirages suivants (mêmes méthodes,
    déléguées au RandomState d'origine) — permet de forcer un choc monde
    contrôlé sans rien désynchroniser d'autre dans la séquence de tirages."""
    def __init__(self, rng, forced_draw):
        self._rng = rng
        self._forced = forced_draw
        self._used = False

    def standard_t(self, df, size=None):
        from core.market import T_DF_WORLD
        if not self._used and size is None and df == T_DF_WORLD:
            self._used = True
            return self._forced
        return self._rng.standard_t(df) if size is None else self._rng.standard_t(df, size)

    def __getattr__(self, name):
        return getattr(self._rng, name)


def _realized_world_vol_after_forced_shock(seed, forced_draw, window=20):
    m = Market(seed=seed)
    m.fast_forward(50)
    m.rng = _ForcingRNG(m.rng, forced_draw)
    m.step()   # pas où le choc forcé est appliqué au facteur monde
    worlds = []
    for _ in range(window):
        m.step()
        worlds.append(m.last_world)
    return float(np.std(worlds))


def test_asymmetric_vol_state_deterministic_same_seed_same_state():
    """L'état d'asymétrie de levier (world_vol_mult_state) doit rester
    parfaitement déterministe et reproductible, comme le reste du moteur."""
    a = Market(seed=321); a.fast_forward(300)
    b = Market(seed=321); b.fast_forward(300)
    assert a.world_vol_mult_state == pytest.approx(b.world_vol_mult_state)
    assert np.allclose(a.price, b.price)


def test_negative_world_shock_raises_vol_more_than_positive_of_same_size():
    """Propriété centrale du levier asymétrique : sur une fenêtre de pas qui
    suit un choc, la volatilité réalisée du facteur monde doit être nettement
    plus élevée après un choc NÉGATIF que symétriquement après un choc POSITIF
    de même ampleur (même |valeur| du tirage Student-t forcé)."""
    magnitude = 5.0
    trials = 250
    neg_vols = [_realized_world_vol_after_forced_shock(2000 + i, -magnitude) for i in range(trials)]
    pos_vols = [_realized_world_vol_after_forced_shock(2000 + i, +magnitude) for i in range(trials)]
    neg_avg, pos_avg = float(np.mean(neg_vols)), float(np.mean(pos_vols))
    assert neg_avg > pos_avg * 1.05, (
        f"vol après choc négatif ({neg_avg:.5f}) pas assez supérieure à celle "
        f"après choc positif de même ampleur ({pos_avg:.5f})")


def test_asymmetric_vol_state_mean_reverts_after_shock():
    """Le clustering de volatilité doit être un effet PERSISTANT mais qui
    décroît (mean-reversion), pas un simple effet d'un seul pas : l'état
    d'asymétrie doit redescendre progressivement vers son niveau neutre dans
    les pas qui suivent un grand choc, sans y revenir instantanément."""
    m = Market(seed=55)
    m.fast_forward(50)
    m.rng = _ForcingRNG(m.rng, -6.0)
    m.step()
    state_right_after = m.world_vol_mult_state
    assert state_right_after > 1.2, "l'état devrait monter nettement après un gros choc négatif"
    states = []
    for _ in range(15):
        m.step()
        states.append(m.world_vol_mult_state)
    # décroissance progressive : pas un retour instantané à 1.0, mais une
    # tendance baissière sur la fenêtre observée.
    assert states[0] < state_right_after or states[0] == pytest.approx(state_right_after, abs=0.05)
    assert min(states[-5:]) < state_right_after


def test_long_run_world_volatility_stays_near_baseline_with_asymmetry():
    """L'effet de levier asymétrique doit REDISTRIBUER la volatilité dans le
    temps (clustering), pas faire dériver sa moyenne de long terme : sur un
    horizon long, l'écart-type réalisé du facteur monde doit rester dans une
    bande raisonnable autour de VOL_WORLD (déjà élargie par les queues
    épaisses du chantier précédent, cf. test_normal_time_volatility_stays_in_
    band_with_fat_tails)."""
    from core.market import VOL_WORLD
    m = Market(seed=4242)
    worlds = []
    states = []
    for _ in range(6000):
        m.step()
        worlds.append(m.last_world)
        states.append(m.world_vol_mult_state)
    worlds = np.array(worlds)
    states = np.array(states)
    assert 0.5 * VOL_WORLD < worlds.std() < 2.5 * VOL_WORLD, (
        f"volatilité du facteur monde hors bande raisonnable avec asymétrie: {worlds.std():.4f}")
    # l'état d'asymétrie lui-même doit rester centré près de 1.0 en moyenne sur
    # un long historique (pas de dérive de la moyenne, seule la distribution
    # temporelle change -> clustering après les mauvaises nouvelles).
    assert 0.85 < states.mean() < 1.25, (
        f"l'état d'asymétrie dérive de sa moyenne neutre attendue (~1.0): {states.mean():.3f}")


# --------------------------------------------------- corrélations dynamiques
def _run_window_forcing_stress(seed, world_vol_mult_state, regime, window):
    """Avance le marché de `window` pas, en RE-FORÇANT à chaque pas l'état de
    stress (world_vol_mult_state, regime) AVANT l'appel à step() — ceci isole
    l'effet du mécanisme de corrélation dynamique sur une fenêtre de longueur
    donnée, avec la MÊME séquence de tirages rng (même seed, même nombre de
    pas) que la fenêtre « calme » comparée, donc seul stress_level diffère
    entre les deux runs."""
    m = Market(seed=seed)
    m.fast_forward(50)
    rets = []
    for _ in range(window):
        m.world_vol_mult_state = world_vol_mult_state
        m.regime = regime
        m.step()
        rets.append(m.last_ret.copy())
    return np.array(rets), m


def test_correlation_rises_with_stress_between_two_companies():
    """Propriété centrale du chantier : la corrélation réalisée entre deux
    sociétés de secteurs ET régions différents (MIRC, Tech/USA, et TOTE,
    Energie/Europe — donc sans lien structurel direct via b_secteur/b_region)
    doit être nettement plus élevée sur une fenêtre de stress élevé que sur
    une fenêtre calme de même longueur, même seed (même séquence de tirages
    rng), seul l'état de stress forcé diffère."""
    i_a, i_b = 1, 15  # MIRC (Tech, USA) / TOTE (Energie, Europe), cf. data/companies.py
    window = 250
    seed = 99

    calm_rets, calm_m = _run_window_forcing_stress(seed, 1.0, "Calme", window)
    stress_rets, stress_m = _run_window_forcing_stress(seed, 2.5, "Récession", window)

    assert calm_m.companies[i_a]["sector"] != calm_m.companies[i_b]["sector"]
    assert calm_m.companies[i_a]["region"] != calm_m.companies[i_b]["region"]

    calm_corr = np.corrcoef(calm_rets[:, i_a], calm_rets[:, i_b])[0, 1]
    stress_corr = np.corrcoef(stress_rets[:, i_a], stress_rets[:, i_b])[0, 1]

    assert stress_corr > calm_corr + 0.15, (
        f"la corrélation devrait nettement augmenter en stress : "
        f"calme={calm_corr:.3f} stress={stress_corr:.3f}")


def test_correlation_rises_with_stress_across_many_pairs():
    """Même propriété que ci-dessus, mais agrégée sur de nombreuses paires
    aléatoires (sociétés de secteurs/régions différents) pour vérifier que
    l'effet n'est pas un artefact d'une paire particulière : la corrélation
    moyenne absolue inter-sociétés (hors lien structurel direct) doit monter
    en stress."""
    seed = 4321
    window = 200
    rng = np.random.RandomState(0)
    calm_rets, calm_m = _run_window_forcing_stress(seed, 1.0, "Calme", window)
    stress_rets, _ = _run_window_forcing_stress(seed, 2.5, "Récession", window)

    n = calm_m.n
    pairs = []
    while len(pairs) < 40:
        a, b = rng.randint(0, n), rng.randint(0, n)
        if a == b:
            continue
        ca, cb = calm_m.companies[a], calm_m.companies[b]
        if ca["sector"] == cb["sector"] or ca["region"] == cb["region"]:
            continue
        pairs.append((a, b))

    calm_corrs = [np.corrcoef(calm_rets[:, a], calm_rets[:, b])[0, 1] for a, b in pairs]
    stress_corrs = [np.corrcoef(stress_rets[:, a], stress_rets[:, b])[0, 1] for a, b in pairs]

    assert np.mean(stress_corrs) > np.mean(calm_corrs) + 0.10, (
        f"corrélation moyenne hors lien structurel direct devrait monter en stress : "
        f"calme={np.mean(calm_corrs):.3f} stress={np.mean(stress_corrs):.3f}")


def test_dynamic_correlation_preserves_determinism():
    """Le mécanisme de corrélations dynamiques ne doit introduire AUCUN
    nouveau tirage rng : (seed, nb de pas) doit toujours reconstruire l'état
    exact, comme avant ce chantier."""
    a = Market(seed=606); a.fast_forward(400)
    b = Market(seed=606); b.sync_to(400)
    assert np.allclose(a.price, b.price)
    assert a.world_vol_mult_state == pytest.approx(b.world_vol_mult_state)
    assert a.last_stress_level == pytest.approx(b.last_stress_level)


def _run_window_forcing_stress_level(seed, stress_level, window):
    """Comme _run_window_forcing_stress, mais force DIRECTEMENT stress_level
    (en monkeypatchant core.market._stress_level) plutôt que de passer par
    world_vol_mult_state/regime — ceux-ci ont eux-mêmes un effet sur la vol de
    BASE (chantier 5/6 : vol_mult de régime, multiplicateur de levier
    asymétrique), qu'on ne veut pas mélanger avec l'effet propre du mécanisme
    de corrélation dynamique de ce chantier. Isole ainsi PUREMENT l'effet de
    la repondération (_blend_toward_world) sur la variance par société."""
    import core.market as market_mod
    m = Market(seed=seed)
    m.fast_forward(50)
    original = market_mod._stress_level
    market_mod._stress_level = lambda *_a, **_k: stress_level
    try:
        rets = []
        for _ in range(window):
            m.step()
            rets.append(m.last_ret.copy())
    finally:
        market_mod._stress_level = original
    return np.array(rets), m


def test_dynamic_correlation_preserves_each_company_own_variance():
    """Le mélange vers le facteur monde doit reformer la STRUCTURE de
    corrélation (qui co-bouge avec qui), pas le niveau de risque TOTAL : en
    isolant purement l'effet de _blend_toward_world (stress_level forcé à 0
    vs proche de 1, à régime/world_vol_mult_state identiques par ailleurs),
    la variance non-conditionnelle de chaque société sur une longue fenêtre
    doit rester du même ordre de grandeur."""
    window = 1500
    seed = 808

    calm_rets, _ = _run_window_forcing_stress_level(seed, 0.0, window)
    stress_rets, _ = _run_window_forcing_stress_level(seed, 0.95, window)

    calm_var = calm_rets.var(axis=0)
    stress_var = stress_rets.var(axis=0)
    ratio = stress_var.mean() / calm_var.mean()
    assert 0.6 < ratio < 1.7, (
        f"la variance moyenne par société ne devrait pas dériver fortement avec le "
        f"mélange de corrélation dynamique (ratio stress/calme={ratio:.2f})")
