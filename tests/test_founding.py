"""Tests de la fondation de firme (core/founding.py) : conditions d'accès,
effets (coût, titre, salaire d'associé, carnet de clients qui suit)."""
import random

from core import clients, config, founding, rivals
from core.game_state import GameState


def _partner(cash=10_000_000.0):
    gs = GameState()
    p = gs.player
    p.grade_index = len(config.GRADES) - 1
    p.cash = cash
    return gs, p


def test_requires_top_grade_and_cash():
    _gs, p = _partner()
    p.grade_index = 5
    assert founding.can_found(p) == (False, "grade")
    p.grade_index = len(config.GRADES) - 1
    p.cash = 100.0
    assert founding.can_found(p) == (False, "cash")
    p.cash = founding.FOUNDING_COST + 1
    assert founding.can_found(p) == (True, None)


def test_found_applies_all_effects():
    _gs, p = _partner()
    p.track = "Quant"
    rivals.designate_nemesis(p, notify=False)
    clients.ensure_book(p, random.Random(3))
    trust_before = [c["trust"] for c in p.clients]
    cash_before = p.cash
    rep_before = p.reputation
    res = founding.found(p, "  Moreau Capital  ")
    assert res["ok"]
    assert p.firm_name == "Moreau Capital"
    assert p.cash == cash_before - founding.FOUNDING_COST
    assert "Fondateur" in p.titles
    assert p.reputation > rep_before
    assert p.salary_bonus_per_step >= founding.FOUNDER_DRAW_PER_STEP
    # le carnet suit le fondateur
    assert all(c["trust"] == t + founding.CLIENT_TRUST_BONUS
               for c, t in zip(p.clients, trust_before))
    # journal + messages (direction et némésis)
    assert any("Moreau Capital" in e["text"] for e in p.journal)
    senders = {m.get("sender", "") for m in p.inbox}
    assert any("Direction" in s for s in senders)
    nem = rivals.personal_nemesis(p)
    assert nem["name"] in senders


def test_cannot_found_twice():
    _gs, p = _partner()
    assert founding.found(p, "Alpha")["ok"]
    assert founding.found(p, "Beta") == {"ok": False, "reason": "founded"}
    assert p.firm_name == "Alpha"


def test_empty_name_rejected():
    _gs, p = _partner()
    assert founding.found(p, "   ") == {"ok": False, "reason": "name"}
    assert not founding.founded(p)


def test_rival_leaderboard_shows_firm_name():
    _gs, p = _partner()
    founding.found(p, "Nova Partners")
    from core.market import Market
    m = Market(seed=8)
    for _ in range(3):
        m.step()
    board = rivals.leaderboard(p, m)
    mine = next(row for row in board if row["is_player"])
    assert mine["firm"] == "Nova Partners"
