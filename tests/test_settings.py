"""
tests/test_settings.py — Réglages : modes d'affichage (core/display_settings)
et son (core/audio). Logique pure + robustesse headless ; ne vérifie pas le
rendu (couvert par test_scene_smoke pour la scène "settings").
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from core import audio, display_settings


def test_display_modes_cycle_and_persist():
    display_settings.set_mode("windowed")
    assert display_settings.get_mode() == "windowed"
    # next_mode parcourt les 3 modes en boucle
    seen = {display_settings.next_mode() for _ in range(3)}
    assert seen == set(display_settings.MODES)
    # un mode inconnu retombe sur "windowed"
    assert display_settings.set_mode("bogus") == "windowed"


def test_display_labels_bilingual():
    assert display_settings.label("fullscreen", "fr") == "Plein écran"
    assert display_settings.label("fullscreen", "en") == "Fullscreen"


def test_audio_volume_clamped_and_toggle():
    audio.set_volume(0.5)
    assert audio.get_volume() == 0.5
    audio.set_volume(5.0)            # borné à 1.0
    assert audio.get_volume() == 1.0
    audio.set_volume(-1.0)           # borné à 0.0
    assert audio.get_volume() == 0.0
    audio.set_muted(False)
    assert audio.toggle_mute() is True
    assert audio.toggle_mute() is False


def test_audio_play_is_noop_when_muted_or_headless():
    # ne doit jamais lever, même sans carte son (driver dummy) ou en sourdine
    audio.set_muted(True)
    audio.play("order")
    audio.set_muted(False)
    audio.set_volume(0.6)
    audio.play("order")
    audio.play("inexistant")         # effet inconnu : ignoré silencieusement
