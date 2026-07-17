"""Tests des affectations d'analystes (core/team.py) : effets tangibles par
poste, fatigue qui monte en poste actif et récupère au repos, épuisement qui
force le retour au poste libre."""
from core import team
from core.game_state import GameState
from core.market import Market


def _setup(n=1):
    gs = GameState()
    p = gs.player
    p.grade_index = 8
    p.cash = 1_000_000.0
    for _ in range(n):
        team.hire(p, "equity_junior")
    m = Market(seed=55)
    for _ in range(5):
        m.step()
    p.market_step = m.step_count
    return gs, p, m


def test_assign_and_labels():
    _gs, p, _m = _setup()
    assert team.assign(p, 0, "recherche")["ok"]
    assert p.analysts[0]["assignment"] == "recherche"
    assert team.assign(p, 0, "inconnu")["ok"] is False
    assert team.assign(p, 5, "deals")["ok"] is False
    for key in team.ASSIGNMENTS:
        assert team.assignment_label(key) and team.assignment_desc(key)


def test_research_assignment_publishes_notes():
    _gs, p, m = _setup()
    p.watchlist = [m.companies[0]["ticker"]]
    team.assign(p, 0, "recherche")
    events = []
    for _ in range(team.RESEARCH_EVERY_STEPS + 1):
        p.market_step += 1
        events += team.assignments_step(p, m)
    notes = [e for e in events if e["kind"] == "research_note"]
    assert notes
    assert notes[0]["note"]["ticker"] == m.companies[0]["ticker"]
    assert m.companies[0]["ticker"] in p.research


def test_risk_assignment_cools_heat():
    _gs, p, m = _setup()
    p.heat = 50
    team.assign(p, 0, "risque")
    team.assignments_step(p, m)
    assert p.heat < 50


def test_deals_assignment_adds_offer_probability():
    _gs, p, _m = _setup()
    assert team.deals_assign_bonus(p) == 0.0
    team.assign(p, 0, "deals")
    assert team.deals_assign_bonus(p) > 0.0


def test_fatigue_rises_then_forces_rest_then_recovers():
    _gs, p, m = _setup()
    team.assign(p, 0, "deals")
    a = p.analysts[0]
    rested = False
    for _ in range(60):
        events = team.assignments_step(p, m)
        if any(e["kind"] == "rest" for e in events):
            rested = True
            break
    assert rested
    assert a["assignment"] == "libre" and a.get("exhausted")
    # épuisé : refuse un poste actif tant qu'il n'a pas récupéré
    assert team.assign(p, 0, "recherche")["ok"] is False
    fat = a["fatigue"]
    team.assignments_step(p, m)
    assert a["fatigue"] < fat   # la fatigue récupère au repos


def test_old_save_analysts_default_to_libre():
    _gs, p, m = _setup()
    p.analysts[0].pop("assignment", None)
    p.analysts[0].pop("fatigue", None)
    events = team.assignments_step(p, m)   # ne lève pas
    assert events == []
