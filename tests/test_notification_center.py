"""
tests/test_notification_center.py — Centre de notifications (bureau) :
historique des toasts (`ui/notifications.py::NotificationCenter.history`,
alimenté par `App.notify`) et son panneau (`apps/app_notifications.py`), qui
permet de retrouver un évènement passé et de rouvrir son contexte
(`action`/`action_kwargs`, cf. `App.route_scene`).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main


@pytest.fixture()
def app():
    from core import desktop_onboarding
    desktop_onboarding.mark_seen()
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.reputation = 80
    return a


def _click(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y))


def test_notify_records_history_with_action_and_day(app):
    app.gs.player.day = 42
    app.notify("Test message", "info", action="mandates")
    entry = app.notes.history[-1]
    assert entry["text"] == "Test message"
    assert entry["action"] == "mandates"
    assert entry["day"] == 42


def test_notify_without_action_records_none(app):
    app.notify("Sans contexte", "good")
    entry = app.notes.history[-1]
    assert entry["action"] is None
    assert entry["action_kwargs"] == {}


def test_history_is_capped(app):
    for i in range(80):
        app.notify(f"msg {i}", "info")
    assert len(app.notes.history) <= 60


def test_notification_app_appears_on_desktop(app):
    from scenes.scene_desktop_common import APPS
    assert any(k == "notifcenter" for k, *_ in APPS)
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("notifcenter")
    assert w is not None
    assert w.key == "notifcenter"


def test_clicking_a_row_with_action_opens_the_target_window(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.notify("Offre de mandat : Client X", "info", action="mandates")
    w = desk._launch("notifcenter")
    napp = w.app_obj
    napp.draw(app.screen, w.content_rect)
    assert napp._row_rects, "au moins une ligne d'historique attendue"
    r, entry = next(iter(napp._row_rects.values()))
    assert entry["action"] == "mandates"
    napp.handle_event(_click(r.centerx, r.centery), w.content_rect)
    assert any(win.key == "scene:mandates" for win in desk.wm.windows)


def test_clicking_a_row_without_action_does_nothing(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.notify("Simple info", "info")
    w = desk._launch("notifcenter")
    napp = w.app_obj
    napp.draw(app.screen, w.content_rect)
    n_windows_before = len(desk.wm.windows)
    r, entry = next(iter(napp._row_rects.values()))
    assert entry["action"] is None
    napp.handle_event(_click(r.centerx, r.centery), w.content_rect)
    assert len(desk.wm.windows) == n_windows_before
