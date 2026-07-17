"""
team.py — Équipe d'analystes juniors (logique pure, sans pygame).

Le joueur peut, à partir d'un grade avancé (cf. core/unlocks.py, clé "team"),
recruter des analystes juniors qui apportent un bonus passif récurrent en
échange d'un coût récurrent par tour (salaire). Mirroring volontaire du
pattern `salary_bonus_per_step` (core/review.py) : ce module expose des
fonctions PURES (`team_cost_per_step`, `team_bonus_rep_per_step`) que
l'orchestrateur (core/game_state.py: advance_step) branchera lui-même dans le
calcul du net par tour — ce module ne les appelle jamais automatiquement.

Structure (PlayerState) :
  analysts : list[{"profile_id": str, "hired_step": int}]
             "hired_step" mémorise `player.market_step` au moment de
             l'embauche (utile pour un futur affichage d'ancienneté ; non
             utilisé par les calculs actuels).

Catalogue (`PROFILES`) : chaque profil a un coût récurrent par tour et 1-2
effets passifs simples :
  - rep_per_step       : réputation passive gagnée par tour (cf. perk-like)
  - cert_cost_mult     : multiplicateur sur le coût des certifications (<1 = moins cher)
  - deal_prob_bonus    : bonus additif de probabilité d'offre de deal/mandat
"""
from core import unlocks

HIRE_COST = 5_000  # coût d'embauche ponctuel, identique pour tous les profils (simple)

PROFILES = {
    "equity_junior": {
        "label": "Analyste actions junior",
        "desc": "Couvre les valeurs phares, étoffe la recherche actions au quotidien.",
        "cost_per_step": 1_200,
        "rep_per_step": 0.05,
        "deal_prob_bonus": 0.01,
    },
    "credit_junior": {
        "label": "Analyste crédit junior",
        "desc": "Surveille la qualité de crédit, sécurise les dossiers obligataires.",
        "cost_per_step": 1_100,
        "rep_per_step": 0.04,
        "cert_cost_mult": 0.97,
    },
    "quant_junior": {
        "label": "Analyste quant junior",
        "desc": "Affine les modèles internes, allège la charge d'étude technique.",
        "cost_per_step": 1_400,
        "cert_cost_mult": 0.92,
        "deal_prob_bonus": 0.01,
    },
    "macro_junior": {
        "label": "Analyste macro junior",
        "desc": "Suit les banques centrales et les cycles, utile en mandat/desk FX.",
        "cost_per_step": 1_300,
        "rep_per_step": 0.06,
    },
}


def available_profiles():
    """Retourne le catalogue des profils embauchables (dict profile_id -> infos)."""
    return PROFILES


def _profile(profile_id):
    return PROFILES.get(profile_id)


def hire(player, profile_id):
    """Recrute un analyste junior du profil `profile_id`.

    Vérifie défensivement le déblocage par grade (clé "team") même si l'appelant
    est censé le faire — sécurité en profondeur. Vérifie aussi le budget pour le
    coût d'embauche ponctuel (HIRE_COST) et l'existence du profil.

    Retourne {"ok": True, "profile_id": ...} ou {"ok": False, "reason": ...}
    avec reason ∈ {"grade", "unknown_profile", "budget"}.
    """
    if not unlocks.unlocked(player, "team"):
        return {"ok": False, "reason": "grade"}
    profile = _profile(profile_id)
    if profile is None:
        return {"ok": False, "reason": "unknown_profile"}
    if player.cash < HIRE_COST:
        return {"ok": False, "reason": "budget"}
    player.adjust_cash(-HIRE_COST, category="evenements")
    player.analysts.append({
        "profile_id": profile_id,
        "hired_step": getattr(player, "market_step", 0),
    })
    return {"ok": True, "profile_id": profile_id}


def fire(player, index):
    """Licencie l'analyste à l'index `index` de `player.analysts`.

    Retourne {"ok": True, "removed": {...}} ou {"ok": False, "reason": "bad_index"}.
    """
    analysts = getattr(player, "analysts", None) or []
    if index < 0 or index >= len(analysts):
        return {"ok": False, "reason": "bad_index"}
    removed = analysts.pop(index)
    return {"ok": True, "removed": removed}


def team_cost_per_step(player):
    """Somme des coûts récurrents par tour de l'équipe actuelle (fonction pure,
    non câblée automatiquement — l'orchestrateur la soustrait dans advance_step)."""
    total = 0.0
    for a in getattr(player, "analysts", None) or []:
        profile = _profile(a.get("profile_id"))
        if profile:
            total += profile.get("cost_per_step", 0.0)
    return total


def team_bonus_rep_per_step(player):
    """Somme du bonus de réputation passive par tour apporté par l'équipe
    (fonction pure, non câblée automatiquement)."""
    total = 0.0
    for a in getattr(player, "analysts", None) or []:
        profile = _profile(a.get("profile_id"))
        if profile:
            total += profile.get("rep_per_step", 0.0)
    return total


def team_cert_cost_mult(player):
    """Multiplicateur cumulé sur le coût des certifications apporté par
    l'équipe (1.0 = neutre ; chaque analyste pertinent réduit légèrement le
    coût). Fonction pure, non câblée automatiquement."""
    mult = 1.0
    for a in getattr(player, "analysts", None) or []:
        profile = _profile(a.get("profile_id"))
        if profile and "cert_cost_mult" in profile:
            mult *= profile["cert_cost_mult"]
    return mult


def team_deal_prob_bonus(player):
    """Bonus additif cumulé de probabilité d'offre de deal/mandat apporté par
    l'équipe. Fonction pure, non câblée automatiquement."""
    total = 0.0
    for a in getattr(player, "analysts", None) or []:
        profile = _profile(a.get("profile_id"))
        if profile:
            total += profile.get("deal_prob_bonus", 0.0)
    return total


# ---------------------------------------------------------------------------
# AFFECTATIONS (l'équipe devient un CHOIX, pas une rente passive)
# ---------------------------------------------------------------------------
# Chaque analyste peut être affecté à un poste actif : ses effets passifs
# continuent, mais le poste ajoute un effet TANGIBLE — au prix d'une FATIGUE
# qui monte tant qu'il est affecté (à 100, il repart se reposer : affectation
# remise à « libre », fatigue qui décroît). Champs ajoutés à l'entrée
# analyste (tolérants : .get, sauvegardes anciennes = libre/0) :
#     "assignment": "libre"|"recherche"|"deals"|"risque",  "fatigue": 0-100

ASSIGNMENTS = {
    "libre": {
        "label": ("Libre", "Free"),
        "desc": ("Effets passifs seuls ; la fatigue récupère.",
                 "Passive effects only; fatigue recovers."),
    },
    "recherche": {
        "label": ("Recherche", "Research"),
        "desc": ("Publie régulièrement des notes de recherche sur vos valeurs "
                 "(watchlist et portefeuille).",
                 "Regularly publishes research notes on your names (watchlist "
                 "and portfolio)."),
    },
    "deals": {
        "label": ("Support deals", "Deal support"),
        "desc": ("Augmente la probabilité d'offres de deals/mandats.",
                 "Increases the probability of deal/mandate offers."),
    },
    "risque": {
        "label": ("Contrôle des risques", "Risk control"),
        "desc": ("Fait retomber plus vite le scrutin réglementaire (heat).",
                 "Cools down regulatory scrutiny (heat) faster."),
    },
}

FATIGUE_PER_STEP = 3       # fatigue gagnée par pas sur un poste actif
REST_RECOVERY = 5          # fatigue récupérée par pas au repos (libre)
FATIGUE_MAX = 100
RESEARCH_EVERY_STEPS = 5   # cadence de publication d'un analyste en recherche
RESEARCH_FRESH_DAYS = 25   # ne réécrit pas une note plus récente que ça
DEALS_ASSIGN_BONUS = 0.05  # bonus additif de proba d'offre par analyste affecté
RISK_HEAT_DECAY = 0.6      # décrue de heat supplémentaire par analyste affecté


def assignment_label(key):
    from core.i18n import get_lang
    a = ASSIGNMENTS.get(key, ASSIGNMENTS["libre"])
    return a["label"][1] if get_lang() == "en" else a["label"][0]


def assignment_desc(key):
    from core.i18n import get_lang
    a = ASSIGNMENTS.get(key, ASSIGNMENTS["libre"])
    return a["desc"][1] if get_lang() == "en" else a["desc"][0]


def assign(player, index, assignment):
    """Affecte l'analyste `index` au poste `assignment`. Un analyste épuisé
    (fatigue == max) ne peut pas reprendre un poste actif tant qu'il n'a pas
    récupéré sous 50."""
    if assignment not in ASSIGNMENTS:
        return {"ok": False, "reason": "assignment"}
    analysts = getattr(player, "analysts", None) or []
    if not (0 <= index < len(analysts)):
        return {"ok": False, "reason": "index"}
    a = analysts[index]
    if assignment != "libre" and a.get("fatigue", 0) >= 50 and a.get("exhausted"):
        return {"ok": False, "reason": "fatigue"}
    a["assignment"] = assignment
    if assignment == "libre":
        a.pop("exhausted", None)
    return {"ok": True}


def _effective(a):
    """Facteur d'efficacité d'un analyste sur poste actif (la fatigue pèse)."""
    return max(0.3, 1.0 - a.get("fatigue", 0) / 150.0)


def deals_assign_bonus(player):
    """Bonus additif de proba d'offre apporté par les analystes affectés au
    support deals (s'ajoute à team_deal_prob_bonus, les perks passifs)."""
    total = 0.0
    for a in getattr(player, "analysts", None) or []:
        if a.get("assignment") == "deals":
            total += DEALS_ASSIGN_BONUS * _effective(a)
    return total


def _research_target(player, market):
    """Prochaine valeur à couvrir : watchlist puis portefeuille, sans note
    fraîche (< RESEARCH_FRESH_DAYS jours)."""
    candidates = list(getattr(player, "watchlist", None) or [])
    candidates += [tk for tk in player.portfolio if tk not in candidates]
    for tk in candidates:
        note = player.research.get(tk)
        if not note or player.day - note.get("day", 0) >= RESEARCH_FRESH_DAYS:
            return tk
    return None


def assignments_step(player, market):
    """Joue les effets des affectations pour CE pas (appelé par le hook de
    pas "team_assignments"). Retourne une liste d'évènements notifiables :
    [{"kind": "research_note"|"rest", ...}]."""
    events = []
    analysts = getattr(player, "analysts", None) or []
    for a in analysts:
        assignment = a.get("assignment", "libre")
        if assignment == "libre":
            a["fatigue"] = max(0, a.get("fatigue", 0) - REST_RECOVERY)
            continue
        a["fatigue"] = min(FATIGUE_MAX, a.get("fatigue", 0) + FATIGUE_PER_STEP)
        eff = _effective(a)
        if assignment == "recherche":
            since = getattr(player, "market_step", 0) - a.get("last_research_step", -999)
            if since >= RESEARCH_EVERY_STEPS:
                tk = _research_target(player, market)
                if tk is not None:
                    from core import research_notes as _rn
                    note = _rn.write_note(player, market, tk)
                    if note:
                        a["last_research_step"] = getattr(player, "market_step", 0)
                        events.append({"kind": "research_note", "analyst": a,
                                       "note": note})
        elif assignment == "risque":
            player.heat = max(0, player.heat - RISK_HEAT_DECAY * eff)
        if a["fatigue"] >= FATIGUE_MAX:
            a["assignment"] = "libre"
            a["exhausted"] = True
            events.append({"kind": "rest", "analyst": a})
    return events
