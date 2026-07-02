"""
hall_of_fame.py — Panthéon local des runs terminés (logique pure).

Chaque fin de partie (game over) enregistre un résumé du run — nom, grade
atteint, voie, durée, patrimoine record, score composite (core/score.py) —
dans `saves/hall_of_fame.json`, PERSISTANT entre parties (comme
core/profile.py, distinct des slots de sauvegarde). L'écran de fin
(scene_gameover) affiche le classement : finir une run laisse une trace et
donne un point de comparaison à la suivante — une raison de relancer.

Classement par score composite décroissant, borné à `MAX_RUNS` entrées.

Les runs joués en « Défi du jour » (core/difficulty.py — marché déterministe
partagé, dérivé de la date) sont marqués (`daily_date`, la date ISO du défi)
et comparables ENTRE EUX via `top_for_daily(date)` — classement à part du
panthéon général, où ils affrontaient un marché différent des autres runs
(comparer un score de défi à un score classique serait trompeur).
"""
import datetime
import json
import os
import uuid

from core import config, difficulty

MAX_RUNS = 10
# stockage à PART pour les runs de défi du jour (fichier séparé, pas mêlé au
# panthéon général) : sans ça, un run de défi excellent parmi les défis mais
# modeste face à des runs classiques serait évincé du top MAX_RUNS général
# et donc invisible de top_for_daily — chaque table a son propre budget.
MAX_DAILY_RUNS = 50

_PATH = None
_DAILY_PATH = None


def _path():
    global _PATH
    if _PATH is None:
        _PATH = os.path.join(config.SAVE_DIR, "hall_of_fame.json")
    return _PATH


def _daily_path():
    global _DAILY_PATH
    if _DAILY_PATH is None:
        _DAILY_PATH = os.path.join(config.SAVE_DIR, "hall_of_fame_daily.json")
    return _DAILY_PATH


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            runs = json.load(f)
        return runs if isinstance(runs, list) else []
    except Exception:
        return []


def _save_json(path, runs):
    try:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(runs, f, ensure_ascii=False)
    except Exception:
        pass    # jamais bloquant (disque en lecture seule, CI…)


def load():
    return _load_json(_path())


def _save(runs):
    _save_json(_path(), runs)


def load_daily():
    return _load_json(_daily_path())


def _save_daily(runs):
    _save_json(_daily_path(), runs)


def make_entry(player, score_total, date=None):
    """Résumé JSON-sérialisable d'un run terminé."""
    d = date or datetime.date.today()
    return {
        "id": uuid.uuid4().hex[:12],
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
        # date ISO du défi du jour affronté, ou None (run classique) — cf.
        # difficulty.is_daily_challenge/mark_daily.
        "daily_date": player.flags.get("daily_challenge")
                      if difficulty.is_daily_challenge(player) else None,
    }


def record(player, score_total, date=None):
    """Enregistre le run et retourne son RANG (1 = meilleur run local), ou
    None s'il ne rentre pas dans le tableau (au-delà de MAX_RUNS). Un run de
    défi du jour est AUSSI enregistré dans la table dédiée (top_for_daily),
    indépendamment de son sort dans le panthéon général. L'id de l'entrée est
    posé sur `player.flags['hof_entry_id']` (pour retrouver son propre rang
    dans le classement du défi via `daily_rank`)."""
    entry = make_entry(player, score_total, date)
    player.flags["hof_entry_id"] = entry["id"]
    runs = load()
    runs.append(entry)
    # tri stable par score décroissant : à score égal, le run le plus ancien
    # garde son rang (le nouveau se classe derrière).
    runs.sort(key=lambda r: -r.get("score", 0.0))
    rank = runs.index(entry) + 1
    _save(runs[:MAX_RUNS])
    if entry["daily_date"]:
        daily = load_daily()
        daily.append(entry)
        daily.sort(key=lambda r: -r.get("score", 0.0))
        _save_daily(daily[:MAX_DAILY_RUNS])
    return rank if rank <= MAX_RUNS else None


def top(n=MAX_RUNS):
    return load()[:n]


def top_for_daily(date, n=5):
    """Classement des runs ayant affronté le défi du jour DE CETTE DATE
    (même marché déterministe) — comparaison équitable, distincte du
    panthéon général qui mélange des marchés différents."""
    iso = date.isoformat() if hasattr(date, "isoformat") else date
    return [r for r in load_daily() if r.get("daily_date") == iso][:n]


def daily_rank(player):
    """Rang du dernier run enregistré (player.flags['hof_entry_id']) dans le
    classement de SON défi du jour, ou None (run non-défi, ou hors du top
    MAX_DAILY_RUNS conservé)."""
    entry_id = player.flags.get("hof_entry_id")
    daily_date = player.flags.get("daily_challenge")
    if not entry_id or not daily_date:
        return None
    ranked = [r for r in load_daily() if r.get("daily_date") == daily_date]
    for i, r in enumerate(ranked, start=1):
        if r.get("id") == entry_id:
            return i
    return None
