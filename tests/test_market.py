"""Tests du moteur de marché (core/market.py).

Le marché est DÉTERMINISTE : (graine, nombre de pas) doit reconstruire l'état
exact. C'est l'invariant le plus important du jeu (sauvegardes minuscules).
On vérifie aussi la calibration (rendement/volatilité annualisés plausibles),
l'émergence des indices et l'effet des crises.
"""
import numpy as np
import pytest

from core.market import Market, Crisis

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
    p0 = m.price.copy()
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
