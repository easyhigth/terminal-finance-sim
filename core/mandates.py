"""
mandates.py — Mandats clients (logique pure, sans pygame).

Un client confie un capital à gérer avec un OBJECTIF DE RENDEMENT sur un horizon
(en trimestres) et une LIMITE DE RISQUE (bêta max). À l'échéance :
  - succès si la valeur nette a crû d'au moins `target_pct` ET que le bêta du
    portefeuille respecte la limite → commission (% du capital) + réputation ;
  - échec sinon → perte de réputation (le client se détourne).

Disponible à partir d'un certain grade (on confie de l'argent aux seniors).

Structures (PlayerState) :
  mandate_offers : offres en attente d'acceptation
  mandates       : mandats acceptés en cours (avec snapshot de départ)
"""
import random

from core import tracks

MIN_GRADE = 6              # Vice President et au-delà (cf. unlocks)
MAX_ACTIVE = 2            # mandats simultanés
OFFER_PROB = 0.18         # proba d'une offre par tour (si place dispo)

CLIENTS = [
    "Fonds de pension Helven", "Family Office Drax", "Assureur Norvik",
    "Fondation Maray", "Hedge Fund Cyrl", "Trésorerie Ostia", "Dotation Veles",
]


def _scale(grade):
    return 1.0 + 0.6 * grade


def maybe_offer(player, rng=None):
    """Génère éventuellement une offre de mandat. Retourne l'offre ou None."""
    rng = rng or random
    if player.grade_index < MIN_GRADE:
        return None
    if len(player.mandates) + len(player.mandate_offers) >= MAX_ACTIVE + 1:
        return None
    if rng.random() > OFFER_PROB * tracks.perk(player, "mandate_offer_mult"):
        return None
    capital = round(rng.uniform(300_000, 1_200_000) * _scale(player.grade_index), -3)
    horizon = rng.choice([2, 3, 4])
    target = round(rng.uniform(4.0, 7.0) * horizon, 1)     # % cumulé sur l'horizon
    max_beta = round(rng.choice([1.0, 1.15, 1.3, 1.5]), 2)
    fee_pct = rng.uniform(0.010, 0.025)
    offer = {
        "id": player.next_mandate_id,
        "client": rng.choice(CLIENTS),
        "capital": capital,
        "target_pct": target,
        "horizon": horizon,
        "max_beta": max_beta,
        "reward_cash": round(capital * fee_pct * tracks.perk(player, "mandate_reward_mult"), 2),
        "reward_rep": rng.randint(6, 11),
        "penalty_rep": rng.randint(4, 8),
    }
    player.next_mandate_id += 1
    player.mandate_offers.append(offer)
    return offer


def accept(player, mandate_id, market):
    """Accepte une offre : la déplace en mandat actif avec un snapshot de départ."""
    from core import portfolio
    offer = next((o for o in player.mandate_offers if o["id"] == mandate_id), None)
    if offer is None:
        return None
    if len(player.mandates) >= MAX_ACTIVE:
        return "full"
    player.mandate_offers = [o for o in player.mandate_offers if o["id"] != mandate_id]
    offer = dict(offer)
    offer["start_nw"] = portfolio.net_worth(player, market)
    offer["deadline_q"] = player.quarter + offer["horizon"]
    player.mandates.append(offer)
    return offer


def decline(player, mandate_id):
    before = len(player.mandate_offers)
    player.mandate_offers = [o for o in player.mandate_offers if o["id"] != mandate_id]
    return len(player.mandate_offers) < before


def progress(player, market, m):
    """Retourne (croissance_%, bêta_courant) d'un mandat actif."""
    from core import portfolio
    nw = portfolio.net_worth(player, market)
    growth = (nw / m["start_nw"] - 1) * 100 if m.get("start_nw") else 0.0
    return growth, portfolio.portfolio_beta(player, market)


MAX_HISTORY = 12   # nb de postmortems conservés pour affichage (scene_mandates)


def failure_reason(m, growth, beta):
    """Construit un message d'échec SPÉCIFIQUE (chiffré) plutôt qu'un « Échoué » générique.
    Un mandat peut échouer sur l'un des deux critères, ou les deux à la fois."""
    miss_target = growth < m["target_pct"]
    miss_risk = beta > m["max_beta"] + 0.01
    parts = []
    if miss_target:
        parts.append(f"Rendement cible non atteint : {growth:+.1f}% vs objectif "
                      f"+{m['target_pct']:.1f}%")
    if miss_risk:
        parts.append(f"Risque dépassé : bêta {beta:.2f} vs limite {m['max_beta']:.2f}")
    if not parts:
        parts.append("Échoué")
    return " · ".join(parts)


def evaluate_due(player, market):
    """Évalue les mandats arrivés à échéance (au changement de trimestre).
    Applique récompenses/pénalités. Retourne la liste des résultats (chacun
    augmenté d'un champ `reason` pour le postmortem affiché dans l'UI)."""
    from core import career
    results = []
    still = []
    for m in player.mandates:
        if player.quarter < m["deadline_q"]:
            still.append(m)
            continue
        growth, beta = progress(player, market, m)
        ok = growth >= m["target_pct"] and beta <= m["max_beta"] + 0.01
        if ok:
            player.adjust_cash(m["reward_cash"])
            player.adjust_reputation(m["reward_rep"])
            player.flags["mandates_won"] = player.flags.get("mandates_won", 0) + 1
            reason = f"Objectif atteint : {growth:+.1f}% (cible +{m['target_pct']:.1f}%), " \
                     f"bêta {beta:.2f} sous la limite {m['max_beta']:.2f}."
            career.log(player, "deal", f"Mandat {m['client']} réussi (+{growth:.1f}%)")
        else:
            player.adjust_reputation(-m["penalty_rep"])
            reason = failure_reason(m, growth, beta)
            career.log(player, "crisis", f"Mandat {m['client']} échoué ({reason})")
        result = {"mandate": m, "ok": ok, "growth": growth, "beta": beta, "reason": reason,
                  "client": m["client"], "target_pct": m["target_pct"], "max_beta": m["max_beta"],
                  "reward_cash": m["reward_cash"], "reward_rep": m["reward_rep"],
                  "penalty_rep": m["penalty_rep"], "day": player.day, "quarter": player.quarter}
        results.append(result)
        player.mandate_history.append(result)
        if len(player.mandate_history) > MAX_HISTORY:
            player.mandate_history.pop(0)
    player.mandates = still
    return results
