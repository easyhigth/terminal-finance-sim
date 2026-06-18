"""Tests des scénarios de départ (core/startscenarios.py)."""
from core import startscenarios as scen
from core.game_state import PlayerState


def test_all_scenarios_have_fields():
    for s in scen.SCENARIOS:
        assert s["cash"] > 0
        assert 0 <= s["grade_index"] <= 11
        assert 0 <= s["reputation"] <= 100
        assert isinstance(s["crisis"], bool)


def test_apply_small_firm_less_cash():
    p = PlayerState()
    scen.apply(p, "small_firm")
    assert p.cash == 120_000.0
    assert p.cash_history == [120_000.0]
    assert p.flags["start_scenario"] == "small_firm"
    assert not p.flags.get("start_crisis")


def test_apply_crisis_sets_flag():
    p = PlayerState()
    scen.apply(p, "crisis")
    assert p.flags.get("start_crisis") is True


def test_apply_veteran_starts_higher_grade():
    p = PlayerState()
    scen.apply(p, "veteran")
    assert p.grade_index == 2
    assert p.flags.get("can_choose_track") is True
    assert p.cash == 500_000.0


def test_unknown_scenario_falls_back_to_standard():
    p = PlayerState()
    sc = scen.apply(p, "does_not_exist")
    assert sc["id"] == "standard"
