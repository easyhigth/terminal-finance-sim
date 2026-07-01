"""
main.py — Point d'entrée du jeu.
Lancement :  python main.py
Dépendances : pygame  (pip install pygame)
"""
import os
import random
import sys

import pygame

# Qualité de mise à l'échelle de pygame.SCALED (plein écran / sans bordure) :
# "photo" demande un filtre linéaire (net) au lieu du filtre par défaut
# (plus flou). Doit être posé AVANT pygame.init(). Le driver vidéo factice
# (SDL_VIDEODRIVER=dummy, utilisé par les tests headless / CI) n'a pas de
# renderer matériel : forcer "photo" y fait échouer pygame.display.set_mode.
if os.environ.get("SDL_VIDEODRIVER") != "dummy":
    os.environ.setdefault("PYGAME_FORCE_SCALE", "photo")

from core import config, display_settings
from core.game_state import GameState
from core.market import Market
from core.pages import PageManager
from core.scene_manager import SceneManager
from core.sim_clock import SimClock
from scenes.scene_academy import AcademyScene
from scenes.scene_achievements import AchievementsScene
from scenes.scene_alerts import AlertsScene
from scenes.scene_alm import AlmScene
from scenes.scene_analytics import AnalyticsScene
from scenes.scene_bonds import BondsScene
from scenes.scene_book import BookScene
from scenes.scene_calendar import CalendarScene
from scenes.scene_career import CareerScene
from scenes.scene_cert import CertScene
from scenes.scene_commands import CommandsScene
from scenes.scene_commodities import CommoditiesScene
from scenes.scene_company import CompanyScene
from scenes.scene_compare import CompareScene
from scenes.scene_continent import ContinentScene
from scenes.scene_credit import CreditScene
from scenes.scene_crypto import CryptoScene
from scenes.scene_dashboard import DashboardScene
from scenes.scene_deal import DealScene
from scenes.scene_deals import DealsScene
from scenes.scene_desktop import DesktopScene
from scenes.scene_dilemma import DilemmaScene
from scenes.scene_etfs import ETFScene
from scenes.scene_evaluation import EvaluationScene
from scenes.scene_examcert import ExamCertScene
from scenes.scene_explorer import MarketExplorerScene
from scenes.scene_financials import FinancialsScene
from scenes.scene_frontier_lab import FrontierLabScene
from scenes.scene_fx import FXScene
from scenes.scene_gameover import GameOverScene
from scenes.scene_glossary import GlossaryScene
from scenes.scene_governments import GovernmentsScene
from scenes.scene_graph import GraphScene
from scenes.scene_hedge import HedgeScene
from scenes.scene_history import HistoryScene
from scenes.scene_inbox import InboxScene
from scenes.scene_intro import IntroScene
from scenes.scene_ipo import IPOScene
from scenes.scene_ma import MAScene
from scenes.scene_ma_target import MATargetScene
from scenes.scene_mandates import MandatesScene
from scenes.scene_markethub import MarketHubScene
from scenes.scene_menu import MenuScene
from scenes.scene_mission import MissionScene
from scenes.scene_more import MoreScene
from scenes.scene_news import NewsScene
from scenes.scene_notifications import NotificationsScene
from scenes.scene_options import OptionsScene
from scenes.scene_performance import PerformanceScene
from scenes.scene_portfolio import PortfolioScene
from scenes.scene_portfolio_unified import PortfolioUnifiedScene
from scenes.scene_quant import QuantScene
from scenes.scene_review import ReviewScene
from scenes.scene_risk import RiskScene
from scenes.scene_rivals import RivalsScene
from scenes.scene_runsetup import RunSetupScene
from scenes.scene_sandbox import SandboxScene
from scenes.scene_saves import SavesScene
from scenes.scene_settings import SettingsScene
from scenes.scene_shop import ShopScene
from scenes.scene_splash import SplashScene
from scenes.scene_spreadsheet import SpreadsheetScene
from scenes.scene_stresstest import StressTestScene
from scenes.scene_structured import StructuredScene
from scenes.scene_swaps import SwapsScene
from scenes.scene_team import TeamScene
from scenes.scene_terminal import TerminalScene
from scenes.scene_track import TrackScene
from scenes.scene_tradingwall import TradingWallScene
from scenes.scene_tutorials import TutorialsScene
from ui.logo import make_icon_surface
from ui.notifications import NotificationCenter


def build_scene_manager(app):
    """Crée un SceneManager flambant neuf avec une instance dédiée de
    chaque scène — utilisé pour le SceneManager principal de l'app et pour
    chaque nouvelle page (onglet), afin que chaque page ait son propre état
    (scroll, recherche, filtres...) totalement isolé des autres."""
    m = SceneManager(app)
    m.register("menu", MenuScene(app))
    m.register("continent", ContinentScene(app))
    m.register("runsetup", RunSetupScene(app))
    m.register("sandbox", SandboxScene(app))
    m.register("terminal", TerminalScene(app))
    m.register("desktop", DesktopScene(app))
    m.register("glossary", GlossaryScene(app))
    m.register("evaluation", EvaluationScene(app))
    m.register("portfolio", PortfolioScene(app))
    m.register("portfolio_unified", PortfolioUnifiedScene(app))
    m.register("ma", MAScene(app))
    m.register("ma_target", MATargetScene(app))
    m.register("mandates", MandatesScene(app))
    m.register("deals", DealsScene(app))
    m.register("track", TrackScene(app))
    m.register("risk", RiskScene(app))
    m.register("quant", QuantScene(app))
    m.register("spreadsheet", SpreadsheetScene(app))
    m.register("saves", SavesScene(app))
    m.register("gameover", GameOverScene(app))
    m.register("company", CompanyScene(app))
    m.register("compare", CompareScene(app))
    m.register("commands", CommandsScene(app))
    m.register("mission", MissionScene(app))
    m.register("career", CareerScene(app))
    m.register("book", BookScene(app))
    m.register("inbox", InboxScene(app))
    m.register("dilemma", DilemmaScene(app))
    m.register("intro", IntroScene(app))
    m.register("academy", AcademyScene(app))
    m.register("cert", CertScene(app))
    m.register("deal", DealScene(app))
    m.register("financials", FinancialsScene(app))
    m.register("bonds", BondsScene(app))
    m.register("governments", GovernmentsScene(app))
    m.register("commodities", CommoditiesScene(app))
    m.register("crypto", CryptoScene(app))
    m.register("dashboard", DashboardScene(app))
    m.register("etfs", ETFScene(app))
    m.register("news", NewsScene(app))
    m.register("notifications", NotificationsScene(app))
    m.register("more", MoreScene(app))
    m.register("structured", StructuredScene(app))
    m.register("credit", CreditScene(app))
    m.register("alm", AlmScene(app))
    m.register("swaps", SwapsScene(app))
    m.register("hedge", HedgeScene(app))
    m.register("options", OptionsScene(app))
    m.register("ipo", IPOScene(app))
    m.register("fx", FXScene(app))
    m.register("review", ReviewScene(app))
    m.register("calendar", CalendarScene(app))
    m.register("graph", GraphScene(app))
    m.register("rivals", RivalsScene(app))
    m.register("analytics", AnalyticsScene(app))
    m.register("frontier_lab", FrontierLabScene(app))
    m.register("performance", PerformanceScene(app))
    m.register("explorer", MarketExplorerScene(app))
    m.register("tutorials", TutorialsScene(app))
    m.register("alerts", AlertsScene(app))
    m.register("splash", SplashScene(app))
    m.register("markethub", MarketHubScene(app))
    m.register("wall", TradingWallScene(app))
    m.register("settings", SettingsScene(app))
    m.register("shop", ShopScene(app))
    m.register("examcert", ExamCertScene(app))
    m.register("stresstest", StressTestScene(app))
    m.register("history", HistoryScene(app))
    m.register("team", TeamScene(app))
    m.register("achievements", AchievementsScene(app))
    return m


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        pygame.display.set_icon(make_icon_surface(64))
        self.window_mode = display_settings.get_mode()
        self.screen = None
        self._apply_window_mode()
        self.clock = pygame.time.Clock()
        self.running = True
        self.cheats = False           # activé par main_cheat.py (commandes de test)
        self.sim_clock = SimClock()   # horloge de jeu temps réel (vitesse, pause)
        self.pending_market_steps = 0  # pas de marché bancarisés par l'horloge, à jouer au terminal

        # état de jeu courant (créé à la sélection du continent)
        self.gs = GameState()
        self.sheet = None       # tableur plein écran historique (créé à la 1re ouverture)
        self.workbook = None    # classeur multi-feuilles de l'app Tableur du bureau
        self.market = None  # moteur de marché (créé/synchronisé à l'entrée du terminal)
        self.notes = NotificationCenter()   # centre de notifications (toasts)

        # gestionnaire de scènes de l'onglet principal + système de pages
        main_manager = build_scene_manager(self)
        main_manager.go("splash")
        self.pages = PageManager(self, main_manager, main_scene_name="splash")

    @property
    def scenes(self):
        """SceneManager de l'onglet (page) actif. Toute la navigation
        existante (self.app.scenes.go(...)) agit donc sur la page courante."""
        return self.pages.manager

    def notify(self, text, kind="info"):
        """Pousse une notification (toast) affichée en overlay."""
        self.notes.push(text, kind)

    def route_scene(self, name, **kwargs):
        """Navigation FORCÉE par le jeu (pas un clic joueur) — ex. un dilemme
        qui se déclenche pendant que le temps passe. Si le bureau est la scène
        courante, ouvre `name` en fenêtre (comme un popup de choix parmi
        d'autres fenêtres) au lieu de basculer tout l'écran ; sinon,
        comportement classique (bascule plein écran)."""
        if self.scenes.current_name == "desktop":
            # popup FORCÉ (pas un clic joueur) : clignote dans la barre des
            # tâches tant qu'on ne l'a pas regardé (cf. Window.attention).
            self.scenes.current._open_scene_window(name, attention=True, **kwargs)
        else:
            self.scenes.go(name, **kwargs)

    def _apply_window_mode(self):
        """(Ré)applique le mode d'affichage courant. La résolution LOGIQUE reste
        toujours (SCREEN_WIDTH x WINDOW_HEIGHT) : en plein écran on s'appuie sur
        pygame.SCALED pour que l'image soit mise à l'échelle du moniteur (net sur
        écran Retina/Mac) sans rien recalculer dans les scènes."""
        size = (config.SCREEN_WIDTH, config.WINDOW_HEIGHT)
        if self.window_mode == "fullscreen":
            flags = pygame.FULLSCREEN | pygame.SCALED
        elif self.window_mode == "borderless":
            flags = pygame.NOFRAME | pygame.SCALED
        else:
            flags = 0
        try:
            self.screen = pygame.display.set_mode(size, flags)
        except Exception:
            # repli sûr : fenêtré classique si le mode plein écran échoue
            # (driver vidéo restreint, environnement headless…)
            self.window_mode = "windowed"
            self.screen = pygame.display.set_mode(size, 0)

    def set_window_mode(self, mode):
        """Change le mode d'affichage (fenêtré / plein écran / plein écran
        fenêtré), l'applique immédiatement et le persiste."""
        self.window_mode = display_settings.set_mode(mode)
        self._apply_window_mode()

    def toggle_fullscreen(self):
        """Bascule rapide (touche F11) fenêtré <-> plein écran."""
        self.set_window_mode("windowed" if self.window_mode == "fullscreen"
                             else "fullscreen")

    def ensure_market(self):
        """Crée/synchronise le moteur de marché avec l'état du joueur.
        Le marché est déterministe : (graine, nb de pas) reconstruit l'état exact.
        """
        p = self.gs.player
        if not p.market_seed:
            p.market_seed = random.randint(1, 2_000_000_000)
            p.market_step = 0
        if self.market is None or self.market.seed != p.market_seed:
            self.market = Market(seed=p.market_seed)
        self.market.sync_to(p.market_step)
        return self.market

    def run(self):
        while self.running:
            dt = self.clock.tick(config.FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                    continue
                self.pages.handle_event(event)
            if self.gs.player.market_seed:
                self.pending_market_steps += self.sim_clock.advance(dt, config.DAYS_PER_STEP)
            self.pages.update(dt)
            self.pages.draw(self.screen)
            pygame.display.flip()

        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    App().run()
