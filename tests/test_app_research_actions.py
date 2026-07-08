"""Tests des liens inter-apps de l'app Recherche (apps/app_research.py) —
notamment le nouveau bouton « Alerte » qui ouvre l'app Alertes pré-filtrée
sur la valeur consultée (jusqu'ici, seules les notifications savaient le
faire ; il fallait rouvrir Alertes et retaper le ticker à la main)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main

pygame.font.init()

RECT = pygame.Rect(0, 0, 820, 520)


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 5
    p.cash = 100_000.0
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    a.scenes.go("desktop")
    return a


def _click(rect):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)


def test_research_has_alert_action_button(app):
    desk = app.scenes.current
    w = desk._launch("research")
    research = w.app_obj
    research.draw(app.screen, RECT)
    assert "alert" in research._action_rects


def test_alert_action_opens_alerts_app_preselected(app):
    desk = app.scenes.current
    w = desk._launch("research")
    research = w.app_obj
    tk = app.market.top_companies(n=1)[0]["ticker"]
    research.sel = tk
    research.draw(app.screen, RECT)
    research.handle_event(_click(research._action_rects["alert"]), RECT)

    alerts_win = next(win for win in desk.wm.windows if win.key == "alerts")
    assert alerts_win.app_obj.sel_ticker == tk
    assert alerts_win.app_obj.text_focus == "price"


def test_other_research_actions_still_present(app):
    """Régression : le nouveau bouton n'a pas fait disparaître les autres."""
    desk = app.scenes.current
    w = desk._launch("research")
    research = w.app_obj
    research.draw(app.screen, RECT)
    assert {"watch", "trade", "sheet", "analyse", "alert"} == set(research._action_rects)
