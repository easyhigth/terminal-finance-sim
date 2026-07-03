"""
tests/test_shop_explorer_search.py — CTRL+F (façon navigateur) dans
l'Explorateur et la Boutique : redonne le focus au champ de recherche et
remonte en haut de la liste filtrée. La recherche elle-même est déjà
tapable sans action préalable dans ces deux écrans (comme la plupart des
écrans du jeu), donc CTRL+F sert surtout à revenir à la recherche après
avoir navigué ailleurs (ex. champ QUANTITÉ en Boutique, flèches).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    return a


def _ctrl_f():
    return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f, mod=pygame.KMOD_CTRL, unicode="")


def test_explorer_ctrl_f_resets_scroll(app):
    app.scenes.go("explorer")
    sc = app.scenes.current
    sc.scroll = 240
    sc.handle_event(_ctrl_f())
    assert sc.scroll == 0


def test_explorer_typing_already_reaches_search_without_ctrl_f(app):
    """La recherche est déjà tapable sans action préalable — CTRL+F n'est
    pas un prérequis pour filtrer, seulement un raccourci de confort."""
    app.scenes.go("explorer")
    sc = app.scenes.current
    sc.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode="a"))
    assert sc.search == "a"


def test_shop_ctrl_f_refocuses_search_from_qty(app):
    app.scenes.go("shop")
    sc = app.scenes.current
    sc.text_focus = "qty"
    sc.scroll = 100
    sc.handle_event(_ctrl_f())
    assert sc.text_focus == "search"
    assert sc.scroll == 0


def test_shop_ctrl_f_keeps_existing_search_text(app):
    app.scenes.go("shop")
    sc = app.scenes.current
    sc.search = "MVC"
    sc.text_focus = "qty"
    sc.handle_event(_ctrl_f())
    assert sc.search == "MVC"
    assert sc.text_focus == "search"
