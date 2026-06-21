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

def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


PERKS = {
    "Portfolio": {
        "commission_mult": 0.5, "deal_bonus": 0.10,
        "label": ("Gestion active : commissions de trading réduites de moitié. "
                  "Rythme régulier, sans à-coups particuliers.",
                  "Active management: trading commissions halved. "
                  "Steady pace, no particular swings."),
    },
    "M&A": {
        "deal_reward_mult": 1.3, "deal_bonus": 0.12,
        "deal_gen_prob_mult": 0.65, "deal_days_mult": 1.5,
        "label": ("Dealmaker : deals rares mais nettement plus rémunérateurs, et "
                  "plus de temps pour les mener — peu de décisions, mais énormes.",
                  "Dealmaker: rare deals but much more lucrative, and more time "
                  "to close them — few decisions, but huge ones."),
    },
    "Risk": {
        "max_leverage_add": 0.5, "margin_spread_mult": 0.5, "maint_margin": 0.20,
        "deal_bonus": 0.10, "stresstest_period_mult": 0.5,
        "label": ("Gestion du risque : levier accru, marge moins chère, appels de "
                  "marge plus cléments — mais stress tests réglementaires deux fois "
                  "plus fréquents : sous contrôle permanent.",
                  "Risk management: higher leverage, cheaper margin, gentler margin "
                  "calls — but regulatory stress tests twice as frequent: under "
                  "constant scrutiny."),
    },
    "Quant": {
        "deal_bonus": 0.18, "diff_relief": 0.06,
        "deal_gen_prob_mult": 1.4, "deal_days_mult": 0.6,
        "label": ("Quant : deals techniques fréquents mais à résoudre vite — "
                  "beaucoup de petites décisions rapides plutôt que de gros coups.",
                  "Quant: frequent technical deals but to resolve quickly — "
                  "lots of small, fast decisions rather than big plays."),
    },
    "Advisory": {
        "mandate_offer_mult": 1.7, "mandate_reward_mult": 1.3, "deal_bonus": 0.10,
        "label": ("Conseil : davantage de mandats clients, mieux rémunérés — le "
                  "rythme se cale sur la relation client, pas sur le marché.",
                  "Advisory: more client mandates, better paid — the pace follows "
                  "the client relationship, not the market."),
    },
    "General": {"label": ("Aucune spécialisation : choisissez une voie (TRACK).",
                          "No specialization: choose a track (TRACK).")},
}

_DEFAULTS = {
    "commission_mult": 1.0, "deal_reward_mult": 1.0, "deal_bonus": 0.10,
    "diff_relief": 0.0, "max_leverage_add": 0.0, "margin_spread_mult": 1.0,
    "maint_margin": None, "mandate_offer_mult": 1.0, "mandate_reward_mult": 1.0,
    "deal_gen_prob_mult": 1.0, "deal_days_mult": 1.0, "stresstest_period_mult": 1.0,
}

# ---------------------------------------------------------------------------
# Reconversion : le choix initial de voie (post-Analyst) est gratuit, mais
# changer de voie ENSUITE a un coût tangible — sinon le choix de voie (et tout
# pivot ultérieur) n'engage à rien. Coût cash proportionnel à la valeur nette
# + période de "rodage" pendant laquelle les avantages de la nouvelle voie
# montent en puissance progressivement (perk() interpole depuis le neutre)
# plutôt que d'être pleinement actifs dès le changement.
RECONVERSION_COST_FRAC = 0.08   # part de la valeur nette payée en cash
RAMP_DAYS = 90                  # durée du rodage (perks montent en puissance)


def _ramp_factor(player):
    """0.0 juste après une reconversion -> 1.0 une fois le rodage terminé
    (ou si aucune reconversion n'a eu lieu)."""
    switch_day = player.flags.get("track_switch_day") if hasattr(player, "flags") else None
    if switch_day is None:
        return 1.0
    elapsed = player.day - switch_day
    if elapsed >= RAMP_DAYS:
        return 1.0
    return max(0.0, min(1.0, elapsed / RAMP_DAYS))


def reconversion_cost(player, market=None):
    """Coût cash d'une reconversion, proportionnel à la valeur nette courante
    (ou au cash si le marché n'est pas disponible)."""
    nw = player.cash
    if market is not None:
        try:
            from core import portfolio_margin as pm
            nw = pm.net_worth(player, market)
        except Exception:
            nw = player.cash
    return max(0.0, nw) * RECONVERSION_COST_FRAC


def switch_track(player, market, new_track):
    """Change de voie après le choix initial (gratuit, via TRACK), contre un
    coût tangible. Retourne un dict {ok, ...} : si ok, {cost, ramp_days} ;
    sinon {reason} parmi {"invalid_track", "same_track", "cash"}."""
    if new_track not in PERKS or new_track == "General":
        return {"ok": False, "reason": "invalid_track"}
    if getattr(player, "track", "General") == new_track:
        return {"ok": False, "reason": "same_track"}
    cost = reconversion_cost(player, market)
    if player.cash < cost:
        return {"ok": False, "reason": "cash", "cost": cost}
    player.cash -= cost
    player.track = new_track
    player.flags["track_switch_day"] = player.day
    return {"ok": True, "cost": cost, "ramp_days": RAMP_DAYS}


def perk(player, key):
    """Valeur du perk `key` pour la voie du joueur (ou défaut neutre). Si une
    reconversion est en cours de rodage, la valeur est interpolée entre le
    défaut neutre et la pleine valeur de la voie (cf. RAMP_DAYS)."""
    track = getattr(player, "track", "General")
    raw = PERKS.get(track, {}).get(key, _DEFAULTS.get(key))
    if key == "label" or raw is None:
        return raw
    default = _DEFAULTS.get(key)
    if raw == default:
        return raw
    ramp = _ramp_factor(player)
    if ramp >= 1.0:
        return raw
    if default is None:
        return None   # rodage : pas encore d'override actif (ex. maint_margin)
    return default + (raw - default) * ramp


def deal_edge(player, deal):
    """Bonus de proba de réussite (+ allègement de difficulté) si le deal
    relève de la voie du joueur. Retourne (bonus_prob, diff_relief)."""
    if deal.get("kind") and deal["kind"] == getattr(player, "track", None):
        return perk(player, "deal_bonus"), perk(player, "diff_relief")
    return 0.0, 0.0


def label(track):
    lbl = PERKS.get(track, {}).get("label")
    return _L(*lbl) if lbl else ""
