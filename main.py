"""
main.py — Point d'entrée du jeu.
Lancement :  python main.py
Dépendances : pygame  (pip install pygame)
"""
import sys
import random
import pygame
from core import config
from core.game_state import GameState
from core.scene_manager import SceneManager
from core.market import Market
from ui.notifications import NotificationCenter
from scenes.scene_menu import MenuScene
from scenes.scene_continent import ContinentScene
from scenes.scene_terminal import TerminalScene
from scenes.scene_glossary import GlossaryScene
from scenes.scene_evaluation import EvaluationScene
from scenes.scene_portfolio import PortfolioScene
from scenes.scene_ma import MAScene
from scenes.scene_track import TrackScene
from scenes.scene_risk import RiskScene
from scenes.scene_quant import QuantScene
from scenes.scene_spreadsheet import SpreadsheetScene
from scenes.scene_saves import SavesScene
from scenes.scene_gameover import GameOverScene
from scenes.scene_company import CompanyScene
from scenes.scene_commands import CommandsScene
from scenes.scene_mission import MissionScene
from scenes.scene_career import CareerScene
from scenes.scene_book import BookScene
from scenes.scene_inbox import InboxScene
from scenes.scene_dilemma import DilemmaScene
from scenes.scene_intro import IntroScene
from scenes.scene_academy import AcademyScene
from scenes.scene_cert import CertScene
from scenes.scene_deal import DealScene
from scenes.scene_financials import FinancialsScene
from scenes.scene_bonds import BondsScene
from scenes.scene_governments import GovernmentsScene
from scenes.scene_commodities import CommoditiesScene
from scenes.scene_crypto import CryptoScene
from scenes.scene_structured import StructuredScene
from scenes.scene_credit import CreditScene
from scenes.scene_alm import AlmScene
from scenes.scene_graph import GraphScene
from scenes.scene_rivals import RivalsScene
from scenes.scene_analytics import AnalyticsScene
from scenes.scene_tutorials import TutorialsScene
from scenes.scene_splash import SplashScene
from ui.logo import make_icon_surface


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        pygame.display.set_icon(make_icon_surface(64))
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.cheats = False           # activé par main_cheat.py (commandes de test)
        self.advance_on_return = 0    # tics de temps à jouer au retour au terminal

        # état de jeu courant (créé à la sélection du continent)
        self.gs = GameState()
        self.sheet = None   # tableur partagé (créé à la 1re ouverture)
        self.market = None  # moteur de marché (créé/synchronisé à l'entrée du terminal)
        self.notes = NotificationCenter()   # centre de notifications (toasts)

        # gestionnaire de scènes
        self.scenes = SceneManager(self)
        self.scenes.register("menu", MenuScene(self))
        self.scenes.register("continent", ContinentScene(self))
        self.scenes.register("terminal", TerminalScene(self))
        self.scenes.register("glossary", GlossaryScene(self))
        self.scenes.register("evaluation", EvaluationScene(self))
        self.scenes.register("portfolio", PortfolioScene(self))
        self.scenes.register("ma", MAScene(self))
        self.scenes.register("track", TrackScene(self))
        self.scenes.register("risk", RiskScene(self))
        self.scenes.register("quant", QuantScene(self))
        self.scenes.register("spreadsheet", SpreadsheetScene(self))
        self.scenes.register("saves", SavesScene(self))
        self.scenes.register("gameover", GameOverScene(self))
        self.scenes.register("company", CompanyScene(self))
        self.scenes.register("commands", CommandsScene(self))
        self.scenes.register("mission", MissionScene(self))
        self.scenes.register("career", CareerScene(self))
        self.scenes.register("book", BookScene(self))
        self.scenes.register("inbox", InboxScene(self))
        self.scenes.register("dilemma", DilemmaScene(self))
        self.scenes.register("intro", IntroScene(self))
        self.scenes.register("academy", AcademyScene(self))
        self.scenes.register("cert", CertScene(self))
        self.scenes.register("deal", DealScene(self))
        self.scenes.register("financials", FinancialsScene(self))
        self.scenes.register("bonds", BondsScene(self))
        self.scenes.register("governments", GovernmentsScene(self))
        self.scenes.register("commodities", CommoditiesScene(self))
        self.scenes.register("crypto", CryptoScene(self))
        self.scenes.register("structured", StructuredScene(self))
        self.scenes.register("credit", CreditScene(self))
        self.scenes.register("alm", AlmScene(self))
        self.scenes.register("graph", GraphScene(self))
        self.scenes.register("rivals", RivalsScene(self))
        self.scenes.register("analytics", AnalyticsScene(self))
        self.scenes.register("tutorials", TutorialsScene(self))
        self.scenes.register("splash", SplashScene(self))
        self.scenes.go("splash")

    def notify(self, text, kind="info"):
        """Pousse une notification (toast) affichée en overlay."""
        self.notes.push(text, kind)

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
                self.scenes.handle_event(event)
            self.scenes.update(dt)
            self.scenes.draw(self.screen)
            pygame.display.flip()

        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    App().run()
