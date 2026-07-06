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

from apps.app_calculator import CalculatorApp
from apps.app_notifications import NotificationCenterApp
from apps.app_research import ResearchApp
from apps.app_sheet import SheetApp
from apps.app_trading import TradingApp
from apps.app_watchlist import WatchlistApp
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
    ("watchlist", "Watchlist", "star", WatchlistApp),
    ("calculator", "Calculatrice", "calc", CalculatorApp),
    ("notifcenter", "Notifications", "bell", NotificationCenterApp),
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
    ("qmarket", "Marché", "market", "markethub"),
    ("qbook", "Portef.", "book", "book"),
    ("qalerts", "Alertes", "alert", "alerts"),
    ("qinbox", "Inbox", "inbox", "inbox"),
    ("qnews", "News", "news", "news"),
    ("qmission", "Mission", "mission", "mission"),
    ("qmandates", "Mandats", "advisory", "mandates"),
    ("qdeals", "Deals", "deals", "deals"),
    ("qdecide", "Décide", "decide", "dilemma"),
    ("qexamcert", "Exam/Certif", "examcert", "examcert"),
    ("qwall", "Mur", "wall", "wall"),
    ("qshop", "Shop", "shop", "shop"),
    ("qexplorer", "Explorateur", "explorer", "explorer"),
    ("qgraph", "Graphes", "graph", "graph"),
    ("save", "Sauver", "save", None),
    ("qcommands", "Aide", "help", "commands"),
]

# Icônes du bureau soumises au déblocage progressif (core/unlocks.py) : la
# complexité arrive par paliers de grade, comme les commandes du terminal —
# une icône verrouillée n'apparaît tout simplement pas (et son apparition au
# grade suivant fait office de récompense, cf. DesktopScene._check_new_icons).
ICON_FEATURE = {
    "trading": "trade",
    "qmandates": "mandates",
    "qdeals": "deals",
}

# Raccourcis Ctrl+<lettre> des icônes du bureau — mêmes mnémoniques que les
# raccourcis du terminal (RAIL_SHORTCUTS, scenes/scene_terminal.py, garder
# synchronisé) pour ne pas avoir deux dialectes. Ctrl+T/W/Tab sont réservés
# par la barre d'onglets (core/pages.py), Ctrl+K par la palette, Ctrl+/ par
# la recherche globale — jamais réutilisés ici. Ctrl+O (Plus/Apps) n'est PAS
# ici : il n'ouvre pas une icône mais bascule le menu Démarrer directement
# (cf. DesktopScene.handle_event), pas de fenêtre dédiée à ouvrir.
DESKTOP_SHORTCUTS = {
    pygame.K_m: "qmarket",
    pygame.K_p: "qbook",
    pygame.K_i: "qinbox",
    pygame.K_n: "qnews",
    pygame.K_j: "qmission",
    pygame.K_a: "qmandates",
    pygame.K_d: "qdeals",
    pygame.K_x: "qexamcert",
    pygame.K_b: "qshop",
    pygame.K_s: "save",
    pygame.K_h: "qcommands",
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


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


def _scene_label(name):
    return _SCENE_LABEL.get(name, name.capitalize())
