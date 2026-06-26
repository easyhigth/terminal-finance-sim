"""
tests/test_scene_portfolio_unified.py — Tests du graphe pnl(t) par position
de scenes/scene_portfolio_unified.py::PortfolioUnifiedScene (couvre l'idée
originale du joueur : visualiser le P&L d'une position commodity comme le
pétrole dans le temps, généralisée à toutes les classes d'actifs).
"""
import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from core import commodities as cmd
from core import portfolio as pf
from core.game_state import GameState
from core.market import Market


@pytest.fixture(scope="module", autouse=True)
def _pygame_init():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield


class _FakeScenes:
    def go(self, name, **kwargs):
        pass


class _FakeApp:
    def __init__(self, gs, market):
        self.gs = gs
        self.market = market
        self.scenes = _FakeScenes()

    def ensure_market(self):
        return self.market


def _make_app_with_positions():
    market = Market(seed=1)
    for _ in range(30):
        market.step()
    gs = GameState()
    p = gs.player
    p.cash = 200_000.0
    tk = market.companies[0]["ticker"]
    pf.buy(p, market, tk, 10)
    cmd.buy(p, market, "OIL", 5)
    app = _FakeApp(gs, market)
    return app, tk


def test_pnl_series_for_commodity_oil_position_matches_avg_qty():
    from scenes.scene_portfolio_unified import PortfolioUnifiedScene

    app, _ = _make_app_with_positions()
    scene = PortfolioUnifiedScene(app)
    scene.on_enter(return_to="terminal")
    rows = scene._rows()
    oil_row = next(r for r in rows if r["id"] == "OIL")
    series = scene._pnl_series(oil_row)
    hist = cmd.history(app.market, "OIL")
    assert len(series) == len(hist)
    # le P&L(t) reconstruit le prix du future "front" (pas le spot) via le
    # ratio front/spot constant (slope de courbe fixe), comme commodities.holdings
    ratio = math.exp(-cmd.roll_yield(app.market, "OIL") / 12.0)
    expected = [(s * ratio - oil_row["avg"]) * cmd.MULTIPLIER * oil_row["qty"] for s in hist]
    assert series == pytest.approx(expected, rel=1e-9)
    # le dernier point du P&L(t) doit correspondre au P&L latent affiché dans la table
    assert series[-1] == pytest.approx(oil_row["pnl"], rel=1e-6)


def test_pnl_series_for_equity_position():
    from scenes.scene_portfolio_unified import PortfolioUnifiedScene

    app, tk = _make_app_with_positions()
    scene = PortfolioUnifiedScene(app)
    scene.on_enter(return_to="terminal")
    rows = scene._rows()
    row = next(r for r in rows if r["id"] == tk)
    series = scene._pnl_series(row)
    assert len(series) >= 2
    assert series[-1] == pytest.approx(row["pnl"], rel=1e-6)


def test_clicking_pnl_cell_opens_chart_view_without_navigating_away():
    from scenes.scene_portfolio_unified import PortfolioUnifiedScene

    app, _ = _make_app_with_positions()
    scene = PortfolioUnifiedScene(app)
    scene.on_enter(return_to="terminal")
    scene.update(0.016)
    surf = pygame.Surface((1280, 720))
    scene.draw(surf)
    assert scene._pnl_rects, "les cellules valeur/P&L doivent être cliquables"

    rect, row = scene._pnl_rects[0]
    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
    scene.handle_event(event)
    assert scene.chart_row is row

    scene.update(0.016)
    scene.draw(surf)  # doit dessiner la vue graphe sans exception


def test_escape_from_chart_view_returns_to_list_not_caller_scene():
    from scenes.scene_portfolio_unified import PortfolioUnifiedScene

    app, _ = _make_app_with_positions()
    scene = PortfolioUnifiedScene(app)
    scene.on_enter(return_to="terminal")
    scene.update(0.016)
    surf = pygame.Surface((1280, 720))
    scene.draw(surf)
    rect, row = scene._pnl_rects[0]
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
    assert scene.chart_row is not None

    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert scene.chart_row is None


def test_chart_view_renders_with_empty_history_gracefully():
    """Une position sans historique disponible (cas limite) ne doit pas
    faire planter la vue graphe."""
    from scenes.scene_portfolio_unified import PortfolioUnifiedScene

    app, _ = _make_app_with_positions()
    scene = PortfolioUnifiedScene(app)
    scene.on_enter(return_to="terminal")
    fake_row = {"cls": "equity", "id": "ZZZZ", "name": "ZZZZ", "qty": 1,
                "avg": 10.0, "price": 10.0, "value": 10.0, "pnl": 0.0,
                "value_abs": 10.0}
    scene.chart_row = fake_row
    scene.update(0.016)
    surf = pygame.Surface((1280, 720))
    scene.draw(surf)
