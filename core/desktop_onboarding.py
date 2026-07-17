"""
desktop_onboarding.py — Mémorise si le joueur a déjà vu la carte d'accueil du
BUREAU (refonte UI « Jeu PC »).

Distinct de `core/onboarding.py` (le parcours guidé du TERMINAL, étapes de
carrière) : ici on ne mémorise qu'un booléen « la carte d'accueil du bureau
a-t-elle été montrée ? », persisté séparément (fichier JSON dédié sous
`config.SAVE_DIR`, comme `core/anim_settings.py`) — c'est une préférence
d'interface, pas un état de partie. `scenes/scene_desktop.py` affiche la carte
tant que `seen()` est faux, et appelle `mark_seen()` au premier passage.
"""
import json
import os

from core import config, crashlog

_SEEN = False
_PATH = os.path.join(config.SAVE_DIR, "desktop_onboarding.json")


def _load():
    global _SEEN
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            _SEEN = bool(json.load(f).get("desktop_seen", False))
    except Exception:
        _SEEN = False


def _save():
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump({"desktop_seen": _SEEN}, f)
    except Exception:
        crashlog.swallowed("core.desktop_onboarding")


def seen():
    return _SEEN


def mark_seen():
    global _SEEN
    if not _SEEN:
        _SEEN = True
        _save()


def reset():
    """Réaffiche la carte d'accueil (tests / option « revoir l'intro »)."""
    global _SEEN
    _SEEN = False
    _save()


_load()
