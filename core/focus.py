"""
focus.py — FOCUS DU TRIMESTRE : où passez-vous vos journées ? (logique pure)

Le métier réel est un arbitrage de temps ; le jeu ne le simulait pas — on
pouvait tout faire à fond à chaque pas. Le focus introduit l'arbitrage sans
refondre la boucle : le joueur choisit UN axe (dans l'écran Carrière), qui
donne un bonus FRANC sur cet axe et un léger malus sur les autres. Changer de
focus est gratuit mais limité à une fois par trimestre (on ne réorganise pas
son agenda tous les matins).

État : `player.flags["focus"]` (clé de FOCUS) et
`player.flags["focus_quarter"]` (trimestre du dernier changement).
Consommé par : portfolio._commission (trading), mandates.maybe_offer /
deals.maybe_generate (clients), missions.compute_rewards (recherche), et le
hook de pas "focus_network" (réseau : réputation passive).
"""
from core.i18n import get_lang


def _L(fr, en):
    return en if get_lang() == "en" else fr


# perk -> (valeur si focalisé, valeur sinon). "1.0 sinon" = pas de malus
# croisé pour ce perk ; les malus croisés sont volontairement LÉGERS.
FOCUS = {
    "trading": {
        "label": ("Trading", "Trading"),
        "desc": ("Commissions d'exécution -15 %. Moins présent pour les "
                 "clients (offres un peu plus rares).",
                 "Execution commissions -15%. Less available for clients "
                 "(slightly rarer offers)."),
        "perks": {"commission_mult": 0.85, "offer_mult": 0.95},
    },
    "clients": {
        "label": ("Clients", "Clients"),
        "desc": ("Offres de deals et mandats nettement plus fréquentes. "
                 "Moins de temps d'écran (commissions +5 %).",
                 "Deal and mandate offers noticeably more frequent. Less "
                 "screen time (commissions +5%)."),
        "perks": {"offer_mult": 1.35, "commission_mult": 1.05},
    },
    "recherche": {
        "label": ("Recherche", "Research"),
        "desc": ("Missions mieux valorisées (+25 % de réputation). Offres "
                 "clients un peu plus rares.",
                 "Missions better valued (+25% reputation). Client offers "
                 "slightly rarer."),
        "perks": {"mission_rep_mult": 1.25, "offer_mult": 0.95},
    },
    "reseau": {
        "label": ("Réseau", "Network"),
        "desc": ("Réputation passive (+0.12/tour) : conférences, déjeuners, "
                 "visibilité. Commissions +5 %.",
                 "Passive reputation (+0.12/step): conferences, lunches, "
                 "visibility. Commissions +5%."),
        "perks": {"rep_per_step": 0.12, "commission_mult": 1.05},
    },
}

_DEFAULTS = {"commission_mult": 1.0, "offer_mult": 1.0,
             "mission_rep_mult": 1.0, "rep_per_step": 0.0}


def current(player):
    """Clé du focus actif, ou None (aucun choisi : tout à 1.0, comme avant)."""
    key = player.flags.get("focus")
    return key if key in FOCUS else None


def label(key):
    f = FOCUS.get(key)
    return _L(*f["label"]) if f else _L("Aucun", "None")


def desc(key):
    f = FOCUS.get(key)
    return _L(*f["desc"]) if f else ""


def perk(player, name):
    """Valeur du perk `name` selon le focus actif (défaut neutre sinon) —
    même convention que tracks.perk/firms.perk."""
    key = current(player)
    if key is None:
        return _DEFAULTS.get(name, 1.0)
    return FOCUS[key]["perks"].get(name, _DEFAULTS.get(name, 1.0))


def can_change(player):
    """Un changement de focus par trimestre (le premier choix est libre)."""
    return player.flags.get("focus_quarter") != player.quarter


def set_focus(player, key):
    """Choisit le focus du trimestre. Retourne {"ok": bool, "reason": str}."""
    if key is not None and key not in FOCUS:
        return {"ok": False, "reason": "key"}
    if not can_change(player):
        return {"ok": False, "reason": "quarter"}
    if key is None:
        player.flags.pop("focus", None)
    else:
        player.flags["focus"] = key
    player.flags["focus_quarter"] = player.quarter
    return {"ok": True}
