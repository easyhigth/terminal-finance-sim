"""
scene_track.py — Choix de la voie de spécialisation.
Débloqué après le grade Analyst. Chaque voie ouvre des modules,
des questions d'évaluation et des concepts spécifiques.
"""
import pygame

from core import config, tracks
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
        self.return_to = kwargs.get("return_to", "terminal")
        self.selected = None
        self.confirm = widgets.Button(
            (config.SCREEN_WIDTH//2-150, config.SCREEN_HEIGHT-58, 300, 44),
            "CONFIRMER LA VOIE", config.COL_UP, enabled=False)
        self.back = widgets.Button(
            (40, config.SCREEN_HEIGHT-58, 160, 44), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self._cards = {}
        self._names = list(TRACK_INFO.keys())
        self.focus = 0   # index de la carte ayant le focus clavier

    def _select(self, name):
        self.selected = name
        self.confirm.enabled = True

    def _confirm_track(self):
        if not self.selected:
            return
        p = self.app.gs.player
        p.track = self.selected
        p.flags["can_choose_track"] = False
        self.app.gs.save(config.AUTOSAVE_SLOT)
        self.app.scenes.go(self.return_to)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in self._cards.items():
                if rect.collidepoint(event.pos):
                    self._select(name)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.scenes.go(self.return_to)
                return
            if event.key in (pygame.K_TAB, pygame.K_RIGHT, pygame.K_LEFT,
                             pygame.K_UP, pygame.K_DOWN):
                n = len(self._names)
                step = -1 if event.key in (pygame.K_LEFT, pygame.K_UP) else 1
                self.focus = (self.focus + step) % n
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._select(self._names[self.focus])
        if self.back.handle(event):
            self.app.scenes.go(self.return_to)
        if self.confirm.handle(event):
            self._confirm_track()

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
        n = len(TRACK_INFO)
        margin, gap = 20, 12
        cw = (config.SCREEN_WIDTH - 2 * margin - (n - 1) * gap) // n
        x0 = margin
        y0 = 108
        ch = config.SCREEN_HEIGHT - y0 - 70   # laisse la place au footer de boutons
        pad = 14
        text_w = cw - 2 * pad
        for i, (name, info) in enumerate(TRACK_INFO.items()):
            x = x0 + i * (cw + gap)
            y = y0
            rect = pygame.Rect(x, y, cw, ch)
            self._cards[name] = rect
            sel = (self.selected == name)
            focused = (self.focus == i)
            accent = info["color"]
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect)
            border_col = config.COL_CYAN if focused else (accent if sel else config.COL_BORDER)
            pygame.draw.rect(surf, border_col, rect, 2 if (sel or focused) else 1)

            ty = y + pad
            widgets.draw_text(surf, name.upper(), (x + pad, ty),
                              fonts.head(bold=True), accent)
            ty += fonts.head().get_height() + 8

            desc_h = widgets.draw_text_wrapped(surf, info["desc"], (x + pad, ty),
                                               fonts.small(), config.COL_TEXT, text_w, line_gap=3)
            ty += desc_h + 10

            widgets.draw_text(surf, "AVANTAGE DE JEU :", (x + pad, ty),
                              fonts.tiny(bold=True), accent)
            ty += fonts.tiny(bold=True).get_height() + 4
            perk_h = widgets.draw_text_wrapped(surf, tracks.label(name), (x + pad, ty),
                                               fonts.tiny(), config.COL_WHITE, text_w, line_gap=2)
            ty += perk_h + 10

            widgets.draw_text(surf, "CONCEPTS CLÉS :", (x + pad, ty),
                              fonts.tiny(bold=True), config.COL_TEXT_DIM)
            ty += fonts.tiny(bold=True).get_height() + 4
            widgets.draw_text_wrapped(surf, info["concepts"], (x + pad, ty),
                                      fonts.tiny(), config.COL_NEUTRAL, text_w, line_gap=2)

            footer_label = "VOIE SÉLECTIONNÉE ✓" if sel else "SÉLECTIONNER CETTE VOIE"
            widgets.draw_card_footer(surf, rect, footer_label, accent,
                                     hover=rect.collidepoint(pygame.mouse.get_pos()))

        self.confirm.draw(surf)
        self.back.draw(surf)
