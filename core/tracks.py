"""
tracks.py — Asymétrie des voies de spécialisation (logique pure, sans pygame).

Chaque voie donne un EDGE mécanique distinct, pour que jouer Portfolio, M&A,
Risk, Quant ou Advisory ne change pas seulement les questions d'examen mais le
STYLE DE JEU. Les autres modules lisent ces perks (commission, marge/levier,
deals, mandats) au lieu de coder en dur des constantes.

Clés de perk (toutes optionnelles ; valeur par défaut = neutre) :
  commission_mult     : multiplie la commission de trading        (def 1.0)
  deal_reward_mult    : multiplie le gain cash des deals générés   (def 1.0)
  deal_bonus          : bonus de proba de réussite sur les deals DE SA VOIE (def 0.10)
  diff_relief         : réduit la pénalité de difficulté des deals de sa voie (def 0.0)
  max_leverage_add    : levier maximal supplémentaire              (def 0.0)
  margin_spread_mult  : multiplie le surcoût d'emprunt sur marge   (def 1.0)
  maint_margin        : marge de maintenance (appel de marge)      (def None -> défaut portfolio)
  mandate_offer_mult  : multiplie la proba d'offre de mandat       (def 1.0)
  mandate_reward_mult : multiplie la récompense des mandats        (def 1.0)
"""

PERKS = {
    "Portfolio": {
        "commission_mult": 0.5, "deal_bonus": 0.10,
        "label": "Gestion active : commissions de trading réduites de moitié.",
    },
    "M&A": {
        "deal_reward_mult": 1.3, "deal_bonus": 0.12,
        "label": "Dealmaker : deals nettement plus rémunérateurs.",
    },
    "Risk": {
        "max_leverage_add": 0.5, "margin_spread_mult": 0.5, "maint_margin": 0.20,
        "deal_bonus": 0.10,
        "label": "Gestion du risque : levier accru, marge moins chère, appels de marge plus cléments.",
    },
    "Quant": {
        "deal_bonus": 0.18, "diff_relief": 0.06,
        "label": "Quant : fort avantage sur les deals techniques de sa voie.",
    },
    "Advisory": {
        "mandate_offer_mult": 1.7, "mandate_reward_mult": 1.3, "deal_bonus": 0.10,
        "label": "Conseil : davantage de mandats clients, mieux rémunérés.",
    },
    "General": {"label": "Aucune spécialisation : choisissez une voie (TRACK)."},
}

_DEFAULTS = {
    "commission_mult": 1.0, "deal_reward_mult": 1.0, "deal_bonus": 0.10,
    "diff_relief": 0.0, "max_leverage_add": 0.0, "margin_spread_mult": 1.0,
    "maint_margin": None, "mandate_offer_mult": 1.0, "mandate_reward_mult": 1.0,
}


def perk(player, key):
    """Valeur du perk `key` pour la voie du joueur (ou défaut neutre)."""
    track = getattr(player, "track", "General")
    return PERKS.get(track, {}).get(key, _DEFAULTS.get(key))


def deal_edge(player, deal):
    """Bonus de proba de réussite (+ allègement de difficulté) si le deal
    relève de la voie du joueur. Retourne (bonus_prob, diff_relief)."""
    if deal.get("kind") and deal["kind"] == getattr(player, "track", None):
        return perk(player, "deal_bonus"), perk(player, "diff_relief")
    return 0.0, 0.0


def label(track):
    return PERKS.get(track, {}).get("label", "")
