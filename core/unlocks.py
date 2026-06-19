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
    "options": 6,    # options sur actions individuelles (calls/puts)
    "ipo": 4,        # souscription aux introductions en bourse
    "fx": 5,         # desk FX (spot + forward sur devises)
    "calendar": 2,   # calendrier macro (paris sur évènements programmés)
    "team": 6,       # recrutement d'analystes juniors (équipe)
    "alm": 1,        # desk ALM (sandbox actif-passif, lecture/simulation seule)
    "risk": 1,       # module risk (VaR/stress sur exposition de référence, sandbox)
    "quant": 1,      # module quant (pricing d'options, sandbox)
    "credit": 6,     # titrisation : tranches de pool de prêts (cash réellement investi)
    "structured": 6,  # produits structurés (cash réellement investi)
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
    "options": "Options sur actions (OPTIONS)",
    "ipo": "Souscription aux IPO (IPO)",
    "fx": "Desk FX (spot & forward) (FX)",
    "calendar": "Calendrier macro (MACRO)",
    "team": "Équipe d'analystes juniors (TEAM)",
    "alm": "Desk ALM bancaire (ALM)",
    "risk": "Module risque / VaR (RISK)",
    "quant": "Module quant / pricing d'options (QUANT)",
    "credit": "Titrisation / tranches de crédit (CREDIT)",
    "structured": "Produits structurés (STRUCT)",
}

# fonctionnalité -> id de tutoriel (data/tutorials.py) à proposer automatiquement
# au déblocage (toutes les fonctionnalités n'ont pas de tutoriel dédié).
FEATURE_TUTORIAL = {
    "trade": "buy_sell",
    "hedge": "hedge",
    "leverage": "short",
    "ma": "ma",
    "options": "options",
    "ipo": "ipo",
    "fx": "fx",
    "calendar": "calendar",
    "team": "team",
    "alm": "alm",
    "risk": "risk",
    "quant": "quant",
    "credit": "credit",
    "structured": "structured",
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
    "OPTIONS": "options", "OPTION": "options",
    "IPO": "ipo", "IPOS": "ipo",
    "FX": "fx",
    "AGENDA": "calendar", "PRONOS": "calendar",
    "TEAM": "team", "EQUIPE": "team",
    "ALM": "alm", "BANKING": "alm",
    "RISK": "risk",
    "QUANT": "quant",
    "CREDIT": "credit", "TITRISATION": "credit", "ABS": "credit", "CLO": "credit",
    "STRUCT": "structured", "STRUCTURED": "structured", "STRUCTURES": "structured",
}


VETERAN_HEADSTART = 2   # grades d'avance sur les paliers pour un profil "vétéran"


def required_grade(feature):
    return UNLOCKS.get(feature, 0)


def effective_required_grade(player, feature):
    """Grade minimal requis, raccourci pour un profil vétéran (déjà allé loin
    dans une partie antérieure) : il rouvre la complexité plus vite."""
    g = required_grade(feature)
    if player.flags.get("veteran"):
        g = max(0, g - VETERAN_HEADSTART)
    return g


def unlocked(player, feature):
    return player.grade_index >= effective_required_grade(player, feature)


def cmd_unlocked(player, cmd):
    """Vrai si la commande (token) est autorisée au grade courant."""
    feat = CMD_FEATURE.get(cmd)
    return feat is None or unlocked(player, feat)


def feature_label(feature):
    return LABELS.get(feature, feature)


def next_unlock(player):
    """Prochaine fonctionnalité à débloquer (label, grade) ou None si tout est ouvert."""
    best = None
    for feat in UNLOCKS:
        g = effective_required_grade(player, feat)
        if g > player.grade_index and (best is None or g < best[1]):
            best = (LABELS[feat], g)
    return best
