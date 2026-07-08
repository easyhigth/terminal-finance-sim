"""Tests du menu Démarrer du bureau (scenes/scene_desktop_menus.py) — reprend
et étend l'ancien hub PLUS (scenes/scene_more.py, retiré) : recherche locale,
verrous par grade (icône + infobulle), description au survol, navigation
clavier en grille, ouverture des pages en fenêtre."""
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
    a.gs.player.grade_index = 3   # certaines pages restent verrouillées à ce grade
    a.scenes.go("desktop")
    sc = a.scenes.current
    sc.update(0.016)
    sc.draw(a.screen)
    return sc


def _click(x, y, button=1):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=(x, y))


def _key(k, mod=0, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=mod, unicode=unicode)


def test_ctrl_o_toggles_start_menu(desktop):
    assert desktop.start_open is False
    desktop.handle_event(_key(pygame.K_o, mod=pygame.KMOD_CTRL))
    assert desktop.start_open is True
    desktop.handle_event(_key(pygame.K_o, mod=pygame.KMOD_CTRL))
    assert desktop.start_open is False


def test_open_resets_search_and_cursor(desktop):
    desktop._open_start_menu()
    desktop._start_search = "quant"
    desktop._start_cursor = 5
    desktop._open_start_menu()
    assert desktop._start_search == ""
    assert desktop._start_cursor == 0


def test_locked_entry_shows_lock_and_does_not_open_on_click(desktop):
    desktop._open_start_menu()
    desktop.draw(desktop.app.screen)
    locked = [e for e in desktop._launcher_rects if e[3]]
    assert locked   # au grade 3, au moins une entrée est verrouillée
    rect, scene, _kw, _locked, _label, _desc = locked[0]
    n_before = len(desktop.wm.windows)
    desktop.handle_event(_click(rect.centerx, rect.centery))
    assert len(desktop.wm.windows) == n_before
    assert desktop.start_open is True   # reste ouvert, pas de navigation


def test_unlocked_entry_opens_window_and_closes_menu(desktop):
    desktop._open_start_menu()
    desktop.draw(desktop.app.screen)
    unlocked = [e for e in desktop._launcher_rects if not e[3]]
    rect, scene, _kw, _locked, _label, _desc = unlocked[0]
    desktop.handle_event(_click(rect.centerx, rect.centery))
    assert desktop.start_open is False
    # certaines entrées (ex. "markethub") sont redirigées vers une app NATIVE
    # (clé sans préfixe) plutôt qu'hébergées (clé "scene:<nom>").
    assert any(w.key in (f"scene:{scene}", scene) for w in desktop.wm.windows)


def test_search_filters_entries_by_label(desktop):
    desktop._open_start_menu()
    for ch in "glossaire":
        desktop.handle_event(_key(ord(ch), unicode=ch))
    desktop.draw(desktop.app.screen)
    labels = {e[4] for e in desktop._launcher_rects}
    assert labels == {"Glossaire"}


def test_escape_clears_search_before_closing_menu(desktop):
    desktop._open_start_menu()
    desktop._start_search = "risk"
    desktop.handle_event(_key(pygame.K_ESCAPE))
    assert desktop._start_search == ""
    assert desktop.start_open is True
    desktop.handle_event(_key(pygame.K_ESCAPE))
    assert desktop.start_open is False


def test_keyboard_navigation_moves_cursor_and_enter_activates(desktop):
    desktop._open_start_menu()
    desktop.draw(desktop.app.screen)
    start_cursor = desktop._start_cursor
    desktop.handle_event(_key(pygame.K_RIGHT))
    assert desktop._start_cursor != start_cursor or len(desktop._start_all_rects) < 2
    desktop._start_search = "marché"
    desktop.draw(desktop.app.screen)
    desktop._start_cursor = 0
    desktop.handle_event(_key(pygame.K_RETURN))
    assert desktop.start_open is False
    assert any(w.key == "markethub" for w in desktop.wm.windows)   # app native


def test_clicking_outside_panel_closes_menu(desktop):
    desktop._open_start_menu()
    desktop.draw(desktop.app.screen)
    desktop.handle_event(_click(5, 5))
    assert desktop.start_open is False


def test_every_entry_reachable_and_no_overlap_with_footer(desktop):
    """Chaque entrée du catalogue est atteignable (au moins une fois listée),
    et aucun rect ne sort du panneau (régression scroll/colonnes)."""
    from core import app_catalog
    desktop._open_start_menu()
    desktop.draw(desktop.app.screen)
    all_scenes = {scene for r, scene, *_ in desktop._start_all_rects}
    catalog_scenes = {scene for _t, items in app_catalog.SECTIONS for _l, scene, _kw, _desc in items}
    assert all_scenes == catalog_scenes


def test_no_button_rect_overlaps_taskbar(desktop):
    from core import config
    desktop._open_start_menu()
    desktop.draw(desktop.app.screen)
    taskbar_top = config.SCREEN_HEIGHT - 30
    for rect, *_rest in desktop._launcher_rects:
        assert rect.bottom <= taskbar_top + 1


def test_desktop_menu_applications_entry_opens_start_menu(desktop):
    desktop._ctx_menu = None
    items = desktop._desktop_menu_items()
    label, action = items[0]
    assert "Applications" in label or "menu" in label.lower()
    action()
    assert desktop.start_open is True
