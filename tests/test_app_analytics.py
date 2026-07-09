"""Tests de l'app native Analyse du portefeuille (apps/app_analytics.py) —
migration de scenes/scene_analytics.py hors de l'hébergement flou (netteté),
liée en permanence via le bouton « ANALYSE (PA) » de Trading/Portefeuille."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from apps.app_analytics import AnalyticsApp
from core import portfolio as pf

pygame.font.init()

RECT = pygame.Rect(0, 0, 1120, 680)


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    for _ in range(30):
        a.market.step()
    a.scenes.go("desktop")
    return a


def _click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def _open(app):
    desk = app.scenes.current
    w = desk._open_scene_window("analytics")
    return desk, w


def _with_positions(app, n=3):
    p = app.gs.player
    for c in app.market.top_companies(n=n):
        pf.buy(p, app.market, c["ticker"], 10)


def test_analytics_is_native_app_not_hosted(app):
    desk, w = _open(app)
    assert w.key == "analytics" and isinstance(w.app_obj, AnalyticsApp)


def test_draws_empty_portfolio_without_crash(app):
    desk, w = _open(app)
    w.app_obj.draw(app.screen, RECT)


def test_draws_with_positions_wide_and_narrow(app):
    _with_positions(app)
    desk, w = _open(app)
    w.app_obj.draw(app.screen, RECT)                       # 3 colonnes
    w.app_obj.draw(app.screen, pygame.Rect(0, 0, 760, 500))  # empilé, sans graphes


def test_click_holding_opens_popup(app):
    _with_positions(app)
    desk, w = _open(app)
    an = w.app_obj
    an.draw(app.screen, RECT)
    tk, r = next(iter(an._holding_rects.items()))
    an.handle_event(_click(r.center), RECT)
    assert len(an.popups) == 1


def test_book_link_opens_portfolio_window(app):
    _with_positions(app)
    desk, w = _open(app)
    an = w.app_obj
    an.draw(app.screen, RECT)
    an.handle_event(_click(an._book_btn.center), RECT)
    assert any(win.key == "book" for win in desk.wm.windows)


def test_stress_link_opens_hosted_window(app):
    _with_positions(app)
    desk, w = _open(app)
    an = w.app_obj
    an.draw(app.screen, RECT)
    an.handle_event(_click(an._stress_btn.center), RECT)
    assert any(win.key == "scene:stresstest" for win in desk.wm.windows)


def test_analytics_button_of_book_opens_native_app(app):
    """Le bouton ANALYSE (PA) du Portefeuille route vers l'app NATIVE."""
    desk = app.scenes.current
    w = desk._open_scene_window("book")
    book = w.app_obj
    book.draw(app.screen, pygame.Rect(0, 0, 980, 600))
    book.handle_event(_click(book._pa_btn.center), pygame.Rect(0, 0, 980, 600))
    win = next(win for win in desk.wm.windows if win.key == "analytics")
    assert isinstance(win.app_obj, AnalyticsApp)


def test_analytics_is_factory_only_no_standing_icon(app):
    desk = app.scenes.current
    keys = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert "analytics" not in keys
