"""
tests/test_scene_saves.py — Écran de gestion des sauvegardes (scenes/scene_saves.py) :
export/import de sauvegarde en fichier portable (transport entre machines),
en plus des flux classiques charger/enregistrer/supprimer déjà couverts par
le test de fumée.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main
from core import config
from core.game_state import GameState


@pytest.fixture()
def isolated_save_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SAVE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture()
def app(isolated_save_dir):
    a = main.App()
    a.ensure_market()
    a.gs.player.name = "Export Test"
    a.gs.player.cash = 42_000.0
    a.scenes.go("saves", return_to="terminal")
    return a


def _click(rect):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)


def test_export_button_opens_path_prompt_prefilled(app):
    scene = app.scenes.current
    app.gs.save("slot1")
    scene._refresh()
    scene.draw(app.screen)          # peuple self._export_rects
    rect = scene._export_rects["slot1"]
    scene.handle_event(_click(rect))
    assert scene.path_prompt == {"kind": "export", "slot": "slot1"}
    assert scene.path_buf          # pré-rempli (dossier par défaut + nom de fichier)


def test_export_writes_a_standalone_file_readable_by_import(app, tmp_path):
    app.gs.save("slot1")
    scene = app.scenes.current
    scene._refresh()
    dest = tmp_path / "elsewhere" / "portable_save.json"
    scene.path_prompt = {"kind": "export", "slot": "slot1"}
    scene.path_buf = str(dest)
    scene._confirm_path_prompt()
    assert scene.path_prompt is None
    assert dest.exists()
    imported = GameState.import_from(str(dest))
    assert imported is not None
    assert imported.player.name == "Export Test"
    assert imported.player.cash == 42_000.0


def test_export_missing_slot_shows_failure_message(app):
    scene = app.scenes.current
    scene.path_prompt = {"kind": "export", "slot": "does_not_exist"}
    scene.path_buf = "/tmp/whatever.json"
    scene._confirm_path_prompt()
    assert scene.path_prompt is None
    assert "chec" in scene.message.lower() or "fail" in scene.message.lower()


def test_import_button_opens_prompt(app):
    scene = app.scenes.current
    scene.draw(app.screen)
    scene.handle_event(_click(scene._import_btn.rect))
    assert scene.path_prompt == {"kind": "import"}


def test_import_loads_game_and_returns_to_desktop(app, tmp_path):
    # prépare un fichier exporté depuis une AUTRE partie
    other = GameState()
    other.player.name = "Imported Player"
    other.player.cash = 999.0
    dest = tmp_path / "incoming.json"
    other.export_to(str(dest))

    scene = app.scenes.current
    scene.path_prompt = {"kind": "import"}
    scene.path_buf = str(dest)
    scene._confirm_path_prompt()
    assert app.scenes.current_name == "desktop"
    assert app.gs.player.name == "Imported Player"
    assert app.gs.player.cash == 999.0


def test_import_missing_file_shows_failure_and_stays_open(app):
    scene = app.scenes.current
    scene.path_prompt = {"kind": "import"}
    scene.path_buf = "/definitely/not/a/real/path.json"
    scene._confirm_path_prompt()
    assert scene.path_prompt is None
    assert app.scenes.current_name == "saves"   # pas de navigation en cas d'échec
    assert scene.message


def test_path_prompt_escape_cancels_without_side_effect(app):
    scene = app.scenes.current
    scene.path_prompt = {"kind": "import"}
    scene.path_buf = "/tmp/x.json"
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert scene.path_prompt is None
    assert app.scenes.current_name == "saves"


def test_path_prompt_typing_appends_and_backspace_removes(app):
    scene = app.scenes.current
    scene.path_prompt = {"kind": "export", "slot": "slot1"}
    scene.path_buf = ""
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="a"))
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, unicode="b"))
    assert scene.path_buf == "ab"
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode=""))
    assert scene.path_buf == "a"


def test_path_prompt_pastes_via_ctrl_v(app, monkeypatch):
    from core import clipboard
    monkeypatch.setattr(clipboard, "paste", lambda: "/tmp/pasted_save.json")

    scene = app.scenes.current
    scene.path_prompt = {"kind": "export", "slot": "slot1"}
    scene.path_buf = ""
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v,
                                           unicode="v", mod=pygame.KMOD_CTRL))
    assert scene.path_buf == "/tmp/pasted_save.json"


def test_empty_path_shows_message_and_keeps_prompt_open(app):
    scene = app.scenes.current
    scene.path_prompt = {"kind": "export", "slot": "slot1"}
    scene.path_buf = "   "
    scene._confirm_path_prompt()
    assert scene.path_prompt is not None     # reste ouvert : chemin vide refusé
    assert scene.message
