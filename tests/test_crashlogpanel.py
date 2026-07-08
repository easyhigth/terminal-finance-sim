"""Tests du visualiseur de journal de plantage : core/crashlog.py::read/clear
et l'overlay ui/crashlogpanel.py::CrashLogPanel ouvert depuis l'écran
RÉGLAGES (scenes/scene_settings.py) — permet à un joueur sans accès au
système de fichiers de consulter/copier les tracebacks journalisés par le
filet de sécurité (main.py::App._safe_call)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from core import crashlog
from ui.crashlogpanel import CrashLogPanel

pygame.font.init()


@pytest.fixture()
def isolated_crashlog(tmp_path, monkeypatch):
    monkeypatch.setattr(crashlog, "_PATH", str(tmp_path / "crash.log"))
    return tmp_path


def _click(rect):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)


# ------------------------------------------------------------- core/crashlog
def test_read_returns_empty_string_when_no_log(isolated_crashlog):
    assert crashlog.read() == ""


def test_read_returns_recorded_content(isolated_crashlog):
    try:
        raise ValueError("boom de test")
    except ValueError as exc:
        crashlog.record(exc, "test")
    content = crashlog.read()
    assert "ValueError" in content
    assert "boom de test" in content


def test_clear_removes_the_log_file(isolated_crashlog):
    try:
        raise RuntimeError("x")
    except RuntimeError as exc:
        crashlog.record(exc, "test")
    assert crashlog.read() != ""
    crashlog.clear()
    assert crashlog.read() == ""


def test_clear_is_a_no_op_when_no_log_exists(isolated_crashlog):
    crashlog.clear()   # ne doit pas lever


# ------------------------------------------------------------ CrashLogPanel
def test_panel_draws_empty_state_without_crash(isolated_crashlog):
    surf = pygame.Surface((1280, 720))
    panel = CrashLogPanel()
    panel.draw(surf)   # ne doit pas lever, journal vide


def test_panel_draws_with_content_and_scrolls(isolated_crashlog):
    for i in range(30):
        try:
            raise ValueError(f"erreur {i}")
        except ValueError as exc:
            crashlog.record(exc, f"ctx{i}")
    a = main.App()
    panel = CrashLogPanel()
    panel.draw(a.screen)
    assert panel._max_scroll > 0


def test_panel_copy_button_copies_log(isolated_crashlog, monkeypatch):
    try:
        raise ValueError("à copier")
    except ValueError as exc:
        crashlog.record(exc, "test")
    from core import clipboard
    copied = {}
    monkeypatch.setattr(clipboard, "copy", lambda text: copied.setdefault("text", text))

    a = main.App()
    panel = CrashLogPanel()
    panel.draw(a.screen)
    panel.handle(_click(panel._copy_rect))
    assert "à copier" in copied.get("text", "")


def test_panel_clear_button_clears_log(isolated_crashlog):
    try:
        raise ValueError("à vider")
    except ValueError as exc:
        crashlog.record(exc, "test")
    a = main.App()
    panel = CrashLogPanel()
    panel.draw(a.screen)
    panel.handle(_click(panel._clear_rect))
    assert crashlog.read() == ""


def test_panel_escape_closes():
    panel = CrashLogPanel()
    panel.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="", mod=0))
    assert panel.closed is True


def test_panel_close_button_closes(isolated_crashlog):
    try:
        raise ValueError("x")
    except ValueError as exc:
        crashlog.record(exc, "test")
    a = main.App()
    panel = CrashLogPanel()
    panel.draw(a.screen)
    panel.handle(_click(panel._close_rect()))
    assert panel.closed is True


# --------------------------------------------------------- scene_settings.py
def test_settings_crashlog_button_opens_panel(isolated_crashlog):
    a = main.App()
    a.ensure_market()
    a.scenes.go("settings", return_to="menu")
    scene = a.scenes.current
    scene.draw(a.screen)
    assert scene.crashlog_panel is None
    scene.handle_event(_click(scene.crashlog_btn.rect))
    assert scene.crashlog_panel is not None


def test_settings_crashlog_panel_escape_closes_without_leaving_settings(isolated_crashlog):
    a = main.App()
    a.ensure_market()
    a.scenes.go("settings", return_to="menu")
    scene = a.scenes.current
    scene.draw(a.screen)
    scene.handle_event(_click(scene.crashlog_btn.rect))
    assert scene.crashlog_panel is not None
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="", mod=0))
    assert scene.crashlog_panel is None
    assert a.scenes.current_name == "settings"   # Échap ferme le panneau, pas l'écran
