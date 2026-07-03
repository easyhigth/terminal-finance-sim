"""
tests/test_autosave_settings.py — Cadence de sauvegarde automatique
configurable (core/autosave_settings.py + le chokepoint dans
GameState.save(), core/game_state.py).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from core import autosave_settings as AS
from core import config
from core.game_state import GameState


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(AS, "_PATH", str(tmp_path / "autosave_settings.json"))
    monkeypatch.setattr(config, "SAVE_DIR", str(tmp_path / "saves"))
    AS._INTERVAL = 0.0
    yield
    AS._INTERVAL = 0.0


def test_default_interval_is_zero_every_action():
    assert AS.get_interval() == 0.0


def test_set_and_get_interval():
    AS.set_interval(30.0)
    assert AS.get_interval() == 30.0


def test_set_interval_none_disables():
    AS.set_interval(None)
    assert AS.get_interval() is None


def test_set_interval_clamps_negative_to_zero():
    AS.set_interval(-5.0)
    assert AS.get_interval() == 0.0


def test_persisted_across_reload(tmp_path):
    AS.set_interval(120.0)
    AS._INTERVAL = 0.0   # simule un module rechargé
    AS._load()
    assert AS.get_interval() == 120.0


def test_preset_label_known_and_unknown_value():
    assert AS.preset_label(0.0) == "À chaque action"
    assert AS.preset_label(None) == "Désactivée"
    assert AS.preset_label(999.0) == "999.0"


# ============================== chokepoint GameState.save() ===================
def _fresh_gs():
    return GameState()


def test_interval_zero_saves_every_time():
    AS.set_interval(0.0)
    gs = _fresh_gs()
    p1 = gs.save(config.AUTOSAVE_SLOT)
    p2 = gs.save(config.AUTOSAVE_SLOT)
    assert p1 is not None
    assert p2 is not None


def test_disabled_never_writes_autosave_slot():
    AS.set_interval(None)
    gs = _fresh_gs()
    assert gs.save(config.AUTOSAVE_SLOT) is None
    assert not os.path.exists(os.path.join(config.SAVE_DIR, f"{config.AUTOSAVE_SLOT}.json"))


def test_disabled_does_not_affect_manual_slots():
    AS.set_interval(None)
    gs = _fresh_gs()
    assert gs.save("manual") is not None


def test_interval_throttles_rapid_successive_autosaves():
    AS.set_interval(120.0)
    gs = _fresh_gs()
    first = gs.save(config.AUTOSAVE_SLOT)
    second = gs.save(config.AUTOSAVE_SLOT)   # immédiatement après : trop tôt
    assert first is not None
    assert second is None


def test_interval_allows_save_once_elapsed():
    AS.set_interval(10.0)
    gs = _fresh_gs()
    assert gs.save(config.AUTOSAVE_SLOT) is not None
    gs.last_saved -= 11.0   # simule 11s écoulées depuis la dernière écriture
    assert gs.save(config.AUTOSAVE_SLOT) is not None


def test_sandbox_mode_still_takes_priority_over_autosave_settings():
    AS.set_interval(0.0)
    gs = _fresh_gs()
    gs.player.sandbox = True
    assert gs.save(config.AUTOSAVE_SLOT) is None
