"""
scene_intro.py — Briefing de lancement d'une nouvelle partie.
Explique le but du jeu et son fonctionnement avant d'entrer dans le terminal.
"""
import pygame

from core import config
from core.scene_manager import Scene
from ui import fonts, widgets

GOAL = ("De stagiaire à Partner : gravissez 12 grades en bâtissant votre "
        "réputation et votre fortune, dans une simulation de marché vivante.")

HOW = [
    ("ADV", "Avance le temps de 5 jours. Le marché (320 sociétés fictives, "
            "interconnectées) évolue, des actus et des crises surgissent."),
    ("MISSION", "Accomplis le travail de ton grade (analyse, décisions...) "
                "pour gagner de la réputation."),
    ("EVAL", "Quand réputation + critères (missions, deals, ancienneté) sont "
             "réunis, passe l'examen pour être promu."),
    ("BUY / SELL", "Investis dans de vraies sociétés du roster : ta VALEUR NETTE "
                   "monte et descend avec le marché. RESEARCH pour une reco."),
    ("DEALS / MANDATS", "Traite des opportunités à délai et gère des mandats "
                        "clients (objectif de rendement + limite de risque)."),
    ("DÉCISIONS", "Des dilemmes éthiques/réglementaires : couper les coins paie… "
                  "mais fait monter le scrutin réglementaire (risque d'enquête)."),
    ("RIVAUX & CRISES", "Des concurrents te disputent les deals ; des crises "
                        "(krach, choc de taux...) frappent ton portefeuille."),
]


class IntroScene(Scene):
    def on_enter(self, **kwargs):
        self.start_btn = widgets.Button(
            (config.SCREEN_WIDTH // 2 - 150, config.SCREEN_HEIGHT - 64, 300, 48),
            "COMMENCER LA CARRIÈRE", config.COL_UP)

    def handle_event(self, event):
        if self.start_btn.handle(event):
            self.app.scenes.go("terminal")
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            self.app.scenes.go("terminal")

    def update(self, dt):
        self.start_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        cx = config.SCREEN_WIDTH // 2
        widgets.draw_text(surf, "BIENVENUE AU TERMINAL", (cx, 30),
                          fonts.title(bold=True), config.COL_AMBER, align="center")
        info = config.CONTINENTS.get(p.continent, {})
        sub = f"{p.continent} · {info.get('regulator','')} · devise {info.get('currency','$')}"
        widgets.draw_text(surf, sub, (cx, 78), fonts.small(), config.COL_TEXT_DIM, align="center")

        # but du jeu
        goal = pygame.Rect(cx - 460, 110, 920, 78)
        gi = widgets.draw_panel(surf, goal, "Votre objectif", config.COL_CYAN)
        widgets.draw_text_wrapped(surf, GOAL, (gi.x, gi.y), fonts.body(),
                                  config.COL_TEXT, gi.w, line_gap=6)

        # comment ça marche
        how = pygame.Rect(cx - 460, 200, 920, config.footer_y() - 210)
        hi = widgets.draw_panel(surf, how, "Comment ça fonctionne", config.COL_AMBER)
        y = hi.y
        for cmd, desc in HOW:
            widgets.draw_text(surf, cmd, (hi.x, y), fonts.body(bold=True), config.COL_AMBER)
            h = widgets.draw_text_wrapped(surf, desc, (hi.x + 200, y), fonts.small(),
                                          config.COL_TEXT, hi.w - 200, line_gap=3)
            y += max(28, h + 10)
        widgets.draw_text(surf, "Astuce : tout se pilote au clavier (ou via le rail à "
                                "gauche). Tape COMMANDS pour la liste, clique la carte pour zoomer.",
                          (hi.x, hi.bottom - 18), fonts.tiny(), config.COL_TEXT_DIM)

        self.start_btn.draw(surf)
