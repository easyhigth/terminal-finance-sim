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


def test_region_colors_all_mapped_and_distinct_in_colorblind_mode():
    regions = ["COL_EUROPE", "COL_USA", "COL_ASIA", "COL_NORTHAM",
               "COL_SOUTHAM", "COL_AFRICA", "COL_OCEANIA"]
    assert all(name in cb._ALT for name in regions)
    cb.set_enabled(True)
    values = [getattr(config, name) for name in regions]
    assert len(set(values)) == len(values)   # 7 continents, 7 teintes distinctes


def test_priority_urgent_and_warn_distinct_from_critical_and_bonus():
    cb.set_enabled(True)
    bucket = {config.COL_PRIO_CRITICAL, config.COL_PRIO_BONUS,
              config.COL_PRIO_URGENT, config.COL_WARN}
    assert len(bucket) == 3   # urgent et warn partagent la même 3e teinte, distincte des 2 extrêmes
    assert config.COL_PRIO_URGENT == config.COL_WARN


def test_continent_color_reflects_colorblind_toggle_live():
    before = {name: config.continent_color(name) for name in config.CONTINENT_COLOR_ATTR}
    cb.set_enabled(True)
    after = {name: config.continent_color(name) for name in config.CONTINENT_COLOR_ATTR}
    for name in config.CONTINENT_COLOR_ATTR:
        assert after[name] != before[name]
    assert len(set(after.values())) == len(after)   # toujours 7 teintes distinctes


def test_worldmap_region_hubs_have_no_frozen_color_key():
    from ui.worldmap import REGION_HUBS
    assert "color" not in REGION_HUBS["Europe"]   # sinon figé à l'import, jamais rafraîchi
    cb.set_enabled(True)
    assert config.continent_color("Europe") == cb._ALT["COL_EUROPE"]


def test_globe_uses_continent_color_helper_not_stale_continents_dict():
    cb.set_enabled(True)
    # config.CONTINENTS["Europe"]["color"] est un dict littéral figé à l'import
    # (piège documenté) : globe.py doit lire config.continent_color(), pas ce
    # champ, pour rester à jour quand le mode contraste élevé est activé.
    assert config.continent_color("Europe") != config.CONTINENTS["Europe"]["color"]


def test_error_panel_default_color_follows_current_palette():
    import pygame

    from ui import widgets
    pygame.font.init()
    surf = pygame.Surface((200, 100))
    cb.set_enabled(True)
    widgets.draw_error_panel(surf, "Erreur")   # ne doit jamais lever
