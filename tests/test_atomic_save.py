"""Tests de l'écriture atomique des sauvegardes (core/jsonio.py) et de son
intégration dans GameState.save/load/delete : un crash en plein dump ne doit
jamais coûter la partie, et un slot corrompu doit retomber sur son .bak."""
import json
import os

import pytest

from core import config, jsonio
from core.game_state import GameState


@pytest.fixture
def save_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SAVE_DIR", str(tmp_path))
    return tmp_path


# ------------------------------------------------------------------ jsonio
def test_write_then_read(tmp_path):
    p = str(tmp_path / "x.json")
    jsonio.write_json_atomic(p, {"a": 1})
    data, source = jsonio.read_json_with_backup(p)
    assert data == {"a": 1} and source == "main"


def test_backup_rotation_keeps_previous_version(tmp_path):
    p = str(tmp_path / "x.json")
    jsonio.write_json_atomic(p, {"v": 1})
    jsonio.write_json_atomic(p, {"v": 2})
    assert json.load(open(p)) == {"v": 2}
    assert json.load(open(jsonio.backup_path(p))) == {"v": 1}


def test_corrupt_main_falls_back_to_backup(tmp_path):
    p = str(tmp_path / "x.json")
    jsonio.write_json_atomic(p, {"v": 1})
    jsonio.write_json_atomic(p, {"v": 2})
    with open(p, "w") as f:
        f.write('{"v": 2')   # tronqué : crash simulé en plein écriture
    data, source = jsonio.read_json_with_backup(p)
    assert data == {"v": 1} and source == "backup"


def test_failed_serialisation_leaves_previous_file_intact(tmp_path):
    p = str(tmp_path / "x.json")
    jsonio.write_json_atomic(p, {"v": 1})
    with pytest.raises(TypeError):
        jsonio.write_json_atomic(p, {"bad": object()})
    # le fichier final n'a pas bougé et aucun .tmp ne traîne
    assert json.load(open(p)) == {"v": 1}
    assert [fn for fn in os.listdir(tmp_path) if fn.endswith(".tmp")] == []


def test_read_missing_returns_none(tmp_path):
    assert jsonio.read_json_with_backup(str(tmp_path / "nope.json")) == (None, None)


# --------------------------------------------------------------- GameState
def test_save_load_roundtrip(save_dir):
    gs = GameState()
    gs.player.name = "Atomique"
    gs.player.cash = 123_456.0
    gs.save("slot_test")
    loaded = GameState.load("slot_test")
    assert loaded.player.name == "Atomique"
    assert loaded.player.cash == 123_456.0


def test_load_recovers_from_corrupt_slot(save_dir):
    gs = GameState()
    gs.player.name = "V1"
    gs.save("slot_test")
    gs.player.name = "V2"
    gs.save("slot_test")
    path = os.path.join(str(save_dir), "slot_test.json")
    with open(path, "w") as f:
        f.write("{ corrompu")
    loaded = GameState.load("slot_test")
    assert loaded is not None
    assert loaded.player.name == "V1"   # récupéré depuis le .bak


def test_delete_removes_backup_too(save_dir):
    gs = GameState()
    gs.save("slot_test")
    gs.save("slot_test")   # crée le .bak
    assert GameState.delete("slot_test") is True
    assert GameState.load("slot_test") is None


# ---------------------------------------------------- rotation d'autosaves
def test_autosave_rotation_keeps_generations(save_dir, monkeypatch):
    from core import autosave_settings
    monkeypatch.setattr(autosave_settings, "get_interval", lambda: 0)
    gs = GameState()
    for i, name in enumerate(["V1", "V2", "V3", "V4"]):
        gs.player.name = name
        gs.last_saved = 0.0
        gs.save(config.AUTOSAVE_SLOT)
    assert GameState.load(config.AUTOSAVE_SLOT).player.name == "V4"
    assert GameState.load(config.AUTOSAVE_HISTORY_SLOTS[0]).player.name == "V3"
    assert GameState.load(config.AUTOSAVE_HISTORY_SLOTS[1]).player.name == "V2"


def test_manual_slots_do_not_rotate(save_dir, monkeypatch):
    gs = GameState()
    gs.player.name = "M1"
    gs.save("slot1")
    gs.player.name = "M2"
    gs.save("slot1")
    assert GameState.load(config.AUTOSAVE_HISTORY_SLOTS[0]) is None
