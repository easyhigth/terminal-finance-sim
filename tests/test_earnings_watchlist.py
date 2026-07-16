"""Tests de la notification de résultats trimestriels pour une société
SUIVIE (watchlist) — core/game_state.py::advance_step, câblée sur
market.last_earnings (déjà produit à chaque pas par Market._step_earnings,
mais jusqu'ici silencieux si le joueur n'était pas sur la bonne fiche)."""
from core import notify_queue
from core.game_state import GameState, PlayerState
from core.market import Market
from core.market_constants import EARN_PERIOD


def _advance_to_next_earnings(market, ticker):
    """Avance le marché pas à pas jusqu'à ce que `ticker` publie ses
    résultats ; retourne le rapport."""
    for _ in range(EARN_PERIOD + 1):
        market.step()
        for rep in market.last_earnings:
            if rep["ticker"] == ticker:
                return rep
    raise AssertionError(f"{ticker} n'a pas publié dans la fenêtre attendue")


def _player(watchlist=None):
    p = PlayerState()
    p.watchlist = watchlist or []
    return p


def test_watched_ticker_earnings_push_toast_and_inbox_message():
    m = Market(seed=7)
    tk = m.companies[3]["ticker"]
    _advance_to_next_earnings(m, tk)

    p = _player(watchlist=[tk])
    gs = GameState()
    gs.player = p
    inbox_before = len(p.inbox)
    gs.advance_step(market=m)

    toasts = notify_queue.drain(p)
    assert any(tk in t["text"] for t in toasts)
    assert len(p.inbox) == inbox_before + 1
    assert tk in p.inbox[-1]["subject"] or tk in p.inbox[-1]["body"]


def test_toast_action_targets_company_scene():
    m = Market(seed=7)
    tk = m.companies[3]["ticker"]
    _advance_to_next_earnings(m, tk)

    p = _player(watchlist=[tk])
    gs = GameState()
    gs.player = p
    gs.advance_step(market=m)

    toasts = notify_queue.drain(p)
    hit = next(t for t in toasts if tk in t["text"])
    assert hit["action"] == "scene"
    assert hit["action_kwargs"]["name"] == "company"
    assert hit["action_kwargs"]["ticker"] == tk


def test_unwatched_ticker_earnings_are_silent():
    m = Market(seed=7)
    tk = m.companies[3]["ticker"]
    _advance_to_next_earnings(m, tk)

    p = _player(watchlist=[])   # rien suivi
    gs = GameState()
    gs.player = p
    inbox_before = len(p.inbox)
    gs.advance_step(market=m)

    toasts = notify_queue.drain(p)
    assert not any(tk in t["text"] for t in toasts)
    assert len(p.inbox) == inbox_before


def test_watchlist_case_insensitive_match():
    m = Market(seed=7)
    tk = m.companies[3]["ticker"]
    _advance_to_next_earnings(m, tk)

    p = _player(watchlist=[tk.lower()])
    gs = GameState()
    gs.player = p
    gs.advance_step(market=m)

    toasts = notify_queue.drain(p)
    assert any(tk in t["text"] for t in toasts)


def test_no_crash_when_no_earnings_this_step():
    m = Market(seed=7)
    tk = m.companies[0]["ticker"]
    p = _player(watchlist=[tk])
    gs = GameState()
    gs.player = p
    # un pas qui ne publie rien pour ce ticker ne doit jamais lever
    for _ in range(3):
        m.step()
        if not any(r["ticker"] == tk for r in m.last_earnings):
            gs.advance_step(market=m)
            break
