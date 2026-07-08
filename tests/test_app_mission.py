"""Tests de l'app native Mission (apps/app_mission.py) — migration de
scenes/scene_mission.py hors de l'hébergement flou (netteté), même principe
que Décision/Revue. Vérifie le flux complet intro → question → feedback →
result, les récompenses, la conservation d'une mission EN COURS quand on
ré-ouvre la fenêtre, et le redémarrage à neuf après une mission terminée."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from apps.app_mission import MissionApp

pygame.font.init()


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 2
    p.cash = 100_000.0
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    for _ in range(10):
        a.market.step()
    return a


def _click(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y))


def _key(k, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=unicode, mod=0)


RECT = pygame.Rect(0, 0, 1000, 640)


def _open(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("mission")
    return desk, w


def test_mission_is_native_app_not_hosted(app):
    desk, w = _open(app)
    assert w.key == "mission" and isinstance(w.app_obj, MissionApp)


def test_mission_full_run_grants_rewards_and_advances_market(app):
    desk, w = _open(app)
    m = w.app_obj
    p = app.gs.player
    rep0, missions0 = p.reputation, p.missions_done
    pending0 = app.pending_market_steps
    m.draw(app.screen, RECT)
    m.handle_event(_key(pygame.K_RETURN), RECT)     # intro -> question
    assert m.state == "question"
    guard = 0
    while m.state != "result" and guard < 50:
        guard += 1
        item = m._item()
        if m.state == "question":
            if item["kind"] == "mcq":
                m._answer_mcq(item["answer"])       # toujours la bonne réponse
            else:
                m.input = str(item["answer"])
                m._submit_fill()
        elif m.state == "feedback":
            m._next_item()
        m.draw(app.screen, RECT)
    assert m.state == "result"
    total = len(m.mission["items"])
    assert m.score == total
    assert p.reputation > rep0
    assert p.missions_done == missions0 + 1
    assert app.pending_market_steps == pending0 + 1
    m.draw(app.screen, RECT)   # écran de résultat sans exception


def test_mission_result_screen_terminate_closes_window(app):
    desk, w = _open(app)
    m = w.app_obj
    m.state = "result"
    m.rep_gain, m.cash_gain = 3, 500.0
    m.draw(app.screen, RECT)
    assert m._continue_rect is not None
    m.handle_event(_click(*m._continue_rect.center), RECT)
    assert not any(win.key == "mission" for win in desk.wm.windows)


def test_reopening_in_progress_mission_keeps_state(app):
    desk, w1 = _open(app)
    m1 = w1.app_obj
    m1.state = "question"
    m1.idx = 1
    w2 = desk._open_scene_window("mission")
    assert w2.app_obj is m1          # même instance : progression conservée
    assert w2.app_obj.idx == 1


def test_reopening_finished_mission_starts_a_fresh_one(app):
    desk, w1 = _open(app)
    w1.app_obj.state = "result"
    w1.app_obj.rep_gain, w1.app_obj.cash_gain = 3, 500.0
    w2 = desk._open_scene_window("mission")
    assert w2.app_obj is not w1.app_obj
    assert w2.app_obj.state == "intro"


def test_mission_window_pauses_time(app):
    desk, w = _open(app)
    assert desk._engaged_in_focus_work() is True


def test_mission_narrow_window_draws_without_crash(app):
    desk, w = _open(app)
    m = w.app_obj
    m.state = "question"
    small = pygame.Rect(0, 0, 640, 460)
    m.draw(app.screen, small)
    m.state = "feedback"
    m.chosen = 0
    m.draw(app.screen, small)


def test_mission_calculator_toggle(app):
    desk, w = _open(app)
    m = w.app_obj
    m.draw(app.screen, RECT)
    assert m._calc_rect is not None
    m.handle_event(_click(*m._calc_rect.center), RECT)
    assert m.calc is not None
    m.draw(app.screen, RECT)
    m.handle_event(_click(*m._calc_rect.center), RECT)
    assert m.calc is None
