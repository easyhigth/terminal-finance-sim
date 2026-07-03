"""
tests/test_experience_mode.py — Mode débutant/expert (core/experience_mode.py) :
masque les pages financières avancées non pertinentes pour la voie du joueur
dans le menu Démarrer/la palette Ctrl+K, sans jamais rien supprimer.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from core import config
from core import experience_mode as XP


class _FakePlayer:
    def __init__(self, track="General"):
        self.track = track


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(XP, "_PATH", str(tmp_path / "experience_mode.json"))
    monkeypatch.setattr(config, "SAVE_DIR", str(tmp_path / "saves"))
    XP._mode = "expert"
    yield
    XP._mode = "expert"


def test_default_mode_is_expert():
    assert XP.get_mode() == "expert"
    assert XP.is_beginner() is False


def test_set_mode_beginner_and_back():
    XP.set_mode("beginner")
    assert XP.get_mode() == "beginner"
    assert XP.is_beginner() is True
    XP.set_mode("expert")
    assert XP.is_beginner() is False


def test_set_mode_ignores_unknown_value():
    XP.set_mode("bogus")
    assert XP.get_mode() == "expert"


def test_persisted_across_reload():
    XP.set_mode("beginner")
    XP._mode = "expert"   # simule un module rechargé
    XP._load()
    assert XP.get_mode() == "beginner"


def test_expert_mode_never_hides_anything():
    p = _FakePlayer(track="General")
    for scene in XP.ADVANCED_SCENES:
        assert XP.scene_hidden(scene, p) is False


def test_beginner_mode_hides_advanced_scenes_off_track():
    XP.set_mode("beginner")
    p = _FakePlayer(track="General")
    assert XP.scene_hidden("structured", p) is True
    assert XP.scene_hidden("risk", p) is True


def test_beginner_mode_keeps_track_relevant_scenes_visible():
    XP.set_mode("beginner")
    p = _FakePlayer(track="Risk")
    assert XP.scene_hidden("risk", p) is False
    assert XP.scene_hidden("alm", p) is False
    assert XP.scene_hidden("structured", p) is True   # toujours hors voie


def test_beginner_mode_never_hides_non_advanced_scenes():
    XP.set_mode("beginner")
    p = _FakePlayer(track="General")
    assert XP.scene_hidden("markethub", p) is False
    assert XP.scene_hidden("book", p) is False
