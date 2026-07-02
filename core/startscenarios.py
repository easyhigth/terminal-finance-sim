"""
startscenarios.py — Scénarios de départ (variantes de run).

Chaque scénario fixe les conditions initiales d'une carrière : capital, grade de
départ, réputation, et un éventuel choc de marché injecté au lancement. Ils
donnent de la variété de difficulté et de « montants » sans toucher aux formules
de carrière (salaires/coûts/deals), qui restent l'ossature commune.

apply(player) règle l'état persistant ; le choc de marché des scénarios « crise »
est posé une seule fois par le terminal (flag start_crisis).
"""
from core import config

SCENARIOS = [
    {"id": "standard", "name": "Carrière standard",
     "desc": "Capital de départ normal, marché calme. L'expérience de référence.",
     "cash": config.START_CASH, "grade_index": 0, "reputation": 50, "crisis": False},
    {"id": "small_firm", "name": "Petite firme",
     "desc": "Peu de capital, marge d'erreur réduite : chaque décision compte.",
     "cash": 120_000.0, "grade_index": 0, "reputation": 45, "crisis": False},
    {"id": "crisis", "name": "Krach en cours",
     "desc": "Vous démarrez en pleine tempête : le marché s'effondre dès les "
             "premiers tours. Survivre est l'objectif.",
     "cash": 300_000.0, "grade_index": 0, "reputation": 50, "crisis": True},
    {"id": "veteran", "name": "Recrue expérimentée",
     "desc": "Vous arrivez déjà Analyst, avec plus de capital — mais les attentes "
             "sont plus hautes.",
     "cash": 500_000.0, "grade_index": 2, "reputation": 60, "crisis": False},
    {"id": "hardcore_boot", "name": "Tout ou rien",
     "desc": "Capital confortable mais réputation fragile : une erreur d'éthique "
             "et c'est fini.",
     "cash": 400_000.0, "grade_index": 0, "reputation": 30, "crisis": False},
    {"id": "veteran_rush", "name": "Vétéran pressé",
     "desc": "Promu Senior VP en accéléré, capital solide — mais réputation encore "
             "fragile pour le rang. Pas de lune de miel : mandats, deals et M&A "
             "vous attendent dès le premier jour, sans marge d'apprentissage.",
     "cash": 2_000_000.0, "grade_index": 7, "reputation": 55, "crisis": False},
]
_BY_ID = {s["id"]: s for s in SCENARIOS}


def get(scenario_id):
    return _BY_ID.get(scenario_id, SCENARIOS[0])


def apply(player, scenario_id):
    """Applique les conditions initiales d'un scénario à un PlayerState neuf."""
    sc = get(scenario_id)
    player.cash = sc["cash"]
    player.grade_index = sc["grade_index"]
    player.reputation = sc["reputation"]
    player.cash_history = [sc["cash"]]
    player.flags["start_scenario"] = sc["id"]
    if sc["grade_index"] >= 2 and player.track == "General":
        player.flags["can_choose_track"] = True
    if sc["crisis"]:
        player.flags["start_crisis"] = True
    return sc
