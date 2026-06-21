from core import archetypes
from core.game_state import PlayerState


def test_archetypes_list_well_formed():
    assert len(archetypes.ARCHETYPES) == 5
    ids = [a["id"] for a in archetypes.ARCHETYPES]
    assert len(ids) == len(set(ids))
    for a in archetypes.ARCHETYPES:
        assert "name" in a and "tagline" in a and "desc" in a and "perks" in a


def test_get_known_and_unknown_id():
    a = archetypes.get("quant")
    assert a is not None and a["id"] == "quant"
    assert archetypes.get("does-not-exist") is None


def test_perk_unknown_archetype_returns_default():
    p = PlayerState(continent="Europe")
    assert p.archetype == ""
    for key, _, _ in archetypes.PERK_INFO:
        assert archetypes.perk(p, key) == archetypes._DEFAULTS.get(key)


def test_perk_known_archetype_overrides_default():
    p = PlayerState(continent="Europe")
    p.archetype = "agressif"
    arch = archetypes._BY_ID["agressif"]
    for key, val in arch["perks"].items():
        assert archetypes.perk(p, key) == val


def test_apply_sets_archetype_and_scales_cash():
    p = PlayerState(continent="Europe")
    p.cash = 100_000.0
    arch = archetypes.apply(p, "agressif")
    assert p.archetype == "agressif"
    mult = arch["perks"].get("starting_cash_mult", 1.0)
    assert p.cash == 100_000.0 * mult


def test_apply_syncs_cash_history_last_entry():
    p = PlayerState(continent="Europe")
    p.cash = 100_000.0
    p.cash_history.append(100_000.0)
    archetypes.apply(p, "agressif")
    assert p.cash_history[-1] == p.cash


def test_apply_unknown_id_falls_back_to_first():
    p = PlayerState(continent="Europe")
    arch = archetypes.apply(p, "totally-unknown")
    assert arch["id"] == archetypes.ARCHETYPES[0]["id"]
    assert p.archetype == archetypes.ARCHETYPES[0]["id"]
