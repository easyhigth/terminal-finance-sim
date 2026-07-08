"""Tests de l'app native Évaluation (apps/app_evaluation.py) — migration de
scenes/scene_evaluation.py hors de l'hébergement flou (netteté), même
principe que Mission. Vérifie le flux complet promotion et certification,
la pause/reprise (player.eval_state), le redémarrage à neuf après un examen
terminé, et la conservation d'un examen en cours à la ré-ouverture."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from apps.app_evaluation import EvaluationApp

pygame.font.init()

RECT = pygame.Rect(0, 0, 1040, 660)


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 2
    p.cash = 100_000.0
    p.reputation = 80
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    return a


def _click(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y))


def _key(k, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=unicode, mod=0)


def _open(app, **kwargs):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("evaluation", **kwargs)
    return desk, w


def _answer_all_correctly(ev):
    guard = 0
    while ev.state != "result" and guard < 60:
        guard += 1
        it = ev._item()
        if ev.state == "question":
            if ev._is_mcq(it):
                ev._answer_mcq(it["answer"], it)
            elif it["kind"] == "text":
                ev.input = it["answers"][0]
                ev._submit(it)
            else:
                ev.input = str(it["answer"])
                ev._submit(it)
        elif ev.state == "feedback":
            ev._next()


def test_evaluation_is_native_app_not_hosted(app):
    desk, w = _open(app)
    assert w.key == "evaluation" and isinstance(w.app_obj, EvaluationApp)


def test_evaluation_defaults_to_promotion_mode(app):
    desk, w = _open(app)
    assert w.app_obj.mode == "promotion"
    assert w.app_obj.state == "intro"


def test_evaluation_full_run_promotes_on_pass(app):
    desk, w = _open(app)
    ev = w.app_obj
    ev.draw(app.screen, RECT)
    ev.handle_event(_key(pygame.K_RETURN), RECT)   # intro -> question
    assert ev.state == "question"
    grade_before = app.gs.player.grade_index
    _answer_all_correctly(ev)
    assert ev.state == "result"
    assert ev.passed is True
    assert app.gs.player.grade_index == grade_before + 1
    ev.draw(app.screen, RECT)   # écran résultat sans exception


def test_evaluation_result_terminate_closes_window(app):
    desk, w = _open(app)
    ev = w.app_obj
    ev.state = "result"
    ev.passed = True
    ev.draw(app.screen, RECT)
    assert ev._continue_rect is not None
    ev.handle_event(_click(*ev._continue_rect.center), RECT)
    assert not any(win.key == "evaluation" for win in desk.wm.windows)


def test_evaluation_pause_saves_state_and_closes_window(app):
    desk, w = _open(app)
    ev = w.app_obj
    ev.draw(app.screen, RECT)
    ev.handle_event(_key(pygame.K_RETURN), RECT)
    ev.draw(app.screen, RECT)
    assert ev._pause_rect is not None
    ev.handle_event(_click(*ev._pause_rect.center), RECT)
    assert not any(win.key == "evaluation" for win in desk.wm.windows)
    assert app.gs.player.eval_state.get("mode") == "promotion"
    assert app.gs.player.eval_state.get("items")


def test_reopening_paused_evaluation_resumes(app):
    desk, w1 = _open(app)
    ev1 = w1.app_obj
    ev1.draw(app.screen, RECT)
    ev1.handle_event(_key(pygame.K_RETURN), RECT)
    ev1.draw(app.screen, RECT)
    ev1.handle_event(_click(*ev1._pause_rect.center), RECT)

    desk2, w2 = _open(app)
    ev2 = w2.app_obj
    assert ev2.state == "question"
    assert ev2.idx == 0


def test_reopening_finished_evaluation_starts_fresh(app):
    desk, w1 = _open(app)
    ev1 = w1.app_obj
    ev1.state = "result"
    ev1.passed = False
    desk2, w2 = _open(app)
    assert w2.app_obj is not ev1
    assert w2.app_obj.state == "intro"


def test_inprogress_evaluation_keeps_same_window(app):
    desk, w1 = _open(app)
    ev1 = w1.app_obj
    ev1.draw(app.screen, RECT)
    ev1.handle_event(_key(pygame.K_RETURN), RECT)
    ev1.idx = 1
    w2 = desk._open_scene_window("evaluation")
    assert w2.app_obj is ev1
    assert w2.app_obj.idx == 1


def test_certification_mode_via_configure(app):
    from core import certifications as C
    pid = next(iter(C.PROGRAMS))
    started = C.pay_and_start(app.gs.player, pid)
    assert started is not None
    tier, level = started
    desk, w = _open(app, mode="cert", program=pid, tier=tier, level=level, return_to="cert")
    ev = w.app_obj
    assert ev.mode == "cert"
    assert ev.cert_program == pid
    ev.draw(app.screen, RECT)


def test_evaluation_pauses_time_via_focus_scene_names(app):
    desk, w = _open(app)
    assert desk._engaged_in_focus_work() is True


def test_evaluation_narrow_window_draws_without_crash(app):
    desk, w = _open(app)
    ev = w.app_obj
    small = pygame.Rect(0, 0, 700, 480)
    ev.draw(app.screen, small)
    ev.handle_event(_key(pygame.K_RETURN), small)
    ev.draw(app.screen, small)


def test_evaluation_calculator_toggle(app):
    desk, w = _open(app)
    ev = w.app_obj
    ev.draw(app.screen, RECT)
    ev.handle_event(_key(pygame.K_RETURN), RECT)
    ev.draw(app.screen, RECT)
    assert ev._calc_rect is not None
    ev.handle_event(_click(*ev._calc_rect.center), RECT)
    assert ev.calc is not None
    ev.draw(app.screen, RECT)
    ev.handle_event(_click(*ev._calc_rect.center), RECT)
    assert ev.calc is None
