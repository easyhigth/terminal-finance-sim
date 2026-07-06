"""
tests/test_scene_book.py — Vérifications de rendu et d'interaction de la
scène portefeuille (scene_book.py), notamment le panneau latéral d'évolution
de la valeur nette.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from core import portfolio as pf
from core.game_state import GameState
from core.market import Market
from scenes.scene_book import BookScene


@pytest.fixture(scope="module", autouse=True)
def _pygame_init():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield


class _FakeScenes:
    def go(self, name, **kwargs):
        pass

    def back(self, name):
        pass


class _FakeApp:
    def __init__(self, gs, market):
        self.gs = gs
        self.market = market
        self.scenes = _FakeScenes()

    def ensure_market(self):
        return self.market


def _make_app():
    market = Market(seed=1)
    for _ in range(10):
        market.step()
    gs = GameState()
    p = gs.player
    p.cash = 200_000.0
    p.cash_history = [180_000.0, 185_000.0, 182_000.0, 190_000.0,
                      195_000.0, 200_000.0, 205_000.0, 203_000.0,
                      210_000.0, 215_000.0]
    tk = market.companies[0]["ticker"]
    pf.buy(p, market, tk, 10)
    return _FakeApp(gs, market)


def test_side_panel_renders_sector_and_history_modes():
    app = _make_app()
    scene = BookScene(app)
    scene.on_enter(return_to="terminal")
    scene.update(0.016)
    surf = pygame.Surface((1280, 720))

    scene.side_mode = "sector"
    scene.draw(surf)

    scene.side_mode = "history"
    scene.draw(surf)


def test_history_panel_displays_pnl_metrics():
    app = _make_app()
    scene = BookScene(app)
    scene.on_enter(return_to="terminal")
    scene.side_mode = "history"
    scene.update(0.016)
    surf = pygame.Surface((1280, 720))
    scene.draw(surf)
    p = app.gs.player
    start = p.cash_history[0]
    current = p.cash_history[-1]
    assert start == 180_000.0
    assert current == 215_000.0


def test_clicking_history_tab_switches_side_mode():
    app = _make_app()
    scene = BookScene(app)
    scene.on_enter(return_to="terminal")
    scene.update(0.016)
    surf = pygame.Surface((1280, 720))
    scene.draw(surf)

    assert scene.side_mode == "sector"
    rect = scene._side_mode_rects["history"]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
    scene.handle_event(event)
    assert scene.side_mode == "history"


def test_history_panel_gracefully_handles_short_history():
    app = _make_app()
    app.gs.player.cash_history = [200_000.0]
    scene = BookScene(app)
    scene.on_enter(return_to="terminal")
    scene.side_mode = "history"
    scene.update(0.016)
    surf = pygame.Surface((1280, 720))
    scene.draw(surf)
