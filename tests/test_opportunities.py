"""Tests des critères d'opportunités sauvegardés (core/opportunities.py)."""
import pytest

from core import opportunities as O
from core.game_state import PlayerState
from core.market import Market


def _setup():
    p = PlayerState()
    m = Market(seed=2024)
    m.fast_forward(60)
    return p, m


def test_add_screen_assigns_id_and_label():
    p, m = _setup()
    e = O.add_screen(p, "stock", {"pe_max": 12.0}, label="Value picks")
    assert e["id"] == 1
    assert p.next_screen_id == 2
    assert e["label"] == "Value picks"
    assert e["criteria"] == {"pe_max": 12.0}
    assert len(p.saved_screens) == 1


def test_add_screen_default_label_when_missing():
    p, m = _setup()
    e = O.add_screen(p, "etf", {"theme": "esg"})
    assert e["label"] == "etf#1"


def test_add_screen_rejects_invalid_kind():
    p, m = _setup()
    with pytest.raises(ValueError):
        O.add_screen(p, "bond", {})


def test_add_screen_enforces_limit():
    p, m = _setup()
    for _ in range(O.MAX_SCREENS):
        O.add_screen(p, "stock", {"pe_max": 50.0})
    with pytest.raises(ValueError):
        O.add_screen(p, "stock", {"pe_max": 50.0})


def test_remove_screen():
    p, m = _setup()
    e = O.add_screen(p, "stock", {"pe_max": 12.0})
    assert O.remove_screen(p, e["id"]) is True
    assert p.saved_screens == []
    assert O.remove_screen(p, e["id"]) is False


def test_run_screen_stock_matches_screener_directly():
    from core import screener
    p, m = _setup()
    e = O.add_screen(p, "stock", {"pe_max": 15.0})
    out = O.run_screen(m, e, limit=200)
    expected = screener.screen_stocks(m, pe_max=15.0, limit=200)
    assert [c["ticker"] for c in out] == [c["ticker"] for c in expected]


def test_run_screen_etf():
    p, m = _setup()
    e = O.add_screen(p, "etf", {"theme": "esg"})
    out = O.run_screen(m, e, limit=20)
    assert all(True for _ in out)  # ne doit pas lever, contenu vérifié par test_screener


def test_run_all_returns_pairs_in_order():
    p, m = _setup()
    e1 = O.add_screen(p, "stock", {"pe_max": 12.0})
    e2 = O.add_screen(p, "etf", {"theme": "esg"})
    results = O.run_all(p, m, limit=5)
    assert [s["id"] for s, _ in results] == [e1["id"], e2["id"]]
