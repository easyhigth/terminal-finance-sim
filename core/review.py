"""
review.py — Revue de performance annuelle (négociation de bonus en cash).

Tous les `REVIEW_PERIOD_QUARTERS` trimestres, le joueur a un entretien avec son
manager : un résumé de performance est présenté (réputation, missions du grade,
P&L réalisé récent) accompagné d'un « bonus standard » de référence proportionnel
au grade. Le joueur choisit alors comment négocier :

  - "accept"        : encaisse le bonus standard, aucun risque, légère hausse de
                       réputation (gratitude envers le manager).
  - "negotiate_up"   : tente d'obtenir 1.5x à 2x le bonus standard. Probabilité de
                       succès dépendant de la performance (réputation, missions du
                       grade), tirée via `random.random()` — événement de gameplay
                       ponctuel non seedé, comme `core.mandates.maybe_offer`. En cas
                       d'échec, un bonus réduit est quand même versé (pas de bonus
                       nul) mais la réputation baisse (déception du manager).
  - "ask_fixed"      : renonce au bonus ponctuel pour une hausse de salaire FIXE et
                       permanente, sans risque mais d'un montant plus modeste.
                       Incrémente `player.salary_bonus_per_step`. Ce champ n'est
                       PAS automatiquement intégré à `PlayerState.salary_per_step()`
                       ici (fonction partagée, non modifiée par ce module) :
                       l'orchestrateur (`core/game_state.py: advance_step` ou
                       `salary_per_step`) décidera de le créditer, soit en l'ajoutant
                       au calcul du salaire, soit en le créditant lui-même par tour.

Logique pure, sans pygame — testable headless.
"""
import random

REVIEW_PERIOD_QUARTERS = 4   # une revue tous les 4 trimestres (~1 an)

# ---------------------------------------------------------------------------
# Déclenchement
# ---------------------------------------------------------------------------
def maybe_trigger(player, quarter_changed):
    """Déclenche éventuellement une revue de performance.

    Appelée chaque tour par l'orchestrateur avec `quarter_changed` (vrai quand le
    trimestre vient de changer, cf. `summary["quarter_changed"]` de
    `GameState.advance_step`). Si la période est écoulée et qu'aucune revue n'est
    déjà en attente, construit l'offre, l'assigne à `player.pending_review` et la
    retourne. Sinon retourne None.
    """
    if not quarter_changed:
        return None
    if player.pending_review is not None:
        return None
    if player.quarter - player.last_review_quarter < REVIEW_PERIOD_QUARTERS:
        return None

    base = 2_000 + player.grade_index * 3_000
    offer = {
        "quarter": player.quarter,
        "reputation": player.reputation,
        "grade_missions": player.grade_missions,
        "realized_pnl": getattr(player, "realized_pnl", 0.0) or 0.0,
        "standard_bonus": base,
    }
    player.pending_review = offer
    return offer


def has_pending(player):
    """Utilitaire pour l'orchestrateur : une revue attend-elle une réponse ?"""
    return bool(player.pending_review)


# ---------------------------------------------------------------------------
# Résolution
# ---------------------------------------------------------------------------
def negotiate(player, choice):
    """Résout la revue en attente selon `choice` ∈
    {"accept", "negotiate_up", "ask_fixed"}.

    Retourne un dict résultat :
      {ok, choice, bonus_paid, rep_delta, message}
    ou {"ok": False, "reason": "no_pending"} si aucune revue n'est en attente.
    """
    offer = player.pending_review
    if offer is None:
        return {"ok": False, "reason": "no_pending"}

    base = offer["standard_bonus"]

    if choice == "accept":
        bonus_paid = base
        rep_delta = random.choice([1, 2])
        player.adjust_cash(bonus_paid)
        player.adjust_reputation(rep_delta)
        message = (f"Vous acceptez le bonus standard de {bonus_paid:,.0f}. "
                   "Votre manager apprécie votre attitude constructive.")
        result = {"ok": True, "choice": choice, "bonus_paid": bonus_paid,
                  "rep_delta": rep_delta, "message": message}

    elif choice == "negotiate_up":
        success_prob = (0.3 + min(0.5, player.reputation / 200)
                         + min(0.2, player.grade_missions * 0.05))
        success = random.random() < success_prob
        if success:
            multiplier = random.uniform(1.5, 2.0)
            bonus_paid = base * multiplier
            rep_delta = random.choice([1, 2, 3])
            message = (f"Négociation réussie ! Vous obtenez {bonus_paid:,.0f} "
                       f"({multiplier:.1f}x le bonus standard).")
        else:
            bonus_paid = base * 0.7
            rep_delta = -random.choice([1, 2, 3])
            message = (f"La négociation échoue. Votre manager, déçu de votre "
                       f"insistance, ne vous verse que {bonus_paid:,.0f}.")
        player.adjust_cash(bonus_paid)
        player.adjust_reputation(rep_delta)
        result = {"ok": success, "choice": choice, "bonus_paid": bonus_paid,
                  "rep_delta": rep_delta, "message": message}

    elif choice == "ask_fixed":
        increment = 200 * (1 + player.grade_index * 0.1)
        player.salary_bonus_per_step += increment
        rep_delta = 0
        message = (f"Vous renoncez au bonus ponctuel pour une hausse de salaire "
                   f"fixe de {increment:,.0f} par tour, désormais acquise.")
        result = {"ok": True, "choice": choice, "bonus_paid": 0.0,
                  "rep_delta": rep_delta, "message": message}

    else:
        return {"ok": False, "reason": "invalid_choice"}

    player.last_review_quarter = player.quarter
    player.pending_review = None
    return result
