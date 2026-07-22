"""
scene_review.py — Revue de performance annuelle (négociation de bonus en cash).

Présente le résumé de performance (réputation, missions du grade, bonus standard
proposé) puis trois choix de négociation. Au clic, résout immédiatement via
`core.review.negotiate` et affiche le résultat avant de revenir au terminal.
"""
import pygame

from core import config
from core import review as R
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr


_CHOICES = [
    ("accept", ("Accepter le bonus standard", "Accept the standard bonus")),
    ("negotiate_up", ("Négocier à la hausse", "Negotiate for more")),
    ("ask_fixed", ("Demander une augmentation fixe", "Ask for a fixed raise")),
]


class ReviewScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        p = self.app.gs.player
        self.offer = p.pending_review
        self.state = "decide"
        self.result = None
        self.option_rects = {}
        self.focus = 0
        self.continue_btn = widgets.Button(
            (config.SCREEN_WIDTH // 2 - 130, config.SCREEN_HEIGHT - 78, 260, 48),
            _L("CONTINUER", "CONTINUE"), config.COL_UP)
        self.back_btn = widgets.Button(config.back_button_rect(),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def handle_event(self, event):
        if self.offer is None:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.app.scenes.back(self.return_to)
            if self.back_btn.handle(event):
                self.app.scenes.back(self.return_to)
            return
        if self.state == "decide" and self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state == "decide":
                for i, rect in self.option_rects.items():
                    if rect.collidepoint(event.pos):
                        self._choose(i)
            elif self.state == "outcome" and self.continue_btn.rect.collidepoint(event.pos):
                self._leave()
        if event.type == pygame.KEYDOWN:
            if self.state == "outcome" and event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self._leave()
            elif self.state == "decide":
                n = len(_CHOICES)
                if event.key in (pygame.K_DOWN, pygame.K_TAB):
                    self.focus = (self.focus + 1) % n
                elif event.key == pygame.K_UP:
                    self.focus = (self.focus - 1) % n
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._choose(self.focus)
                elif event.key == pygame.K_ESCAPE:
                    self.app.scenes.back(self.return_to)

    def _choose(self, i):
        p = self.app.gs.player
        choice_id = _CHOICES[i][0]
        self.result = R.negotiate(p, choice_id)
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)
        self.state = "outcome"

    def _leave(self):
        p = self.app.gs.player
        if p.check_game_over():
            self.app.scenes.go("gameover")
        else:
            self.app.scenes.back(self.return_to)

    def update(self, dt):
        self.continue_btn.update(pygame.mouse.get_pos(), dt)
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        if self.offer is None:
            widgets.draw_text(surf, _L("Aucune revue de performance en attente.", "No pending performance review."),
                              (40, 40), fonts.head(bold=True), config.COL_TEXT_DIM)
            widgets.draw_text(surf, _L("ESC pour revenir.", "ESC to return."), (40, 90), fonts.small(),
                              config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            return
        widgets.draw_text(surf, _L("REVUE DE PERFORMANCE", "PERFORMANCE REVIEW"), (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_badge(surf, "ANNUELLE", (config.SCREEN_WIDTH - 40, 30),
                           config.COL_CYAN, align="right")

        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        panel = pygame.Rect(120, 100, config.SCREEN_WIDTH - 240, 150)
        inner = widgets.draw_panel(surf, panel, _L("Bilan annuel", "Annual review"), config.COL_CYAN)
        o = self.offer
        lines = _L(
            f"Réputation actuelle : {o['reputation']}/100\n"
            f"Missions réalisées ce grade : {o['grade_missions']}\n"
            f"P&L réalisé récent : {widgets.format_money(o['realized_pnl'], cur)}\n"
            f"Bonus standard proposé : {widgets.format_money(o['standard_bonus'], cur)}",
            f"Current reputation: {o['reputation']}/100\n"
            f"Missions completed this grade: {o['grade_missions']}\n"
            f"Recent realized P&L: {widgets.format_money(o['realized_pnl'], cur)}\n"
            f"Standard bonus offered: {widgets.format_money(o['standard_bonus'], cur)}"
        )
        widgets.draw_text_wrapped(surf, lines, (inner.x, inner.y), fonts.body(),
                                  config.COL_TEXT, inner.w, line_gap=6)

        if self.state == "decide":
            self._draw_options(surf, cur)
        else:
            self._draw_outcome(surf, cur)

    def _draw_options(self, surf, cur):
        self.option_rects = {}
        widgets.draw_text(surf, _L("Votre réponse :", "Your response:"), (120, 270), fonts.small(bold=True),
                          config.COL_TEXT_DIM)
        y = 300
        mp = pygame.mouse.get_pos()
        for i, (_, label_pair) in enumerate(_CHOICES):
            label = _L(*label_pair)
            rect = pygame.Rect(120, y, config.SCREEN_WIDTH - 240, 60)
            self.option_rects[i] = rect
            hover = rect.collidepoint(mp)
            focused = (i == self.focus)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if (hover or focused) else config.COL_PANEL, rect)
            pygame.draw.rect(surf, config.COL_CYAN if (hover or focused) else config.COL_AMBER, rect,
                             3 if focused else (2 if hover else 1))
            widgets.draw_text(surf, f"{chr(65+i)}. {label}", (rect.x + 16, rect.y + 18),
                              fonts.body(bold=True), config.COL_WHITE)
            y += 70
        self.back_btn.draw(surf)

    def _draw_outcome(self, surf, cur):
        r = self.result
        panel = pygame.Rect(120, 280, config.SCREEN_WIDTH - 240, 200)
        inner = widgets.draw_panel(surf, panel, _L("Issue de la négociation", "Negotiation outcome"), config.COL_CYAN)
        widgets.draw_text_wrapped(surf, r.get("message", ""), (inner.x, inner.y),
                                  fonts.body(), config.COL_TEXT, inner.w, line_gap=6)
        eff = []
        bonus_paid = r.get("bonus_paid", 0.0)
        if bonus_paid:
            eff.append((_L(f"bonus +{widgets.format_money(bonus_paid, cur)}", f"bonus +{widgets.format_money(bonus_paid, cur)}"), config.COL_UP))
        rep_delta = r.get("rep_delta", 0)
        if rep_delta:
            eff.append((_L(f"réputation {rep_delta:+d}", f"reputation {rep_delta:+d}"),
                        config.COL_UP if rep_delta >= 0 else config.COL_DOWN))
        x = inner.x
        for text, c in eff:
            rct = widgets.draw_text(surf, text, (x, inner.bottom - 40), fonts.small(bold=True), c)
            x = rct.right + 20
        self.continue_btn.draw(surf)
