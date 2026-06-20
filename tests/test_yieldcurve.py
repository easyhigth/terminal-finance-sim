"""Tests du modèle de courbe des taux à 3 facteurs (Nelson-Siegel niveau/pente/
courbure, core/market.py). Complète tests/test_market.py (courbe instantanée
déjà couverte là) en se concentrant sur :
  - le déterminisme de l'état persistant (curve_slope_state/curve_curv_state) ;
  - la cohérence de sens régime <-> pente/courbure ;
  - l'évolution LISSE (pas de saut brutal) pas après pas ;
  - des bornes saines sur tous les états et rendements produits.
"""
import numpy as np
import pytest

from core.market import (
    ASYM_VOL_MAX_MULT,
    CURVE_CURV_BOUND,
    CURVE_SLOPE_BOUND,
    Crisis,
    Market,
)


def _setup(seed=7):
    return Market(seed=seed)


# --------------------------------------------------------------- déterminisme
def test_curve_factors_are_deterministic_same_seed():
    a = Market(seed=99); a.fast_forward(80)
    b = Market(seed=99); b.fast_forward(80)
    assert a.curve_slope_state == pytest.approx(b.curve_slope_state)
    assert a.curve_curv_state == pytest.approx(b.curve_curv_state)
    assert a.curve_point(10.0, smoothed=True) == pytest.approx(b.curve_point(10.0, smoothed=True))


def test_curve_factors_reconstruct_via_sync_to():
    """Invariant central du jeu : (seed, nb de pas) doit reconstruire EXACTEMENT
    l'état (cf. CLAUDE.md) -- y compris les nouveaux facteurs pente/courbure."""
    ref = Market(seed=123); ref.fast_forward(50)
    m = Market(seed=123)
    m.sync_to(50)
    assert m.curve_slope_state == pytest.approx(ref.curve_slope_state)
    assert m.curve_curv_state == pytest.approx(ref.curve_curv_state)
    assert m.step_count == ref.step_count == 50


def test_curve_factors_differ_across_seeds():
    a = Market(seed=1); a.fast_forward(100)
    b = Market(seed=2); b.fast_forward(100)
    # au moins un des deux facteurs persistants doit diverger entre graines
    # (régimes/macro tirés différemment) -- sinon le facteur ne dépendrait pas
    # vraiment de la trajectoire de marché.
    assert (a.curve_slope_state != pytest.approx(b.curve_slope_state)
            or a.curve_curv_state != pytest.approx(b.curve_curv_state))


# ---------------------------------------------------------- réaction au régime
def test_slope_factor_tracks_recession_target_downward():
    """En récession + croissance négative maintenues sur la durée (le régime
    étant lui-même une chaîne de Markov rejouée à chaque step(), on le réimpose
    à chaque pas comme on réimposerait un scénario), l'état persistant de pente
    doit converger vers une cible négative (inversion)."""
    m = _setup()
    for _ in range(40):
        m.regime = "Récession"
        m.macro["growth"]["v"] = -4.0
        m.step()
    assert m.curve_slope_state < 0.0
    assert m.curve_point(10.0, smoothed=True) < m.curve_point(2.0, smoothed=True)


def test_slope_factor_tracks_expansion_target_upward():
    """En expansion + forte croissance maintenues, l'état de pente doit
    converger vers une cible positive (pentification normale)."""
    m = _setup()
    for _ in range(40):
        m.regime = "Expansion"
        m.macro["growth"]["v"] = 5.0
        m.step()
    assert m.curve_slope_state > 0.0
    assert m.curve_point(10.0, smoothed=True) > m.curve_point(2.0, smoothed=True)


def test_curvature_rises_with_stress():
    """La composante de courbure doit monter quand le stress de marché
    (last_stress_level, chantier 7, dérivé de world_vol_mult_state) est élevé
    et rester nulle au calme. On impose world_vol_mult_state à son maximum
    avant chaque pas (comme on réimpose regime/growth ailleurs) pour piloter
    le stress de façon déterministe plutôt que d'attendre qu'il émerge d'une
    dynamique probabiliste lente."""
    calm = _setup(seed=11)
    for _ in range(15):
        calm.step()           # marché resté calme -> stress nul -> courbure nulle
    stressed = _setup(seed=11)
    for _ in range(15):
        stressed.world_vol_mult_state = ASYM_VOL_MAX_MULT
        stressed.step()
    assert stressed.last_stress_level > calm.last_stress_level
    assert stressed.curve_curv_state > calm.curve_curv_state
    assert stressed.curve_curv_state > 0.005


def test_curvature_is_near_zero_in_calm_steady_state():
    m = _setup(seed=21)
    m.regime = "Calme"
    for _ in range(60):
        m.step()
    # marché resté calme -> peu/pas de stress accumulé -> courbure faible
    assert abs(m.curve_curv_state) < 0.01


# --------------------------------------------------------------- douceur (pas de saut)
def test_curve_factors_evolve_smoothly_step_to_step():
    """Les états persistants pente/courbure ne doivent jamais sauter d'un coup
    à leur cible : la variation par pas reste bornée par la vitesse de
    mean-reversion (CURVE_FACTOR_MEAN_REV) appliquée à l'écart maximal
    possible avec la cible (régime/croissance/stress les plus extrêmes)."""
    m = _setup(seed=33)
    # un évènement brutal qui fait basculer le régime d'un coup au pas suivant
    m.regime = "Calme"
    for _ in range(10):
        m.step()
    prev_slope, prev_curv = m.curve_slope_state, m.curve_curv_state
    m.regime = "Récession"
    m.macro["growth"]["v"] = -6.0
    m.add_crisis(Crisis("choc brutal", steps=5, world=-0.15, vol_mult=2.5))
    max_step_slope = 2.0 * CURVE_SLOPE_BOUND   # pire cas : cible à l'extrême opposé
    max_step_curv = 2.0 * CURVE_CURV_BOUND
    for _ in range(8):
        m.step()
        d_slope = abs(m.curve_slope_state - prev_slope)
        d_curv = abs(m.curve_curv_state - prev_curv)
        # la variation par pas reste une fraction (mean-rev < 1) de l'écart
        # max possible -> jamais un saut "tout ou rien" vers la borne opposée.
        assert d_slope <= max_step_slope
        assert d_curv <= max_step_curv
        prev_slope, prev_curv = m.curve_slope_state, m.curve_curv_state


def test_smoothed_curve_lags_instantaneous_after_sudden_regime_change():
    """Juste après un changement brutal de régime (sans rejouer step()), la
    courbe LISSÉE doit rester proche de l'ancien état (pas encore rattrapée),
    alors que la courbe INSTANTANÉE bascule immédiatement -- c'est la
    différence attendue entre smoothed=True (gameplay) et smoothed=False
    (lecture réactive immédiate, cf. tests/test_market.py)."""
    m = _setup(seed=44)
    m.regime = "Calme"
    for _ in range(15):
        m.step()
    slope_state_before = m.curve_slope_state
    m.regime = "Récession"
    m.macro["growth"]["v"] = -5.0
    instant_slope = m.curve_slope(smoothed=False)
    smoothed_slope = m.curve_slope(smoothed=True)
    assert instant_slope < 0.0
    # la version lissée n'a pas encore bougé (aucun step() rejoué) : l'état
    # persistant qui la pilote vaut toujours sa valeur d'avant le changement
    # de régime, donc smoothed_slope == ancien état (PAS la nouvelle cible
    # instantanée, qui elle réagit immédiatement).
    assert m.curve_slope_state == pytest.approx(slope_state_before)
    assert smoothed_slope != pytest.approx(instant_slope)


# ------------------------------------------------------------------- bornes
def test_curve_factor_states_stay_within_bounds_under_extreme_path():
    m = _setup(seed=55)
    m.regime = "Récession"
    m.macro["growth"]["v"] = -6.0
    for _ in range(10):
        m.add_crisis(Crisis(f"crise_{_}", steps=8, world=-0.1, vol_mult=2.5))
        m.step()
    assert -CURVE_SLOPE_BOUND - 1e-9 <= m.curve_slope_state <= CURVE_SLOPE_BOUND + 1e-9
    assert -CURVE_CURV_BOUND - 1e-9 <= m.curve_curv_state <= CURVE_CURV_BOUND + 1e-9


def test_curve_point_stays_non_negative_and_sane_under_stress():
    m = _setup(seed=66)
    m.regime = "Récession"
    m.macro["growth"]["v"] = -6.0
    m.macro["rate"]["v"] = 0.1
    for _ in range(20):
        m.add_crisis(Crisis("stress", steps=5, world=-0.1, vol_mult=2.5))
        m.step()
    for years in (0.25, 1, 2, 5, 10, 20, 30):
        y_inst = m.curve_point(years, smoothed=False)
        y_smooth = m.curve_point(years, smoothed=True)
        assert y_inst >= 0.0
        assert y_smooth >= 0.0
        assert y_inst < 0.25     # borne large anti-aberration (25%/an)
        assert y_smooth < 0.25


def test_yield_curve_dict_has_all_tenors_and_is_sane():
    m = _setup(seed=77)
    m.fast_forward(30)
    curve = m.yield_curve()
    assert set(curve.keys()) == {"3M", "2Y", "5Y", "10Y", "30Y"}
    assert all(0.0 <= v < 0.25 for v in curve.values())
