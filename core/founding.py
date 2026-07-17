"""
founding.py — FONDER SA FIRME : l'acte final de la carrière (logique pure).

Le champ `player.firm_name` dormait depuis le premier jour du projet.
Au grade maximal (Partner / C-Suite), avec un capital suffisant, le joueur
peut fonder sa propre boutique — le deuxième acte que l'endgame n'avait pas :

  - coût d'installation substantiel (bureaux, licences, avocats) ;
  - votre CARNET DE CLIENTS vous suit (confiance +10, capital confié +20 % :
    ils investissaient sur VOTRE nom, pas celui de la banque) ;
  - revenu d'associé-gérant : supplément de salaire fixe permanent ;
  - titre « Fondateur », réputation, journal, réaction du némésis ;
  - le classement des rivaux affiche désormais VOTRE enseigne.

L'ADN de firme (core/firms.py) reste le vôtre : on fonde la maison qu'on a
toujours voulue, avec la culture qu'on s'est forgée. Déclenché depuis
l'écran Carrière (bouton visible au grade max).
"""
from core import config
from core.i18n import get_lang

FOUNDING_COST = 4_000_000.0     # bureaux, licences, garanties réglementaires
FOUNDER_DRAW_PER_STEP = 3_000.0  # revenu d'associé-gérant (salaire fixe)
CLIENT_TRUST_BONUS = 10          # le carnet vous suit
CLIENT_CAPITAL_BONUS = 1.2
REP_BONUS = 12


def _L(fr, en):
    return en if get_lang() == "en" else fr


def founded(player):
    return bool(player.firm_name)


def can_found(player):
    """(ok, raison) — grade max, capital suffisant, pas déjà fondée."""
    if founded(player):
        return False, "founded"
    if player.grade_index < len(config.GRADES) - 1:
        return False, "grade"
    if player.cash < FOUNDING_COST:
        return False, "cash"
    return True, None


def found(player, name):
    """Fonde la firme `name`. Retourne {"ok": bool, "reason": str|None}."""
    ok, reason = can_found(player)
    if not ok:
        return {"ok": False, "reason": reason}
    name = (name or "").strip()
    if not name:
        return {"ok": False, "reason": "name"}
    player.adjust_cash(-FOUNDING_COST, category="evenements")
    player.firm_name = name
    player.flags["founded_day"] = player.day
    player.salary_bonus_per_step = (getattr(player, "salary_bonus_per_step", 0.0)
                                    + FOUNDER_DRAW_PER_STEP)
    title = _L("Fondateur", "Founder")
    if title not in player.titles:
        player.titles.append(title)
    player.adjust_reputation(REP_BONUS, reason=_L(f"Fondation de {name}",
                                                  f"Founding of {name}"))
    # le carnet de clients vous suit : ils investissaient sur votre nom
    from core import clients as _clients
    for c in _clients.active_clients(player):
        c["trust"] = min(100, c["trust"] + CLIENT_TRUST_BONUS)
        c["capital_mult"] = min(_clients.CAPITAL_MULT_MAX,
                                c["capital_mult"] * CLIENT_CAPITAL_BONUS)
    from core import career
    career.log(player, "deal", _L(f"Vous fondez votre firme : {name}",
                                  f"You found your own firm: {name}"))
    from core import inbox as _inbox
    _inbox.push(player, "manager", _L("Direction générale", "Executive board"),
                _L("Une page se tourne", "A page turns"),
                _L(f"Vous quittez la maison pour fonder {name}. Nous perdons un "
                   f"grand professionnel — et gagnons un concurrent redoutable. "
                   f"Bonne route.",
                   f"You are leaving the house to found {name}. We lose a great "
                   f"professional — and gain a formidable competitor. Godspeed."))
    # le némésis réagit toujours
    from core import rivals as _rivals
    r = _rivals.personal_nemesis(player)
    if r is not None:
        _inbox.push(player, "rival", r["name"],
                    _L("Alors comme ça, on s'installe", "So you're setting up shop"),
                    _L(f"{name}. Joli nom pour une future cible d'acquisition. "
                       f"Le marché est petit, on se recroisera — d'égal à égal "
                       f"cette fois. Ne me décevez pas. — {r['name']}",
                       f"{name}. Nice name for a future acquisition target. The "
                       f"market is small, we'll meet again — as equals this "
                       f"time. Don't disappoint me. — {r['name']}"))
    return {"ok": True, "reason": None}
