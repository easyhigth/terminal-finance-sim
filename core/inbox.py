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

from core import crashlog
from data.inbox_en import _SENS_EN, INBOX_EN

MAX_INBOX = 40

_MANAGERS = {
    "Portfolio": "S. Brandt (Manager)", "M&A": "R. Mornay (Manager)",
    "Risk": "L. Ortega (Manager)", "Quant": "K. Sato (Manager)",
    "Advisory": "I. Cole (Manager)", "General": "M. Sterling (Manager)",
}


def manager_name(player):
    return _MANAGERS.get(player.track, _MANAGERS["General"])


def _tpl(msg_id):
    """Renvoie le modèle (sender/subject/body) localisé pour msg_id, ou {} si absent."""
    from core.i18n import get_lang
    if get_lang() == "en":
        return INBOX_EN.get(msg_id, {})
    return {}


def push(player, kind, sender, subject, body):
    """Empile un message dans la boîte de réception."""
    msg = {"id": player.next_msg_id, "day": player.day, "kind": kind,
           "sender": sender, "subject": subject, "body": body, "read": False}
    player.next_msg_id += 1
    player.inbox.append(msg)
    if len(player.inbox) > MAX_INBOX:
        player.inbox.pop(0)
    # Son de notification (sauf pour les messages système)
    if kind not in ("system",):
        try:
            from core import audio
            audio.play("message")
        except Exception:
            crashlog.swallowed("core.inbox")
    return msg


def unread_count(player):
    return sum(1 for m in player.inbox if not m.get("read"))


# ---------------------------------------------------------------------------
# Déclencheurs contextuels
# ---------------------------------------------------------------------------
def on_promotion(player):
    e = _tpl("promotion")
    push(player, "manager", manager_name(player),
         e.get("subject", "Bravo pour votre promotion"),
         e.get("body", "{name}, votre passage au grade {grade} est mérité. "
               "De nouvelles responsabilités vous attendent — ne décevez pas le comité.")
         .format(name=player.name, grade=player.grade))
    if player.grade_index >= 6:
        e = _tpl("promotion_package")
        push(player, "hr", e.get("sender", "RH"),
             e.get("subject", "Nouveau package"),
             e.get("body", "Votre accès aux mandats stratégiques et aux deals premium "
                   "est activé. Le desk compte sur vous."))


def on_quarter(player, report):
    if not report or not report.get("total"):
        return
    done, total = report["done"], report["total"]
    if done == total:
        e = _tpl("quarter_all")
        push(player, "hr", e.get("sender", "RH"),
             e.get("subject", "Bonus trimestriel exceptionnel"),
             e.get("body", "Tous vos objectifs du trimestre sont atteints ({done}/{total}). "
                   "Le comité salue la performance : bonus et visibilité accrue.")
             .format(done=done, total=total))
    elif done == 0:
        e = _tpl("quarter_none")
        push(player, "manager", manager_name(player),
             e.get("subject", "Trimestre décevant"),
             e.get("body", "Aucun objectif atteint ce trimestre. Le comité surveille vos "
                   "résultats. Ressaisissez-vous : missions, deals, gestion du book."))
    else:
        e = _tpl("quarter_partial")
        push(player, "manager", manager_name(player),
             e.get("subject", "Revue trimestrielle"),
             e.get("body", "{done}/{total} objectifs atteints. Correct, mais le comité "
                   "attend mieux pour valider une progression.")
             .format(done=done, total=total))


def on_crisis(player, name, kind):
    if kind == "good":
        e = _tpl("crisis_good")
        push(player, "desk", e.get("sender", "Desk"),
             e.get("subject", "Opportunité : {name}").format(name=name),
             e.get("body", "Le marché s'emballe favorablement. Le desk recommande "
                   "d'évaluer les positions à renforcer — mais gare aux retournements."))
    else:
        e = _tpl("crisis_bad")
        push(player, "manager", manager_name(player),
             e.get("subject", "Alerte marché : {name}").format(name=name),
             e.get("body", "Le marché décroche. Gardez la tête froide : vérifiez votre "
                   "exposition (bêta), votre liquidité et vos couvertures. On compte sur "
                   "votre sang-froid."))


def on_deal_sniped(player, deal, rival_name):
    e = _tpl("deal_sniped")
    push(player, "client",
         e.get("sender", "Client — {title}").format(title=deal["title"]),
         e.get("subject", "Mandat confié ailleurs"),
         e.get("body", "Faute de réponse de votre part, nous avons confié « {title} » à "
               "{rival_name}. Soyez plus réactif la prochaine fois.")
         .format(title=deal["title"], rival_name=rival_name))


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
        e = _tpl("compliance_beta")
        return push(player, "compliance", e.get("sender", "Conformité"),
                    e.get("subject", "Exposition de marché élevée"),
                    e.get("body", "Votre portefeuille affiche un bêta de {beta:.2f}. En cas "
                          "de retournement, les pertes seraient amplifiées. Envisagez HEDGE.")
                    .format(beta=beta))
    if top > 0.55:
        sector = max(alloc, key=alloc.get)
        player.flags["compliance_day"] = player.day
        e = _tpl("compliance_concentration")
        return push(player, "compliance", e.get("sender", "Conformité"),
                    e.get("subject", "Concentration sectorielle"),
                    e.get("body", "{top:.0f}% du book est sur le secteur {sector}. La "
                          "diversification est insuffisante au regard de nos limites "
                          "internes (REBALANCE).")
                    .format(top=top * 100, sector=sector))
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
        from core.i18n import get_lang
        sens = "bondit" if best[1] > 0 else "recule"
        if get_lang() == "en":
            sens = _SENS_EN.get(sens, sens)
        e = _tpl("periodic_brief")
        subject = e.get("subject", "Brief : {index_name} {sens}").format(
            index_name=best[0], sens=sens)
        body = e.get("body", "Le {index_name} {sens} de {chg:+.2f}% sur la séance. "
              "Réunion de desk pour ajuster les vues. Restez attentif aux flux.").format(
            index_name=best[0], sens=sens, chg=best[1])
        return push(player, "desk", e.get("sender", "Desk"), subject, body)
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
