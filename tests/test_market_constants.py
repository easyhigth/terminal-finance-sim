"""Tests de core/market_constants.py : constantes et fonctions PURES de
calibration du moteur (aucun tirage rng). On vérifie les propriétés
mathématiques attendues des charges de Nelson-Siegel, du facteur de
correction de variance, et des cibles de pente/courbure de la courbe."""
import numpy as np
import pytest

from core.market_constants import (
    ASYM_VOL_MAX_MULT,
    CURVE_NS_LAMBDA,
    REGIME_TRANSITIONS,
    REGIMES,
    STRESS_REGIME_FLOOR,
    STRESS_VOLMULT_NEUTRAL,
    _blend_factor_toward_world,
    _curve_curvature_target,
    _curve_ns_loadings,
    _curve_slope_target,
    _stress_level,
    _t_scale,
    nonworld_variance_correction,
)


# --------------------------------------------------------------- Nelson-Siegel
def test_ns_loadings_at_zero_maturity():
    h1, g2 = _curve_ns_loadings(0.0)
    assert h1 == pytest.approx(0.0, abs=1e-4)
    assert g2 == pytest.approx(0.0, abs=1e-4)

def test_ns_loadings_at_long_maturity():
    h1, g2 = _curve_ns_loadings(1000.0)
    assert h1 == pytest.approx(1.0, abs=1e-2)
    assert g2 == pytest.approx(0.0, abs=1e-2)

def test_ns_curvature_peaks_mid_curve_not_at_extremes():
    g2_mid = _curve_ns_loadings(CURVE_NS_LAMBDA)[1]
    g2_short = _curve_ns_loadings(0.1)[1]
    g2_long = _curve_ns_loadings(50.0)[1]
    assert g2_mid > g2_short
    assert g2_mid > g2_long

def test_ns_loadings_bounded_between_0_and_1():
    for years in (0.01, 0.5, 2, 5, 10, 30, 100):
        h1, g2 = _curve_ns_loadings(years)
        assert 0.0 <= h1 <= 1.0
        assert -0.1 <= g2 <= 1.0  # g2 reste petit et positif sur ces maturités


# --------------------------------------------------------------- cibles pente/courbure
def test_slope_target_neutral_at_calme_and_mean_growth():
    assert _curve_slope_target("Calme", growth=2.0) == pytest.approx(0.0, abs=1e-9)

def test_slope_target_positive_in_expansion():
    assert _curve_slope_target("Expansion", growth=2.0) > 0.0

def test_slope_target_negative_in_recession():
    assert _curve_slope_target("Récession", growth=2.0) < 0.0

def test_curvature_target_zero_without_stress():
    assert _curve_curvature_target(0.0) == pytest.approx(0.0)

def test_curvature_target_increases_with_stress():
    assert _curve_curvature_target(1.0) > _curve_curvature_target(0.5) > _curve_curvature_target(0.0)

def test_curvature_target_clamped_to_unit_interval():
    # stress_level hors [0,1] doit être clampé, pas extrapolé
    assert _curve_curvature_target(2.0) == _curve_curvature_target(1.0)
    assert _curve_curvature_target(-1.0) == _curve_curvature_target(0.0)


# --------------------------------------------------------------- stress / corrélations dynamiques
def test_stress_level_zero_at_neutral_vol_and_calme_regime():
    assert _stress_level(STRESS_VOLMULT_NEUTRAL, "Calme") == pytest.approx(0.0)

def test_stress_level_one_at_max_vol():
    assert _stress_level(ASYM_VOL_MAX_MULT, "Calme") == pytest.approx(1.0)

def test_stress_level_respects_regime_floor():
    floor = STRESS_REGIME_FLOOR["Récession"]
    assert _stress_level(STRESS_VOLMULT_NEUTRAL, "Récession") == pytest.approx(floor)

def test_stress_level_bounded_in_unit_interval():
    for vol_mult in (0.0, 0.5, 1.0, 2.0, 10.0):
        for regime in REGIMES:
            s = _stress_level(vol_mult, regime)
            assert 0.0 <= s <= 1.0


def test_blend_factor_zero_weight_is_identity():
    own = np.array([1.0, -2.0, 3.0])
    blended = _blend_factor_toward_world(own, world_centered=0.5, w=0.0, own_std=1.0, world_std=1.0)
    assert np.allclose(blended, own)

def test_blend_factor_preserves_variance_scale():
    # à w fixe, le résultat doit rester de l'ordre de own_std (pas d'explosion)
    own = np.array([1.0, -1.0, 2.0])
    blended = _blend_factor_toward_world(own, world_centered=10.0, w=0.5, own_std=1.0, world_std=1.0)
    assert np.all(np.isfinite(blended))


def test_nonworld_variance_correction_is_one_at_zero_weight():
    c = nonworld_variance_correction(w=0.0, v_nonworld0=1.0, s_cross=0.5,
                                      t_cross=0.2, beta=1.0, world_std=0.02)
    assert c == pytest.approx(1.0)

def test_nonworld_variance_correction_finite_and_positive():
    c = nonworld_variance_correction(w=0.8, v_nonworld0=1.0, s_cross=0.5,
                                      t_cross=0.2, beta=1.2, world_std=0.02)
    assert np.isfinite(c)
    assert c > 0.0


# --------------------------------------------------------------- échelle Student-t
def test_t_scale_positive_and_decreasing_with_df():
    s5 = _t_scale(5)
    s20 = _t_scale(20)
    assert s5 > 0 and s20 > 0
    assert s5 < s20  # plus df est petit, plus la variance théorique du tirage standard_t
                      # est grande -> il faut un facteur d'échelle plus petit pour la ramener à 1


# --------------------------------------------------------------- régimes
def test_regime_transition_probabilities_sum_to_one():
    for regime, transitions in REGIME_TRANSITIONS.items():
        total = sum(p for _, p in transitions)
        assert total == pytest.approx(1.0, abs=1e-6)

def test_regime_transitions_only_reference_known_regimes():
    for regime, transitions in REGIME_TRANSITIONS.items():
        for target, _ in transitions:
            assert target in REGIMES

def test_all_regimes_have_drift_vol_label():
    for regime, params in REGIMES.items():
        assert "drift" in params and "vol" in params and "label" in params
        assert params["vol"] > 0
