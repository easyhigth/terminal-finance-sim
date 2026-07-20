"""
momentum.py — Séries chaudes / creux de carrière (logique pure, sans pygame).

La performance n'est pas qu'un chiffre : elle a une DYNAMIQUE. Sur la base des
séries de trimestres déjà suivies par core/legacy.py (`profit_streak` : valeur
nette en hausse trimestre après trimestre ; `loss_streak` : l'inverse), le
momentum donne un STATUT lisible et de vrais effets :

  - « en forme » (hot, >= HOT_STREAK trimestres gagnants) : le boss vous fait
    confiance — plus d'offres de mandat, et un filet de réputation chaque
    trimestre ;
  - « passe difficile » (cold, >= COLD_STREAK trimestres perdants) : on vous
    surveille — moins d'offres, et un léger effritement de réputation.

`apply_quarter_effect` est appelé une fois par trimestre écoulé (juste après
les séries de core/legacy), et renvoie un toast (texte, kind) ou None.
"""
from core.i18n import get_lang

HOT_STREAK = 2
COLD_STREAK = 2
HOT_REP_BONUS = 2
COLD_REP_MALUS = 1
HOT_OFFER_MULT = 1.25
COLD_OFFER_MULT = 0.7


def _L(fr, en):
    return en if get_lang() == "en" else fr


def profit_streak(player):
    return int(player.flags.get("profit_streak", 0))


def loss_streak(player):
    return int(player.flags.get("loss_streak", 0))


def status(player):
    """'hot' | 'cold' | 'neutral' — la dynamique de carrière courante."""
    if profit_streak(player) >= HOT_STREAK:
        return "hot"
    if loss_streak(player) >= COLD_STREAK:
        return "cold"
    return "neutral"


def label(player):
    """Libellé du statut de momentum (ou None si neutre)."""
    s = status(player)
    if s == "hot":
        return _L(f"En forme (série de {profit_streak(player)})",
                  f"On a roll (streak of {profit_streak(player)})")
    if s == "cold":
        return _L(f"Passe difficile (série de {loss_streak(player)})",
                  f"Rough patch (streak of {loss_streak(player)})")
    return None


def offer_mult(player):
    """Multiplicateur de fréquence des offres de mandat selon le momentum."""
    s = status(player)
    return HOT_OFFER_MULT if s == "hot" else COLD_OFFER_MULT if s == "cold" else 1.0


def apply_quarter_effect(player):
    """Effet trimestriel du momentum (réputation), à appeler APRÈS la mise à jour
    des séries de core/legacy. Retourne (texte, kind) pour un toast, ou None."""
    s = status(player)
    if s == "hot":
        player.adjust_reputation(HOT_REP_BONUS,
                                 reason="Momentum : série de trimestres gagnants")
        return (_L(f"En forme : +{HOT_REP_BONUS} réputation (le boss vous confie plus)",
                   f"On a roll: +{HOT_REP_BONUS} reputation (the boss trusts you more)"), "good")
    if s == "cold":
        player.adjust_reputation(-COLD_REP_MALUS,
                                 reason="Momentum : passe difficile")
        return (_L(f"Passe difficile : −{COLD_REP_MALUS} réputation (on vous surveille)",
                   f"Rough patch: −{COLD_REP_MALUS} reputation (you're being watched)"), "bad")
    return None
