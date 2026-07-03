"""Tests pour la navigation clavier des icônes du bureau (scene_desktop.py)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main
from core import desktop_onboarding
from ui import keynav


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


def _key(k, mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=mod, unicode="")


def test_no_focus_by_default(desktop):
    assert desktop._icon_focus is None


def test_tab_focuses_first_icon(desktop):
    assert desktop._icon_rects
    first = next(iter(desktop._icon_rects))
    desktop.handle_event(_key(pygame.K_TAB))
    assert desktop._icon_focus == first


def test_tab_cycles_forward_and_wraps(desktop):
    keys = list(desktop._icon_rects)
    # 1er TAB initialise sur keys[0] (pas un "pas") ; les len(keys) TAB suivants
    # font un tour complet et reviennent sur keys[0].
    for _ in range(len(keys) + 1):
        desktop.handle_event(_key(pygame.K_TAB))
    assert desktop._icon_focus == keys[0]


def test_shift_tab_cycles_backward(desktop):
    keys = list(desktop._icon_rects)
    desktop.handle_event(_key(pygame.K_TAB))
    assert desktop._icon_focus == keys[0]
    desktop.handle_event(_key(pygame.K_TAB, mod=pygame.KMOD_SHIFT))
    assert desktop._icon_focus == keys[-1]


def test_arrow_key_moves_focus_spatially(desktop):
    desktop.handle_event(_key(pygame.K_TAB))
    start = desktop._icon_focus
    rects = {k: r for k, (r, _kind, _label) in desktop._icon_rects.items()}
    desktop.handle_event(_key(pygame.K_RIGHT))
    expected = keynav.nearest_in_direction(rects, start, "right")
    assert desktop._icon_focus == expected


def test_arrow_key_initializes_focus_when_none(desktop):
    assert desktop._icon_focus is None
    desktop.handle_event(_key(pygame.K_DOWN))
    assert desktop._icon_focus in desktop._icon_rects


def test_enter_launches_focused_icon(desktop):
    desktop.handle_event(_key(pygame.K_TAB))
    key = desktop._icon_focus
    n_before = len(desktop.wm.windows)
    desktop.handle_event(_key(pygame.K_RETURN))
    assert len(desktop.wm.windows) > n_before or key == "save"


def test_escape_clears_focus_when_no_window_focused(desktop):
    desktop.handle_event(_key(pygame.K_TAB))
    assert desktop._icon_focus is not None
    desktop.handle_event(_key(pygame.K_ESCAPE))
    assert desktop._icon_focus is None


def test_icon_keynav_disabled_when_a_window_is_focused(desktop):
    desktop.handle_event(_key(pygame.K_TAB))
    desktop.handle_event(_key(pygame.K_RETURN))   # ouvre une fenêtre, la focalise
    assert desktop.wm.focused is not None
    focus_before = desktop._icon_focus
    desktop.handle_event(_key(pygame.K_TAB))
    assert desktop._icon_focus == focus_before   # TAB va à la fenêtre, pas aux icônes


def test_mouse_click_on_icon_sets_focus(desktop):
    key, (r, _kind, _label) = next(iter(desktop._icon_rects.items()))
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=r.center)
    desktop.handle_event(ev)
    assert desktop._icon_focus == key
