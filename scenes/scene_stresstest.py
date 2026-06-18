"""
scene_stresstest.py — Stress test réglementaire périodique.

Présente le scénario de choc tiré par le superviseur fictif, l'impact simulé sur le
book réel (montant et % de la valeur nette) et le verdict (réussi/échoué), puis deux
choix de réponse. Au clic, résout immédiatement via `core.stresstest.acknowledge` et
affiche le résultat avant de revenir au terminal.
"""
import pygame
from core import config
from core import stresstest as ST
from core.scene_manager import Scene
from ui import fonts, widgets

_CHOICES = [
    ("accept", "Prendre acte (aucun coût)"),
    ("hedge_now", "Renforcer la couverture immédiatement"),
]


class StressTestScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        p = self.app.gs.player
        self.test = p.pending_stresstest
        self.state = "decide"
        self.result = None
        self.option_rects = {}
        self.focus = 0
        self.continue_btn = widgets.Button(
            (config.SCREEN_WIDTH // 2 - 130, config.SCREEN_HEIGHT - 78, 260, 48),
            "RETOUR AU TERMINAL", config.COL_UP)

    def handle_event(self, event):
        if self.test is None:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.app.scenes.go(self.return_to)
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
                    self.app.scenes.go(self.return_to)

    def _choose(self, i):
        p = self.app.gs.player
        action_id = _CHOICES[i][0]
        self.result = ST.acknowledge(p, action_id)
        if not p.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)
        self.state = "outcome"

    def _leave(self):
        p = self.app.gs.player
        if p.check_game_over():
            self.app.scenes.go("gameover")
        else:
            self.app.scenes.go(self.return_to)

    def update(self, dt):
        self.continue_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        if self.test is None:
            widgets.draw_text(surf, "Aucun stress test réglementaire en attente.",
                              (40, 40), fonts.head(bold=True), config.COL_TEXT_DIM)
            widgets.draw_text(surf, "ESC pour revenir.", (40, 90), fonts.small(),
                              config.COL_TEXT_DIM)
            return
        widgets.draw_text(surf, "STRESS TEST RÉGLEMENTAIRE", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_badge(surf, "SEMESTRIEL", (config.SCREEN_WIDTH - 40, 30),
                           config.COL_CYAN, align="right")

        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        panel = pygame.Rect(120, 100, config.SCREEN_WIDTH - 240, 150)
        inner = widgets.draw_panel(surf, panel, "Scénario imposé par le superviseur", config.COL_CYAN)
        t = self.test
        verdict = "RÉUSSI" if t["passed"] else "ÉCHOUÉ"
        vcol = config.COL_UP if t["passed"] else config.COL_DOWN
        lines = (
            f"Scénario : {t['scenario']}\n"
            f"Impact total simulé : {widgets.format_money(t['impact_total']*1e6, cur)} "
            f"({t['loss_ratio']*100:.1f}% de la valeur nette)\n"
            f"Seuil de tolérance : {t['fail_ratio']*100:.0f}% de la valeur nette\n"
            f"Valeur nette : {widgets.format_money(t['net_worth'], cur)}"
        )
        widgets.draw_text_wrapped(surf, lines, (inner.x, inner.y), fonts.body(),
                                  config.COL_TEXT, inner.w, line_gap=6)
        widgets.draw_text(surf, f"VERDICT : {verdict}", (inner.x, inner.bottom - 28),
                          fonts.body(bold=True), vcol)

        if self.state == "decide":
            self._draw_options(surf, cur)
        else:
            self._draw_outcome(surf, cur)

    def _draw_options(self, surf, cur):
        self.option_rects = {}
        widgets.draw_text(surf, "Votre réponse :", (120, 270), fonts.small(bold=True),
                          config.COL_TEXT_DIM)
        y = 300
        mp = pygame.mouse.get_pos()
        for i, (_, label) in enumerate(_CHOICES):
            rect = pygame.Rect(120, y, config.SCREEN_WIDTH - 240, 60)
            self.option_rects[i] = rect
            hover = rect.collidepoint(mp)
            focused = (i == self.focus)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if (hover or focused) else config.COL_PANEL, rect)
            pygame.draw.rect(surf, config.COL_CYAN if (hover or focused) else config.COL_BORDER, rect,
                             3 if focused else (2 if hover else 1))
            widgets.draw_text(surf, f"{chr(65+i)}. {label}", (rect.x + 16, rect.y + 18),
                              fonts.body(bold=True), config.COL_WHITE)
            y += 70

    def _draw_outcome(self, surf, cur):
        r = self.result
        panel = pygame.Rect(120, 280, config.SCREEN_WIDTH - 240, 200)
        inner = widgets.draw_panel(surf, panel, "Issue du contrôle réglementaire", config.COL_CYAN)
        widgets.draw_text_wrapped(surf, r.get("message", ""), (inner.x, inner.y),
                                  fonts.body(), config.COL_TEXT, inner.w, line_gap=6)
        eff = []
        cash_delta = r.get("cash_delta", 0.0)
        if cash_delta:
            eff.append((f"trésorerie {widgets.format_money(cash_delta, cur)}",
                        config.COL_UP if cash_delta >= 0 else config.COL_DOWN))
        rep_delta = r.get("rep_delta", 0)
        if rep_delta:
            eff.append((f"réputation {rep_delta:+d}",
                        config.COL_UP if rep_delta >= 0 else config.COL_DOWN))
        x = inner.x
        for text, c in eff:
            rct = widgets.draw_text(surf, text, (x, inner.bottom - 40), fonts.small(bold=True), c)
            x = rct.right + 20
        self.continue_btn.draw(surf)
