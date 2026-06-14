"""
deals.py — Génération et cycle de vie des deals (logique pure, sans pygame).

Un deal est une opportunité limitée dans le temps. Le joueur peut le traiter
(resolve_deal) avant son échéance : la réussite dépend de sa réputation et de
la difficulté du deal. Un deal non traité à temps expire et inflige une
pénalité (réputation surtout).

Structure d'un deal (dict) :
  id          : identifiant entier unique (PlayerState.next_deal_id)
  title       : intitulé
  kind        : voie concernée ("M&A", "Portfolio", "Risk", "Quant", "Advisory", "General")
  desc        : description courte
  reward_cash : gain de trésorerie en cas de réussite
  reward_rep  : gain de réputation en cas de réussite
  penalty_cash: perte si échec ou expiration
  penalty_rep : perte de réputation si échec ou expiration
  difficulty  : 1..5
  days_left   : jours restants avant échéance
"""
import random
from core import config
from core import tracks


MAX_ACTIVE_DEALS = 4        # au-delà, plus de génération
GEN_PROBABILITY = 0.45      # proba de générer un deal à un tour donné
MISS_PENALTY_FRAC = 0.05    # un deal manqué coûte surtout de la réputation,
                            # et seulement une petite fraction du gain en cash


# Modèles de deals par voie. Les montants seront mis à l'échelle du grade.
DEAL_TEMPLATES = [
    {"kind": "M&A", "title": "Acquisition mid-cap",
     "desc": "Structurer le rachat d'une cible industrielle pour un client.",
     "base_cash": 120_000, "rep": 7, "difficulty": 4, "days": 25},
    {"kind": "M&A", "title": "Cession de division",
     "desc": "Piloter la cession d'une division non stratégique.",
     "base_cash": 90_000, "rep": 5, "difficulty": 3, "days": 20},

    {"kind": "Portfolio", "title": "Mandat d'allocation institutionnel",
     "desc": "Construire une allocation moyenne-variance pour un fonds de pension.",
     "base_cash": 70_000, "rep": 6, "difficulty": 3, "days": 20},
    {"kind": "Portfolio", "title": "Rebalancement sous contrainte",
     "desc": "Rééquilibrer un portefeuille en limitant le tracking error.",
     "base_cash": 45_000, "rep": 4, "difficulty": 2, "days": 15},

    {"kind": "Risk", "title": "Revue de limites de VaR",
     "desc": "Recalibrer les limites de risque avant l'audit prudentiel.",
     "base_cash": 55_000, "rep": 6, "difficulty": 4, "days": 18},
    {"kind": "Risk", "title": "Stress test réglementaire",
     "desc": "Mener un stress test sur le book avant reporting.",
     "base_cash": 50_000, "rep": 5, "difficulty": 3, "days": 20},

    {"kind": "Quant", "title": "Pricing d'un exotique",
     "desc": "Calibrer un modèle pour valoriser une option à barrière.",
     "base_cash": 80_000, "rep": 6, "difficulty": 5, "days": 16},
    {"kind": "Quant", "title": "Backtest d'une stratégie",
     "desc": "Valider une stratégie systématique avant mise en production.",
     "base_cash": 60_000, "rep": 5, "difficulty": 4, "days": 22},

    {"kind": "Advisory", "title": "Pitch de financement",
     "desc": "Préparer un pitch de financement pour un client corporate.",
     "base_cash": 65_000, "rep": 6, "difficulty": 3, "days": 18},

    {"kind": "General", "title": "Note de marché urgente",
     "desc": "Produire une note de conjoncture pour le comité d'investissement.",
     "base_cash": 30_000, "rep": 4, "difficulty": 2, "days": 12},
    {"kind": "General", "title": "Présentation au comité",
     "desc": "Défendre une recommandation devant le comité d'investissement.",
     "base_cash": 40_000, "rep": 5, "difficulty": 3, "days": 14},
]


def _scale(player):
    """Facteur d'échelle des montants selon le grade."""
    return 1.0 + 0.7 * player.grade_index


def _eligible_templates(player):
    """Deals proposés : ceux de la voie du joueur + les 'General'."""
    track = player.track
    out = []
    for t in DEAL_TEMPLATES:
        if t["kind"] == "General" or t["kind"] == track:
            out.append(t)
    # avant de choisir une voie, on ne propose que du General + un peu de tout
    if track in ("General", "", None):
        out = DEAL_TEMPLATES
    return out


def maybe_generate(player, rng=None):
    """Génère éventuellement un nouveau deal. Retourne la liste des deals créés."""
    rng = rng or random
    if len(player.deals) >= MAX_ACTIVE_DEALS:
        return []
    if rng.random() > GEN_PROBABILITY:
        return []
    t = rng.choice(_eligible_templates(player))
    scale = _scale(player)
    # bonus de récompense si le deal relève de la voie du joueur (M&A surtout)
    track_mult = tracks.perk(player, "deal_reward_mult") if t["kind"] == player.track else 1.0
    reward_cash = round(t["base_cash"] * scale * track_mult * rng.uniform(0.85, 1.25), 2)
    deal = {
        "id": player.next_deal_id,
        "title": t["title"],
        "kind": t["kind"],
        "desc": t["desc"],
        "reward_cash": reward_cash,
        "reward_rep": t["rep"],
        "penalty_cash": round(reward_cash * MISS_PENALTY_FRAC, 2),
        "penalty_rep": max(1, t["difficulty"] - 1),
        "difficulty": t["difficulty"],
        "days_left": t["days"],
    }
    player.next_deal_id += 1
    player.deals.append(deal)
    return [deal]


def age_deals(player):
    """
    Fait vieillir les deals d'un tour. Les deals échus non traités sont retirés
    et infligent leur pénalité. Retourne la liste des deals expirés.
    """
    expired = []
    still_active = []
    for d in player.deals:
        d["days_left"] -= config.DAYS_PER_STEP
        if d["days_left"] <= 0:
            player.adjust_cash(-d["penalty_cash"])
            player.adjust_reputation(-d["penalty_rep"])
            expired.append(d)
        else:
            still_active.append(d)
    player.deals = still_active
    return expired


def find_deal(player, deal_id):
    for d in player.deals:
        if d["id"] == deal_id:
            return d
    return None


def success_probability(player, deal):
    """
    Probabilité de réussite d'un deal : base liée à la réputation, pénalisée
    par la difficulté, bornée dans [0.10, 0.95].
    """
    rep_factor = player.reputation / 100.0          # 0..1
    edge, relief = tracks.deal_edge(player, deal)    # bonus si deal de sa voie
    diff_penalty = max(0.0, (deal["difficulty"] - 1) * 0.12 - relief)
    p = 0.45 + 0.5 * rep_factor - diff_penalty + edge
    return max(0.10, min(0.95, p))


def apply_outcome(player, deal_id, quality):
    """Applique le résultat d'un mini-jeu de deal selon la QUALITÉ du choix :
      good → succès plein · ok → succès partiel · bad → échec.
    Retourne un dict résultat, ou {ok: False} si le deal n'existe pas."""
    deal = find_deal(player, deal_id)
    if deal is None:
        return {"ok": False}
    if quality == "good":
        player.adjust_cash(deal["reward_cash"])
        player.adjust_reputation(deal["reward_rep"])
        player.deals_won += 1
        player.grade_deals += 1
        outcome = "success"
    elif quality == "ok":
        player.adjust_cash(round(deal["reward_cash"] * 0.5, 2))
        player.adjust_reputation(max(1, deal["reward_rep"] // 2))
        player.deals_won += 1
        player.grade_deals += 1
        outcome = "partial"
    else:  # bad
        player.adjust_cash(-deal["penalty_cash"])
        player.adjust_reputation(-deal["penalty_rep"])
        outcome = "fail"
    player.deals = [d for d in player.deals if d["id"] != deal_id]
    return {"ok": True, "outcome": outcome, "deal": deal, "quality": quality}


def resolve_deal(player, deal_id, rng=None):
    """
    Tente de conclure un deal. Retourne un dict résultat :
      {ok: bool, success: bool, deal: ..., prob: float}
    ok=False si le deal n'existe pas.
    """
    rng = rng or random
    deal = find_deal(player, deal_id)
    if deal is None:
        return {"ok": False, "success": False, "deal": None, "prob": 0.0}
    prob = success_probability(player, deal)
    success = rng.random() < prob
    if success:
        player.adjust_cash(deal["reward_cash"])
        player.adjust_reputation(deal["reward_rep"])
        player.deals_won += 1
        player.grade_deals += 1
    else:
        player.adjust_cash(-deal["penalty_cash"])
        player.adjust_reputation(-deal["penalty_rep"])
    player.deals = [d for d in player.deals if d["id"] != deal_id]
    return {"ok": True, "success": success, "deal": deal, "prob": prob}
