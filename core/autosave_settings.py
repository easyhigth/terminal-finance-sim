"""
autosave_settings.py — Cadence de la sauvegarde automatique (accessibilité /
préférence joueur), persistée séparément de `core/i18n.py` (settings.json),
même principe que `core/anim_settings.py`/`core/audio.py`.

Historiquement, la sauvegarde auto se déclenchait à CHAQUE action notable
(achat, deal conclu, mission terminée…) — des dizaines de points d'appel
dans `scenes/*.py`, tous `self.app.gs.save(config.AUTOSAVE_SLOT)`. Plutôt que
de réécrire chacun de ces call sites, le seul chokepoint réel est
`GameState.save()` lui-même (core/game_state.py, déjà utilisé pour le
mode sandbox) : quand le slot cible est le slot auto ET qu'un intervalle est
configuré, `save()` ignore l'appel si la dernière écriture réelle est trop
récente — le comportement "à chaque action" (intervalle 0, historique et
toujours la valeur par défaut) reste inchangé pour qui ne touche pas au
réglage.
"""
import json
import os

from core import config, crashlog

# secondes entre deux écritures RÉELLES du slot auto ; 0 = à chaque action
# (comportement historique) ; None = sauvegarde auto désactivée (seule la
# commande SAVE, manuelle, écrit encore).
PRESETS = [
    (0.0, ("À chaque action", "Every action")),
    (30.0, ("Toutes les 30s", "Every 30s")),
    (120.0, ("Toutes les 2min", "Every 2min")),
    (None, ("Désactivée", "Disabled")),
]

_INTERVAL = 0.0
_PATH = os.path.join(config.SAVE_DIR, "autosave_settings.json")


def _load():
    global _INTERVAL
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        v = d.get("interval_seconds", 0.0)
        _INTERVAL = None if v is None else float(v)
    except Exception:
        _INTERVAL = 0.0


def _save():
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump({"interval_seconds": _INTERVAL}, f)
    except Exception:
        crashlog.swallowed("core.autosave_settings")


def get_interval():
    """None = désactivée ; 0.0 = à chaque action ; sinon secondes entre deux
    écritures réelles du slot auto."""
    return _INTERVAL


def set_interval(seconds):
    global _INTERVAL
    _INTERVAL = None if seconds is None else max(0.0, float(seconds))
    _save()


def preset_label(seconds, lang="fr"):
    for v, (fr, en) in PRESETS:
        if v == seconds:
            return en if lang == "en" else fr
    return str(seconds)


_load()
