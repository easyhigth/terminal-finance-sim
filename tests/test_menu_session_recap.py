"""Tests du toast « au revoir » au retour au menu depuis une partie en cours
(scenes/scene_menu.py::_notify_session_recap)."""
import main


def test_recap_toast_shown_when_returning_from_active_game():
    app = main.App()
    app.ensure_market()
    app.scenes.go("menu")
    assert len(app.notes.toasts) == 1
    assert "score" in app.notes.toasts[-1]["text"]


def test_no_recap_toast_at_cold_start():
    app = main.App()
    app.scenes.go("menu")
    assert app.notes.toasts == []


def test_no_recap_toast_for_sandbox_run():
    app = main.App()
    app.ensure_market()
    app.gs.player.sandbox = True
    app.scenes.go("menu")
    assert app.notes.toasts == []


def test_no_recap_toast_after_real_game_over():
    app = main.App()
    app.ensure_market()
    app.gs.player.game_over = True
    app.scenes.go("menu")
    assert app.notes.toasts == []


def test_recap_shown_again_on_repeated_menu_visits():
    """Chaque retour explicite au menu depuis une partie active pousse son
    propre toast (pas de déduplication artificielle) — cohérent avec le
    reste du jeu (les toasts sont éphémères, pas des évènements uniques)."""
    app = main.App()
    app.ensure_market()
    app.scenes.go("desktop")
    app.scenes.go("menu")
    app.scenes.go("desktop")
    app.scenes.go("menu")
    recaps = [t for t in app.notes.toasts if "score" in t["text"]]
    assert len(recaps) == 2
