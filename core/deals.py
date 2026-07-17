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

from core import archetypes, config, crashlog, firms, tracks, unlocks

MAX_ACTIVE_DEALS = 4        # au-delà, plus de génération
GEN_PROBABILITY = 0.45      # proba de générer un deal à un tour donné
MISS_PENALTY_FRAC = 0.05    # un deal manqué coûte surtout de la réputation,
                            # et seulement une petite fraction du gain en cash
MAX_DEALS_HISTORY = 20      # nb de deals résolus conservés pour le replay (UI)


def _record_history(player, deal, outcome, cash_delta, rep_delta):
    """Ajoute un deal résolu (conclu/partiel/échoué/expiré) à l'historique de
    replay du joueur (cf. PlayerState.deals_history), capé à MAX_DEALS_HISTORY
    entrées les plus récentes."""
    player.deals_history.append({
        "day": player.day, "quarter": player.quarter,
        "title": deal["title"], "kind": deal["kind"], "outcome": outcome,
        "cash_delta": cash_delta, "rep_delta": rep_delta,
        "difficulty": deal["difficulty"],
    })
    if len(player.deals_history) > MAX_DEALS_HISTORY:
        player.deals_history.pop(0)


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

    {"kind": "DCM", "title": "Émission obligataire corporate",
     "desc": "Originer et placer une émission de dette pour un client corporate.",
     "base_cash": 95_000, "rep": 6, "difficulty": 3, "days": 20},
    {"kind": "DCM", "title": "Refinancement à l'échéance",
     "desc": "Structurer le refinancement d'une dette qui arrive à échéance.",
     "base_cash": 70_000, "rep": 5, "difficulty": 2, "days": 16},
    {"kind": "DCM", "title": "Émission high-yield",
     "desc": "Placer une émission spéculative auprès d'investisseurs high-yield.",
     "base_cash": 110_000, "rep": 7, "difficulty": 4, "days": 18},

    {"kind": "General", "title": "Note de marché urgente",
     "desc": "Produire une note de conjoncture pour le comité d'investissement.",
     "base_cash": 30_000, "rep": 4, "difficulty": 2, "days": 12},
    {"kind": "General", "title": "Présentation au comité",
     "desc": "Défendre une recommandation devant le comité d'investissement.",
     "base_cash": 40_000, "rep": 5, "difficulty": 3, "days": 14},
]


# --------------------------------------------------------------------------
# Deals SOUVERAINS : mandats avec des gouvernements, déclenchés par l'actualité
# politique (core/politics.py) quand c'est COHÉRENT avec la situation du pays.
# --------------------------------------------------------------------------
GOV_DEAL_PROBABILITY = 0.45     # proba quand un événement éligible survient
MAX_GOV_DEALS = 2               # plafond de deals souverains actifs simultanés

# Selon la tonalité de l'événement politique, un type de mandat différent :
#   good  → financement d'infrastructure / privatisation (mandat lucratif) ;
#   bad   → restructuration de dette / stabilisation (mission de crise) ;
#   info  → conseil stratégique (plus modeste).
_GOV_TEMPLATES = {
    "good": {"kind": "Advisory", "title": "Mandat souverain — financement d'infrastructure",
             "desc": "Structurer et placer l'emprunt d'infrastructure de {country}.",
             "base_cash": 140_000, "rep": 8, "difficulty": 4, "days": 26},
    "bad": {"kind": "Risk", "title": "Mandat souverain — restructuration de dette",
            "desc": "Conseiller {country} sur la restructuration et la stabilisation de sa dette.",
            "base_cash": 160_000, "rep": 9, "difficulty": 5, "days": 22},
    "info": {"kind": "Advisory", "title": "Mandat souverain — conseil stratégique",
             "desc": "Accompagner {country} dans l'arbitrage de sa politique économique.",
             "base_cash": 90_000, "rep": 6, "difficulty": 3, "days": 20},
}


def maybe_government_deal(player, event, rng=None):
    """Génère éventuellement un DEAL avec un gouvernement, en cohérence avec un
    événement politique (event = dict de core/politics.maybe_trigger). Retourne
    le deal créé ou None. Réservé aux grades qui peuvent traiter des deals."""
    rng = rng or random
    if not event or player.grade_index < 3:        # deals souverains : Associate+
        return None
    n_gov = sum(1 for d in player.deals if d.get("gov"))
    if n_gov >= MAX_GOV_DEALS:
        return None
    if rng.random() > GOV_DEAL_PROBABILITY:
        return None
    tmpl = _GOV_TEMPLATES.get(event.get("kind"), _GOV_TEMPLATES["info"])
    country = event.get("country", "un État")
    scale = _scale(player)
    reward_cash = round(tmpl["base_cash"] * scale * rng.uniform(0.9, 1.25), 2)
    deal = {
        "id": player.next_deal_id,
        "title": tmpl["title"],
        "kind": tmpl["kind"],
        "desc": tmpl["desc"].format(country=country),
        "reward_cash": reward_cash,
        "reward_rep": tmpl["rep"],
        "penalty_cash": round(reward_cash * MISS_PENALTY_FRAC, 2),
        "penalty_rep": max(2, tmpl["difficulty"] - 1),
        "difficulty": tmpl["difficulty"],
        "days_left": tmpl["days"],
        "gov": country,                     # marqueur de contrepartie souveraine
        "region": event.get("region"),
    }
    player.next_deal_id += 1
    player.deals.append(deal)
    return deal


def _scale(player):
    """Facteur d'échelle des montants selon le grade."""
    return 1.0 + 0.7 * player.grade_index


def _eligible_templates(player):
    """Deals proposés : ceux de la voie du joueur + les 'General'/'DCM'.

    DCM n'a pas de voie dédiée : ses deals restent ouverts à tous, comme
    'General', plutôt que de réserver l'origination obligataire à une voie."""
    track = player.track
    out = []
    for t in DEAL_TEMPLATES:
        if t["kind"] in ("General", "DCM") or t["kind"] == track:
            out.append(t)
    # avant de choisir une voie, on ne propose que du General + un peu de tout
    if track in ("General", "", None):
        out = DEAL_TEMPLATES
    return out


def maybe_generate(player, rng=None):
    """Génère éventuellement un nouveau deal. Retourne la liste des deals créés."""
    rng = rng or random
    if not unlocks.unlocked(player, "deals"):
        return []
    if len(player.deals) >= MAX_ACTIVE_DEALS:
        return []
    prob_bonus = 0.0
    try:
        from core import team
        prob_bonus = (team.team_deal_prob_bonus(player)
                      + team.deals_assign_bonus(player))   # analystes affectés au support deals
    except Exception:
        crashlog.swallowed("core.deals")
    from core import focus as _focus
    gen_prob = (GEN_PROBABILITY * tracks.perk(player, "deal_gen_prob_mult")
                * archetypes.perk(player, "deal_gen_prob_mult")
                * firms.perk(player, "deal_gen_prob_mult")
                * _focus.perk(player, "offer_mult"))
    if rng.random() > gen_prob + prob_bonus:
        return []
    t = rng.choice(_eligible_templates(player))
    scale = _scale(player)
    own_track = t["kind"] == player.track
    # bonus de récompense si le deal relève de la voie du joueur (M&A surtout),
    # composé avec le multiplicateur de l'archétype (philosophie de run) et
    # celui de l'ADN de la firme (boutique M&A surtout)
    track_mult = tracks.perk(player, "deal_reward_mult") if own_track else 1.0
    arch_mult = archetypes.perk(player, "deal_reward_mult")
    firm_mult = firms.perk(player, "deal_reward_mult")
    reward_cash = round(t["base_cash"] * scale * track_mult * arch_mult * firm_mult
                        * rng.uniform(0.85, 1.25), 2)
    # délai de traitement modulé par voie (M&A : plus long ; Quant : plus court)
    days_mult = tracks.perk(player, "deal_days_mult") if own_track else 1.0
    days_left = max(3, round(t["days"] * days_mult))
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
        "days_left": days_left,
    }
    player.next_deal_id += 1
    player.deals.append(deal)
    return [deal]


def age_deals(player):
    """
    Fait vieillir les deals d'un tour. Les deals échus non traités sont retirés
    et infligent leur pénalité. Retourne la liste des deals expirés.
    """
    from core.i18n import get_lang
    en = get_lang() == "en"
    expired = []
    still_active = []
    for d in player.deals:
        d["days_left"] -= config.DAYS_PER_STEP
        if d["days_left"] <= 0:
            player.adjust_cash(-d["penalty_cash"], category="deals")
            reason = (f"Deal expired: {d['title']}" if en
                      else f"Deal expiré : {d['title']}")
            player.adjust_reputation(-d["penalty_rep"], reason=reason)
            _record_history(player, d, "expired", -d["penalty_cash"], -d["penalty_rep"])
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
    p = (0.45 + 0.5 * rep_factor - diff_penalty + edge
         + archetypes.perk(player, "deal_success_bonus") + firms.perk(player, "deal_success_bonus"))
    return max(0.10, min(0.95, p))


def apply_outcome(player, deal_id, quality):
    """Applique le résultat d'un mini-jeu de deal selon la QUALITÉ du choix :
      good → succès plein · ok → succès partiel · bad → échec.
    Retourne un dict résultat, ou {ok: False} si le deal n'existe pas."""
    from core.i18n import get_lang
    en = get_lang() == "en"
    deal = find_deal(player, deal_id)
    if deal is None:
        return {"ok": False}
    if quality == "good":
        cash_delta = deal["reward_cash"]
        rep_delta = deal["reward_rep"]
        reason = (f"Deal closed: {deal['title']}" if en else f"Deal conclu : {deal['title']}")
        player.adjust_cash(cash_delta, category="deals")
        player.adjust_reputation(rep_delta, reason=reason)
        player.deals_won += 1
        player.grade_deals += 1
        outcome = "success"
    elif quality == "ok":
        cash_delta = round(deal["reward_cash"] * 0.5, 2)
        rep_delta = max(1, deal["reward_rep"] // 2)
        reason = (f"Deal partially closed: {deal['title']}" if en
                  else f"Deal partiellement conclu : {deal['title']}")
        player.adjust_cash(cash_delta, category="deals")
        player.adjust_reputation(rep_delta, reason=reason)
        player.deals_won += 1
        player.grade_deals += 1
        outcome = "partial"
    else:  # bad
        cash_delta = -deal["penalty_cash"]
        rep_delta = -round(deal["penalty_rep"] * archetypes.perk(player, "rep_loss_mult"))
        reason = (f"Deal failed: {deal['title']}" if en else f"Deal échoué : {deal['title']}")
        player.adjust_cash(cash_delta, category="deals")
        player.adjust_reputation(rep_delta, reason=reason)
        outcome = "fail"
    player.deals = [d for d in player.deals if d["id"] != deal_id]
    _record_history(player, deal, outcome, cash_delta, rep_delta)
    return {"ok": True, "outcome": outcome, "deal": deal, "quality": quality,
            "cash_delta": cash_delta, "rep_delta": rep_delta}


def resolve_deal(player, deal_id, rng=None):
    """
    Tente de conclure un deal. Retourne un dict résultat :
      {ok: bool, success: bool, deal: ..., prob: float}
    ok=False si le deal n'existe pas.
    """
    from core.i18n import get_lang
    en = get_lang() == "en"
    rng = rng or random
    deal = find_deal(player, deal_id)
    if deal is None:
        return {"ok": False, "success": False, "deal": None, "prob": 0.0}
    prob = success_probability(player, deal)
    success = rng.random() < prob
    if success:
        reason = (f"Deal closed: {deal['title']}" if en else f"Deal conclu : {deal['title']}")
        player.adjust_cash(deal["reward_cash"], category="deals")
        player.adjust_reputation(deal["reward_rep"], reason=reason)
        player.deals_won += 1
        player.grade_deals += 1
        _record_history(player, deal, "success", deal["reward_cash"], deal["reward_rep"])
    else:
        rep_delta = -round(deal["penalty_rep"] * archetypes.perk(player, "rep_loss_mult"))
        reason = (f"Deal failed: {deal['title']}" if en else f"Deal échoué : {deal['title']}")
        player.adjust_cash(-deal["penalty_cash"], category="deals")
        player.adjust_reputation(rep_delta, reason=reason)
        _record_history(player, deal, "fail", -deal["penalty_cash"], rep_delta)
    player.deals = [d for d in player.deals if d["id"] != deal_id]
    return {"ok": True, "success": success, "deal": deal, "prob": prob}
