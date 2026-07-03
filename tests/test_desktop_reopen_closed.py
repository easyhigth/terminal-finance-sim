"""Tests pour le raccourci « Rouvrir la dernière fenêtre fermée »
(CTRL+MAJ+Z, scene_desktop.py)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main
from core import desktop_onboarding


@pytest.fixture()
def desktop():
    desktop_onboarding.mark_seen()
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.reputation = 80
    a.scenes.go("desktop")
    sc = a.scenes.current
    sc.update(0.016)
    sc.draw(a.screen)
    return sc


def _reopen_key():
    return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z,
                              mod=pygame.KMOD_CTRL | pygame.KMOD_SHIFT, unicode="")


def test_reopens_a_closed_scene_window_with_its_context(desktop):
    tk = desktop.app.market.top_companies(n=1)[0]["ticker"]
    w = desktop._open_scene_window("company", ticker=tk, return_to="markethub")
    desktop.wm.close(w)
    assert not any(win.key == "scene:company" for win in desktop.wm.windows)

    desktop.handle_event(_reopen_key())

    reopened = next(win for win in desktop.wm.windows if win.key == "scene:company")
    assert reopened.app_obj.scene.ticker == tk


def test_reopens_a_closed_native_app(desktop):
    w = desktop._launch("research")
    desktop.wm.close(w)
    assert not any(win.key == "research" for win in desktop.wm.windows)

    desktop.handle_event(_reopen_key())

    assert any(win.key == "research" for win in desktop.wm.windows)


def test_closing_terminal_is_never_tracked_for_reopen(desktop):
    tk = desktop.app.market.top_companies(n=1)[0]["ticker"]
    w = desktop._open_scene_window("company", ticker=tk)
    desktop.wm.close(w)   # dernier fermé = "company"

    term = next(win for win in desktop.wm.windows if win.key == "scene:terminal")
    desktop.wm.close(term)   # ne doit PAS écraser _last_closed

    assert desktop._last_closed == ("scene", "company", {"ticker": tk})


def test_reopen_is_a_noop_when_nothing_was_closed(desktop):
    n_before = len(desktop.wm.windows)
    desktop.handle_event(_reopen_key())
    assert len(desktop.wm.windows) == n_before


def test_reopen_consumes_the_record_only_once(desktop):
    w = desktop._launch("research")
    desktop.wm.close(w)
    desktop.handle_event(_reopen_key())
    assert desktop._last_closed is None
    n_after_first = len(desktop.wm.windows)
    desktop.handle_event(_reopen_key())   # rien à rouvrir la 2e fois
    assert len(desktop.wm.windows) == n_after_first


def test_only_the_most_recently_closed_window_is_remembered(desktop):
    w1 = desktop._launch("research")
    w2 = desktop._launch("calculator")
    desktop.wm.close(w1)
    desktop.wm.close(w2)
    assert desktop._last_closed == ("app", "calculator", {})
