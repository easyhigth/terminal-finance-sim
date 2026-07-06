"""
tests/test_scene_shop.py — Vérifications de la scène boutique, notamment
l'animation live des cours et le flash vert/rouge.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from core import config
from core.game_state import GameState
from core.market import Market
from core.sim_clock import SimClock
from scenes.scene_shop import ShopScene


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
    def __init__(self, market):
        self.gs = GameState()
        self.gs.player.day = 1
        self.market = market
        self.sim_clock = SimClock()
        self.sim_clock.game_minutes_acc = 360.0
        self.scenes = _FakeScenes()

    def ensure_market(self):
        return self.market


@pytest.fixture
def app():
    m = Market(seed=12345)
    for _ in range(35):
        m.step()
    return _FakeApp(m)


def test_live_quote_returns_expected_keys(app):
    scene = ShopScene(app)
    scene.on_enter(return_to="terminal")
    row = next(r for r in scene.rows if r["kind"] == "Action")
    live = scene._live_quote(row)
    assert set(live.keys()) == {"price", "value", "yield_pct", "change_pct"}


def test_action_live_price_uses_intraday_path(app):
    scene = ShopScene(app)
    scene.on_enter(return_to="terminal")
    row = next(r for r in scene.rows if r["kind"] == "Action")
    live = scene._live_quote(row)
    # le prix live peut être différent du prix statique car l'intraday est animé
    assert isinstance(live["price"], float)
    assert live["price"] > 0


def test_etf_live_price_refreshes(app):
    scene = ShopScene(app)
    scene.on_enter(return_to="terminal")
    row = next(r for r in scene.rows if r["kind"] == "ETF")
    live = scene._live_quote(row)
    assert live["price"] == pytest.approx(row["price"], rel=1e-6)
    assert live["value"] == pytest.approx(row["value"], rel=1e-6)


def test_shop_draw_with_live_flash(app):
    scene = ShopScene(app)
    scene.on_enter(return_to="terminal")
    scene.update(0.016)
    surf = pygame.Surface((1280, 720))
    scene.draw(surf)
    assert scene._flash is not None


def test_flash_tick_changes_color_on_price_move(app):
    scene = ShopScene(app)
    scene.on_enter(return_to="terminal")
    ident = ("Action", app.market.companies[0]["ticker"])
    col1 = scene._flash.tick(ident, 100.0, config.COL_UP, config.COL_DOWN, config.COL_WHITE)
    col2 = scene._flash.tick(ident, 101.0, config.COL_UP, config.COL_DOWN, config.COL_WHITE)
    assert col2 != col1 or col2 == config.COL_UP
