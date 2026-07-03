"""Tests pour core/desktop_onboarding.py — carte d'accueil du bureau vue/pas vue."""
import pytest

from core import desktop_onboarding as onb


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(onb, "_PATH", str(tmp_path / "desktop_onboarding.json"))
    onb._SEEN = False
    yield
    onb._SEEN = False


def test_not_seen_by_default():
    assert onb.seen() is False


def test_mark_seen_sets_flag():
    onb.mark_seen()
    assert onb.seen() is True


def test_mark_seen_is_idempotent():
    onb.mark_seen()
    onb.mark_seen()
    assert onb.seen() is True


def test_reset_clears_flag():
    onb.mark_seen()
    onb.reset()
    assert onb.seen() is False


def test_mark_seen_writes_to_path(tmp_path):
    onb.mark_seen()
    assert (tmp_path / "desktop_onboarding.json").exists()


def test_persisted_value_reloaded_from_disk(tmp_path, monkeypatch):
    path = str(tmp_path / "desktop_onboarding2.json")
    monkeypatch.setattr(onb, "_PATH", path)
    onb.mark_seen()
    onb._SEEN = False
    onb._load()
    assert onb.seen() is True


def test_load_defaults_to_false_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(onb, "_PATH", str(tmp_path / "missing.json"))
    onb._SEEN = True
    onb._load()
    assert onb.seen() is False
