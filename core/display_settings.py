"""
display_settings.py — Mode d'affichage de la fenêtre (fenêtré / plein écran /
plein écran fenêtré), persisté entre deux lancements.

Stocké dans `display_settings.json` (sous `config.SAVE_DIR`), à part de
`settings.json` (langue) et `anim_settings.json` (animations), pour garder
chaque préférence indépendante. `core.App.set_window_mode()` consomme ce
réglage ; ce module ne fait que le mémoriser/le restituer.
"""
import json
import os

from core import config

# Modes valides + libellés bilingues (l'UI réglages les affiche).
MODES = ("windowed", "fullscreen", "borderless")
MODE_LABELS = {
    "fr": {"windowed": "Fenêtré",
           "fullscreen": "Plein écran",
           "borderless": "Plein écran fenêtré"},
    "en": {"windowed": "Windowed",
           "fullscreen": "Fullscreen",
           "borderless": "Borderless"},
}

_PATH = os.path.join(config.SAVE_DIR, "display_settings.json")
_MODE = "windowed"


def _load():
    global _MODE
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            m = json.load(f).get("mode", "windowed")
        _MODE = m if m in MODES else "windowed"
    except Exception:
        _MODE = "windowed"


def _save():
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump({"mode": _MODE}, f)
    except Exception:
        pass


def get_mode():
    return _MODE


def set_mode(mode):
    global _MODE
    _MODE = mode if mode in MODES else "windowed"
    _save()
    return _MODE


def next_mode():
    """Mode suivant dans le cycle (pour un raccourci de bascule rapide)."""
    i = MODES.index(_MODE) if _MODE in MODES else 0
    return set_mode(MODES[(i + 1) % len(MODES)])


def label(mode=None, lang="fr"):
    mode = mode or _MODE
    return MODE_LABELS.get(lang, MODE_LABELS["fr"]).get(mode, mode)


_load()
