"""
display_settings.py — Mode d'affichage de la fenêtre (fenêtré / plein écran /
plein écran fenêtré) + résolution, persisté entre deux lancements.

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
_RESOLUTION = config.DEFAULT_RESOLUTION


def _load():
    global _MODE, _RESOLUTION
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        m = data.get("mode", "windowed")
        _MODE = m if m in MODES else "windowed"
        r = data.get("resolution", config.DEFAULT_RESOLUTION)
        _RESOLUTION = r if r in config.RESOLUTION_PRESETS else config.DEFAULT_RESOLUTION
    except Exception:
        _MODE = "windowed"
        _RESOLUTION = config.DEFAULT_RESOLUTION


def _save():
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump({"mode": _MODE, "resolution": _RESOLUTION}, f)
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


def get_resolution():
    return _RESOLUTION


def set_resolution(res_key):
    """Change la résolution. Nécessite un redémarrage de la fenêtre (appelé
    par main.py qui recrée l'affichage). Retourne la clé effective."""
    global _RESOLUTION
    if res_key in config.RESOLUTION_PRESETS:
        _RESOLUTION = res_key
    else:
        _RESOLUTION = config.DEFAULT_RESOLUTION
    _save()
    return _RESOLUTION


def apply_resolution():
    """Applique la résolution choisie aux constantes de config.
    À appeler AVANT pygame.display.set_mode()."""
    preset = config.RESOLUTION_PRESETS.get(_RESOLUTION, config.RESOLUTION_PRESETS[config.DEFAULT_RESOLUTION])
    config.SCREEN_WIDTH = preset["w"]
    config.SCREEN_HEIGHT = preset["h"]
    config.WINDOW_HEIGHT = config.SCREEN_HEIGHT + config.TAB_BAR_H


def resolution_label(res_key=None, lang="fr"):
    """Libellé lisible de la résolution pour l'UI."""
    key = res_key or _RESOLUTION
    preset = config.RESOLUTION_PRESETS.get(key, config.RESOLUTION_PRESETS[config.DEFAULT_RESOLUTION])
    lbl = preset["label"]
    return lbl[1] if lang == "en" else lbl[0]


_load()
