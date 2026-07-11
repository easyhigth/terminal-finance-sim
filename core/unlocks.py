"""
unlocks.py — Déblocage progressif des actions selon le grade (logique pure).

Au début (stagiaire), le joueur se concentre sur l'essentiel : apprendre,
faire ses missions, analyser le marché (en lecture seule). Les actions à
conséquence et techniques se débloquent ensuite, par paliers de grade — pour
une montée en complexité maîtrisée.
"""
from core import config

# fonctionnalité -> grade minimal requis.
#
# Étalé sur les grades 1 à 9 à raison de 2-3 déblocages par grade (au lieu de
# grosses vagues concentrées sur 2-3 paliers, cf. l'historique de ce fichier
# avant ce rééquilibrage) : à chaque promotion, le joueur retrouve quelque
# chose de nouveau à essayer, plutôt que rien pendant plusieurs grades puis
# neuf fonctionnalités d'un coup. Les grades 10-11 (Managing Director/Partner)
# ne débloquent plus rien de nouveau : à ce stade tout l'outillage est déjà
# ouvert, la fin de carrière est affaire de score et de maîtrise, pas de
# contenu supplémentaire. Grade requis synchronisé avec les constantes
# `MIN_GRADE` dédiées de `core/ipo.py`, `core/macrocal.py` et
# `core/mandates.py` (mécanique réelle, indépendante de ce dict mais qui doit
# rester alignée dessus — sinon une commande semblerait débloquée dans l'UI
# tout en étant encore refusée par le module).
UNLOCKS = {
    # ouvert dès l'arrivée (Intern) : ce sont des outils 100% lecture/analyse,
    # sans impact économique (pas d'argent en jeu) — de quoi avoir une vraie
    # activité (watchlist, alertes, recherche) avant le déblocage du trading.
    "analyst": 0,    # watchlist, alertes, comparaison, valeur relative, recherche
    "alm": 0,        # desk ALM (sandbox actif-passif, lecture/simulation seule)
    "risk": 0,       # module risk (VaR/stress sur exposition de référence, sandbox)
    "quant": 0,      # module quant (pricing d'options, sandbox)
    # grade 1 (Junior Analyst) : choisir sa voie et commencer à investir.
    "track": 1,      # choisir une voie de spécialisation
    "deals": 1,      # traiter des deals
    "trade": 1,      # investir : acheter / vendre / allouer / rééquilibrer
    # grade 2 (Analyst) : premiers outils complémentaires au trading.
    "calendar": 2,   # calendrier macro (paris sur évènements programmés)
    "ipo": 2,        # souscription aux introductions en bourse
    # grade 3 (Senior Analyst) : premier vrai jalon M&A/advisory.
    "pitch": 3,      # démarcher un client pour un mandat
    "ma": 3,         # M&A : acquisition de cibles privées (LBO réel)
    "footballfield": 3,   # Football Field (valorisation multi-méthodes) — affinité M&A
    # grade 4 (Associate) : outils d'analyse de niveau 2.
    "valuation": 4,     # Desk Valorisation (DCF/SML/pont IRR) — affinité M&A
    "attribution": 4,   # Attribution de performance (Brinson/facteurs) — affinité Portfolio
    # grade 5 (Senior Associate) : vague d'outils Portfolio.
    "backtester": 5,    # Backtesteur de stratégies — affinité Portfolio
    "pnlexplain": 5,    # P&L Explain (décomposition du patrimoine) — affinité Portfolio
    "strategicalloc": 5,  # Allocation stratégique multi-actifs — affinité Portfolio
    # grade 6 (Vice President) : desks de marché avancés.
    "fx": 6,         # desk FX (spot + forward sur devises)
    "hedge": 6,      # couverture du portefeuille (réduction d'exposition)
    # grade 7 (Senior VP) : levier et mandats clients.
    "leverage": 7,   # levier & vente à découvert (short)
    "mandates": 7,   # mandats clients
    # grade 8 (Director) : outils les plus avancés/spécialisés.
    "pitchbook": 8,       # Pitch Book (démarchage actif de mandats) — affinité Advisory
    "options": 8,    # options sur actions individuelles (calls/puts)
    "team": 8,       # recrutement d'analystes juniors (équipe)
    # grade 9 (Executive Director) : produits de crédit structurés.
    "credit": 9,     # titrisation : tranches de pool de prêts (cash réellement investi)
    "structured": 9,  # produits structurés (cash réellement investi)
    "creditdesk": 9,    # Desk Crédit (Merton/waterfall/CDS/convertibles) — affinité M&A
}

def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


_LABELS_RAW = {
    "analyst": ("Outils d'analyse (watchlist, alertes, recherche, RV)",
                "Analysis tools (watchlist, alerts, research, comps)"),
    "track": ("Choix d'une voie de spécialisation", "Choosing a specialization track"),
    "deals": ("Traiter des deals", "Handling deals"),
    "trade": ("Investir (acheter / vendre / allouer)", "Investing (buy / sell / allocate)"),
    "pitch": ("Démarcher des mandats (PITCH)", "Pitching for mandates (PITCH)"),
    "hedge": ("Couverture du portefeuille (HEDGE)", "Portfolio hedging (HEDGE)"),
    "leverage": ("Levier & vente à découvert (SHORT/COVER)", "Leverage & short selling (SHORT/COVER)"),
    "mandates": ("Mandats clients", "Client mandates"),
    "ma": ("M&A : acquisition de cibles privées", "M&A: acquiring private targets"),
    "options": ("Options sur actions (OPTIONS)", "Stock options (OPTIONS)"),
    "ipo": ("Souscription aux IPO (IPO)", "Subscribing to IPOs (IPO)"),
    "fx": ("Desk FX (spot & forward) (FX)", "FX desk (spot & forward) (FX)"),
    "calendar": ("Calendrier macro (MACRO)", "Macro calendar (MACRO)"),
    "team": ("Équipe d'analystes juniors (TEAM)", "Junior analyst team (TEAM)"),
    "alm": ("Desk ALM bancaire (ALM)", "Bank ALM desk (ALM)"),
    "risk": ("Module risque / VaR (RISK)", "Risk / VaR module (RISK)"),
    "quant": ("Module quant / pricing d'options (QUANT)", "Quant / options pricing module (QUANT)"),
    "credit": ("Titrisation / tranches de crédit (CREDIT)", "Securitization / credit tranches (CREDIT)"),
    "structured": ("Produits structurés (STRUCT)", "Structured products (STRUCT)"),
    "valuation": ("Desk Valorisation (DCF/SML/LBO)", "Valuation desk (DCF/SML/LBO)"),
    "creditdesk": ("Desk Crédit (Merton/CDS/convertibles)", "Credit desk (Merton/CDS/convertibles)"),
    "attribution": ("Attribution de performance (Brinson)", "Performance attribution (Brinson)"),
    "backtester": ("Backtesteur de stratégies", "Strategy backtester"),
    "pnlexplain": ("P&L Explain (décomposition du patrimoine)", "P&L Explain (net worth breakdown)"),
    "footballfield": ("Football Field (valorisation M&A)", "Football Field (M&A valuation)"),
    "pitchbook": ("Pitch Book (démarchage de mandats)", "Pitch Book (mandate pitching)"),
    "strategicalloc": ("Allocation stratégique multi-actifs", "Strategic multi-asset allocation"),
}
LABELS = {k: v[0] for k, v in _LABELS_RAW.items()}

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
    "valuation": "valuation",
    "creditdesk": "creditdesk",
    "attribution": "attribution",
    "backtester": "backtester",
    "pnlexplain": "pnlexplain",
    "footballfield": "footballfield",
    "pitchbook": "pitchbook",
    "strategicalloc": "strategicalloc",
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

# Contenu exclusif par voie : une fois la spécialisation choisie, certains
# modules « historiquement » associés à une AUTRE voie deviennent une vraie
# porte fermée (pas juste un malus) jusqu'au grade max — où toutes les voies
# redeviennent accessibles librement, en cohérence avec le déverrouillage de
# la reconversion libre (core/tracks.py::TOP_GRADE_INDEX).
TRACK_AFFINITY = {
    "ma": "M&A",
    "hedge": "Risk",
    "options": "Quant",
    "mandates": "Advisory",
    "structured": "Portfolio",
    "valuation": "M&A",
    "creditdesk": "M&A",
    "attribution": "Portfolio",
    "backtester": "Portfolio",
    "pnlexplain": "Portfolio",
    "footballfield": "M&A",
    "pitchbook": "Advisory",
    "strategicalloc": "Portfolio",
}
TRACK_LOCK_GRADE = len(config.GRADES) - 1


def required_grade(feature):
    return UNLOCKS.get(feature, 0)


def effective_required_grade(player, feature):
    """Grade minimal requis, raccourci pour un profil vétéran (déjà allé loin
    dans une partie antérieure) : il rouvre la complexité plus vite. Un
    module à affinité de voie reste verrouillé jusqu'au grade max si le
    joueur a choisi une AUTRE voie — un vétéran ne contourne pas ce verrou,
    qui dépend du choix de voie, pas de l'expérience générale."""
    g = required_grade(feature)
    if player.flags.get("veteran"):
        g = max(0, g - VETERAN_HEADSTART)
    affinity = TRACK_AFFINITY.get(feature)
    track = getattr(player, "track", "General")
    if affinity and track not in (affinity, "General"):
        g = max(g, TRACK_LOCK_GRADE)
    return g


def track_lock_note(player, feature):
    """Phrase explicative (FR/EN) si le module est verrouillé pour cause de
    voie incompatible (plutôt que de simple grade insuffisant), sinon None."""
    affinity = TRACK_AFFINITY.get(feature)
    track = getattr(player, "track", "General")
    if not affinity or track in (affinity, "General"):
        return None
    return _L(
        f"     réservé à la voie {affinity} (la vôtre : {track}) — accessible "
        f"librement au grade {config.GRADES[TRACK_LOCK_GRADE]}.",
        f"     reserved for the {affinity} track (yours: {track}) — freely "
        f"accessible at grade {config.GRADES[TRACK_LOCK_GRADE]}.",
    )


def unlocked(player, feature):
    return player.grade_index >= effective_required_grade(player, feature)


def cmd_unlocked(player, cmd):
    """Vrai si la commande (token) est autorisée au grade courant."""
    feat = CMD_FEATURE.get(cmd)
    return feat is None or unlocked(player, feat)


def feature_label(feature):
    raw = _LABELS_RAW.get(feature)
    return _L(*raw) if raw else feature


def next_unlock(player):
    """Prochaine fonctionnalité à débloquer (label, grade) ou None si tout est ouvert."""
    best = None
    for feat in UNLOCKS:
        g = effective_required_grade(player, feat)
        if g > player.grade_index and (best is None or g < best[1]):
            best = (feature_label(feat), g)
    return best
