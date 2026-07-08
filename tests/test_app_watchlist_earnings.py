"""Tests du rappel « publie bientôt » dans l'app Watchlist
(apps/app_watchlist.py) — réutilise `Market.metrics()["steps_to_earnings"]`
(déjà calculé pour la fiche société) pour afficher une pastille + tooltip
quand une valeur suivie publie ses résultats dans les tout prochains pas."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from apps.app_watchlist import EARNINGS_SOON_STEPS, WatchlistApp

pygame.font.init()

RECT = pygame.Rect(0, 0, 420, 460)


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    return a


def _open(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("watchlist")
    return desk, w


def test_earnings_days_soon_company(app):
    # au step_count=0, l'entreprise d'indice 0 a steps_to_earnings == 0
    tk = app.market.companies[0]["ticker"]
    desk, w = _open(app)
    wl = w.app_obj
    assert wl._earnings_days(tk) == 0


def test_earnings_days_none_when_far(app):
    # une entreprise avec steps_to_earnings > EARNINGS_SOON_STEPS -> None
    tk = next(c["ticker"] for i, c in enumerate(app.market.companies)
              if i > EARNINGS_SOON_STEPS + 2)
    desk, w = _open(app)
    wl = w.app_obj
    assert wl._earnings_days(tk) is None


def test_dot_and_tooltip_drawn_for_soon_earnings(app, monkeypatch):
    tk = app.market.companies[0]["ticker"]
    app.gs.player.watchlist = [tk]
    desk, w = _open(app)
    wl = w.app_obj
    wl.view = "list"
    wl.draw(app.screen, RECT)
    assert tk in wl._earnings_rects

    # survol de la pastille -> tooltip
    dot = wl._earnings_rects[tk]
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: dot.center)
    wl.draw(app.screen, RECT)
    assert wl._tooltip is not None
    assert "aujourd'hui" in wl._tooltip[0].lower()


def test_no_dot_for_ticker_without_soon_earnings(app):
    tk = next(c["ticker"] for i, c in enumerate(app.market.companies)
              if i > EARNINGS_SOON_STEPS + 2)
    app.gs.player.watchlist = [tk]
    desk, w = _open(app)
    wl = w.app_obj
    wl.draw(app.screen, RECT)
    assert tk not in wl._earnings_rects


def test_watchlist_draws_without_crash_when_empty(app):
    desk, w = _open(app)
    w.app_obj.draw(app.screen, RECT)
