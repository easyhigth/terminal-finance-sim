"""Tests du widget « À faire » (core/todo.py, logique pure)."""
from core import todo
from core.game_state import PlayerState


def _player(**kw):
    p = PlayerState()
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def test_empty_player_has_no_suggestions():
    assert todo.suggestions(_player()) == []


def test_pending_dilemma_is_first_priority():
    p = _player(pending_dilemmas=[{"title": "Insider"}],
                mandate_offers=[{"id": 1}])
    items = todo.suggestions(p)
    assert items[0]["scene"] == "dilemma"
    assert "Insider" in items[0]["label"]


def test_review_and_stresstest_are_listed():
    p = _player(pending_review={"standard_bonus": 1000},
                pending_stresstest={"id": 1})
    scenes = [it["scene"] for it in todo.suggestions(p)]
    assert scenes == ["review", "stresstest"]


def test_urgent_deal_and_mandate_offers():
    p = _player(deals=[{"title": "IPO Nordal", "days_left": 3},
                       {"title": "Lointain", "days_left": 30}],
                mandate_offers=[{"id": 1}, {"id": 2}])
    items = todo.suggestions(p)
    scenes = [it["scene"] for it in items]
    assert "deals" in scenes and "mandates" in scenes
    deal = next(it for it in items if it["scene"] == "deals")
    assert "IPO Nordal" in deal["label"] and "3j" in deal["label"]


def test_unread_inbox_is_listed():
    p = _player()
    from core import inbox
    inbox.push(p, "manager", "Boss", "Sujet", "Corps")
    items = todo.suggestions(p)
    assert items and items[-1]["scene"] == "inbox"


def test_list_is_capped_at_max_items():
    p = _player(pending_dilemmas=[{"title": "X"}],
                pending_review={"a": 1},
                pending_stresstest={"a": 1},
                mandate_offers=[{"id": 1}],
                deals=[{"title": "D", "days_left": 1}])
    from core import inbox
    inbox.push(p, "manager", "Boss", "Sujet", "Corps")
    assert len(todo.suggestions(p)) == todo.MAX_ITEMS
