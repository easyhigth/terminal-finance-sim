"""Tests de core/global_search.py : recherche sur les données de PARTIE du
joueur (positions, watchlist, inbox, mandats, deals) — distincte de la
palette Ctrl+K qui cherche du contenu de référence (marché/glossaire/scènes)."""
from core import global_search as GS
from core.game_state import PlayerState
from core.market import Market


def _setup():
    m = Market(seed=123)
    p = PlayerState()
    return p, m


def test_empty_query_returns_all_entries_capped_to_limit():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    p.portfolio[tk] = {"shares": 10.0, "avg": 100.0}
    entries = GS.search(p, m, "")
    assert len(entries) == 1
    assert entries[0]["kind"] == "position"


def test_position_entry_includes_ticker_and_company_name():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    name = m.companies[0]["name"]
    p.portfolio[tk] = {"shares": 25.0, "avg": 50.0}
    entries = GS.search(p, m, tk)
    assert len(entries) == 1
    assert tk in entries[0]["label"]
    assert name in entries[0]["label"]
    assert entries[0]["action"] == {"open": "trading", "ticker": tk}


def test_position_labels_long_vs_short():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    p.portfolio[tk] = {"shares": -10.0, "avg": 50.0}
    entries = GS.search(p, m, tk)
    assert "short" in entries[0]["label"]


def test_watchlist_entry_searchable():
    p, m = _setup()
    tk = m.companies[1]["ticker"]
    p.watchlist = [tk]
    entries = GS.search(p, m, tk)
    assert len(entries) == 1
    assert entries[0]["kind"] == "watchlist"
    assert entries[0]["action"] == {"open": "trading", "ticker": tk}


def test_inbox_entry_matches_subject_and_body():
    p, m = _setup()
    p.inbox = [{"id": 1, "subject": "Alerte concentration", "sender": "Conformité",
               "body": "Votre position sur MVC dépasse 20%.", "read": False}]
    hits_subject = GS.search(p, m, "concentration")
    assert len(hits_subject) == 1
    assert hits_subject[0]["kind"] == "inbox"
    assert hits_subject[0]["action"] == {"open": "scene", "name": "inbox"}
    hits_body = GS.search(p, m, "dépasse")
    assert len(hits_body) == 1


def test_mandate_entry_matches_client_name():
    p, m = _setup()
    p.mandates = [{"client": "Fondation Vermillon", "target_pct": 0.1, "max_beta": 1.0}]
    entries = GS.search(p, m, "Vermillon")
    assert len(entries) == 1
    assert entries[0]["kind"] == "mandate"
    assert entries[0]["action"] == {"open": "scene", "name": "mandates"}


def test_deal_entry_matches_title():
    p, m = _setup()
    p.deals = [{"id": 1, "title": "LBO Atlas Industries", "kind": "M&A",
               "reward_cash": 10000, "days_left": 5}]
    entries = GS.search(p, m, "Atlas")
    assert len(entries) == 1
    assert entries[0]["kind"] == "deal"
    assert entries[0]["action"] == {"open": "scene", "name": "deals"}


def test_no_match_returns_empty():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    p.portfolio[tk] = {"shares": 10.0, "avg": 100.0}
    assert GS.search(p, m, "zzz_definitely_not_present_zzz") == []


def test_search_spans_all_categories_at_once():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    p.portfolio[tk] = {"shares": 10.0, "avg": 100.0}
    p.watchlist = [m.companies[1]["ticker"]]
    p.inbox = [{"id": 1, "subject": "Bonus trimestriel", "sender": "RH", "body": "", "read": False}]
    p.mandates = [{"client": "Client X"}]
    p.deals = [{"id": 1, "title": "Deal Y"}]
    all_entries = GS.search(p, m, "")
    kinds = {e["kind"] for e in all_entries}
    assert kinds == {"position", "watchlist", "inbox", "mandate", "deal"}


def test_search_without_market_still_works_for_non_ticker_content():
    p, m = _setup()
    p.inbox = [{"id": 1, "subject": "Sujet test", "sender": "X", "body": "", "read": False}]
    entries = GS.search(p, None, "Sujet")
    assert len(entries) == 1


def test_results_capped_at_limit():
    p, m = _setup()
    p.deals = [{"id": i, "title": f"Deal {i}"} for i in range(50)]
    entries = GS.search(p, m, "", limit=10)
    assert len(entries) == 10
