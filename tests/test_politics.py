"""Tests des événements politiques régionaux (core/politics.py).

Le système est déjà partiellement couvert (déterminisme, intégration crise/crédit)
dans tests/test_governments.py ; ce module complète avec des tests ciblés sur
_pick_government, l'intégrité des pools d'événements par région, et les effets
appliqués au marché par maybe_trigger.
"""
import random

import pytest

from core import politics
from core import governments as gov_mod
from core.market import Market
from core.game_state import PlayerState
from data import companies as comp_data

_REGIONS = set(comp_data.REGIONS)


def _setup(seed=2024):
    m = Market(seed=seed)
    p = PlayerState()
    return p, m


# --------------------------------------------------------------- pools de données
def test_all_pool_regions_are_valid_market_regions():
    for region in politics._POOLS:
        assert region in _REGIONS


def test_every_government_region_has_a_pool():
    # tous les gouvernements appartiennent à une région couverte par _POOLS
    # (sinon maybe_trigger retournerait None systématiquement pour eux)
    gov_regions = {g["region"] for g in gov_mod.GOVERNMENTS}
    assert gov_regions <= set(politics._POOLS.keys())


def test_pool_events_have_required_fields():
    for region, pool in politics._POOLS.items():
        ids = [ev["id"] for ev in pool]
        assert len(ids) == len(set(ids)), f"ids dupliqués dans la région {region}"
        for ev in pool:
            assert ev["kind"] in ("good", "bad", "info")
            assert ev["name"] and ev["name_en"]
            assert "{country}" in ev["fr"]
            assert "{country}" in ev["en"]
            assert isinstance(ev["sectors"], dict)
            assert isinstance(ev.get("region", 0.0), float)
            assert isinstance(ev.get("credit", 0), (int, float))
            assert ev.get("steps", 3) > 0
            assert ev.get("vol", 1.0) > 0


def test_good_events_have_non_negative_region_shock_and_negative_credit():
    # cohérence narrative : bonne nouvelle -> facteur régional positif (ou neutre)
    # et resserrement du spread de crédit (credit <= 0)
    for pool in politics._POOLS.values():
        for ev in pool:
            if ev["kind"] == "good":
                assert ev.get("region", 0.0) >= 0.0
                assert ev.get("credit", 0) <= 0


def test_bad_events_have_non_positive_region_shock_and_positive_credit():
    for pool in politics._POOLS.values():
        for ev in pool:
            if ev["kind"] == "bad":
                assert ev.get("region", 0.0) <= 0.0
                assert ev.get("credit", 0) >= 0


# --------------------------------------------------------------- _pick_government
def test_pick_government_only_returns_govs_with_a_pool():
    rng = random.Random(7)
    for _ in range(100):
        g = politics._pick_government(rng)
        assert g["region"] in politics._POOLS


def test_pick_government_favors_unstable_governments():
    # un gouvernement très instable (faible 'stability') doit être choisi
    # nettement plus souvent qu'un gouvernement très stable sur un grand échantillon
    rng = random.Random(42)
    counts = {}
    for _ in range(4000):
        g = politics._pick_government(rng)
        counts[g["code"]] = counts.get(g["code"], 0) + 1
    most_stable = max(
        (g for g in gov_mod.GOVERNMENTS if g["region"] in politics._POOLS),
        key=lambda g: g.get("stability", 0.8),
    )
    least_stable = min(
        (g for g in gov_mod.GOVERNMENTS if g["region"] in politics._POOLS),
        key=lambda g: g.get("stability", 0.8),
    )
    assert counts.get(least_stable["code"], 0) > counts.get(most_stable["code"], 0)


# --------------------------------------------------------------- maybe_trigger
def test_maybe_trigger_returns_none_with_rng_above_threshold():
    p, m = _setup()

    class _AlwaysHigh:
        def random(self):
            return 0.99

    ev = politics.maybe_trigger(p, m, _AlwaysHigh())
    assert ev is None


def test_maybe_trigger_default_rng_uses_module_random(monkeypatch):
    # quand rng=None, le module utilise `random` (le module global) ; on force
    # un seed connu pour vérifier que ça ne lève pas et reste cohérent.
    random.seed(0)
    p, m = _setup()
    # ne doit pas lever d'exception, que l'événement se déclenche ou non
    politics.maybe_trigger(p, m)


def test_maybe_trigger_event_shape_when_fired():
    p, m = _setup()
    rng = random.Random(1)
    ev = None
    for _ in range(500):
        ev = politics.maybe_trigger(p, m, rng)
        if ev:
            break
    assert ev is not None
    assert set(ev.keys()) == {
        "id", "name", "name_en", "story", "story_en", "kind",
        "region", "country", "country_en", "gov",
    }
    assert ev["region"] in _REGIONS
    assert ev["kind"] in ("good", "bad", "info")
    gov = gov_mod.get(ev["gov"])
    assert gov is not None
    assert ev["country"] == gov["name"]
    assert ev["country_en"] == gov["name_en"]
    assert ev["country"] in ev["story"]
    assert ev["country_en"] in ev["story_en"]


def test_maybe_trigger_injects_crisis_with_matching_region():
    p, m = _setup()
    rng = random.Random(3)
    ev = None
    for _ in range(500):
        n_before = len(m.crises)
        ev = politics.maybe_trigger(p, m, rng)
        if ev:
            assert len(m.crises) == n_before + 1
            crisis = m.crises[-1]
            assert ev["region"] in crisis.regions
            break
    assert ev is not None


def test_maybe_trigger_bumps_region_credit_in_expected_direction():
    p, m = _setup()
    rng = random.Random(5)
    ev = None
    for _ in range(500):
        ev = politics.maybe_trigger(p, m, rng)
        if ev:
            break
    assert ev is not None
    bump = m.region_credit_bump.get(ev["region"], 0.0)
    if ev["kind"] == "good":
        assert bump <= 0.0
    elif ev["kind"] == "bad":
        assert bump >= 0.0


def test_maybe_trigger_is_deterministic_for_same_seed():
    p1, m1 = _setup()
    p2, m2 = _setup()
    r1, r2 = random.Random(99), random.Random(99)
    out1 = [politics.maybe_trigger(p1, m1, r1) for _ in range(80)]
    out2 = [politics.maybe_trigger(p2, m2, r2) for _ in range(80)]
    ids1 = [e["id"] if e else None for e in out1]
    ids2 = [e["id"] if e else None for e in out2]
    assert ids1 == ids2
