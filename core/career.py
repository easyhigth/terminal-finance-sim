"""
career.py — Progression de carrière (logique pure, sans pygame).

Regroupe :
  - les conditions de promotion COMBINÉES (réputation, missions, deals,
    ancienneté) — l'examen QCM n'est plus que l'étape finale ;
  - les objectifs TRIMESTRIELS (2 à 4 cibles par trimestre, récompensées) ;
  - le journal de carrière (événements marquants) ;
  - les titres de prestige attribués aux promotions.

Aucune dépendance pygame : testable en headless.
"""
import random

from core import config, crashlog, missions


# ---------------------------------------------------------------------------
# Journal de carrière
# ---------------------------------------------------------------------------
def log(player, kind, text):
    """Ajoute une entrée datée au journal (kind: promo|deal|crisis|objective|info)."""
    player.journal.append({"day": player.day, "quarter": player.quarter,
                           "kind": kind, "text": text})
    if len(player.journal) > 80:
        player.journal.pop(0)


# ---------------------------------------------------------------------------
# Profil de risque (style de jeu, indépendant de la progression de grade)
# ---------------------------------------------------------------------------
RISK_PROFILES = ("Prudent", "Modéré", "Risque élevé")


def risk_profile(player):
    """Profil de risque dérivé de l'usage du levier/marge au fil de la carrière
    (compteurs alimentés par portfolio.check_margin_call et game_state.advance_step) :
    survivre à des margin calls répétés en restant très levier marque le style de
    jeu, pas seulement le grade. Sert à moduler les mandats proposés (core.mandates)."""
    mc = player.flags.get("margin_call_count", 0)
    hl = player.flags.get("high_leverage_steps", 0)
    if mc >= 3 or hl >= 20:
        return "Risque élevé"
    if mc >= 1 or hl >= 5:
        return "Modéré"
    return "Prudent"


_RISK_PROFILE_EN = {"Risque élevé": "High risk", "Modéré": "Moderate", "Prudent": "Conservative"}


def risk_profile_label(profile):
    """Libellé localisé du profil de risque (la clé FR reste la valeur de logique)."""
    from core.i18n import get_lang
    return _RISK_PROFILE_EN.get(profile, profile) if get_lang() == "en" else profile


# ---------------------------------------------------------------------------
# Conditions de promotion (combinées)
# ---------------------------------------------------------------------------
def promotion_requirements(player):
    """Liste des critères de promotion avec valeur courante / cible / atteint."""
    gi = player.grade_index
    thr = missions.reputation_threshold(gi)
    req_missions = 2 + gi // 3
    # bonus de certification (CFA/FRM/CQF complète correspondant à la voie)
    try:
        from core import certifications
        rep_cut, miss_cut = certifications.promotion_bonus(player)
        thr = max(50, thr - rep_cut)
        req_missions = max(1, req_missions - miss_cut)
    except Exception:
        crashlog.swallowed("core.career")
    req_deals = 0 if gi <= 1 else (1 if gi <= 5 else 2)
    req_tenure = 0 if gi <= 3 else 1          # trimestres dans le grade
    tenure = max(0, player.quarter - player.grade_start_quarter)
    reqs = [
        {"label": "Réputation", "current": player.reputation, "target": thr,
         "met": player.reputation >= thr, "kind": "rep"},
        {"label": "Missions (ce grade)", "current": player.grade_missions,
         "target": req_missions, "met": player.grade_missions >= req_missions, "kind": "count"},
    ]
    if req_deals > 0:
        reqs.append({"label": "Deals conclus (ce grade)", "current": player.grade_deals,
                     "target": req_deals, "met": player.grade_deals >= req_deals, "kind": "count"})
    if req_tenure > 0:
        reqs.append({"label": "Ancienneté (trimestres)", "current": tenure,
                     "target": req_tenure, "met": tenure >= req_tenure, "kind": "count"})
    if gi >= 2 and player.track == "General":
        reqs.append({"label": "Voie de spécialisation choisie (TRACK)", "current": 0,
                     "target": 1, "met": False, "kind": "track"})
    return reqs


def promotion_ready(player):
    """Vrai si tous les critères sont remplis (et promotion possible)."""
    if not player.can_promote():
        return False
    return all(r["met"] for r in promotion_requirements(player))


def missing_criteria(player):
    """Libellés des critères non encore remplis."""
    return [r["label"] for r in promotion_requirements(player) if not r["met"]]


# ---------------------------------------------------------------------------
# Titres de prestige
# ---------------------------------------------------------------------------
_TRACK_TITLES = {
    "Portfolio": "Portfolio Strategist",
    "M&A": "Rainmaker",
    "Risk": "Risk Guardian",
    "Quant": "Quant Star",
    "Advisory": "Trusted Advisor",
}

_TRACK_TITLES_10 = {
    "Portfolio": "Chief Investment Officer",
    "M&A": "Head of M&A",
    "Risk": "Chief Risk Officer",
    "Quant": "Head of Quant Strategies",
    "Advisory": "Head of Advisory",
}

_TRACK_TITLES_11 = {
    "Portfolio": "Légende de l'allocation d'actifs",
    "M&A": "Légende des fusions-acquisitions",
    "Risk": "Légende de la gestion des risques",
    "Quant": "Légende de la finance quantitative",
    "Advisory": "Légende du conseil stratégique",
}


def award_promotion(player):
    """Attribue éventuellement un titre de prestige lors d'une promotion."""
    title = None
    if player.grade_index == 6:        # accès au top management
        title = _TRACK_TITLES.get(player.track, "Senior Banker")
    elif player.grade_index == 10:
        title = _TRACK_TITLES_10.get(player.track, "Managing Director émérite")
    elif player.grade_index == 11:
        title = _TRACK_TITLES_11.get(player.track, "Legend of the Street")
    if title and title not in player.titles:
        player.titles.append(title)
    return title


# ---------------------------------------------------------------------------
# Objectifs trimestriels
# ---------------------------------------------------------------------------
def _round_money(x):
    return float(round(x / 1000.0) * 1000)


def generate_objectives(player, rng=None):
    """Génère 2 à 4 objectifs pour le trimestre courant (cibles selon le grade)."""
    rng = rng or random
    gi = player.grade_index
    cands = [
        {"kind": "missions", "target": 2 + gi // 3, "base": player.missions_done},
        {"kind": "reputation", "target": min(96, player.reputation + rng.randint(4, 10))},
        {"kind": "cash", "target": _round_money(player.cash + 35000 * (1 + gi))},
    ]
    if gi >= 1:
        cands.append({"kind": "deals", "target": 1 + gi // 4, "base": player.deals_won})
        # objectif de P&L imposé par le boss : faire CROÎTRE le patrimoine ce
        # trimestre (mesuré vs l'ancre de début de trimestre, cf.
        # quarter_nw_anchor) — la pression d'un desk, couplée au budget de VaR
        # déjà en place (la jauge du bureau). N'apparaît qu'une fois qu'on peut
        # investir (grade 1+).
        cands.append({"kind": "pnl", "target": _round_money(25000 * (1 + gi))})
    rng.shuffle(cands)
    n = rng.randint(2, min(4, len(cands)))
    objs = []
    for c in cands[:n]:
        c = dict(c)
        c["done"] = False
        c["reward_rep"] = 3
        c["reward_cash"] = _round_money(14000 * (1 + gi))
        objs.append(c)
    return objs


def objective_progress(player, obj):
    """Retourne (courant, cible, atteint) pour un objectif."""
    k = obj["kind"]
    if k == "missions":
        cur = player.missions_done - obj.get("base", 0)
        return cur, obj["target"], cur >= obj["target"]
    if k == "deals":
        cur = player.deals_won - obj.get("base", 0)
        return cur, obj["target"], cur >= obj["target"]
    if k == "reputation":
        return player.reputation, obj["target"], player.reputation >= obj["target"]
    if k == "cash":
        return player.cash, obj["target"], player.cash >= obj["target"]
    if k == "pnl":
        # P&L du trimestre = patrimoine actuel − ancre de début de trimestre
        # (cash_history stocke la valeur nette ; cf. GameState.quarter_nw_anchor)
        nw = player.cash_history[-1] if getattr(player, "cash_history", None) else player.cash
        cur = nw - getattr(player, "quarter_nw_anchor", 0.0)
        return cur, obj["target"], cur >= obj["target"]
    return 0, 1, False


def objective_label(player, obj):
    """Libellé lisible d'un objectif (avec progression intégrée si pertinent)."""
    cur, target, _ = objective_progress(player, obj)
    cur_currency = config.CONTINENTS.get(player.continent, {}).get("currency", "$")
    if obj["kind"] == "missions":
        return f"Réaliser {obj['target']} missions ce trimestre ({max(0,cur)}/{obj['target']})"
    if obj["kind"] == "deals":
        return f"Conclure {obj['target']} deals ce trimestre ({max(0,cur)}/{obj['target']})"
    if obj["kind"] == "reputation":
        return f"Atteindre {obj['target']} de réputation ({player.reputation})"
    if obj["kind"] == "cash":
        return f"Trésorerie ≥ {cur_currency}{obj['target']/1000:.0f}K"
    if obj["kind"] == "pnl":
        return (f"P&L du trimestre ≥ {cur_currency}{obj['target']/1000:.0f}K "
                f"({cur_currency}{cur/1000:+.0f}K)")
    return obj["kind"]


def ensure_objectives(player, rng=None):
    """(Re)génère les objectifs si ceux en mémoire ne sont pas du trimestre courant."""
    if player.objectives_quarter != player.quarter or not player.objectives:
        player.objectives = generate_objectives(player, rng)
        player.objectives_quarter = player.quarter
        return True
    return False


def close_quarter(player):
    """Évalue les objectifs du trimestre écoulé, attribue les récompenses.
    Retourne un résumé. À appeler AVANT de régénérer pour le nouveau trimestre."""
    done = 0
    rep = 0
    cash = 0.0
    total = len(player.objectives)
    for o in player.objectives:
        _, _, ok = objective_progress(player, o)
        if ok:
            done += 1
            rep += o.get("reward_rep", 0)
            cash += o.get("reward_cash", 0)
    if total and done == total:        # bonus « trimestre parfait »
        rep += 4
        cash += _round_money(18000 * (1 + player.grade_index))
        log(player, "objective", f"Trimestre parfait ({done}/{total} objectifs).")
        reason = f"Trimestre parfait ({done}/{total} objectifs)"
    elif done:
        log(player, "objective", f"Objectifs trimestriels : {done}/{total} atteints.")
        reason = f"Objectifs trimestriels : {done}/{total} atteints"
    else:
        reason = "Objectifs trimestriels non atteints" if total else None
    player.adjust_reputation(rep, reason=reason)
    player.adjust_cash(cash, category="objectifs")
    return {"done": done, "total": total, "rep": rep, "cash": cash}
