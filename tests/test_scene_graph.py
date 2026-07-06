"""
tests/test_scene_graph.py — Vérifications de l'atelier de graphes, en
particulier l'amélioration des chandeliers/barres sur les courtes périodes.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from core import intraday
from core.game_state import GameState
from core.market import Market
from core.sim_clock import SimClock
from scenes.scene_graph import GraphScene


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


def _ticker(app):
    return app.market.companies[0]["ticker"]


def test_series_for_ohlc_is_denser_than_default_series_on_short_periods(app):
    tk = _ticker(app)
    scene = GraphScene(app)
    scene.on_enter(tickers=[tk], kind="candles", period=6, return_to="terminal")

    # 1M : série standard
    scene.period = 6
    default = scene._series(tk)
    ohlc, pps = scene._series_for_ohlc(tk)
    assert pps == 50
    assert len(ohlc) > len(default) * 3

    # 3M
    scene.period = 18
    default = scene._series(tk)
    ohlc, pps = scene._series_for_ohlc(tk)
    assert pps == 30
    assert len(ohlc) > len(default) * 2

    # 1A (période moyenne) : plus faible densification
    scene.period = 73
    default = scene._series(tk)
    ohlc, pps = scene._series_for_ohlc(tk)
    assert pps == 8
    assert len(ohlc) >= len(default)


def test_series_for_ohlc_preserves_real_closes_for_stocks(app):
    """La densification OHLC garde les vraies clôtures du moteur comme points
    EXACTS de la série (invariant du chemin canonique)."""
    tk = _ticker(app)
    scene = GraphScene(app)
    scene.on_enter(tickers=[tk], kind="candles", period=6, return_to="terminal")
    for period, pps_expected in ((6, 50), (18, 30)):
        scene.period = period
        closes = app.market.history_of(tk, period)
        ohlc, pps = scene._series_for_ohlc(tk)
        assert pps == pps_expected
        stride = pps + 1
        assert ohlc[::stride][:len(closes)] == pytest.approx(closes)


def test_ohlc_n_buckets_is_period_aware(app):
    tk = _ticker(app)
    scene = GraphScene(app)
    scene.on_enter(tickers=[tk], kind="candles", period=6, return_to="terminal")
    s, _ = scene._series_for_ohlc(tk)

    scene.period = -1440  # 1J
    assert scene._ohlc_n_buckets(s, 24, 60) == 24

    scene.period = -10080  # 1W
    assert scene._ohlc_n_buckets(s, 24, 60) == 48

    scene.period = 6  # 1M
    assert scene._ohlc_n_buckets(s, 24, 60) == 30

    scene.period = 18  # 3M
    assert scene._ohlc_n_buckets(s, 24, 60) == 60

    scene.period = 73  # 1A
    assert scene._ohlc_n_buckets(s, 24, 60) <= 60


def test_ohlc_y_fmt_shows_cents_when_zoomed(app):
    scene = GraphScene.__new__(GraphScene)
    fmt = scene._ohlc_y_fmt(100.0, 100.3)
    assert fmt(100.15) == "100.15"
    fmt = scene._ohlc_y_fmt(100.0, 105.0)
    assert fmt(102.5) == "102.5"
    fmt = scene._ohlc_y_fmt(100.0, 150.0)
    assert fmt(125.0) == "125"


def test_candles_and_bars_render_for_short_periods(app):
    tk = _ticker(app)
    scene = GraphScene(app)
    scene.on_enter(tickers=[tk], kind="candles", period=6, return_to="terminal")
    scene.update(0.016)
    surf = pygame.Surface((1280, 720))
    scene.draw(surf)
    assert len(scene._candle_rects) > 0

    scene.kind = "bars"
    scene.period = 18
    scene.draw(surf)

    scene.kind = "candles"
    scene.period = -1440
    scene.draw(surf)


def test_event_markers_accept_pps_override(app):
    tk = _ticker(app)
    scene = GraphScene(app)
    scene.on_enter(tickers=[tk], kind="candles", period=18, return_to="terminal")
    s, pps = scene._series_for_ohlc(tk)
    assert pps == 30
    # doit s'exécuter sans erreur avec le pps personnalisé
    surf = pygame.Surface((1280, 720))
    rect = pygame.Rect(40, 100, 1200, 500)
    scene._draw_event_markers(surf, rect, s, min(s), max(s) - min(s), pps=pps)


def test_intraday_series_for_ohlc_uses_standard_series(app):
    tk = _ticker(app)
    scene = GraphScene(app)
    scene.on_enter(tickers=[tk], kind="candles", period=-1440, return_to="terminal")
    ohlc, pps = scene._series_for_ohlc(tk)
    assert pps is None
    assert len(ohlc) >= 2
