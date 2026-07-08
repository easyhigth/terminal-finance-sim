"""Tests des apps natives Décision (apps/app_dilemma.py) et Revue de
performance (apps/app_review.py) — migration depuis scenes/scene_dilemma.py
et scenes/scene_review.py (rendu hébergé 1280×720 réduit par smoothscale →
flou) vers un dessin à la résolution de la fenêtre, même principe que
Portefeuille/Marché avant elles. Ces deux écrans sont aussi des popups
FORCÉS par le jeu (App.route_scene) : vérifie le clignotement de barre des
tâches et l'auto-pause (core/sim_clock.FOCUS_SCENE_NAMES)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from apps.app_dilemma import DilemmaApp
from apps.app_review import ReviewApp

pygame.font.init()


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.reputation = 80
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    for _ in range(30):
        a.market.step()
    return a


def _click(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y))


def _dilemma():
    return {
        "id": "test_dilemma", "category": "ethique", "title": "Test",
        "scenario": "Un scénario de test.",
        "options": [
            {"label": "Option A", "outcome": "Issue A", "cash": 1000.0, "rep": 2, "heat": 0},
            {"label": "Option B", "outcome": "Issue B", "cash": -500.0, "rep": -1, "heat": 3},
        ],
    }


# --------------------------------------------------------------------- Dilemma
def test_dilemma_is_native_app_not_hosted(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.gs.player.pending_dilemmas = [_dilemma()]
    w = desk._open_scene_window("dilemma")
    assert w.key == "dilemma" and isinstance(w.app_obj, DilemmaApp)


def test_dilemma_draws_decide_and_outcome_states(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.gs.player.pending_dilemmas = [_dilemma()]
    w = desk._open_scene_window("dilemma")
    rect = pygame.Rect(0, 0, 900, 620)
    w.app_obj.draw(app.screen, rect)   # état "decide"
    assert w.app_obj.option_rects
    i, r = next(iter(w.app_obj.option_rects.items()))
    w.app_obj.handle_event(_click(r.centerx, r.centery), rect)
    assert w.app_obj.state == "outcome"
    w.app_obj.draw(app.screen, rect)   # état "outcome" ne doit pas lever


def test_dilemma_with_no_pending_shows_placeholder_without_crash(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.gs.player.pending_dilemmas = []
    w = desk._open_scene_window("dilemma")
    rect = pygame.Rect(0, 0, 900, 620)
    w.app_obj.draw(app.screen, rect)
    assert w.app_obj.handle_event(_click(10, 10), rect) is False


def test_dilemma_forced_popup_flags_attention(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.gs.player.pending_dilemmas = [_dilemma()]
    app.route_scene("dilemma", return_to="terminal")
    w = next(win for win in desk.wm.windows if win.key == "dilemma")
    assert w.attention is True
    desk.wm.focus(w)
    assert w.attention is False


def test_dilemma_pauses_time_via_focus_scene_names(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.gs.player.pending_dilemmas = [_dilemma()]
    desk._open_scene_window("dilemma")
    assert desk._engaged_in_focus_work() is True


def test_reopening_dilemma_refreshes_stale_state(app):
    """Un nouveau dilemme signature déclenché alors qu'une fenêtre Décision
    déjà résolue traîne encore ouverte doit repartir de zéro (pas garder
    l'état "outcome" du précédent)."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.gs.player.pending_dilemmas = [_dilemma()]
    w1 = desk._open_scene_window("dilemma")
    rect = pygame.Rect(0, 0, 900, 620)
    w1.app_obj.draw(app.screen, rect)
    i, r = next(iter(w1.app_obj.option_rects.items()))
    w1.app_obj.handle_event(_click(r.centerx, r.centery), rect)
    assert w1.app_obj.state == "outcome"

    app.gs.player.pending_dilemmas = [_dilemma()]
    w2 = desk._open_scene_window("dilemma")
    assert w2.app_obj.state == "decide"


# ---------------------------------------------------------------------- Review
def test_review_is_native_app_not_hosted(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.gs.player.pending_review = {"reputation": 80, "grade_missions": 3,
                                     "realized_pnl": 5000.0, "standard_bonus": 20000.0}
    w = desk._open_scene_window("review")
    assert w.key == "review" and isinstance(w.app_obj, ReviewApp)


def test_review_draws_decide_and_outcome_states(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.gs.player.pending_review = {"reputation": 80, "grade_missions": 3,
                                     "realized_pnl": 5000.0, "standard_bonus": 20000.0}
    w = desk._open_scene_window("review")
    rect = pygame.Rect(0, 0, 860, 560)
    w.app_obj.draw(app.screen, rect)
    assert w.app_obj.option_rects
    i, r = next(iter(w.app_obj.option_rects.items()))
    w.app_obj.handle_event(_click(r.centerx, r.centery), rect)
    assert w.app_obj.state == "outcome"
    w.app_obj.draw(app.screen, rect)


def test_review_pauses_time_via_focus_scene_names(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.gs.player.pending_review = {"reputation": 80, "grade_missions": 3,
                                     "realized_pnl": 5000.0, "standard_bonus": 20000.0}
    desk._open_scene_window("review")
    assert desk._engaged_in_focus_work() is True
