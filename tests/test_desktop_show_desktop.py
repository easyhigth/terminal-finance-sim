"""Tests pour le raccourci « Afficher le bureau » (CTRL+MAJ+D, scene_desktop.py)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main
from core import desktop_onboarding


@pytest.fixture()
def desktop():
    desktop_onboarding.mark_seen()   # neutralise la carte d'accueil (1re visite)
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.reputation = 80
    a.scenes.go("desktop")
    sc = a.scenes.current
    sc.update(0.016)
    sc.draw(a.screen)   # peuple self._icon_rects
    return sc


def _show_desktop_key():
    return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d,
                              mod=pygame.KMOD_CTRL | pygame.KMOD_SHIFT, unicode="")


def _open(sc, key):
    return sc._launch(key)


def test_minimizes_all_open_windows(desktop):
    _open(desktop, "research")
    _open(desktop, "trading")
    assert any(not w.minimized for w in desktop.wm.windows)
    desktop.handle_event(_show_desktop_key())
    assert all(w.minimized for w in desktop.wm.windows)


def test_second_press_restores_exactly_what_was_open(desktop):
    _open(desktop, "research")
    _open(desktop, "trading")
    open_before = sorted(w.key for w in desktop.wm.windows if not w.minimized)
    desktop.handle_event(_show_desktop_key())
    desktop.handle_event(_show_desktop_key())
    open_after = sorted(w.key for w in desktop.wm.windows if not w.minimized)
    assert open_after == open_before


def test_does_not_restore_windows_that_were_already_minimized(desktop):
    _open(desktop, "research")
    term = next(w for w in desktop.wm.windows if w.key == "scene:terminal")
    assert term.minimized   # minimisé par défaut au démarrage du bureau
    desktop.handle_event(_show_desktop_key())
    desktop.handle_event(_show_desktop_key())
    assert term.minimized   # toujours minimisé : n'a jamais été « ouvert » au 1er appui


def test_noop_with_no_windows_open(desktop):
    for w in desktop.wm.windows:
        w.minimized = True
    desktop.handle_event(_show_desktop_key())
    assert all(w.minimized for w in desktop.wm.windows)


def test_plain_ctrl_d_still_opens_deals_icon_not_show_desktop(desktop):
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d, mod=pygame.KMOD_CTRL, unicode="")
    desktop.handle_event(ev)
    assert any(w.key == "scene:deals" for w in desktop.wm.windows)
