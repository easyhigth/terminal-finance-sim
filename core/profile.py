"""
profile.py — Profil joueur PERSISTANT entre parties (hors sauvegardes de partie).

Trace la meilleure progression jamais atteinte (toutes parties confondues) dans
saves/profile.json, séparé des slots de sauvegarde. Sert à moduler l'asymétrie
novice/expert (cf. CLAUDE.md, brief stratégique point 4) : un joueur qui a déjà
prouvé sa maîtrise (grade élevé atteint au moins une fois) démarre ses parties
suivantes en « vétéran » — complexité ouverte plus vite, onboarding écourté —
alors qu'un nouveau joueur reste guidé pas à pas.
"""
import json
import os

from core import config
from core.applog import logger

VETERAN_GRADE = 4   # grade déjà atteint une fois -> les parties suivantes démarrent "vétéran"

_PATH = None


def _path():
    global _PATH
    if _PATH is None:
        _PATH = os.path.join(config.SAVE_DIR, "profile.json")
    return _PATH


def load():
    try:
        with open(_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"best_grade_reached": 0}
    except (OSError, ValueError) as exc:
        logger.warning("profile.json illisible (%s), profil réinitialisé", exc)
        return {"best_grade_reached": 0}


def record_grade_reached(grade_index):
    """Met à jour la meilleure progression jamais atteinte par ce profil."""
    data = load()
    if grade_index > data.get("best_grade_reached", 0):
        data["best_grade_reached"] = grade_index
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_path(), "w", encoding="utf-8") as f:
            json.dump(data, f)


def is_veteran():
    """Vrai si ce profil a déjà prouvé sa maîtrise (grade élevé) dans une partie antérieure."""
    return load().get("best_grade_reached", 0) >= VETERAN_GRADE


# ---------------------------------------------------------------------------
# DÉCOUVERTE DES APPS DU BUREAU
# ---------------------------------------------------------------------------
# Le bureau approche les 40 apps : sans mesure, impossible de savoir
# lesquelles ne sont JAMAIS découvertes par les joueurs. On note ici (par
# machine, toutes parties confondues) chaque clé d'app/fenêtre ouverte au
# moins une fois — chokepoint : DesktopScene._launch/_open_scene_window.
# Best-effort : ne doit jamais gêner l'ouverture d'une fenêtre.

def record_app_opened(key):
    """Marque l'app `key` comme découverte (ouverte au moins une fois sur
    cette machine). N'écrit sur disque que la PREMIÈRE fois pour chaque clé."""
    if not key:
        return
    try:
        data = load()
        opened = data.get("apps_opened", [])
        if key in opened:
            return
        opened.append(key)
        data["apps_opened"] = opened
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_path(), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        from core import crashlog
        crashlog.swallowed("profile.record_app_opened")


def apps_opened():
    """Ensemble des clés d'apps déjà ouvertes au moins une fois."""
    return set(load().get("apps_opened", []))


def apps_never_opened(all_keys):
    """Clés de `all_keys` jamais découvertes sur cette machine — pour repérer
    les apps que personne ne trouve (diagnostic de découvrabilité)."""
    return sorted(set(all_keys) - apps_opened())
