"""
audio.py — Effets sonores synthétisés + réglages son (volume maître / mute).

Le jeu n'embarque aucun fichier audio : les sons sont générés à la volée
(petites enveloppes sinusoïdales via numpy) puis joués par `pygame.mixer`.
Tout est **robuste au mode headless** (CI, `SDL_AUDIODRIVER=dummy`, absence de
carte son) : si le mixer ne peut pas s'initialiser, le module bascule en
no-op silencieux — aucune exception ne remonte jamais aux scènes.

Réglages persistés séparément (`audio_settings.json` sous `config.SAVE_DIR`),
à l'image de `core/anim_settings.py`, pour ne pas toucher `settings.json`
(langue) : `muted` (bool) et `volume` (0.0..1.0).

API :
    audio.play("order")          # joue un effet nommé (no-op si muet/indispo)
    audio.set_volume(0.6); audio.get_volume()
    audio.toggle_mute(); audio.is_muted()
"""
import json
import os

from core import config

_PATH = os.path.join(config.SAVE_DIR, "audio_settings.json")

_MUTED = False
_VOLUME = 0.6          # volume maître par défaut (0.0..1.0)

_AVAILABLE = False     # True si le mixer s'est initialisé
_SOUNDS = {}           # nom -> pygame.mixer.Sound (construits paresseusement)
_INIT_TRIED = False

# Spécification de chaque effet : liste de (fréquence Hz, durée s, gain relatif).
# Des accords/séquences très courts, façon « bips » de terminal financier.
_SPECS = {
    "tick_up":   [(880.0, 0.05, 0.5)],
    "tick_down": [(440.0, 0.05, 0.5)],
    "order":     [(660.0, 0.06, 0.6), (990.0, 0.08, 0.6)],
    "alert":     [(740.0, 0.10, 0.7), (740.0, 0.10, 0.0), (740.0, 0.10, 0.7)],
    "bell":      [(1046.5, 0.18, 0.7), (1318.5, 0.22, 0.6)],
    "error":     [(330.0, 0.12, 0.6), (247.0, 0.16, 0.6)],
    # arpège ascendant (do-mi-sol) façon fanfare courte : promotion de grade.
    "promotion": [(523.25, 0.08, 0.6), (659.25, 0.08, 0.65), (783.99, 0.16, 0.75)],
    # étincelle brève et aiguë : déblocage d'un badge/succès.
    "badge":     [(1046.5, 0.05, 0.5), (1568.0, 0.10, 0.65)],
    # ping-pong neutre à deux tons, distinct de "alert" (répétition d'un
    # même ton, plus pressant) — une décision attend, sans connotation
    # positive/négative.
    "dilemma":   [(600.0, 0.08, 0.6), (500.0, 0.08, 0.6)],
    # clic sec bref, aigu puis grave : fenêtre ancrée/maximisée (feedback de
    # docking, cf. ui/window_manager.py) — distinct de "order" (deux tons
    # montants, plus long) pour rester discret sur une action très fréquente.
    "snap":      [(880.0, 0.04, 0.45), (523.25, 0.05, 0.4)],
    # sirène grave descendante : crise de marché qui se déclenche
    "crisis":    [(440.0, 0.15, 0.7), (330.0, 0.20, 0.7), (220.0, 0.30, 0.6)],
    # ping aigu montant : deal gagné / clôturé avec succès
    "deal_won":  [(523.25, 0.06, 0.5), (659.25, 0.06, 0.55), (783.99, 0.12, 0.6)],
    # deux tons descendants : deal perdu / expiré
    "deal_lost": [(523.25, 0.08, 0.5), (392.0, 0.12, 0.5)],
    # ping discret : réception d'un message inbox
    "message":   [(1046.5, 0.04, 0.35), (1318.5, 0.06, 0.4)],
    # clic très bref : feedback des boutons (optionnel, très discret)
    "click":     [(1200.0, 0.02, 0.25)],
    # fanfare courte : succès majeur / achievement
    "achievement": [(523.25, 0.06, 0.5), (659.25, 0.06, 0.55), (783.99, 0.08, 0.6),
                    (1046.5, 0.12, 0.7)],
    # alarme : margin call
    "margin_call": [(880.0, 0.08, 0.7), (660.0, 0.08, 0.7), (880.0, 0.08, 0.7)],
}


def _load():
    global _MUTED, _VOLUME
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        _MUTED = bool(d.get("muted", False))
        _VOLUME = min(1.0, max(0.0, float(d.get("volume", 0.6))))
    except Exception:
        _MUTED, _VOLUME = False, 0.6


def _save():
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump({"muted": _MUTED, "volume": _VOLUME}, f)
    except Exception:
        pass


def _ensure_mixer():
    """Initialise le mixer une seule fois ; tolère l'échec (headless)."""
    global _AVAILABLE, _INIT_TRIED
    if _INIT_TRIED:
        return _AVAILABLE
    _INIT_TRIED = True
    try:
        import pygame
        if pygame.mixer.get_init() is None:
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
        _AVAILABLE = pygame.mixer.get_init() is not None
    except Exception:
        _AVAILABLE = False
    return _AVAILABLE


def _build_sound(name):
    """Construit (et met en cache) le Sound d'un effet via numpy. Renvoie None
    si numpy/mixer indisponible."""
    if name in _SOUNDS:
        return _SOUNDS[name]
    spec = _SPECS.get(name)
    if spec is None or not _ensure_mixer():
        return None
    try:
        import numpy as np
        import pygame
        rate = 44100
        chunks = []
        for freq, dur, gain in spec:
            n = max(1, int(rate * dur))
            t = np.linspace(0.0, dur, n, endpoint=False)
            wave = np.sin(2.0 * np.pi * freq * t) * gain
            # enveloppe attaque/déclin pour éviter les clics
            env = np.minimum(np.linspace(0, 1, n) * 8.0,
                             np.linspace(1, 0, n) * 8.0)
            env = np.clip(env, 0.0, 1.0)
            chunks.append(wave * env)
        mono = np.concatenate(chunks)
        audio = np.int16(np.clip(mono, -1.0, 1.0) * 32767 * 0.6)
        stereo = np.ascontiguousarray(np.column_stack([audio, audio]))
        snd = pygame.sndarray.make_sound(stereo)
        _SOUNDS[name] = snd
        return snd
    except Exception:
        _SOUNDS[name] = None
        return None


# ----------------------------------------------------------------- API publique
def is_muted():
    return _MUTED


def get_volume():
    return _VOLUME


def set_volume(v):
    global _VOLUME
    _VOLUME = min(1.0, max(0.0, float(v)))
    _save()


def set_muted(v):
    global _MUTED
    _MUTED = bool(v)
    _save()


def toggle_mute():
    set_muted(not _MUTED)
    return _MUTED


def play(name):
    """Joue l'effet `name` (no-op si muet, volume nul, ou mixer indisponible)."""
    if _MUTED or _VOLUME <= 0.0:
        return
    snd = _build_sound(name)
    if snd is None:
        return
    try:
        snd.set_volume(_VOLUME)
        snd.play()
    except Exception:
        pass


_load()
