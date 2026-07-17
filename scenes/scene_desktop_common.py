"""
scene_desktop_common.py — Constantes et petits helpers PARTAGÉS entre
`scene_desktop.py` (DesktopScene, cœur : cycle de vie, navigation, dessin des
icônes/barres) et ses deux mixins (`scene_desktop_widgets.py`,
`scene_desktop_menus.py`). Module à part pour éviter tout import circulaire :
ni le cœur ni les mixins n'importent l'un depuis l'autre, tous importent
seulement d'ici (même principe qu'un module `core/`, mais gardé dans
`scenes/` car son contenu — quelles apps, quelles icônes — est spécifique à
l'écran bureau, pas réutilisable ailleurs dans le jeu).
"""
import pygame

from apps.app_alerts import AlertsApp
from apps.app_analytics import AnalyticsApp
from apps.app_attribution import AttributionApp
from apps.app_backtester import BacktesterApp
from apps.app_book import BookApp
from apps.app_calculator import CalculatorApp
from apps.app_clients import ClientsApp
from apps.app_company import CompanyApp
from apps.app_creditdesk import CreditDeskApp
from apps.app_crisislab import CrisisLabApp
from apps.app_deals import DealsApp
from apps.app_dilemma import DilemmaApp
from apps.app_evaluation import EvaluationApp
from apps.app_explorer import ExplorerApp
from apps.app_footballfield import FootballFieldApp
from apps.app_frontier import FrontierApp
from apps.app_funding import FundingApp
from apps.app_fxdesk import FxDeskApp
from apps.app_greeks import GreeksApp
from apps.app_hedge import HedgeApp
from apps.app_inbox import InboxApp
from apps.app_journal import JournalApp
from apps.app_manual import ManualApp
from apps.app_markethub import MarketHubApp
from apps.app_mergerarb import MergerArbApp
from apps.app_mission import MissionApp
from apps.app_notifications import NotificationCenterApp
from apps.app_pairs import PairsApp
from apps.app_pitchbook import PitchBookApp
from apps.app_pnlexplain import PnlExplainApp
from apps.app_rates import RatesApp
from apps.app_research import ResearchApp
from apps.app_review import ReviewApp

# Applications financières avancées
from apps.app_sharpe import SharpeApp
from apps.app_sheet import SheetApp
from apps.app_shop import ShopApp
from apps.app_strategicalloc import StrategicAllocApp
from apps.app_themes import ThemesApp
from apps.app_trading import TradingApp
from apps.app_valuation import ValuationApp
from apps.app_vardesk import VarDeskApp
from apps.app_vollab import VolLabApp
from apps.app_watchlist import WatchlistApp
from apps.app_zscore import ZScoreApp
from core.app_catalog import SECTIONS

TOPBAR_H = 36
TASKBAR_H = 30


def cached_shade(instance, surf, alpha=175):
    """Surface SRCALPHA plein-écran semi-noire, réutilisée tant que la taille
    de `surf` et l'alpha ne changent pas. Évite de recréer une surface à
    chaque frame pour les overlays modaux (guide, bilan trimestre, menus…)."""
    size = surf.get_size()
    key = ("_cached_shade", size, alpha)
    cache = getattr(instance, "_cached_shade_cache", None)
    if cache is None or cache[0] != key:
        shade = pygame.Surface(size, pygame.SRCALPHA)
        shade.fill((0, 0, 0, alpha))
        instance._cached_shade_cache = (key, shade)
    return instance._cached_shade_cache[1]

# Scènes qui restent une bascule PLEIN ÉCRAN classique (flux pré/post-partie —
# quitter le bureau, ce n'est pas ouvrir une fenêtre dessus) : jamais hébergées.
_FULLSCREEN_EXIT = {"desktop", "gameover", "menu", "splash", "intro",
                    "continent", "runsetup", "sandbox"}

# Applications NATIVES du bureau (dessinées en fenêtre, clé, libellé, icône, fabrique)
APPS = [
    ("research", "Recherche", "research", ResearchApp),
    ("trading", "Trading", "trading", TradingApp),
    ("sheet", "Tableur", "sheet", SheetApp),
    ("inbox", "Inbox", "inbox", InboxApp),
    ("alerts", "Alertes", "alert", AlertsApp),
    ("markethub", "Marché", "market", MarketHubApp),
    ("book", "Portefeuille", "book", BookApp),
    ("watchlist", "Watchlist", "star", WatchlistApp),
    ("calculator", "Calculatrice", "calc", CalculatorApp),
    ("manual", "Manuel", "help", ManualApp),
    ("notifcenter", "Notifications", "bell", NotificationCenterApp),
    ("dilemma", "Décision", "decide", DilemmaApp),
    ("review", "Revue de performance", "review", ReviewApp),
    ("mission", "Mission", "mission", MissionApp),
    ("tradejournal", "Journal de trading", "journal", JournalApp),
    ("evaluation", "Évaluation", "examcert", EvaluationApp),
    ("deals", "Deals", "deals", DealsApp),
    ("clients", "Carnet clients", "review", ClientsApp),
    ("company", "Fiche société", "research", CompanyApp),
    ("shop", "Boutique", "shop", ShopApp),
    ("analytics", "Analyse du portefeuille", "graph", AnalyticsApp),
    ("explorer", "Explorateur", "explorer", ExplorerApp),
    # Outils quantitatifs (socle core/quant_tools.py)
    ("sharpe", "Sharpe Ratio", "graph", SharpeApp),
    ("zscore", "Z-Score", "graph", ZScoreApp),
    ("hedge", "Couverture", "shield", HedgeApp),
    ("frontier", "Frontière efficiente", "frontier", FrontierApp),
    ("greeks", "Desk Options", "greeks", GreeksApp),
    ("vardesk", "Risque (VaR)", "risk", VarDeskApp),
    ("rates", "Desk Taux", "rates", RatesApp),
    ("attribution", "Attribution (Brinson)", "graph", AttributionApp),
    ("pairs", "Pairs Trading", "trading", PairsApp),
    ("creditdesk", "Desk Crédit", "quant", CreditDeskApp),
    ("crisislab", "Labo de crise", "alert", CrisisLabApp),
    ("valuation", "Valorisation", "research", ValuationApp),
    ("fxdesk", "Desk FX (carry)", "market", FxDeskApp),
    ("vollab", "Labo de vol", "quant", VolLabApp),
    ("funding", "Desk Financement", "book", FundingApp),
    ("pnlexplain", "P&L Explain", "graph", PnlExplainApp),
    ("backtester", "Backtester", "graph", BacktesterApp),
    # Apps EXCLUSIVES par voie (cf. core/unlocks.TRACK_AFFINITY) : donnent
    # une identité d'outillage propre à chaque spécialisation, au-delà des
    # perks numériques de core/tracks.py.
    ("footballfield", "Football Field", "research", FootballFieldApp),
    ("pitchbook", "Pitch Book", "advisory", PitchBookApp),
    ("strategicalloc", "Allocation stratégique", "portfolio", StrategicAllocApp),
    # Nouveaux modes de trading (contenu — accessibles à toutes les voies)
    ("mergerarb", "Arbitrage de fusion", "deals", MergerArbApp),
    ("themes", "Thématiques", "graph", ThemesApp),
]

# Application supplémentaire propre à la VOIE (track) choisie par le joueur
# (cf. core/tracks.py) : une fois la voie choisie, une icône dédiée apparaît
# sur le bureau et ouvre l'écran correspondant EN FENÊTRE — au même titre que
# les autres apps, ouvrable en même temps (ex. suivre le FX pendant que le
# desk M&A tourne dans une autre fenêtre).
TRACK_APP = {
    # la voie Portfolio ouvre LE portefeuille (book) — même écran que la
    # commande PORTFOLIO, l'icône Portef. et le widget patrimoine ; la vue
    # « Analyse des positions » (ex-portefeuille unifié) reste dans PLUS.
    "Portfolio": ("book", "Portefeuille", "portfolio"),
    "M&A": ("ma", "M&A", "ma"),
    "Risk": ("risk", "Risque", "risk"),
    "Quant": ("quant", "Quant", "quant"),
    "Advisory": ("mandates", "Mandats", "advisory"),
}

# Anciens boutons du rail latéral du terminal (retiré, refonte UI « Jeu PC ») :
# désormais des icônes du bureau, ouvertes en fenêtre comme n'importe quelle
# autre app — plus rien n'est caché dans un panneau à part. (clé, libellé,
# icon_kind, scène) — "save" (clé "save") est une action instantanée (pas une
# fenêtre), cf. `DesktopScene._quick_save`.
QUICK_APPS = [
    # (Marché, Portefeuille, Inbox, Alertes et Mission sont devenues des apps
    # NATIVES, cf. APPS ci-dessus — dessinées à la résolution de leur
    # fenêtre, plus d'hébergement flou ; leur icône vit désormais dans APPS,
    # retirée d'ici pour ne pas en afficher deux)
    ("qnews", "News", "news", "news"),
    ("qmandates", "Mandats", "advisory", "mandates"),
    ("qdeals", "Deals", "deals", "deals"),
    ("qdecide", "Décide", "decide", "dilemma"),
    ("qexamcert", "Exam/Certif", "examcert", "examcert"),
    ("qwall", "Mur", "wall", "wall"),
    ("qshop", "Shop", "shop", "shop"),
    ("qexplorer", "Explorateur", "explorer", "explorer"),
    ("qgraph", "Graphes", "graph", "graph"),
    ("qachievements", "Succès", "star", "achievements"),
    ("save", "Sauver", "save", None),
    ("qcommands", "Aide", "help", "commands"),
]

# Icônes du bureau soumises au déblocage progressif (core/unlocks.py) : la
# complexité arrive par paliers de grade, comme les commandes du terminal —
# une icône verrouillée n'apparaît tout simplement pas (et son apparition au
# grade suivant fait office de récompense, cf. DesktopScene._check_new_icons).
ICON_FEATURE = {
    # --- le stagiaire n'a que 5 apps (Terminal, Mission, Exam/Certif, Inbox,
    # --- Manuel + Sauver/Aide) : le reste du confort arrive au grade 1 ---
    "calculator": "analyst",   # calculatrice : accompagne les outils d'analyse
    "qnews": "analyst",        # fil d'actus dédié — le Terminal suffit au stagiaire
    "notifcenter": "analyst",  # centre de notifications : rien à notifier avant d'agir
    "qachievements": "analyst",  # succès : à découvrir une fois la carrière lancée
    # --- outils d'analyse : arrivent quand on devient analyste (grade 1) ---
    "markethub": "analyst",    # hub Marché : de l'analyse — le Terminal suffit au stagiaire
    "research": "analyst",     # recherche société
    "watchlist": "analyst",    # favoris/watchlist
    "alerts": "analyst",       # alertes de prix
    "qexplorer": "analyst",    # explorateur des 320 sociétés
    "qgraph": "charts",        # graphes : PAS pour un stagiaire (rien à en faire encore)
    # --- ce qui suppose de pouvoir investir/détenir des positions (grade 1) ---
    "book": "trade",           # portefeuille : vide et inutile tant qu'on ne peut pas investir
    "qshop": "trade",          # boutique : acheter tout actif = investir
    "qwall": "trade",          # mur de trading live
    "tradejournal": "trade",   # journal de trading : n'a de sens qu'avec des trades
    # --- boîte à outils quant autonome (grade 2) ---
    "sheet": "tools", "sharpe": "tools", "zscore": "tools",
    "frontier": "tools", "crisislab": "tools",
    # --- Risque (VaR) : suit le module risk (grade 2) ---
    "vardesk": "risk",
    "trading": "trade",
    "qmandates": "mandates",
    "clients": "mandates",
    "qdeals": "deals",
    "hedge": "hedge",        # la couverture arrive au même grade que PROTECT
    "greeks": "options",     # le desk options arrive avec la commande OPTIONS
    "rates": "trade",        # le desk taux arrive quand on peut investir
    "attribution": "attribution",  # affinité Portfolio : juger SA gestion
    "pairs": "leverage",     # la paire exige la vente à découvert
    "creditdesk": "creditdesk",  # affinité M&A : solvabilité d'une cible
    "valuation": "valuation",    # affinité M&A : juger une cible avant offre
    "fxdesk": "trade",       # le carry s'exécute : même palier que le spot FX
    "vollab": "options",     # le labo de vol dialogue avec le desk options
    "funding": "leverage",   # repo/prêt-titres = levier et shorts
    "pnlexplain": "pnlexplain",   # affinité Portfolio : expliquer SON P&L
    "backtester": "backtester",  # affinité Portfolio : tester une stratégie
    "footballfield": "footballfield",     # affinité M&A
    "pitchbook": "pitchbook",             # affinité Advisory
    "strategicalloc": "strategicalloc",   # affinité Portfolio
    "mergerarb": "mergerarb",             # trading événementiel (toutes voies)
    "themes": "themes",                   # thématiques de marché (toutes voies)
}

# Rangement des icônes du bureau en SECTIONS repliables (façon dossiers) —
# chaque icône a UNE catégorie fixe : une app nouvellement débloquée (cf.
# ICON_FEATURE ci-dessus) atterrit donc automatiquement dans la bonne section
# dès son apparition, sans configuration supplémentaire. Une clé absente de
# ce dict tombe dans DEFAULT_ICON_CATEGORY plutôt que de disparaître — filet
# défensif si une future icône est ajoutée sans y penser.
DEFAULT_ICON_CATEGORY = "Autres"
ICON_CATEGORY_ORDER = [
    "Essentiels", "Marché & Analyse", "Quant & Risque", "Crédit & Financement",
    "Carrière", "Outils du bureau", DEFAULT_ICON_CATEGORY,
]
ICON_CATEGORY = {
    # Essentiels : les outils du quotidien, jamais loin.
    "terminal": "Essentiels", "trading": "Essentiels", "research": "Essentiels",
    "book": "Essentiels", "markethub": "Essentiels", "watchlist": "Essentiels",
    # Marché & Analyse : parcourir/comparer/exécuter sur le marché.
    "qexplorer": "Marché & Analyse", "qshop": "Marché & Analyse",
    "qwall": "Marché & Analyse", "qgraph": "Marché & Analyse",
    "fxdesk": "Marché & Analyse", "valuation": "Marché & Analyse",
    "mergerarb": "Marché & Analyse", "themes": "Marché & Analyse",
    # Quant & Risque : les desks quantitatifs/risque avancés.
    "sharpe": "Quant & Risque", "zscore": "Quant & Risque",
    "hedge": "Quant & Risque", "frontier": "Quant & Risque",
    "greeks": "Quant & Risque", "vardesk": "Quant & Risque",
    "rates": "Quant & Risque", "attribution": "Quant & Risque",
    "pairs": "Quant & Risque", "crisislab": "Quant & Risque",
    "vollab": "Quant & Risque", "backtester": "Quant & Risque",
    # Crédit & Financement.
    "creditdesk": "Crédit & Financement", "funding": "Crédit & Financement",
    "pnlexplain": "Crédit & Financement",
    # Carrière : progression, mandats, deals, décisions.
    "mission": "Carrière", "tradejournal": "Carrière", "track": "Carrière",
    "clients": "Carrière",
    "qmandates": "Carrière", "qdeals": "Carrière", "qdecide": "Carrière",
    "qexamcert": "Carrière", "qachievements": "Carrière",
    # Apps exclusives par voie (identité de spécialisation).
    "footballfield": "Carrière", "pitchbook": "Carrière", "strategicalloc": "Carrière",
    # Outils du bureau : messagerie, notes, réglages.
    "sheet": "Outils du bureau", "calculator": "Outils du bureau",
    "notifcenter": "Outils du bureau", "inbox": "Outils du bureau",
    "alerts": "Outils du bureau", "qnews": "Outils du bureau",
    "qcommands": "Outils du bureau", "save": "Outils du bureau",
    "manual": "Outils du bureau",
}


def icon_category(key):
    return ICON_CATEGORY.get(key, DEFAULT_ICON_CATEGORY)

# Raccourcis Ctrl+<lettre> des icônes du bureau — mêmes mnémoniques que les
# raccourcis du terminal (RAIL_SHORTCUTS, scenes/scene_terminal.py, garder
# synchronisé) pour ne pas avoir deux dialectes. Ctrl+T/W/Tab sont réservés
# par la barre d'onglets (core/pages.py), Ctrl+K par la palette, Ctrl+/ par
# la recherche globale — jamais réutilisés ici. Ctrl+O (Plus/Apps) n'est PAS
# ici : il n'ouvre pas une icône mais bascule le menu Démarrer directement
# (cf. DesktopScene.handle_event), pas de fenêtre dédiée à ouvrir.
DESKTOP_SHORTCUTS = {
    pygame.K_m: "markethub",
    pygame.K_p: "book",
    pygame.K_i: "inbox",
    pygame.K_n: "qnews",
    pygame.K_j: "mission",
    pygame.K_a: "qmandates",
    pygame.K_d: "qdeals",
    pygame.K_x: "qexamcert",
    pygame.K_b: "qshop",
    pygame.K_s: "save",
    pygame.K_h: "qcommands",
    # Raccourcis des outils quantitatifs. Ctrl+C (copier) et Ctrl+Z (annuler)
    # sont des conventions universelles — jamais réutilisés ici pour ne pas
    # intercepter le copier/annuler d'une app qui ne consomme pas l'évènement.
    pygame.K_r: "sharpe",    # Ratio de Sharpe
    pygame.K_g: "hedge",     # Couverture (hedGe)
    pygame.K_e: "frontier",  # Frontière Efficiente
}
# icône -> libellé de raccourci (tooltip au survol)
_ICON_SHORTCUT = {icon: "Ctrl+" + pygame.key.name(k).upper()
                  for k, icon in DESKTOP_SHORTCUTS.items()}

# Scènes hébergées (menu Démarrer) nécessitant un actif par défaut si non fourni.
_NEEDS_TICKER = {"company", "financials", "ma_target"}
_NEEDS_TICKERS = {"compare", "graph"}

# Libellé lisible d'une scène (repris du catalogue core/app_catalog.SECTIONS).
_SCENE_LABEL = {scene: label for _title, items in SECTIONS for label, scene, _kw, _desc in items}

ICON_W, ICON_H = 88, 78
ICON_GAP = 6

# scène -> icon_kind (façade visuelle des fenêtres hébergées de la voie choisie)
_TRACK_SCENE_ICON = {scene: kind for _track, (scene, _label, kind) in TRACK_APP.items()}

# scène -> icon_kind pour TOUTES les fenêtres hébergées (barre de titre +
# barre des tâches) : accès rapides + apps de voie + quelques écrans courants.
# Une scène absente d'ici retombe sur l'icône « generic ».
SCENE_ICON = dict(_TRACK_SCENE_ICON)
SCENE_ICON.update({scene: kind for _k, _l, kind, scene in QUICK_APPS if scene})
SCENE_ICON.update({
    "terminal": "terminal",
    "company": "research",
    "saves": "save",
    "achievements": "star",
    "compare": "graph",
    "inbox": "inbox",
    "alerts": "alert",
    "book": "book",
    "markethub": "market",
})


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


def _scene_label(name):
    return _SCENE_LABEL.get(name, name.capitalize())
