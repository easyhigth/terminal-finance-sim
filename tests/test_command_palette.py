"""
tests/test_command_palette.py — Smoke-tests headless de la palette de
navigation globale (Ctrl+K), portée par core/scene_manager.py::SceneManager.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main


@pytest.fixture(scope="module")
def app():
    # Pas de pygame.quit() : invaliderait les Font mis en cache (ui/fonts.py)
    # pour le reste de la session pytest.
    a = main.App()
    a.ensure_market()
    a.gs.player.grade_index = 9
    yield a


def _ctrl_k():
    return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k, mod=pygame.KMOD_CTRL, unicode="")


def _key(k, ch=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=ch)


def test_ctrl_k_toggles_palette(app):
    app.scenes.go("terminal")
    assert not app.scenes.palette_open
    app.scenes.handle_event(_ctrl_k())
    assert app.scenes.palette_open
    app.scenes.handle_event(_ctrl_k())
    assert not app.scenes.palette_open


def test_typing_filters_entries(app):
    app.scenes.go("terminal")
    app.scenes.handle_event(_ctrl_k())
    for ch in "quant":
        app.scenes.handle_event(_key(ord(ch), ch))
    filtered = app.scenes._palette_filtered()
    assert [scene for _, scene, _ in filtered] == ["quant"]


def test_enter_navigates_and_sets_return_to(app):
    app.scenes.go("terminal")
    app.scenes.handle_event(_ctrl_k())
    for ch in "quant":
        app.scenes.handle_event(_key(ord(ch), ch))
    app.scenes.handle_event(_key(pygame.K_RETURN))
    assert not app.scenes.palette_open
    assert app.scenes.current_name == "quant"
    assert app.scenes.current.return_to == "terminal"


def test_escape_closes_without_navigating(app):
    app.scenes.go("terminal")
    app.scenes.handle_event(_ctrl_k())
    app.scenes.handle_event(_key(pygame.K_ESCAPE))
    assert not app.scenes.palette_open
    assert app.scenes.current_name == "terminal"


def test_no_match_shows_empty_list_without_crashing(app):
    app.scenes.go("terminal")
    app.scenes.handle_event(_ctrl_k())
    for ch in "zzzznotfound":
        app.scenes.handle_event(_key(ord(ch[0]), ch[0]))
    assert app.scenes._palette_filtered() == []
    app.scenes.draw(app.screen)
    assert app.scenes.palette_open


def test_palette_does_not_leak_into_underlying_scene(app):
    """Pendant que la palette est ouverte, les touches tapées ne doivent pas
    atteindre la scène sous-jacente (ex: la recherche de la page PLUS)."""
    app.scenes.go("more", return_to="terminal")
    sc = app.scenes.current
    app.scenes.handle_event(_ctrl_k())
    for ch in "quant":
        app.scenes.handle_event(_key(ord(ch), ch))
    assert sc.search == ""


def test_opening_navigating_resets_palette_state(app):
    app.scenes.go("terminal")
    app.scenes.handle_event(_ctrl_k())
    for ch in "quant":
        app.scenes.handle_event(_key(ord(ch), ch))
    app.scenes.handle_event(_key(pygame.K_RETURN))
    app.scenes.handle_event(_ctrl_k())
    assert app.scenes.palette_query == ""
