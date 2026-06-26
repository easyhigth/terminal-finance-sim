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
