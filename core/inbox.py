"""
inbox.py — Messagerie « monde vivant » (logique pure, sans pygame).

Le joueur reçoit des emails contextuels qui donnent vie à la firme :
  - manager    : feedback hiérarchique, félicitations, mises en garde
  - client     : demandes, remerciements, pression
  - compliance : alertes conformité (risque, concentration)
  - desk       : briefs d'équipe, commentaires de marché
  - hr         : bonus, événements de carrière

Les messages sont déclenchés par le contexte (promotion, trimestre, crise,
état du portefeuille) ou périodiquement. Aucune dépendance pygame.
"""
import random

MAX_INBOX = 40

_MANAGERS = {
    "Portfolio": "S. Brandt (Manager)", "M&A": "R. Mornay (Manager)",
    "Risk": "L. Ortega (Manager)", "Quant": "K. Sato (Manager)",
    "Advisory": "I. Cole (Manager)", "General": "M. Sterling (Manager)",
}


def manager_name(player):
    return _MANAGERS.get(player.track, _MANAGERS["General"])


def push(player, kind, sender, subject, body):
    """Empile un message dans la boîte de réception."""
    msg = {"id": player.next_msg_id, "day": player.day, "kind": kind,
           "sender": sender, "subject": subject, "body": body, "read": False}
    player.next_msg_id += 1
    player.inbox.append(msg)
    if len(player.inbox) > MAX_INBOX:
        player.inbox.pop(0)
    return msg


def unread_count(player):
    return sum(1 for m in player.inbox if not m.get("read"))


# ---------------------------------------------------------------------------
# Déclencheurs contextuels
# ---------------------------------------------------------------------------
def on_promotion(player):
    push(player, "manager", manager_name(player), "Bravo pour votre promotion",
         f"{player.name}, votre passage au grade {player.grade} est mérité. "
         "De nouvelles responsabilités vous attendent — ne décevez pas le comité.")
    if player.grade_index >= 6:
        push(player, "hr", "RH", "Nouveau package",
             "Votre accès aux mandats stratégiques et aux deals premium est activé. "
             "Le desk compte sur vous.")


def on_quarter(player, report):
    if not report or not report.get("total"):
        return
    done, total = report["done"], report["total"]
    if done == total:
        push(player, "hr", "RH", "Bonus trimestriel exceptionnel",
             f"Tous vos objectifs du trimestre sont atteints ({done}/{total}). "
             "Le comité salue la performance : bonus et visibilité accrue.")
    elif done == 0:
        push(player, "manager", manager_name(player), "Trimestre décevant",
             "Aucun objectif atteint ce trimestre. Le comité surveille vos résultats. "
             "Ressaisissez-vous : missions, deals, gestion du book.")
    else:
        push(player, "manager", manager_name(player), "Revue trimestrielle",
             f"{done}/{total} objectifs atteints. Correct, mais le comité attend mieux "
             "pour valider une progression.")


def on_crisis(player, name, kind):
    if kind == "good":
        push(player, "desk", "Desk", f"Opportunité : {name}",
             "Le marché s'emballe favorablement. Le desk recommande d'évaluer les "
             "positions à renforcer — mais gare aux retournements.")
    else:
        push(player, "manager", manager_name(player), f"Alerte marché : {name}",
             "Le marché décroche. Gardez la tête froide : vérifiez votre exposition "
             "(bêta), votre liquidité et vos couvertures. On compte sur votre sang-froid.")


def on_deal_sniped(player, deal, rival_name):
    push(player, "client", f"Client — {deal['title']}", "Mandat confié ailleurs",
         f"Faute de réponse de votre part, nous avons confié « {deal['title']} » à "
         f"{rival_name}. Soyez plus réactif la prochaine fois.")


# ---------------------------------------------------------------------------
# Contrôles et messages périodiques
# ---------------------------------------------------------------------------
COMPLIANCE_COOLDOWN = 45   # jours min entre deux alertes conformité


def _compliance_check(player, market):
    """Alerte conformité si le book est trop risqué/concentré. Renvoie msg ou None.
    Soumise à un délai de carence pour éviter le spam."""
    from core import portfolio
    if not player.portfolio:
        return None
    last = player.flags.get("compliance_day", -9999)
    if player.day - last < COMPLIANCE_COOLDOWN:
        return None
    beta = portfolio.portfolio_beta(player, market)
    alloc = portfolio.allocation_by(player, market, "sector")
    total = sum(alloc.values()) or 1.0
    top = max(alloc.values()) / total if alloc else 0.0
    if beta > 1.35:
        player.flags["compliance_day"] = player.day
        return push(player, "compliance", "Conformité", "Exposition de marché élevée",
                    f"Votre portefeuille affiche un bêta de {beta:.2f}. En cas de "
                    "retournement, les pertes seraient amplifiées. Envisagez HEDGE.")
    if top > 0.55:
        sector = max(alloc, key=alloc.get)
        player.flags["compliance_day"] = player.day
        return push(player, "compliance", "Conformité", "Concentration sectorielle",
                    f"{top*100:.0f}% du book est sur le secteur {sector}. La diversification "
                    "est insuffisante au regard de nos limites internes (REBALANCE).")
    return None


def _periodic(player, market, rng):
    """Message d'ambiance occasionnel (brief desk / commentaire de marché)."""
    # indice le plus marquant du dernier pas
    best = None
    for name, *_ in market.index_defs:
        chg = market.index_change_pct(name)
        if best is None or abs(chg) > abs(best[1]):
            best = (name, chg)
    if best and abs(best[1]) > 0.3:
        sens = "bondit" if best[1] > 0 else "recule"
        return push(player, "desk", "Desk", f"Brief : {best[0]} {sens}",
                    f"Le {best[0]} {sens} de {best[1]:+.2f}% sur la séance. "
                    "Réunion de desk pour ajuster les vues. Restez attentif aux flux.")
    return None


def on_step(player, market, summary, rng=None):
    """Appelé à chaque tour : alertes conformité + message d'ambiance occasionnel.
    Retourne la liste des messages créés ce tour."""
    rng = rng or random
    created = []
    msg = _compliance_check(player, market)
    if msg:
        created.append(msg)
    if rng.random() < 0.35:
        msg = _periodic(player, market, rng)
        if msg:
            created.append(msg)
    return created
