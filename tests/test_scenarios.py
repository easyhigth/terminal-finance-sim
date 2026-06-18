"""Tests des scénarios de crise/boom de marché (core/scenarios.py).

Couvre : déclenchement déterministe pour une graine fixe, bornes de sévérité
et éligibilité régionale, et fidélité du texte narratif à la sévérité/région
réellement tirées.
"""
import random

import pytest

from core import scenarios
from core.market import Market
from data import companies as comp_data

_REGIONS = set(comp_data.REGIONS)


def _setup(seed=2024):
    return Market(seed=seed)


# ------------------------------------------------------------------ intégrité
def test_scenario_ids_are_unique():
    ids = [s["id"] for s in scenarios.SCENARIOS]
    assert len(ids) == len(set(ids))


def test_all_scenarios_have_valid_severity_bounds():
    for s in scenarios.SCENARIOS:
        sev_min = s.get("sev_min", 1.0)
        sev_max = s.get("sev_max", 1.0)
        assert 0 < sev_min <= sev_max
        assert sev_max <= 3.0   # bornes raisonnables, anti-dérive extrême


def test_regional_scenarios_reference_known_regions():
    for s in scenarios.SCENARIOS:
        if s.get("regional"):
            pool = s.get("region_pool", scenarios._DEFAULT_REGION_POOL)
            for r in pool:
                assert r in _REGIONS


# --------------------------------------------------------------- maybe_trigger
def test_maybe_trigger_returns_none_above_threshold():
    m = _setup()

    class _AlwaysHigh:
        def random(self):
            return 0.99

    assert scenarios.maybe_trigger(m, _AlwaysHigh()) is None


def test_maybe_trigger_is_deterministic_for_same_seed():
    m1, m2 = _setup(), _setup()
    r1, r2 = random.Random(123), random.Random(123)
    out1 = [scenarios.maybe_trigger(m1, r1) for _ in range(200)]
    out2 = [scenarios.maybe_trigger(m2, r2) for _ in range(200)]
    keys1 = [(e["id"], e["severity"], e["region"]) if e else None for e in out1]
    keys2 = [(e["id"], e["severity"], e["region"]) if e else None for e in out2]
    assert keys1 == keys2
    assert any(keys1)   # au moins un déclenchement sur 200 tours


def test_maybe_trigger_event_shape_when_fired():
    m = _setup()
    rng = random.Random(1)
    ev = None
    for _ in range(2000):
        ev = scenarios.maybe_trigger(m, rng)
        if ev:
            break
    assert ev is not None
    assert set(ev.keys()) == {"id", "name", "kind", "story", "severity", "region"}
    assert ev["kind"] in ("good", "bad")
    assert ev["id"] in {s["id"] for s in scenarios.SCENARIOS}


def test_severity_stays_within_declared_bounds():
    m = _setup()
    rng = random.Random(7)
    found = {}
    for _ in range(5000):
        ev = scenarios.maybe_trigger(m, rng)
        if not ev:
            continue
        sdef = next(s for s in scenarios.SCENARIOS if s["id"] == ev["id"])
        sev_min = sdef.get("sev_min", 1.0)
        sev_max = sdef.get("sev_max", 1.0)
        assert sev_min - 1e-9 <= ev["severity"] <= sev_max + 1e-9
        found.setdefault(ev["id"], []).append(ev["severity"])
    # on a bien observé une dispersion de sévérité (pas une valeur figée)
    multi = [v for v in found.values() if len(v) > 3]
    assert multi, "aucun scénario n'a déclenché assez souvent pour vérifier la dispersion"
    assert any(max(v) - min(v) > 0.05 for v in multi)


def test_region_is_none_for_non_regional_scenarios():
    m = _setup()
    rng = random.Random(11)
    non_regional_ids = {s["id"] for s in scenarios.SCENARIOS if not s.get("regional")}
    for _ in range(2000):
        ev = scenarios.maybe_trigger(m, rng)
        if ev and ev["id"] in non_regional_ids:
            assert ev["region"] is None


def test_regional_scenario_picks_eligible_region():
    m = _setup()
    rng = random.Random(13)
    regional_ids = {s["id"] for s in scenarios.SCENARIOS if s.get("regional")}
    seen_any = False
    for _ in range(5000):
        ev = scenarios.maybe_trigger(m, rng)
        if ev and ev["id"] in regional_ids:
            seen_any = True
            assert ev["region"] in _REGIONS
    assert seen_any, "aucun scénario régional n'a déclenché sur 5000 tirages"


def test_regional_scenario_injects_crisis_with_matching_region():
    m = _setup()
    rng = random.Random(17)
    regional_ids = {s["id"] for s in scenarios.SCENARIOS if s.get("regional")}
    ev = None
    for _ in range(5000):
        n_before = len(m.crises)
        ev = scenarios.maybe_trigger(m, rng)
        if ev and ev["id"] in regional_ids:
            assert len(m.crises) == n_before + 1
            crisis = m.crises[-1]
            assert ev["region"] in crisis.regions
            break
    assert ev is not None and ev["id"] in regional_ids


# --------------------------------------------------------------------- récit
def test_story_mentions_region_when_regional():
    m = _setup()
    rng = random.Random(13)
    regional_ids = {s["id"] for s in scenarios.SCENARIOS if s.get("regional")}
    for _ in range(5000):
        ev = scenarios.maybe_trigger(m, rng)
        if ev and ev["id"] in regional_ids:
            assert ev["region"] in ev["story"]
            return
    pytest.fail("aucun scénario régional n'a déclenché sur 5000 tirages")


def test_story_mentions_severity_word():
    m = _setup()
    rng = random.Random(1)
    ev = None
    for _ in range(2000):
        ev = scenarios.maybe_trigger(m, rng)
        if ev:
            break
    assert ev is not None
    expected_word = scenarios._severity_label(ev["severity"])
    assert expected_word in ev["story"]


def test_maybe_trigger_with_default_rng_does_not_raise(monkeypatch):
    random.seed(0)
    m = _setup()
    scenarios.maybe_trigger(m)   # ne doit pas lever, déclenché ou pas


# --------------------------------------------------------- crises ciblées (pures)
_TARGETED_IDS = {
    "scandale_finance", "antitrust_tech", "immo_asie", "immo_europe",
    "fx_emergent", "sante_sectoriel",
}


def test_targeted_scenarios_exist_and_are_purely_sectoral_or_regional():
    """world=0.0 pour ces scénarios : aucun choc macro global, uniquement
    sectoriel/régional — ce qui permet des shorts/hedges chirurgicaux."""
    found = {s["id"] for s in scenarios.SCENARIOS if s["id"] in _TARGETED_IDS}
    assert found == _TARGETED_IDS
    for s in scenarios.SCENARIOS:
        if s["id"] in _TARGETED_IDS:
            assert s.get("world", 0.0) == 0.0


def test_targeted_scenarios_inject_crisis_without_world_shock():
    """Une fois déclenché, le Crisis injecté dans le marché ne porte aucun choc
    `world`, et les chocs sectoriels/régionaux restent finis et raisonnables."""
    m = _setup()
    rng = random.Random(42)
    seen = {}
    for _ in range(20000):
        n_before = len(m.crises)
        ev = scenarios.maybe_trigger(m, rng)
        if ev and ev["id"] in _TARGETED_IDS and ev["id"] not in seen:
            assert len(m.crises) == n_before + 1
            crisis = m.crises[-1]
            assert crisis.world == 0.0
            # pas de NaN/Inf, et amplitude raisonnable comparée aux scénarios
            # existants ("asia"/"credit" plafonnent vers ~0.05-0.06 avant sévérité,
            # avec sev_max <= 1.8 -> borne large à 0.15 pour rester confortable).
            for choc_map in (crisis.sectors, crisis.regions):
                for v in choc_map.values():
                    assert v == v  # NaN check (NaN != NaN)
                    assert abs(v) < 0.15
            assert 1.0 <= crisis.vol_mult <= 4.0
            seen[ev["id"]] = ev
        if len(seen) == len(_TARGETED_IDS):
            break
    missing = _TARGETED_IDS - set(seen)
    assert not missing, f"scénarios ciblés jamais déclenchés sur 20000 tirages : {missing}"


def test_fx_emergent_targets_only_emerging_region_pool():
    """fx_emergent doit cibler uniquement Am.Sud/Afrique, jamais une autre région."""
    m = _setup()
    rng = random.Random(99)
    seen_regions = set()
    for _ in range(20000):
        ev = scenarios.maybe_trigger(m, rng)
        if ev and ev["id"] == "fx_emergent":
            assert ev["region"] in {"Am.Sud", "Afrique"}
            seen_regions.add(ev["region"])
        if len(seen_regions) == 2:
            break
    assert seen_regions, "fx_emergent ne s'est jamais déclenché sur 20000 tirages"
