"""
app_catalog.py — Catalogue déclaratif de TOUTES les pages/scènes navigables du
jeu (logique pure, sans pygame). Source unique consommée par :
  - le menu Démarrer du bureau (scenes/scene_desktop_menus.py) ;
  - la palette de navigation Ctrl+K et le fil d'Ariane (core/scene_manager.py) ;
  - les libellés lisibles des fenêtres hébergées (scenes/scene_desktop_common.py) ;
  - le garde-fou de couverture (tests/test_app_catalog.py — chaque scène
    jouable enregistrée dans main.py doit apparaître ici).

Anciennement porté par l'écran plein écran « PLUS » (scenes/scene_more.py,
retiré) : le menu Démarrer du bureau couvrait déjà exactement le même besoin
(toutes les pages, ouvrables en fenêtre), le garder en double n'apportait
rien. Ce module ne porte plus que les DONNÉES ; scene_desktop_menus.py porte
le rendu/l'interaction (recherche, verrous, navigation clavier).

Chaque entrée : (libellé, scène, kwargs, description) — la description est un
résumé d'une ligne affiché en infobulle au survol dans le menu Démarrer, pour
qu'un joueur perdu comprenne ce que fait une page avant de cliquer dessus.
"""

# scène -> fonctionnalité gated (core/unlocks.py) dont dépend l'accès à la
# scène ENTIÈRE (et non juste une action à l'intérieur) — cf. le pattern
# `_can()` de chacune de ces scènes, qui affiche un message de verrou plutôt
# que son contenu normal en dessous du grade requis.
SCENE_FEATURE = {
    "deals": "deals", "track": "track", "ma": "ma", "team": "team",
    "hedge": "hedge", "options": "options", "ipo": "ipo", "fx": "fx",
    "structured": "structured", "credit": "credit", "calendar": "calendar",
    "mandates": "mandates", "swaps": "trade",
    # découverte progressive : un stagiaire n'a que les basiques. Les outils
    # d'analyse (grade 1), la mesure de risque / boîte à outils quant (grade 2)
    # et l'exécution (shop/mur, grade 1) n'apparaissent qu'une fois utilisables.
    "markethub": "analyst", "graph": "charts", "explorer": "analyst",
    "compare": "analyst", "risk": "risk", "quant": "quant", "alm": "alm",
    "spreadsheet": "tools", "frontier_lab": "tools", "portfolio": "tools",
    "book": "trade", "wall": "trade", "shop": "trade", "analytics": "trade",
    "performance": "trade", "portfolio_unified": "trade",
}

# (titre de section, [(libellé, scène, kwargs, description)])
SECTIONS = [
    ("Marchés & actifs", [
        ("Marché", "markethub", {}, "Indices mondiaux, taux de change et vue d'ensemble des marchés."),
        ("Boutique (acheter tout actif)", "shop", {}, "Guichet unique pour acheter n'importe quel type d'actif en un clic."),
        ("Explorateur", "explorer", {}, "Parcourir et filtrer les 320 sociétés du marché par secteur, région, taille…"),
        ("ETF", "etfs", {}, "Fonds indiciels : investir sur un panier d'actifs en une seule ligne."),
        ("Obligations", "bonds", {}, "Dette d'entreprise et souveraine : coupon, échéance, sensibilité aux taux."),
        ("Commodities", "commodities", {}, "Matières premières (métaux, énergie, agricole) : cours et positions."),
        ("Crypto", "crypto", {}, "Cryptomonnaies et stablecoins, avec risque de contagion/depeg."),
        ("Produits structurés", "structured", {}, "Construire des produits sur mesure (capital garanti, autocall…)."),
        ("Titrisation / ABS", "credit", {}, "Regrouper des créances en tranches de risque (ABS/CLO)."),
        ("Swaps de devises", "swaps", {}, "Échanger un flux de trésorerie dans une devise contre une autre."),
        ("Gouvernements", "governments", {}, "Cadre réglementaire et régulateurs propres à chaque continent."),
        ("Desk FX", "fx", {}, "Marché des changes : taux de conversion et opérations de change."),
        ("Desk d'options (calls/puts)", "options", {}, "Acheter/vendre des calls et puts sur les actions suivies."),
        ("IPO", "ipo", {}, "Souscrire aux introductions en bourse avant leur première cotation."),
        ("Mur de trading (live)", "wall", {}, "Flux de prix en direct, façon salle de marché, sur plusieurs actifs."),
    ]),
    ("Analyse & outils", [
        ("Fiche société", "company", {}, "Fiche détaillée d'une société : cours, ratios, actualités."),
        ("États financiers", "financials", {}, "Bilan, compte de résultat et flux de trésorerie d'une société."),
        ("Comparateur", "compare", {}, "Comparer plusieurs sociétés côte à côte sur les mêmes critères."),
        ("Graphes", "graph", {"kind": "line"}, "Graphes de cours (ligne, bougies, comparaison, corrélation…)."),
        ("Analyse portefeuille", "analytics", {}, "Décomposition détaillée de la valeur et du risque du portefeuille."),
        ("Performance & attribution", "performance", {}, "D'où vient la performance : par position, secteur, décision."),
        ("Alertes de prix", "alerts", {}, "Être notifié quand un actif franchit un seuil de prix choisi."),
        ("Journal de trading", "tradejournal", {}, "Historique des trades, statistiques et réplication d'ordres."),
        ("Risque (VaR)", "risk", {}, "Value-at-Risk et mesures de risque du portefeuille."),
        ("Quant (options)", "quant", {}, "Grecques et pricing d'options pour un pilotage quantitatif."),
        ("M&A (cibles & LBO)", "ma", {}, "Rechercher des cibles de fusion-acquisition et monter des LBO."),
        ("Optimiseur Markowitz (poids cibles)", "portfolio", {}, "Calculer une allocation optimale (frontière efficiente)."),
        ("Labo frontière efficiente (mes actifs)", "frontier_lab", {}, "Frontière efficiente appliquée à VOS positions actuelles."),
        ("Analyse des positions (tri & P&L)", "portfolio_unified", {}, "Toutes vos positions, triables par gain/perte latent."),
        ("Couverture (hedge)", "hedge", {}, "Se protéger d'une baisse via des instruments de couverture."),
        ("ALM bancaire", "alm", {}, "Gestion actif-passif : équilibrer maturités et liquidité."),
        ("Tableur", "spreadsheet", {}, "Classeur libre avec formules, y compris des cours de marché en direct."),
    ]),
    ("Carrière & monde", [
        ("Portefeuille", "book", {}, "Vos positions actuelles, trésorerie et valeur nette."),
        ("Carrière", "career", {}, "Grade, objectifs du trimestre et historique de carrière."),
        ("Mission", "mission", {}, "Travailler pour progresser dans votre carrière et gagner de l'expérience."),
        ("Examen de promotion (EVAL)", "evaluation", {}, "Passer l'examen requis pour être promu au grade suivant."),
        ("Décisions (dilemmes)", "dilemma", {}, "Trancher les dilemmes éthiques/stratégiques en attente."),
        ("Exam / Certif", "examcert", {}, "Accès aux examens et aux parcours de certification (CFA/FRM/CQF)."),
        ("Revue annuelle (bonus)", "review", {}, "Bilan annuel de performance et calcul du bonus."),
        ("Voie (Track)", "track", {}, "Choisir une spécialisation (M&A, Risk, Quant, Portfolio, Advisory)."),
        ("Rivaux", "rivals", {}, "Classement des concurrents et de leurs actions récentes."),
        ("Inbox", "inbox", {}, "Messagerie : mots du manager, arcs narratifs, notifications."),
        ("News & événements", "news", {}, "Actualités du jour, par région, qui influencent les marchés."),
        ("Centre de notifications", "notifications", {}, "Historique de toutes les notifications reçues."),
        ("Calendrier macro", "calendar", {}, "Agenda des annonces macroéconomiques à venir."),
        ("Mandats clients", "mandates", {}, "Missions de conseil confiées par des clients externes."),
        ("Deals", "deals", {}, "Transactions M&A en cours à faire aboutir."),
        ("Historique complet", "history", {}, "Journal complet des événements de votre carrière."),
        ("Stress test régulateur", "stresstest", {}, "Simulation de crise imposée par le régulateur."),
        ("Équipe / analystes", "team", {}, "Recruter et gérer une équipe d'analystes."),
        ("Succès (badges)", "achievements", {}, "Tous les badges du jeu, obtenus ou encore à débloquer."),
        ("Historique des déblocages", "unlockhistory", {}, "Ce que chaque grade a débloqué, et ce qui reste à venir."),
        ("Statistiques", "stats", {}, "Synthèse de la session : trading, discipline, progression, score composite."),
    ]),
    ("Apprendre", [
        ("Académie", "academy", {}, "Leçons de finance pour progresser en théorie."),
        ("Tutoriels", "tutorials", {}, "Guides pas-à-pas sur les mécaniques du jeu."),
        ("Glossaire", "glossary", {}, "Aide pour comprendre les termes techniques employés dans le jeu."),
        ("Certifications", "cert", {}, "Programmes de certification complets (CFA, FRM, CQF)."),
        ("Aide / Commandes", "commands", {}, "Catalogue complet des commandes tapables dans le terminal."),
    ]),
    ("Système", [
        ("Réglages (affichage, son, langue)", "settings", {}, "Affichage, son, langue, animations et vitesse de jeu."),
        ("Sauvegardes", "saves", {}, "Charger, enregistrer, exporter ou importer une partie."),
    ]),
]


def is_locked(player, scene):
    """True si `scene` est gatée par le grade (core/unlocks.py) et que le
    joueur n'a pas encore le niveau requis."""
    from core import unlocks
    feat = SCENE_FEATURE.get(scene)
    return bool(feat) and not unlocks.unlocked(player, feat)


def lock_message(player, label, scene):
    """Message d'infobulle pour une entrée verrouillée (grade requis)."""
    from core import config, unlocks
    feat = SCENE_FEATURE[scene]
    g = unlocks.effective_required_grade(player, feat)
    return f"{label} — verrouillé jusqu'au grade {config.GRADES[g]}."
