"""
anim_settings.py — Préférence "réduire les animations" (accessibilité / perf).

Persistée séparément de `core/i18n.py` (settings.json) pour ne pas toucher à
ce module existant. Quand activé, `core/intraday.py::wiggle()` retombe sur
l'interpolation linéaire pure (aucun bruit) : les graphes restent corrects,
juste immobiles entre deux pas de marché.
"""
import json
import os

from core import config, crashlog

_REDUCE_MOTION = False
_PATH = os.path.join(config.SAVE_DIR, "anim_settings.json")


def _load():
    global _REDUCE_MOTION
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            _REDUCE_MOTION = bool(json.load(f).get("reduce_motion", False))
    except Exception:
        _REDUCE_MOTION = False


def _save():
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump({"reduce_motion": _REDUCE_MOTION}, f)
    except Exception:
        crashlog.swallowed("core.anim_settings")


def reduce_motion():
    return _REDUCE_MOTION


def set_reduce_motion(v):
    global _REDUCE_MOTION
    _REDUCE_MOTION = bool(v)
    _save()


def toggle_reduce_motion():
    set_reduce_motion(not _REDUCE_MOTION)
    return _REDUCE_MOTION


_load()
