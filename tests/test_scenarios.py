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


# ------------------------------------------------------------- stress macro
def test_macro_stress_is_neutral_at_baseline():
    m = _setup()
    assert scenarios.macro_stress(m) == pytest.approx(1.0, abs=1e-6)


def test_macro_stress_rises_with_credit_and_recession_conditions():
    m = _setup()
    m.macro["credit_hy"]["v"] = 760.0
    m.macro["growth"]["v"] = -3.0
    m.macro["unemployment"]["v"] = 9.0
    assert scenarios.macro_stress(m) > 1.5


def test_crisis_trigger_probability_scales_with_macro_stress():
    """Conditions macro tendues -> davantage de crises déclenchées sur un même
    nombre de tours, à graine identique (item 5 du brief : crises pilotées par
    des seuils macro cohérents, pas un pur tirage indépendant)."""
    m_calm = _setup()
    m_stressed = _setup()
    m_stressed.macro["credit_hy"]["v"] = 900.0
    m_stressed.macro["growth"]["v"] = -3.0
    m_stressed.macro["unemployment"]["v"] = 9.0

    rng_calm, rng_stressed = random.Random(321), random.Random(321)
    n_calm = sum(1 for _ in range(2000) if scenarios.maybe_trigger(m_calm, rng_calm))
    n_stressed = sum(1 for _ in range(2000) if scenarios.maybe_trigger(m_stressed, rng_stressed))
    assert n_stressed > n_calm


def test_high_stress_biases_toward_bad_scenarios():
    m = _setup()
    m.macro["credit_hy"]["v"] = 900.0
    m.macro["growth"]["v"] = -3.0
    m.macro["unemployment"]["v"] = 9.0
    rng = random.Random(7)
    kinds = []
    for _ in range(3000):
        ev = scenarios.maybe_trigger(m, rng)
        if ev:
            kinds.append(ev["kind"])
    assert kinds   # déclenché au moins une fois
    assert kinds.count("bad") > kinds.count("good")


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


# ------------------------------------------------------------------ contagion
def test_contagion_table_references_existing_scenario_ids():
    ids = {s["id"] for s in scenarios.SCENARIOS}
    for src, related in scenarios.CONTAGION.items():
        assert src in ids
        for rid in related:
            assert rid in ids


def test_triggering_a_scenario_sets_contagion_for_related_scenarios():
    m = _setup()
    rng = random.Random(7)
    ev = None
    for _ in range(2000):
        ev = scenarios.maybe_trigger(m, rng)
        if ev and ev["id"] in scenarios.CONTAGION:
            break
    assert ev is not None and ev["id"] in scenarios.CONTAGION
    for rid in scenarios.CONTAGION[ev["id"]]:
        assert m.contagion.get(rid, 0) > 0


def test_contagion_boosts_weight_of_related_scenario():
    """Avec une contagion active sur un scénario donné, son poids de tirage
    (à stress macro neutre) doit être multiplié par CONTAGION_BOOST."""
    m = _setup()
    pool = scenarios.localized("fr")
    idx = next(i for i, s in enumerate(pool) if s["id"] == "credit")
    base_weight = pool[idx]["weight"]

    captured = {}

    class _Recorder(random.Random):
        def random(self):
            return 0.0   # force le franchissement du seuil de déclenchement

        def choices(self, population, weights=None, k=1):
            captured["weights"] = weights
            return super().choices(population, weights=weights, k=k)

    m.contagion = {"credit": scenarios.CONTAGION_STEPS}
    scenarios.maybe_trigger(m, _Recorder(1))
    assert captured["weights"][idx] == pytest.approx(base_weight * scenarios.CONTAGION_BOOST)


def test_contagion_decays_after_enough_turns():
    m = _setup()
    m.contagion = {"credit": 2}
    rng = random.Random(1)
    scenarios.maybe_trigger(m, rng)
    scenarios.maybe_trigger(m, rng)
    scenarios.maybe_trigger(m, rng)
    assert "credit" not in m.contagion


# --------------------------------------------------------------- maybe_warn
def test_maybe_warn_none_when_stress_below_threshold():
    m = _setup()
    assert scenarios.macro_stress(m) < scenarios.WARNING_STRESS_THRESHOLD
    assert scenarios.maybe_warn(m, random.Random(1)) is None


def test_maybe_warn_fires_when_stress_high_and_rng_favourable():
    m = _setup()
    m.macro["credit_hy"]["v"] = 900.0
    m.macro["growth"]["v"] = -3.0
    m.macro["unemployment"]["v"] = 9.0
    assert scenarios.macro_stress(m) >= scenarios.WARNING_STRESS_THRESHOLD

    class _AlwaysLow(random.Random):
        def random(self):
            return 0.0

    out = scenarios.maybe_warn(m, _AlwaysLow())
    assert out is not None
    assert out["kind"] == "warning"
    assert out["story"]
    assert out["stress"] >= scenarios.WARNING_STRESS_THRESHOLD


def test_maybe_warn_respects_cooldown_after_firing():
    m = _setup()
    m.macro["credit_hy"]["v"] = 900.0
    m.macro["growth"]["v"] = -3.0
    m.macro["unemployment"]["v"] = 9.0

    class _AlwaysLow(random.Random):
        def random(self):
            return 0.0

    first = scenarios.maybe_warn(m, _AlwaysLow())
    assert first is not None
    assert m.warning_cooldown == scenarios.WARNING_COOLDOWN_STEPS
    second = scenarios.maybe_warn(m, _AlwaysLow())
    assert second is None
    assert m.warning_cooldown == scenarios.WARNING_COOLDOWN_STEPS - 1


def test_maybe_warn_blocked_during_crisis_cooldown():
    m = _setup()
    m.macro["credit_hy"]["v"] = 900.0
    m.macro["growth"]["v"] = -3.0
    m.macro["unemployment"]["v"] = 9.0
    m.crisis_cooldown = 3

    class _AlwaysLow(random.Random):
        def random(self):
            return 0.0

    assert scenarios.maybe_warn(m, _AlwaysLow()) is None


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


# ----------------------------------------------- scénarios historiques
def test_historic_scenarios_have_weight_zero():
    for sid in scenarios.HISTORIC_IDS:
        s = next(x for x in scenarios.SCENARIOS if x["id"] == sid)
        assert s["weight"] == 0


def test_historic_scenarios_never_fire_via_maybe_trigger():
    m = _setup()
    m.crises = []
    rng = random.Random(7)
    for _ in range(400):
        m.step()
        ev = scenarios.maybe_trigger(m, rng=rng)
        if ev is not None:
            assert ev["id"] not in scenarios.HISTORIC_IDS


def test_all_four_historic_ids_present():
    assert set(scenarios.HISTORIC_IDS) == {"hist1987", "hist2000", "hist2008", "hist2020"}


def test_trigger_by_id_fires_a_historic_scenario_deterministically():
    m1 = _setup()
    m2 = _setup()
    r1 = scenarios.trigger_by_id(m1, "hist2008")
    r2 = scenarios.trigger_by_id(m2, "hist2008")
    assert r1["id"] == "hist2008"
    assert r1["severity"] == pytest.approx(r2["severity"]) == 1.0
    assert m1.crises and m1.crises[-1].world == pytest.approx(m2.crises[-1].world)


def test_historic_scenarios_have_english_story_and_name():
    from data import scenarios_en as en_mod
    for sid in scenarios.HISTORIC_IDS:
        assert sid in en_mod.SCENARIOS_EN
        loc = scenarios.localized("en")
        s = next(x for x in loc if x["id"] == sid)
        assert s["name"] == en_mod.SCENARIOS_EN[sid]["name"]
