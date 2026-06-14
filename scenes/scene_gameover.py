"""
scene_gameover.py — Écran de fin de partie (faillite ou réputation anéantie).
Affiche le motif, un récapitulatif de carrière, et renvoie au menu.
En mode hardcore, la sauvegarde automatique est effacée (run définitif).
"""
import math
import pygame
from core import config
from core.scene_manager import Scene
from core.game_state import GameState
from ui import fonts, widgets


class GameOverScene(Scene):
    def on_enter(self, **kwargs):
        self.t = 0.0
        p = self.app.gs.player
        # run définitif en hardcore : on efface l'autosave
        if p.hardcore:
            GameState.delete(config.AUTOSAVE_SLOT)
        self.menu_btn = widgets.Button(
            (config.SCREEN_WIDTH // 2 - 150, 640, 300, 52),
            "RETOUR AU MENU", config.COL_AMBER)

    def handle_event(self, event):
        if self.menu_btn.handle(event):
            self.app.scenes.go("menu")
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            self.app.scenes.go("menu")

    def update(self, dt):
        self.t += dt
        self.menu_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        cx = config.SCREEN_WIDTH // 2

        # titre pulsé en rouge
        pulse = 0.5 + 0.5 * math.sin(self.t * 2.5)
        col = widgets._lerp_col(config.COL_DOWN, (120, 20, 24), pulse)
        widgets.draw_text(surf, "GAME OVER", (cx, 150),
                          fonts.huge(bold=True), col, align="center")
        widgets.draw_text(surf, "FIN DE CARRIÈRE", (cx, 232),
                          fonts.head(), config.COL_TEXT_DIM, align="center")

        info = config.CONTINENTS.get(p.continent, {})
        cur = info.get("currency", "$")

        # panneau gauche : rapport final + stats de run
        left = pygame.Rect(cx - 380, 290, 380, 330)
        inner = widgets.draw_panel(surf, left, "Rapport final", config.COL_DOWN)
        h = widgets.draw_text_wrapped(surf, p.game_over_reason or "Partie terminée.",
                                      (inner.x, inner.y), fonts.small(),
                                      config.COL_TEXT, inner.w, line_gap=5)
        lines = [
            f"Nom         : {p.name}",
            f"Grade final : {p.grade}",
            f"Voie        : {p.track}",
            f"Région      : {p.continent}",
            f"Carrière    : {p.quarter} trimestres ({p.day} j)",
            f"Trésorerie  : {widgets.format_money(p.cash, cur)}",
            f"Record cash : {widgets.format_money(max(p.best_cash, p.cash), cur)}",
            f"Réputation  : {p.reputation}/100",
            f"Deals       : {p.deals_won}   Missions : {p.missions_done}",
        ]
        y = inner.y + h + 10
        for ln in lines:
            widgets.draw_text(surf, ln, (inner.x, y), fonts.small(), config.COL_TEXT)
            y += 24
        if p.titles:
            widgets.draw_text_wrapped(surf, "Titres : " + " · ".join(p.titles),
                                      (inner.x, y + 2), fonts.tiny(), config.COL_WARN, inner.w)

        # panneau droit : journal de carrière (rétrospective)
        right = pygame.Rect(cx + 10, 290, 370, 330)
        rinner = widgets.draw_panel(surf, right, "Journal de carrière", config.COL_AMBER)
        if p.journal:
            yy = rinner.y
            for e in list(reversed(p.journal))[:11]:
                widgets.draw_text(surf, f"J{e['day']}", (rinner.x, yy),
                                  fonts.tiny(bold=True), config.COL_CYAN)
                widgets.draw_text(surf, e["text"][:40], (rinner.x + 46, yy),
                                  fonts.tiny(), config.COL_TEXT)
                yy += 24
        else:
            widgets.draw_text(surf, "Carrière trop courte pour laisser une trace.",
                              (rinner.x, rinner.y), fonts.small(), config.COL_TEXT_DIM)

        if p.hardcore:
            widgets.draw_badge(surf, "HARDCORE — SAUVEGARDE EFFACÉE",
                               (cx, 628), config.COL_DOWN, align="center")

        self.menu_btn.draw(surf)
