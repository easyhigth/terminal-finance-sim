"""
tracks.py — Asymétrie des voies de spécialisation (logique pure, sans pygame).

Chaque voie donne un EDGE mécanique distinct, pour que jouer Portfolio, M&A,
Risk, Quant ou Advisory ne change pas seulement les questions d'examen mais le
STYLE DE JEU. Les autres modules lisent ces perks (commission, marge/levier,
deals, mandats) au lieu de coder en dur des constantes.

Clés de perk (toutes optionnelles ; valeur par défaut = neutre) :
  commission_mult       : multiplie la commission de trading        (def 1.0)
  deal_reward_mult      : multiplie le gain cash des deals générés   (def 1.0)
  deal_bonus            : bonus de proba de réussite sur les deals DE SA VOIE (def 0.10)
  diff_relief           : réduit la pénalité de difficulté des deals de sa voie (def 0.0)
  max_leverage_add      : levier maximal supplémentaire              (def 0.0)
  margin_spread_mult    : multiplie le surcoût d'emprunt sur marge   (def 1.0)
  maint_margin          : marge de maintenance (appel de marge)      (def None -> défaut portfolio)
  mandate_offer_mult    : multiplie la proba d'offre de mandat       (def 1.0)
  mandate_reward_mult   : multiplie la récompense des mandats        (def 1.0)
  deal_gen_prob_mult    : multiplie la fréquence d'apparition des deals (def 1.0) —
                          RYTHME : M&A en voit moins souvent mais plus gros ;
                          Quant en voit plus souvent mais plus vite résolus.
  deal_days_mult        : multiplie le délai de traitement des deals DE SA VOIE
                          (def 1.0) — TENSION : un délai court force des décisions
                          rapides (Quant), un délai long laisse mûrir un gros coup (M&A).
  stresstest_period_mult: multiplie la période entre deux stress tests réglementaires
                          (def 1.0) — Risk est audité deux fois plus souvent : la
                          tension de la voie est un contrôle permanent, pas un pic isolé.
"""

PERKS = {
    "Portfolio": {
        "commission_mult": 0.5, "deal_bonus": 0.10,
        "label": "Gestion active : commissions de trading réduites de moitié. "
                 "Rythme régulier, sans à-coups particuliers.",
    },
    "M&A": {
        "deal_reward_mult": 1.3, "deal_bonus": 0.12,
        "deal_gen_prob_mult": 0.65, "deal_days_mult": 1.5,
        "label": "Dealmaker : deals rares mais nettement plus rémunérateurs, et "
                 "plus de temps pour les mener — peu de décisions, mais énormes.",
    },
    "Risk": {
        "max_leverage_add": 0.5, "margin_spread_mult": 0.5, "maint_margin": 0.20,
        "deal_bonus": 0.10, "stresstest_period_mult": 0.5,
        "label": "Gestion du risque : levier accru, marge moins chère, appels de "
                 "marge plus cléments — mais stress tests réglementaires deux fois "
                 "plus fréquents : sous contrôle permanent.",
    },
    "Quant": {
        "deal_bonus": 0.18, "diff_relief": 0.06,
        "deal_gen_prob_mult": 1.4, "deal_days_mult": 0.6,
        "label": "Quant : deals techniques fréquents mais à résoudre vite — "
                 "beaucoup de petites décisions rapides plutôt que de gros coups.",
    },
    "Advisory": {
        "mandate_offer_mult": 1.7, "mandate_reward_mult": 1.3, "deal_bonus": 0.10,
        "label": "Conseil : davantage de mandats clients, mieux rémunérés — le "
                 "rythme se cale sur la relation client, pas sur le marché.",
    },
    "General": {"label": "Aucune spécialisation : choisissez une voie (TRACK)."},
}

_DEFAULTS = {
    "commission_mult": 1.0, "deal_reward_mult": 1.0, "deal_bonus": 0.10,
    "diff_relief": 0.0, "max_leverage_add": 0.0, "margin_spread_mult": 1.0,
    "maint_margin": None, "mandate_offer_mult": 1.0, "mandate_reward_mult": 1.0,
    "deal_gen_prob_mult": 1.0, "deal_days_mult": 1.0, "stresstest_period_mult": 1.0,
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
