"""Tests du mode contraste élevé / daltonien (core/colorblind_settings.py)."""
import pytest

from core import colorblind_settings as cb
from core import config


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(cb, "_PATH", str(tmp_path / "colorblind_settings.json"))
    cb.set_enabled(False)   # état neutre avant chaque test
    yield
    cb.set_enabled(False)   # ne pollue pas les autres tests (config est un module partagé)


def test_disabled_by_default_uses_original_palette():
    assert cb.is_enabled() is False
    assert config.COL_UP == cb._DEFAULTS["COL_UP"]
    assert config.COL_DOWN == cb._DEFAULTS["COL_DOWN"]


def test_enable_swaps_all_mapped_colors():
    cb.set_enabled(True)
    assert cb.is_enabled() is True
    for name, alt in cb._ALT.items():
        assert getattr(config, name) == alt


def test_disable_restores_original_colors():
    cb.set_enabled(True)
    cb.set_enabled(False)
    for name, orig in cb._DEFAULTS.items():
        assert getattr(config, name) == orig


def test_toggle_flips_state():
    assert cb.toggle() is True
    assert cb.is_enabled() is True
    assert cb.toggle() is False
    assert cb.is_enabled() is False


def test_up_and_down_colors_are_distinct_in_both_modes():
    assert config.COL_UP != config.COL_DOWN
    cb.set_enabled(True)
    assert config.COL_UP != config.COL_DOWN


def test_persists_across_reload(tmp_path, monkeypatch):
    monkeypatch.setattr(cb, "_PATH", str(tmp_path / "cb2.json"))
    cb.set_enabled(True)
    cb._load()   # simule un redémarrage : relit le JSON persisté
    assert cb.is_enabled() is True


def test_error_panel_default_color_follows_current_palette():
    import pygame

    from ui import widgets
    pygame.font.init()
    surf = pygame.Surface((200, 100))
    cb.set_enabled(True)
    widgets.draw_error_panel(surf, "Erreur")   # ne doit jamais lever
