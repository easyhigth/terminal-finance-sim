"""
unlocks.py — Déblocage progressif des actions selon le grade (logique pure).

Au début (stagiaire), le joueur se concentre sur l'essentiel : apprendre,
faire ses missions, analyser le marché (en lecture seule). Les actions à
conséquence et techniques se débloquent ensuite, par paliers de grade — pour
une montée en complexité maîtrisée.
"""

# fonctionnalité -> grade minimal requis
UNLOCKS = {
    "analyst": 1,    # watchlist, alertes, comparaison, valeur relative, recherche
    "track": 2,      # choisir une voie de spécialisation
    "deals": 2,      # traiter des deals
    "trade": 4,      # investir : acheter / vendre / allouer / rééquilibrer
    "pitch": 4,      # démarcher un client pour un mandat
    "hedge": 6,      # couverture du portefeuille (réduction d'exposition)
    "leverage": 6,   # levier & vente à découvert (short)
    "mandates": 6,   # mandats clients
    "ma": 4,         # M&A : acquisition de cibles privées (LBO réel)
}

LABELS = {
    "analyst": "Outils d'analyse (watchlist, alertes, recherche, RV)",
    "track": "Choix d'une voie de spécialisation",
    "deals": "Traiter des deals",
    "trade": "Investir (acheter / vendre / allouer)",
    "pitch": "Démarcher des mandats (PITCH)",
    "hedge": "Couverture du portefeuille (HEDGE)",
    "leverage": "Levier & vente à découvert (SHORT/COVER)",
    "mandates": "Mandats clients",
    "ma": "M&A : acquisition de cibles privées",
}

# commande (token majuscule) -> fonctionnalité gated
CMD_FEATURE = {
    "WATCHLIST": "analyst", "WATCH": "analyst", "WL": "analyst",
    "ALERT": "analyst", "ALERTE": "analyst", "ALERTS": "analyst", "ALERTES": "analyst",
    "COMPARE": "analyst", "CMP": "analyst",
    "RV": "analyst", "PEERS": "analyst", "COMPS": "analyst",
    "RESEARCH": "analyst", "RECHERCHE": "analyst",
    "TRACK": "track", "VOIE": "track",
    "DEALS": "deals", "DEAL": "deals",
    "BUY": "trade", "ACHETER": "trade", "SELL": "trade", "VENDRE": "trade",
    "BUYETF": "trade", "SELLETF": "trade",
    "ALLOCATE": "trade", "ALLOC": "trade", "REBALANCE": "trade", "REBAL": "trade",
    "MARGIN": "trade", "MARGE": "trade",
    "SHORT": "leverage", "VAD": "leverage", "COVER": "leverage", "RACHETER": "leverage",
    "PITCH": "pitch",
    "HEDGE": "hedge",
    "PROTECT": "hedge",
    "MANDATES": "mandates", "MANDATS": "mandates", "MANDATE": "mandates", "MANDAT": "mandates",
    "MA": "ma", "M&A": "ma",
    "SWAP": "trade", "SWAPS": "trade",
}


def unlocked(player, feature):
    return player.grade_index >= UNLOCKS.get(feature, 0)


def cmd_unlocked(player, cmd):
    """Vrai si la commande (token) est autorisée au grade courant."""
    feat = CMD_FEATURE.get(cmd)
    return feat is None or unlocked(player, feat)


def required_grade(feature):
    return UNLOCKS.get(feature, 0)


def feature_label(feature):
    return LABELS.get(feature, feature)


def next_unlock(player):
    """Prochaine fonctionnalité à débloquer (label, grade) ou None si tout est ouvert."""
    best = None
    for feat, g in UNLOCKS.items():
        if g > player.grade_index and (best is None or g < best[1]):
            best = (LABELS[feat], g)
    return best
