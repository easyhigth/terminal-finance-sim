"""Tests de découvrabilité du bureau : icône « Succès » (panthéon/badges,
jusqu'ici cachée dans le hub PLUS) et bouton loupe de la topbar (recherche
globale Ctrl+/, jusqu'ici accessible uniquement au clavier)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main
from core import desktop_onboarding, desktop_tutorial

pygame.font.init()


@pytest.fixture()
def desktop():
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    a.scenes.go("desktop")
    sc = a.scenes.current
    sc.update(0.016)
    sc.draw(a.screen)
    return sc


def _click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def test_achievements_icon_present_and_opens_window(desktop):
    keys = {k for k, _l, _kind, _acc in desktop._icon_list()}
    assert "qachievements" in keys
    desktop._launch("qachievements")
    assert any(w.key == "scene:achievements" for w in desktop.wm.windows)


def test_topbar_magnifier_opens_global_search(desktop):
    assert desktop._gsearch_rect is not None
    assert desktop._search_open is False
    desktop.handle_event(_click(desktop._gsearch_rect.center))
    assert desktop._search_open is True


def test_magnifier_blocked_by_modal_card(desktop, monkeypatch):
    """Même garde que Ctrl+/ : pas de recherche par-dessus une carte modale."""
    monkeypatch.setattr(desktop, "_blocking_card_pending", lambda: True)
    desktop.handle_event(_click(desktop._gsearch_rect.center))
    assert desktop._search_open is False


def test_index_ticker_drawn_and_opens_markethub(desktop):
    assert desktop._index_ticker_rect is not None
    desktop.handle_event(_click(desktop._index_ticker_rect.center))
    assert any(w.key == "markethub" for w in desktop.wm.windows)


def test_index_ticker_survives_missing_market(desktop):
    desktop.app.market = None
    desktop.draw(desktop.app.screen)   # ne doit pas lever
    assert desktop._index_ticker_rect is None
