"""Tests pour core/display_settings.py — mode d'affichage persiste."""
import pytest

from core import display_settings as ds


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(ds, "_PATH", str(tmp_path / "display_settings.json"))
    ds._MODE = "windowed"
    yield
    ds._MODE = "windowed"


def test_default_mode_is_windowed():
    assert ds.get_mode() == "windowed"


def test_set_mode_valid_persists_in_memory():
    ds.set_mode("fullscreen")
    assert ds.get_mode() == "fullscreen"


def test_set_mode_invalid_falls_back_to_windowed():
    ds.set_mode("fullscreen")
    ds.set_mode("bogus")
    assert ds.get_mode() == "windowed"


def test_set_mode_writes_to_path(tmp_path):
    ds.set_mode("borderless")
    assert (tmp_path / "display_settings.json").exists()


def test_next_mode_cycles_through_all_modes():
    seen = [ds.get_mode()]
    for _ in range(len(ds.MODES)):
        seen.append(ds.next_mode())
    assert seen[0] == seen[-1]
    assert set(seen[:-1]) == set(ds.MODES)


def test_next_mode_updates_get_mode():
    m = ds.next_mode()
    assert ds.get_mode() == m


def test_label_returns_nonempty_string_for_each_mode():
    for mode in ds.MODES:
        assert isinstance(ds.label(mode, "fr"), str) and ds.label(mode, "fr")
        assert isinstance(ds.label(mode, "en"), str) and ds.label(mode, "en")


def test_persisted_mode_reloaded_from_disk(tmp_path, monkeypatch):
    path = str(tmp_path / "display_settings2.json")
    monkeypatch.setattr(ds, "_PATH", path)
    ds.set_mode("fullscreen")
    ds._MODE = "windowed"
    ds._load()
    assert ds.get_mode() == "fullscreen"
