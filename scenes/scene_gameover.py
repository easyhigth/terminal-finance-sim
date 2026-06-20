"""
scene_gameover.py — Écran de fin de partie (faillite ou réputation anéantie).
Affiche le motif, un récapitulatif de carrière, le score composite de fin de
run (core/score.py), et renvoie au menu.
En mode hardcore, la sauvegarde automatique est effacée (run définitif).
"""
import math

import pygame

from core import config
from core import score as score_mod
from core.game_state import GameState
from core.scene_manager import Scene
from ui import fonts, widgets

# libellés FR courts pour les 7 dimensions du score (cf. core/score.py)
SCORE_DIMENSIONS = [
    ("performance", "Performance"),
    ("risque", "Risque"),
    ("drawdown", "Drawdown"),
    ("reputation", "Réputation"),
    ("conformite", "Conformité"),
    ("qualite_execution", "Exécution"),
    ("survie", "Survie"),
]


def _score_color(v):
    """Couleur du dégradé rouge→ambre→vert selon le score 0-100."""
    if v >= 70:
        return config.COL_UP
    if v >= 40:
        return config.COL_WARN
    return config.COL_DOWN


class GameOverScene(Scene):
    def on_enter(self, **kwargs):
        self.t = 0.0
        p = self.app.gs.player
        # run définitif en hardcore : on efface l'autosave
        if p.hardcore:
            GameState.delete(config.AUTOSAVE_SLOT)
        market = getattr(self.app, "market", None)
        self.score = score_mod.compute_final_score(p, market)
        self.menu_btn = widgets.Button(
            (config.SCREEN_WIDTH // 2 - 150, 692, 300, 26),
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

        # titre pulsé en rouge (compact pour laisser de la place au score)
        pulse = 0.5 + 0.5 * math.sin(self.t * 2.5)
        col = widgets._lerp_col(config.COL_DOWN, (120, 20, 24), pulse)
        widgets.draw_text(surf, "GAME OVER", (cx, 56),
                          fonts.title(bold=True), col, align="center")
        widgets.draw_text(surf, "FIN DE CARRIÈRE", (cx, 92),
                          fonts.small(), config.COL_TEXT_DIM, align="center")

        info = config.CONTINENTS.get(p.continent, {})
        cur = info.get("currency", "$")

        top_y = 118
        col_w = 250
        gap = 8
        left_x = cx - (3 * col_w + 2 * gap) // 2

        # panneau gauche : rapport final + stats de run
        left = pygame.Rect(left_x, top_y, col_w, 230)
        inner = widgets.draw_panel(surf, left, "Rapport final", config.COL_DOWN)
        h = widgets.draw_text_wrapped(surf, p.game_over_reason or "Partie terminée.",
                                      (inner.x, inner.y), fonts.tiny(),
                                      config.COL_TEXT, inner.w, line_gap=4)
        lines = [
            f"Nom    : {p.name}",
            f"Grade  : {p.grade}",
            f"Voie   : {p.track}",
            f"Région : {p.continent}",
            f"Durée  : {p.quarter} trim. ({p.day} j)",
            f"Cash   : {widgets.format_money(p.cash, cur)}",
            f"Record : {widgets.format_money(max(p.best_cash, p.cash), cur)}",
            f"Rép.   : {p.reputation}/100",
            f"Deals {p.deals_won}  Miss. {p.missions_done}",
        ]
        y = inner.y + h + 6
        for ln in lines:
            widgets.draw_text(surf, ln, (inner.x, y), fonts.tiny(), config.COL_TEXT)
            y += 18
        if p.titles:
            widgets.draw_text_wrapped(surf, "Titres : " + " · ".join(p.titles),
                                      (inner.x, y + 2), fonts.tiny(), config.COL_WARN, inner.w)

        # panneau central : journal de carrière (rétrospective)
        mid = pygame.Rect(left_x + col_w + gap, top_y, col_w, 230)
        minner = widgets.draw_panel(surf, mid, "Journal de carrière", config.COL_AMBER)
        if p.journal:
            yy = minner.y
            for e in list(reversed(p.journal))[:9]:
                widgets.draw_text(surf, f"J{e['day']}", (minner.x, yy),
                                  fonts.tiny(bold=True), config.COL_CYAN)
                widgets.draw_text(surf, e["text"][:30], (minner.x + 40, yy),
                                  fonts.tiny(), config.COL_TEXT)
                yy += 22
        else:
            widgets.draw_text_wrapped(surf, "Carrière trop courte pour laisser une trace.",
                              (minner.x, minner.y), fonts.tiny(), config.COL_TEXT_DIM, minner.w)

        # panneau droit : score composite de fin de run
        right = pygame.Rect(left_x + 2 * (col_w + gap), top_y, col_w, 230)
        self._draw_score_panel(surf, right)

        # panneau bas : rétrospective graphique de la valeur nette
        bottom = pygame.Rect(left_x, top_y + 238, 3 * col_w + 2 * gap, 88)
        binner = widgets.draw_panel(surf, bottom, "Rétrospective — valeur nette", config.COL_CYAN)
        self._draw_networth_retrospective(surf, binner, p, cur)

        if p.hardcore:
            widgets.draw_badge(surf, "HARDCORE — SAUVEGARDE EFFACÉE",
                               (cx, 680), config.COL_DOWN, align="center")

        self.menu_btn.draw(surf)

    def _draw_score_panel(self, surf, rect):
        """Affiche le score composite de fin de run (core/score.py) : note
        lettre + total, puis une jauge par dimension (0-100)."""
        sc = self.score
        accent = _score_color(sc.total)
        inner = widgets.draw_panel(surf, rect, "Score de carrière", accent)

        widgets.draw_text(surf, f"{sc.grade}", (inner.x, inner.y),
                          fonts.title(bold=True), accent)
        widgets.draw_text(surf, f"{sc.total:.0f}/100", (inner.x + 50, inner.y + 6),
                          fonts.small(bold=True), config.COL_TEXT)
        widgets.draw_text_wrapped(surf, sc.rank_label, (inner.x, inner.y + 30),
                                  fonts.tiny(), config.COL_TEXT_DIM, inner.w)

        bar_y = inner.y + 56
        bar_h = 13
        gap = 5
        for key, label in SCORE_DIMENSIONS:
            val = getattr(sc, key)
            widgets.draw_text(surf, label, (inner.x, bar_y), fonts.tiny(), config.COL_TEXT)
            bar_rect = pygame.Rect(inner.x + 78, bar_y + 1, inner.w - 78 - 28, bar_h - 2)
            widgets.draw_progress(surf, bar_rect, val / 100.0, _score_color(val))
            widgets.draw_text(surf, f"{val:.0f}", (inner.right, bar_y),
                              fonts.tiny(), config.COL_TEXT_DIM, align="right")
            bar_y += bar_h + gap

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
