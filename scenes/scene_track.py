"""
scene_track.py — Choix de la voie de spécialisation.
Débloqué après le grade Analyst. Chaque voie ouvre des modules,
des questions d'évaluation et des concepts spécifiques.
"""
import pygame
from core import config
from core.scene_manager import Scene
from ui import fonts, widgets

TRACK_INFO = {
    "Portfolio": {
        "color": config.COL_CYAN,
        "desc": "Gestion de portefeuille : allocation d'actifs, frontière efficiente, "
                "optimisation moyenne-variance, suivi du Sharpe et rebalancement.",
        "concepts": "Markowitz, CAPM, Sharpe/Sortino, beta, rebalancing, tracking error.",
    },
    "M&A": {
        "color": config.COL_UP,
        "desc": "Fusions & acquisitions : valorisation, LBO, analyse relutif/dilutif, "
                "structuration de deals et synergies.",
        "concepts": "DCF, comparables, LBO, accretion/dilution, goodwill, due diligence.",
    },
    "Risk": {
        "color": config.COL_DOWN,
        "desc": "Gestion des risques : mesure et limitation de l'exposition, "
                "VaR/CVaR, stress tests, couverture et conformité prudentielle.",
        "concepts": "VaR, CVaR, stress testing, Bâle III, hedging, scénarios.",
    },
    "Quant": {
        "color": config.COL_WARN,
        "desc": "Quantitatif : pricing de dérivés, Greeks, modèles stochastiques, "
                "backtesting de stratégies systématiques.",
        "concepts": "Black-Scholes, Greeks, vol implicite, backtest, séries temporelles.",
    },
    "Advisory": {
        "color": config.COL_EUROPE,
        "desc": "Conseil : structuration de financements, relations clients, "
                "négociation et exécution d'opérations stratégiques.",
        "concepts": "Structuration, pitch, négociation, financement, conformité.",
    },
}


class TrackScene(Scene):
    def on_enter(self, **kwargs):
        self.selected = None
        self.confirm = widgets.Button(
            (config.SCREEN_WIDTH//2-150, config.SCREEN_HEIGHT-80, 300, 50),
            "CONFIRMER LA VOIE", config.COL_UP, enabled=False)
        self.back = widgets.Button(
            (40, config.SCREEN_HEIGHT-80, 160, 50), "← TERMINAL", config.COL_TEXT_DIM)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in getattr(self, "_cards", {}).items():
                if rect.collidepoint(event.pos):
                    self.selected = name
                    self.confirm.enabled = True
        if self.back.handle(event):
            self.app.scenes.go("terminal")
        if self.confirm.handle(event) and self.selected:
            p = self.app.gs.player
            p.track = self.selected
            p.flags["can_choose_track"] = False
            self.app.gs.save(config.AUTOSAVE_SLOT)
            self.app.scenes.go("terminal")

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.confirm.update(mp)
        self.back.update(mp)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "CHOISISSEZ VOTRE VOIE", (40, 24),
                          fonts.title(bold=True), config.COL_AMBER)
        p = self.app.gs.player
        widgets.draw_text(surf, f"Grade {p.grade}. Votre spécialisation oriente vos modules et évaluations.",
                          (42, 76), fonts.small(), config.COL_TEXT_DIM)

        self._cards = {}
        cols = 3
        cw, ch, gap = 380, 200, 20
        x0 = 40
        y0 = 120
        for i, (name, info) in enumerate(TRACK_INFO.items()):
            col = i % cols
            row = i // cols
            x = x0 + col * (cw + gap)
            y = y0 + row * (ch + gap)
            rect = pygame.Rect(x, y, cw, ch)
            self._cards[name] = rect
            sel = (self.selected == name)
            accent = info["color"]
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect)
            pygame.draw.rect(surf, accent if sel else config.COL_BORDER, rect, 2 if sel else 1)
            widgets.draw_text(surf, name.upper(), (x+16, y+14),
                              fonts.head(bold=True), accent)
            widgets.draw_text_wrapped(surf, info["desc"], (x+16, y+52),
                                      fonts.small(), config.COL_TEXT, cw-32, line_gap=4)
            widgets.draw_text(surf, "Concepts clés :", (x+16, y+ch-58),
                              fonts.tiny(bold=True), config.COL_TEXT_DIM)
            widgets.draw_text_wrapped(surf, info["concepts"], (x+16, y+ch-42),
                                      fonts.tiny(), config.COL_NEUTRAL, cw-32, line_gap=2)

        self.confirm.draw(surf)
        self.back.draw(surf)
