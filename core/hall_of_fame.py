"""
hall_of_fame.py — Panthéon local des runs terminés (logique pure).

Chaque fin de partie (game over) enregistre un résumé du run — nom, grade
atteint, voie, durée, patrimoine record, score composite (core/score.py) —
dans `saves/hall_of_fame.json`, PERSISTANT entre parties (comme
core/profile.py, distinct des slots de sauvegarde). L'écran de fin
(scene_gameover) affiche le classement : finir une run laisse une trace et
donne un point de comparaison à la suivante — une raison de relancer.

Classement par score composite décroissant, borné à `MAX_RUNS` entrées.
"""
import datetime
import json
import os

from core import config

MAX_RUNS = 10

_PATH = None


def _path():
    global _PATH
    if _PATH is None:
        _PATH = os.path.join(config.SAVE_DIR, "hall_of_fame.json")
    return _PATH


def load():
    try:
        with open(_path(), "r", encoding="utf-8") as f:
            runs = json.load(f)
        return runs if isinstance(runs, list) else []
    except Exception:
        return []


def _save(runs):
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(_path(), "w", encoding="utf-8") as f:
            json.dump(runs, f, ensure_ascii=False)
    except Exception:
        pass    # jamais bloquant (disque en lecture seule, CI…)


def make_entry(player, score_total, date=None):
    """Résumé JSON-sérialisable d'un run terminé."""
    d = date or datetime.date.today()
    return {
        "name": player.name,
        "grade": player.grade,
        "track": player.track,
        "continent": player.continent,
        "quarters": player.quarter,
        "days": player.day,
        "best_nw": round(max(player.best_cash, player.cash), 2),
        "score": round(float(score_total), 1),
        "hardcore": bool(player.hardcore),
        "date": d.isoformat(),
    }


def record(player, score_total, date=None):
    """Enregistre le run et retourne son RANG (1 = meilleur run local), ou
    None s'il ne rentre pas dans le tableau (au-delà de MAX_RUNS)."""
    entry = make_entry(player, score_total, date)
    runs = load()
    runs.append(entry)
    # tri stable par score décroissant : à score égal, le run le plus ancien
    # garde son rang (le nouveau se classe derrière).
    runs.sort(key=lambda r: -r.get("score", 0.0))
    rank = runs.index(entry) + 1
    _save(runs[:MAX_RUNS])
    return rank if rank <= MAX_RUNS else None


def top(n=MAX_RUNS):
    return load()[:n]
