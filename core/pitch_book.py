"""
pitch_book.py — Démarchage ACTIF de mandats clients (voie Advisory, logique
pure).

Jusqu'ici, un mandat n'arrivait que PASSIVEMENT via
`core/mandates.py::maybe_offer` (tirage aléatoire, profil client choisi par
le jeu) — et la commande PITCH existante
(`scenes/scene_terminal_career.py::_cmd_pitch`) ne s'y raccorde même pas
(elle route vers le pipeline de deals générique, sans rapport avec les
mandats). La voie Advisory n'avait donc AUCUN outil proactif propre :
ce module comble le manque.

Le joueur CHOISIT un profil client à approcher (cf.
`core/mandates.CLIENT_PROFILES`) et une AMBITION de mandat (0.5..1.5×,
grossit capital ET objectif visés) ; `win_probability` calcule la chance de
succès AVANT de pitcher (fonction de la réputation, du grade, de la voie et
de l'ambition demandée — voir gros/petit) ; `pitch()` tire le résultat :
  - GAGNÉ : une offre RÉELLE naît, via `core/mandates.py::_build_offer`
    (réutilisé, jamais dupliqué) — le joueur la retrouve ensuite dans son
    inbox/mandats comme une offre normale (à accepter/décliner).
  - PERDU : coûte de la réputation (un pitch raté ternit l'image du
    banquier) et impose un délai de rétractation (cooldown, en trimestres)
    avant de retenter CE MÊME profil — on ne spam pas un client qui vient de
    dire non.
"""
import random

from core import mandates as M

COOLDOWN_QUARTERS = 2
BASE_WIN_PROB = 0.55
FAIL_REP_PENALTY = 3
MIN_AMBITION, MAX_AMBITION = 0.5, 1.5


def fit_score(player, profile_key):
    """Score 0..1 : à quel point le joueur (réputation, grade, voie choisie)
    est un candidat crédible pour CE profil client. Un profil « strict »
    (assureur, institutionnel prudent — cf. CLIENT_PROFILES) est plus
    exigeant à convaincre."""
    profile = M._PROFILE_BY_KEY.get(profile_key)
    if not profile:
        return 0.0
    rep_score = max(0.0, min(1.0, player.reputation / 100.0))
    grade_score = max(0.0, min(1.0, player.grade_index / 9.0))
    track_bonus = 0.15 if getattr(player, "track", None) == "Advisory" else 0.0
    strict_penalty = 0.10 if profile.get("strict") else 0.0
    return max(0.0, min(1.0, 0.45 * rep_score + 0.30 * grade_score + track_bonus
                        + 0.10 - strict_penalty))


def win_probability(player, profile_key, ambition=1.0):
    """Probabilité de gagner le pitch. Viser plus haut que le capital/
    objectif « naturel » (ambition > 1) réduit la probabilité (le client
    négocie plus dur) ; viser plus bas (ambition < 1) l'augmente."""
    fit = fit_score(player, profile_key)
    amb_penalty = (ambition - 1.0) * 0.35
    return max(0.05, min(0.95, BASE_WIN_PROB + (fit - 0.5) * 0.8 - amb_penalty))


def can_pitch(player, profile_key):
    """(autorisé, trimestre_de_déblocage_si_non)."""
    cooldowns = player.flags.get("pitch_cooldowns") or {}
    until = cooldowns.get(profile_key)
    if until is not None and player.quarter < until:
        return False, until
    return True, None


def pitch(player, profile_key, ambition=1.0, rng=None, market=None):
    """Tente un pitch actif sur `profile_key`. Retourne {"ok", "won",
    "offer"?, "probability", "reason"?}. `ok=False` signifie que le pitch
    n'a même pas pu être TENTÉ (cooldown, trop de mandats en cours, profil
    inconnu) — distinct de `won=False` (tenté, perdu)."""
    rng = rng or random
    profile = M._PROFILE_BY_KEY.get(profile_key)
    if not profile:
        return {"ok": False, "reason": "Profil client inconnu."}
    ambition = max(MIN_AMBITION, min(MAX_AMBITION, ambition))
    allowed, until = can_pitch(player, profile_key)
    if not allowed:
        return {"ok": False, "reason": f"Ce client attend encore (trimestre {until})."}
    if len(player.mandates) + len(player.mandate_offers) >= M.MAX_ACTIVE + 1:
        return {"ok": False, "reason": "Trop de mandats/offres en cours."}
    prob = win_probability(player, profile_key, ambition)
    won = rng.random() < prob
    if won:
        offer = M._build_offer(player, profile, rng, market, ambition=ambition)
        player.mandate_offers.append(offer)
        return {"ok": True, "won": True, "offer": offer, "probability": prob}
    cooldowns = player.flags.setdefault("pitch_cooldowns", {})
    cooldowns[profile_key] = player.quarter + COOLDOWN_QUARTERS
    player.adjust_reputation(-FAIL_REP_PENALTY, reason=M._L(
        f"Pitch manqué auprès d'un client {M.profile_label(profile_key)}",
        f"Missed pitch to a {M.profile_label(profile_key)} client"))
    return {"ok": True, "won": False, "probability": prob, "reason": M._L(
        "Le client n'a pas été convaincu.", "The client wasn't convinced.")}
