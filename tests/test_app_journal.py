"""Tests de l'app native Journal de trading (apps/app_journal.py) —
migration de scenes/scene_journal.py hors de l'hébergement flou (netteté),
même principe que Mission/Décision/Revue. Vérifie l'ouverture, le rendu avec
et sans historique, filtres/tri/recherche, annotation et réplication d'un
trade, et les boutons « JOURNAL » ajoutés dans Trading/Portefeuille."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from apps.app_journal import JournalApp
from core import journal as J

pygame.font.init()

RECT = pygame.Rect(0, 0, 1020, 640)


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    return a


def _click(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y))


def _key(k, unicode="", mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=unicode, mod=mod)


def _open(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("tradejournal")
    return desk, w


def _log_trade(app, ticker="MVC", side="achat", realized=None):
    J.log_trade(app.gs.player, app.market, asset_class="Action", key=ticker,
               label=ticker, side=side, qty=10, price=100.0, realized=realized,
               reason="test")


def test_journal_is_native_app_not_hosted(app):
    desk, w = _open(app)
    assert w.key == "tradejournal" and isinstance(w.app_obj, JournalApp)


def test_journal_draws_empty_without_crash(app):
    desk, w = _open(app)
    w.app_obj.draw(app.screen, RECT)


def test_journal_lists_logged_trades(app):
    _log_trade(app, "MVC")
    _log_trade(app, "NVDA")
    desk, w = _open(app)
    j = w.app_obj
    j.draw(app.screen, RECT)
    assert len(j._rows) == 2


def test_journal_search_filters_rows(app):
    _log_trade(app, "MVC")
    _log_trade(app, "NVDA")
    desk, w = _open(app)
    j = w.app_obj
    j.search = "mvc"
    j.draw(app.screen, RECT)
    assert len(j._rows) == 1
    assert j._rows[0]["key"] == "MVC"


def test_journal_asset_and_side_filters(app):
    _log_trade(app, "MVC", side="achat")
    _log_trade(app, "NVDA", side="vente")
    desk, w = _open(app)
    j = w.app_obj
    j.draw(app.screen, RECT)
    j.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                       pos=j._side_rects["vente"].center), RECT)
    assert j.side_filter == "vente"
    j.draw(app.screen, RECT)
    assert len(j._rows) == 1 and j._rows[0]["key"] == "NVDA"


def test_journal_sort_toggle(app):
    _log_trade(app, "MVC")
    desk, w = _open(app)
    j = w.app_obj
    j.draw(app.screen, RECT)
    assert j.sort_key == "day"
    j.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                       pos=j._sort_rects["realized"].center), RECT)
    assert j.sort_key == "realized"


def test_journal_note_dialog_annotate(app):
    _log_trade(app, "MVC")
    desk, w = _open(app)
    j = w.app_obj
    j.draw(app.screen, RECT)
    eid = j._rows[0]["id"]
    j.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                       pos=j._note_rects[eid].center), RECT)
    assert j._note_active == eid
    j.draw(app.screen, RECT)   # boîte modale sans exception
    j._note_text = "belle conviction"
    j._save_note()
    assert j._note_active is None
    entry = J.get_entry(app.gs.player, eid)
    assert entry["comment"] == "belle conviction"


def test_journal_note_dialog_escape_cancels(app):
    _log_trade(app, "MVC")
    desk, w = _open(app)
    j = w.app_obj
    j.draw(app.screen, RECT)
    eid = j._rows[0]["id"]
    j._start_note(j._rows[0])
    j.handle_event(_key(pygame.K_ESCAPE), RECT)
    assert j._note_active is None
    assert not J.get_entry(app.gs.player, eid).get("comment")


def test_journal_replicate_opens_trading(app):
    _log_trade(app, "MVC")
    desk, w = _open(app)
    j = w.app_obj
    j.draw(app.screen, RECT)
    eid = j._rows[0]["id"]
    j.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                       pos=j._replicate_rects[eid].center), RECT)
    assert any(win.key == "trading" for win in desk.wm.windows)


def test_journal_search_pastes_via_ctrl_v(app, monkeypatch):
    from core import clipboard
    monkeypatch.setattr(clipboard, "paste", lambda: "MVC")
    desk, w = _open(app)
    j = w.app_obj
    j.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v,
                                       unicode="v", mod=pygame.KMOD_CTRL), RECT)
    assert j.search == "MVC"


def test_journal_pauses_time_is_not_required():
    """Le journal n'est PAS un écran de travail forcé (pas dans
    FOCUS_SCENE_NAMES) : consulter l'historique ne doit pas geler le temps."""
    from core.sim_clock import FOCUS_SCENE_NAMES
    assert "tradejournal" not in FOCUS_SCENE_NAMES


# --------------------------------------------------- boutons JOURNAL (liens)
def test_trading_app_has_journal_button(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("trading")
    trading = w.app_obj
    trading.draw(app.screen, pygame.Rect(0, 0, 840, 520))
    assert trading._journal_btn is not None
    trading.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                             pos=trading._journal_btn.center),
                          pygame.Rect(0, 0, 840, 520))
    assert any(win.key == "tradejournal" for win in desk.wm.windows)


def test_book_app_has_journal_button(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("book")
    book = w.app_obj
    book.draw(app.screen, pygame.Rect(0, 0, 980, 600))
    assert book._journal_btn is not None
    book.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=book._journal_btn.center),
                       pygame.Rect(0, 0, 980, 600))
    assert any(win.key == "tradejournal" for win in desk.wm.windows)
