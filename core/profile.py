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
