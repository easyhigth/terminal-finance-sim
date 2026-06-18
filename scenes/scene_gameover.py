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
            (config.SCREEN_WIDTH // 2 - 150, 678, 300, 32),
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
        left = pygame.Rect(cx - 380, 290, 380, 260)
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
        right = pygame.Rect(cx + 10, 290, 370, 260)
        rinner = widgets.draw_panel(surf, right, "Journal de carrière", config.COL_AMBER)
        if p.journal:
            yy = rinner.y
            for e in list(reversed(p.journal))[:8]:
                widgets.draw_text(surf, f"J{e['day']}", (rinner.x, yy),
                                  fonts.tiny(bold=True), config.COL_CYAN)
                widgets.draw_text(surf, e["text"][:40], (rinner.x + 46, yy),
                                  fonts.tiny(), config.COL_TEXT)
                yy += 24
        else:
            widgets.draw_text(surf, "Carrière trop courte pour laisser une trace.",
                              (rinner.x, rinner.y), fonts.small(), config.COL_TEXT_DIM)

        # panneau bas : rétrospective graphique de la valeur nette
        bottom = pygame.Rect(cx - 380, 558, 760, 100)
        binner = widgets.draw_panel(surf, bottom, "Rétrospective — valeur nette", config.COL_CYAN)
        self._draw_networth_retrospective(surf, binner, p, cur)

        if p.hardcore:
            widgets.draw_badge(surf, "HARDCORE — SAUVEGARDE EFFACÉE",
                               (cx, 666), config.COL_DOWN, align="center")

        self.menu_btn.draw(surf)

    def _draw_networth_retrospective(self, surf, inner, p, cur):
        """Sparkline de `cash_history` avec annotation du meilleur et du pire
        moment de la carrière. Reste discret si l'historique est trop court."""
        hist = p.cash_history or []
        if len(hist) < 2:
            widgets.draw_text(surf, "Historique trop court pour un graphique.",
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            return

        chart_rect = pygame.Rect(inner.x + 50, inner.y, inner.w - 60, inner.h - 20)
        lo, hi = min(hist), max(hist)
        lo, hi, span = widgets.draw_chart_axes(
            surf, chart_rect, lo, hi,
            y_fmt=lambda v: widgets.format_money(v, cur), rows=2)
        widgets.draw_series(surf, chart_rect, hist, config.COL_CYAN, baseline=False)

        # repère du meilleur et du pire point de la série
        i_max = max(range(len(hist)), key=lambda i: hist[i])
        i_min = min(range(len(hist)), key=lambda i: hist[i])
        n = len(hist)

        def pt(i):
            x = chart_rect.x + int(i / (n - 1) * chart_rect.w)
            y = chart_rect.bottom - int((hist[i] - lo) / span * chart_rect.h)
            return x, y

        x_max, y_max = pt(i_max)
        x_min, y_min = pt(i_min)
        pygame.draw.circle(surf, config.COL_UP, (x_max, y_max), 4)
        pygame.draw.circle(surf, config.COL_DOWN, (x_min, y_min), 4)

        best = max(p.best_cash, hist[i_max])
        label_y = inner.y + inner.h - 14
        widgets.draw_text(surf, f"Record : {widgets.format_money(best, cur)}",
                          (inner.x, label_y), fonts.tiny(bold=True), config.COL_UP)
        widgets.draw_text(surf, f"Plus bas : {widgets.format_money(hist[i_min], cur)}",
                          (inner.x + 220, label_y), fonts.tiny(bold=True), config.COL_DOWN)
