"""Tests des nouveaux effets sonores (core/audio.py) — vérifie juste que les
specs existent et que play() reste no-op-safe headless (SDL_AUDIODRIVER=dummy),
sans dépendre d'un vrai mixer."""
from core import audio


def test_new_sound_specs_registered():
    for name in ("promotion", "badge", "dilemma"):
        assert name in audio._SPECS
        spec = audio._SPECS[name]
        assert spec
        for freq, dur, gain in spec:
            assert freq > 0 and dur > 0 and 0.0 <= gain <= 1.0


def test_play_new_sounds_never_raises_headless():
    for name in ("promotion", "badge", "dilemma"):
        audio.play(name)   # doit rester silencieux et ne jamais lever


def test_play_unknown_sound_is_noop():
    audio.play("does_not_exist")
