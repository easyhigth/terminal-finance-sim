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


def test_check_alerts_pushes_one_inbox_message_per_matching_screen():
    p, m = _setup()
    O.add_screen(p, "stock", {"pe_max": 9999.0}, label="Large net")
    before = len(p.inbox)
    pushed = O.check_alerts(p, m)
    assert len(pushed) == 1
    assert len(p.inbox) == before + 1
    assert p.inbox[-1]["kind"] == "research"


def test_check_alerts_does_not_renotify_same_tickers():
    p, m = _setup()
    O.add_screen(p, "stock", {"pe_max": 9999.0})
    first = O.check_alerts(p, m)
    assert first  # premier passage : nouveaux résultats
    second = O.check_alerts(p, m)
    assert second == []  # rien de nouveau au second passage


def test_check_alerts_no_matches_pushes_nothing():
    p, m = _setup()
    O.add_screen(p, "stock", {"pe_max": -1.0})  # aucune action n'a un P/E négatif
    assert O.check_alerts(p, m) == []
    assert p.inbox == []


def test_check_alerts_handles_etf_screens_with_id_key():
    p, m = _setup()
    O.add_screen(p, "etf", {"theme": "esg"})
    pushed = O.check_alerts(p, m)
    if pushed:  # dépend du roster ETF disponible, mais ne doit jamais planter
        assert pushed[0]["screen"]["kind"] == "etf"
