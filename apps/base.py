"""
base.py — Classe de base des applications du bureau.

Une `DesktopApp` dessine dans le rectangle de contenu de sa fenêtre (fourni à
chaque frame, coordonnées ABSOLUES à l'écran) et reçoit les évènements pygame
quand sa fenêtre est focalisée. Convention de layout : les sous-rectangles
cliquables sont recalculés dans `draw()` et mémorisés sur l'instance, puis
testés dans `handle_event()` (même pattern que les scènes existantes).
"""


# Traductions EN des titres de fenêtre d'app (les clés FR restent l'identité
# canonique de chaque app : `title` sert aussi de libellé de barre de tâches).
# Localisées UNIQUEMENT à l'affichage via `app_title()` — cf. ui/window_manager
# et scenes/scene_desktop. Une entrée absente retombe sur le titre FR.
_APP_TITLE_EN = {
    "Application": "Application",
    "Alertes de prix": "Price alerts",
    "Analyse du portefeuille": "Portfolio analysis",
    "Attribution (Brinson)": "Attribution (Brinson)",
    "Backtester": "Backtester",
    "Portefeuille": "Portfolio",
    "Calculatrice": "Calculator",
    "Carnet clients": "Client book",
    "Fiche société": "Company sheet",
    "Desk Crédit": "Credit Desk",
    "Labo de crise": "Crisis lab",
    "Deals": "Deals",
    "Décision": "Decision",
    "Évaluation": "Evaluation",
    "Explorateur de marché": "Market explorer",
    "Football Field": "Football Field",
    "Frontière efficiente": "Efficient frontier",
    "Desk Financement": "Funding Desk",
    "Desk FX (carry)": "FX Desk (carry)",
    "Desk Options": "Options Desk",
    "Couverture": "Hedging",
    "Inbox": "Inbox",
    "Journal de trading": "Trading journal",
    "Manuel": "Manual",
    "Marché": "Market",
    "Arbitrage de fusion": "Merger arbitrage",
    "Mission": "Mission",
    "Notifications": "Notifications",
    "Pairs Trading": "Pairs Trading",
    "Pitch Book": "Pitch Book",
    "P&L Explain": "P&L Explain",
    "Desk Taux": "Rates Desk",
    "Recherche — Marchés": "Research — Markets",
    "Revue de performance": "Performance review",
    "Sharpe Ratio": "Sharpe Ratio",
    "Tableur": "Spreadsheet",
    "Boutique": "Shop",
    "Allocation stratégique": "Strategic allocation",
    "Thématiques": "Themes",
    "Trading — Orders": "Trading — Orders",
    "Valorisation": "Valuation",
    "Risque (VaR)": "Risk (VaR)",
    "Labo de vol": "Vol lab",
    "Watchlist": "Watchlist",
    "Z-Score": "Z-Score",
}


def app_title(app_obj):
    """Titre de fenêtre localisé (FR canonique → EN selon la langue courante)."""
    from core.i18n import get_lang
    t = getattr(app_obj, "title", "")
    return _APP_TITLE_EN.get(t, t) if get_lang() == "en" else t


class DesktopApp:
    title = "Application"
    icon_kind = "generic"   # clé d'icône vectorielle (cf. ui/desktop_icons.py)
    default_size = (760, 480)
    min_size = (340, 240)

    def __init__(self, app):
        self.app = app          # référence à l'App globale (marché, gs, horloge…)
        self.desktop = None     # back-ref vers DesktopScene (liens inter-apps),
        #                         posée par DesktopScene lors du lancement.

    def on_open(self):
        """Appelé une fois, à l'ouverture de la fenêtre."""
        pass

    def update(self, dt):
        pass

    def draw(self, surf, rect):
        """Dessine le contenu dans `rect` (Rect absolu)."""
        pass

    def handle_event(self, event, rect):
        """Traite un évènement (fenêtre focalisée). `rect` = zone de contenu.
        Retourne True si consommé."""
        return False
