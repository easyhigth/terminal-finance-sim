"""
scene_history.py — Historique de carrière consultable à tout moment (pas
seulement en fin de partie). Reprend le style de scenes/scene_career.py
(panneaux, bouton retour) et la logique de graphique de
scenes/scene_gameover.py::_draw_networth_retrospective (sparkline de
cash_history) + une timeline du journal de carrière via
core/career_history.py::format_timeline.

Ouvert via HISTORY depuis le terminal (câblage central, hors périmètre ici).
"""
import pygame

from core import config
from core.career_history import format_timeline
from core.scene_manager import Scene
from ui import fonts, widgets

_KIND_COLORS = {
    "promo": config.COL_UP, "deal": config.COL_DEAL, "crisis": config.COL_DOWN,
    "objective": config.COL_CYAN, "info": config.COL_TEXT_DIM,
}


class HistoryScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button(
            (config.back_button_rect(200)[0] + 220,
             config.back_button_rect(200)[1], 150, 42),
            "📘 TUTO", config.COL_CYAN)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="history", return_to="history")

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.tuto_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        widgets.draw_text(surf, "HISTORIQUE DE CARRIÈRE", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        sub = f"{p.name} · {p.grade} · jour {p.day} (T{p.quarter})"
        widgets.draw_text(surf, sub, (42, 72), fonts.small(), config.COL_TEXT_DIM)

        M = config.MARGIN
        top = config.content_top()
        bottom = config.footer_y() - 8
        total_h = bottom - top
        chart_h = int(total_h * 0.42)
        gap = 12
        journal_h = total_h - chart_h - gap

        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")
        chart_rect = pygame.Rect(M, top, config.SCREEN_WIDTH - 2 * M, chart_h)
        self._draw_networth_chart(surf, chart_rect, p, cur)

        journal_rect = pygame.Rect(M, top + chart_h + gap,
                                   config.SCREEN_WIDTH - 2 * M, journal_h)
        self._draw_timeline(surf, journal_rect, p)

        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)

    def _draw_networth_chart(self, surf, rect, p, cur):
        inner = widgets.draw_panel(surf, rect, "Valeur nette — évolution", config.COL_CYAN)
        hist = p.cash_history or []
        if len(hist) < 2:
            widgets.draw_text(surf, "Historique trop court pour un graphique.",
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            return

        chart_rect = pygame.Rect(inner.x + 50, inner.y, inner.w - 60, inner.h - 20)
        lo, hi = min(hist), max(hist)
        lo, hi, span = widgets.draw_chart_axes(
            surf, chart_rect, lo, hi,
            y_fmt=lambda v: widgets.format_money(v, cur), rows=4)
        widgets.draw_series(surf, chart_rect, hist, config.COL_CYAN, baseline=False)

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
        widgets.draw_text(
            surf, f"({len(hist)} relevés récents)",
            (inner.right, inner.y), fonts.tiny(), config.COL_TEXT_DIM, align="right")

    def _draw_timeline(self, surf, rect, p):
        inner = widgets.draw_panel(surf, rect, "Timeline des évènements", config.COL_AMBER)
        entries = format_timeline(p.journal, limit=80)
        if not entries:
            widgets.draw_text(surf, "Votre histoire s'écrira ici : promotions, deals, crises…",
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            return

        # on retrouve le 'kind' d'origine (pour la couleur) en ré-associant par
        # position : format_timeline trie déjà du plus récent au plus ancien,
        # comme list(reversed(journal)).
        kinds = [e.get("kind", "info") for e in list(reversed(p.journal))[:len(entries)]]

        line_h = 22
        rows_per_col = max(1, inner.h // line_h)
        ncols = max(1, (len(entries) + rows_per_col - 1) // rows_per_col)
        ncols = min(ncols, 4)
        colw = inner.w // ncols - 10
        for i, (label, text) in enumerate(entries):
            col = i // rows_per_col
            if col >= ncols:
                break
            row = i % rows_per_col
            x = inner.x + col * (colw + 20)
            y = inner.y + row * line_h
            tag = _KIND_COLORS.get(kinds[i] if i < len(kinds) else "info", config.COL_TEXT_DIM)
            widgets.draw_text(surf, label, (x, y), fonts.tiny(bold=True), tag)
            font = fonts.tiny()
            widgets.draw_text(surf, widgets.fit_text(text, font, colw - 46),
                              (x + 46, y), font, config.COL_TEXT)
