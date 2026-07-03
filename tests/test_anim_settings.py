"""Tests pour core/anim_settings.py — préférence « réduire les animations »."""
import pytest

from core import anim_settings as anim


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(anim, "_PATH", str(tmp_path / "anim_settings.json"))
    anim._REDUCE_MOTION = False
    yield
    anim._REDUCE_MOTION = False


def test_disabled_by_default():
    assert anim.reduce_motion() is False


def test_set_reduce_motion_true():
    anim.set_reduce_motion(True)
    assert anim.reduce_motion() is True


def test_set_reduce_motion_coerces_truthy_values():
    anim.set_reduce_motion(1)
    assert anim.reduce_motion() is True
    anim.set_reduce_motion(0)
    assert anim.reduce_motion() is False


def test_toggle_flips_state_and_returns_new_value():
    assert anim.toggle_reduce_motion() is True
    assert anim.reduce_motion() is True
    assert anim.toggle_reduce_motion() is False
    assert anim.reduce_motion() is False


def test_set_reduce_motion_writes_to_path(tmp_path):
    anim.set_reduce_motion(True)
    assert (tmp_path / "anim_settings.json").exists()


def test_persisted_value_reloaded_from_disk(tmp_path, monkeypatch):
    path = str(tmp_path / "anim_settings2.json")
    monkeypatch.setattr(anim, "_PATH", path)
    anim.set_reduce_motion(True)
    anim._REDUCE_MOTION = False
    anim._load()
    assert anim.reduce_motion() is True


def test_load_defaults_to_false_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(anim, "_PATH", str(tmp_path / "missing.json"))
    anim._REDUCE_MOTION = True
    anim._load()
    assert anim.reduce_motion() is False
