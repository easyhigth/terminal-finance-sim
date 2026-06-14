"""
config.py — Constantes globales, palette de couleurs et réglages du jeu.
Inspiration visuelle : Bloomberg Terminal (fond noir, texte ambre/orange,
accents cyan et verts/rouges pour les variations de marché).
"""
import os
import sys

# ---------------------------------------------------------------------------
# FENETRE
# ---------------------------------------------------------------------------
SCREEN_WIDTH = 1280        # format 16:9
SCREEN_HEIGHT = 720        # 1280x720 — tient sur la plupart des écrans
FPS = 60
TITLE = "TERMINAL — Finance Career Simulator"

# ---------------------------------------------------------------------------
# PALETTE BLOOMBERG-STYLE
# Couleurs en (R, G, B)
# ---------------------------------------------------------------------------
COL_BG          = (8, 10, 14)        # fond quasi noir
COL_PANEL       = (16, 19, 26)       # panneaux légèrement plus clairs
COL_PANEL_HEAD  = (24, 28, 38)       # en-têtes de panneaux
COL_BORDER      = (42, 48, 62)       # bordures discrètes
COL_GRID        = (28, 32, 42)       # lignes de grille

COL_AMBER       = (255, 176, 0)      # texte principal — ambre Bloomberg
COL_AMBER_DIM   = (180, 124, 0)      # ambre atténué
COL_TEXT        = (210, 216, 226)    # texte secondaire clair
COL_TEXT_DIM    = (120, 128, 142)    # texte tertiaire / labels
COL_CYAN        = (64, 220, 240)     # accents / liens / sélection
COL_WHITE       = (240, 244, 250)

COL_UP          = (38, 214, 122)     # vert : hausse
COL_DOWN        = (240, 64, 72)      # rouge : baisse
COL_WARN        = (255, 196, 0)      # avertissement
COL_NEUTRAL     = (140, 148, 162)

# Continents — couleur d'accent par région
COL_EUROPE      = (90, 150, 255)
COL_USA         = (80, 220, 140)
COL_ASIA        = (255, 120, 90)
COL_NORTHAM     = (90, 210, 205)     # Amérique du Nord — turquoise
COL_SOUTHAM     = (240, 210, 80)     # Amérique du Sud — jaune
COL_AFRICA      = (235, 150, 70)     # Afrique — orange
COL_OCEANIA     = (150, 130, 245)    # Océanie — violet

# Événements / deals — accents sémantiques
COL_EVENT_GOOD  = (38, 214, 122)     # événement favorable
COL_EVENT_BAD   = (240, 64, 72)      # événement défavorable
COL_EVENT_INFO  = (64, 220, 240)     # événement neutre / information
COL_DEAL        = (255, 176, 0)      # deal en cours
COL_DEAL_URGENT = (255, 120, 90)     # deal proche de l'échéance

# Niveaux de priorité visuelle (hiérarchie de l'information)
COL_PRIO_CRITICAL = (240, 64, 72)    # critique / danger immédiat
COL_PRIO_URGENT   = (255, 120, 90)   # urgent / à traiter
COL_PRIO_BONUS    = (38, 214, 122)   # opportunité / bonne nouvelle
COL_PRIO_NORMAL   = (42, 48, 62)     # neutre (= bordure)
COL_PRESTIGE      = (212, 175, 55)   # or : prestige / badges / titres

# ---------------------------------------------------------------------------
# LAYOUT — marges et espacements cohérents (en pixels)
# Référence unique pour aligner toutes les scènes.
# ---------------------------------------------------------------------------
MARGIN          = 10     # marge extérieure standard des panneaux
PAD             = 12     # padding interne d'un panneau
GAP             = 14     # espace entre deux éléments
TOPBAR_H        = 34     # hauteur du bandeau supérieur
TICKER_H        = 20     # hauteur du bandeau ticker
ROW_H           = 24     # hauteur d'une ligne de liste standard
FOOTER_H        = 54     # bande basse réservée (boutons retour) — anti-chevauchement

# Helpers de zones standard (calculés depuis la résolution)
def content_top():
    """Y de départ du contenu sous le titre d'une scène (modules/écrans)."""
    return 104

def footer_y():
    """Y de la bande des boutons retour (en bas), réservée."""
    return SCREEN_HEIGHT - FOOTER_H

def back_button_rect(width=200, height=42):
    """Rect standard du bouton retour, dans le footer réservé (en bas à gauche)."""
    return (40, SCREEN_HEIGHT - height - 8, width, height)

# ---------------------------------------------------------------------------
# POLICES (monospace = ambiance terminal)
# Tailles logiques, résolues dans ui/fonts.py
# ---------------------------------------------------------------------------
FONT_SIZE_TINY   = 12
FONT_SIZE_SMALL  = 15
FONT_SIZE_BODY   = 18
FONT_SIZE_HEAD   = 24
FONT_SIZE_TITLE  = 40
FONT_SIZE_HUGE   = 64

# ---------------------------------------------------------------------------
# GAMEPLAY — Grades de carrière
# ---------------------------------------------------------------------------
GRADES = [
    "Intern",              # 0  — début de carrière
    "Junior Analyst",      # 1
    "Analyst",             # 2
    "Senior Analyst",      # 3
    "Associate",           # 4  — milieu de carrière
    "Senior Associate",    # 5
    "Vice President",      # 6
    "Senior VP",           # 7
    "Director",            # 8  — fin de carrière
    "Executive Director",  # 9
    "Managing Director",   # 10
    "Partner / C-Suite",   # 11 — sommet
]

# Phases de carrière (pour la différenciation début / milieu / fin)
def career_phase(grade_index):
    if grade_index <= 3:
        return "Début de carrière"
    if grade_index <= 7:
        return "Milieu de carrière"
    return "Fin de carrière"

# Voies de spécialisation débloquées après le grade Analyst
TRACKS = ["Portfolio", "M&A", "Risk", "Quant", "Advisory"]

# Continents jouables + impact réglementaire (résumé, détaillé dans modules)
CONTINENTS = {
    "Europe": {
        "color": COL_EUROPE,
        "regulator": "ESMA / EBA",
        "framework": "MiFID II, Bâle III, IFRS, RGPD",
        "currency": "EUR",
        "blurb": "Régulation stricte, reporting MiFID II, normes IFRS.",
    },
    "USA": {
        "color": COL_USA,
        "regulator": "SEC / FINRA / Fed",
        "framework": "Dodd-Frank, US GAAP, Reg SHO, SOX",
        "currency": "USD",
        "blurb": "Marchés profonds, litiges fréquents, normes US GAAP.",
    },
    "Asia": {
        "color": COL_ASIA,
        "regulator": "HKMA / MAS / FSA",
        "framework": "Bâle III local, contrôles de capitaux variés",
        "currency": "USD/HKD/JPY",
        "blurb": "Fragmentation réglementaire, contrôles de capitaux.",
    },
    "Am.Nord": {
        "color": COL_NORTHAM,
        "regulator": "OSC / BSIF",
        "framework": "NI 51-102, IFRS, Bâle III",
        "currency": "CAD",
        "blurb": "Ressources, banques solides, proximité du marché US.",
    },
    "Am.Sud": {
        "color": COL_SOUTHAM,
        "regulator": "CVM / BCB",
        "framework": "IFRS, contrôles de capitaux, forte inflation",
        "currency": "BRL",
        "blurb": "Matières premières, volatilité et risque devise élevés.",
    },
    "Afrique": {
        "color": COL_AFRICA,
        "regulator": "FSCA / régulateurs locaux",
        "framework": "Marchés frontières, IFRS, liquidité variable",
        "currency": "ZAR/USD",
        "blurb": "Forte croissance, télécoms et matières, marchés peu liquides.",
    },
    "Océanie": {
        "color": COL_OCEANIA,
        "regulator": "ASIC / RBA",
        "framework": "Corporations Act, IFRS, Bâle III",
        "currency": "AUD",
        "blurb": "Mines, grandes banques, exposition à la demande asiatique.",
    },
}

# ---------------------------------------------------------------------------
# TEMPS — calendrier de jeu
# ---------------------------------------------------------------------------
DAYS_PER_QUARTER = 90        # un trimestre = 90 jours
DAYS_PER_STEP    = 5         # un "tour" d'avancement = 5 jours
START_CASH       = 250_000.0 # capital de départ (firme/joueur), en devise locale

# Seuils de fin de partie
BANKRUPTCY_CASH  = -500_000.0  # en-dessous : faillite
MIN_REPUTATION   = 0           # réputation nulle = licenciement

# ---------------------------------------------------------------------------
# SAUVEGARDES
# En développement : dossier "saves" à la racine du projet.
# En version packagée (PyInstaller, sys.frozen) : dossier inscriptible dans
# l'espace utilisateur, car le bundle .app/.exe peut être en lecture seule.
# ---------------------------------------------------------------------------
def _resolve_save_dir():
    if getattr(sys, "frozen", False):
        # application packagée : on écrit dans l'espace utilisateur
        if sys.platform == "darwin":
            base = os.path.expanduser("~/Library/Application Support")
        elif sys.platform.startswith("win"):
            base = os.environ.get("APPDATA", os.path.expanduser("~"))
        else:
            base = os.path.expanduser("~/.local/share")
        return os.path.join(base, "TERMINAL-FinanceSim", "saves")
    return "saves"


SAVE_DIR = _resolve_save_dir()
AUTOSAVE_SLOT = "autosave"
SAVE_SLOTS = ["slot1", "slot2", "slot3"]   # slots manuels visibles dans l'UI
