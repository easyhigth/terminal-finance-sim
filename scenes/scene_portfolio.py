"""
scene_portfolio.py — Module Portfolio : construction et optimisation.
Le joueur ajuste les poids de plusieurs actifs ; le jeu trace en temps réel :
  - la frontière efficiente (Markowitz)
  - le portefeuille courant (rendement / volatilité / Sharpe)
  - les portefeuilles min-variance et max-Sharpe (repères)
Outil réaliste basé sur core.finmath.
"""
import numpy as np
import pygame

from core import config
from core import finmath as fm
from core.scene_manager import Scene
from ui import fonts, widgets

# Univers d'actifs simulé (rendements attendus annualisés + matrice de covariance)
ASSETS = ["Equities", "Bonds", "Real Estate", "Commodities", "Cash"]
MEAN_RETURNS = np.array([0.11, 0.04, 0.08, 0.07, 0.02])
COV = np.array([
    [0.0400, 0.0010, 0.0120, 0.0080, 0.0000],
    [0.0010, 0.0050, 0.0015, 0.0005, 0.0000],
    [0.0120, 0.0015, 0.0300, 0.0060, 0.0000],
    [0.0080, 0.0005, 0.0060, 0.0500, 0.0000],
    [0.0000, 0.0000, 0.0000, 0.0000, 0.0001],
])
RF = 0.02


class PortfolioScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.weights = np.array([0.4, 0.3, 0.1, 0.1, 0.1])
        self._recompute_frontier()
        self.back_btn = widgets.Button(
            (40, config.SCREEN_HEIGHT-66, 160, 44), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.optim_sharpe_btn = widgets.Button(
            (760, 150, 220, 40), "OPTIMISER (SHARPE)", config.COL_UP)
        self.optim_minvar_btn = widgets.Button(
            (760, 198, 220, 40), "MIN-VARIANCE", config.COL_CYAN)
        self.reset_btn = widgets.Button(
            (760, 246, 220, 40), "RÉINITIALISER", config.COL_TEXT_DIM)

    def _recompute_frontier(self):
        self.fvols, self.frets, _ = fm.efficient_frontier(MEAN_RETURNS, COV, 40)
        self.w_sharpe = fm.max_sharpe_portfolio(MEAN_RETURNS, COV, RF)
        self.w_minvar = fm.min_variance_portfolio(MEAN_RETURNS, COV)

    # --- métriques du portefeuille courant -------------------------------
    def _metrics(self, w):
        ret = fm.portfolio_return(w, MEAN_RETURNS)
        vol = fm.portfolio_volatility(w, COV)
        sharpe = fm.sharpe_ratio(w, MEAN_RETURNS, COV, RF)
        return ret, vol, sharpe

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
        if self.optim_sharpe_btn.handle(event):
            self.weights = self.w_sharpe.copy()
        if self.optim_minvar_btn.handle(event):
            self.weights = self.w_minvar.copy()
        if self.reset_btn.handle(event):
            self.weights = np.array([0.2]*5)

        # ajustement des poids via clic sur +/- (gérés dans draw via rects)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, (minus, plus) in getattr(self, "_weight_btns", {}).items():
                if minus.collidepoint(event.pos):
                    self.weights[i] = max(0, self.weights[i] - 0.05)
                    self._normalize()
                elif plus.collidepoint(event.pos):
                    self.weights[i] = min(1, self.weights[i] + 0.05)
                    self._normalize()

    def _normalize(self):
        s = self.weights.sum()
        if s > 0:
            self.weights = self.weights / s

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        for b in (self.back_btn, self.optim_sharpe_btn,
                  self.optim_minvar_btn, self.reset_btn):
            b.update(mp)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "MODULE PORTFOLIO — FRONTIÈRE EFFICIENTE",
                          (40, 24), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Optimisation moyenne-variance (Markowitz). Taux sans risque : "
                                f"{RF*100:.1f}%.",
                          (42, 76), fonts.small(), config.COL_TEXT_DIM)

        self._draw_chart(surf)
        self._draw_weights(surf)
        self._draw_metrics(surf)

        for b in (self.optim_sharpe_btn, self.optim_minvar_btn,
                  self.reset_btn, self.back_btn):
            b.draw(surf)

    # --- graphique frontière efficiente ----------------------------------
    def _draw_chart(self, surf):
        panel = pygame.Rect(40, 110, 700, 560)
        inner = widgets.draw_panel(surf, panel, "Risque / Rendement", config.COL_AMBER)
        x0, y0 = inner.x+40, inner.bottom-30
        w, h = inner.w-60, inner.h-50

        vmin, vmax = 0.0, max(self.fvols.max(), 0.25) * 1.1
        rmin, rmax = 0.0, MEAN_RETURNS.max() * 1.15

        def to_px(vol, ret):
            px = x0 + (vol - vmin) / (vmax - vmin) * w
            py = y0 - (ret - rmin) / (rmax - rmin) * h
            return int(px), int(py)

        # axes
        pygame.draw.line(surf, config.COL_BORDER, (x0, y0), (x0+w, y0), 1)
        pygame.draw.line(surf, config.COL_BORDER, (x0, y0), (x0, y0-h), 1)
        widgets.draw_text(surf, "Volatilité →", (x0+w-90, y0+8),
                          fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, "Rendement ↑", (x0-30, y0-h-4),
                          fonts.tiny(), config.COL_TEXT_DIM)
        # graduations
        for k in range(1, 6):
            vx = vmin + (vmax-vmin)*k/5
            px = x0 + (vx-vmin)/(vmax-vmin)*w
            pygame.draw.line(surf, config.COL_GRID, (px, y0), (px, y0-h), 1)
            widgets.draw_text(surf, f"{vx*100:.0f}%", (px-10, y0+6),
                              fonts.tiny(), config.COL_TEXT_DIM)
            ry = rmin + (rmax-rmin)*k/5
            py = y0 - (ry-rmin)/(rmax-rmin)*h
            pygame.draw.line(surf, config.COL_GRID, (x0, py), (x0+w, py), 1)
            widgets.draw_text(surf, f"{ry*100:.0f}%", (x0-34, py-6),
                              fonts.tiny(), config.COL_TEXT_DIM)

        # frontière efficiente
        pts = [to_px(v, r) for v, r in zip(self.fvols, self.frets)]
        if len(pts) > 1:
            pygame.draw.lines(surf, config.COL_CYAN, False, pts, 2)

        # actifs individuels
        for i, name in enumerate(ASSETS):
            v = np.sqrt(COV[i, i])
            r = MEAN_RETURNS[i]
            px, py = to_px(v, r)
            pygame.draw.circle(surf, config.COL_TEXT_DIM, (px, py), 4)
            widgets.draw_text(surf, name, (px+6, py-6), fonts.tiny(), config.COL_TEXT_DIM)

        # repères min-var et max-sharpe
        for w_ref, col, label in ((self.w_minvar, config.COL_WARN, "MinVar"),
                                  (self.w_sharpe, config.COL_UP, "MaxSharpe")):
            r, v, _ = self._metrics(w_ref)
            px, py = to_px(v, r)
            pygame.draw.circle(surf, col, (px, py), 6, 2)
            widgets.draw_text(surf, label, (px+8, py-4), fonts.tiny(), col)

        # portefeuille courant
        r, v, sh = self._metrics(self.weights)
        px, py = to_px(v, r)
        pygame.draw.circle(surf, config.COL_AMBER, (px, py), 7)
        pygame.draw.circle(surf, config.COL_WHITE, (px, py), 7, 1)
        widgets.draw_text(surf, "VOUS", (px+10, py-6),
                          fonts.small(bold=True), config.COL_AMBER)

        # Capital Market Line (depuis rf au portefeuille tangent)
        r_s, v_s, _ = self._metrics(self.w_sharpe)
        p_rf = to_px(0, RF)
        p_tan = to_px(v_s, r_s)
        pygame.draw.line(surf, (60, 120, 80), p_rf, p_tan, 1)

    def _draw_weights(self, surf):
        panel = pygame.Rect(760, 300, config.SCREEN_WIDTH-800, 250)
        inner = widgets.draw_panel(surf, panel, "Allocation (poids)", config.COL_AMBER)
        self._weight_btns = {}
        y = inner.y
        for i, name in enumerate(ASSETS):
            widgets.draw_text(surf, name, (inner.x, y), fonts.small(), config.COL_TEXT)
            # barre
            bar_x = inner.x+120
            bar_w = 120
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, (bar_x, y+2, bar_w, 14))
            pygame.draw.rect(surf, config.COL_CYAN,
                             (bar_x, y+2, int(bar_w*self.weights[i]), 14))
            widgets.draw_text(surf, f"{self.weights[i]*100:.0f}%",
                              (bar_x+bar_w+8, y), fonts.small(), config.COL_WHITE)
            # boutons +/-
            minus = pygame.Rect(inner.x+inner.w-58, y-2, 24, 22)
            plus = pygame.Rect(inner.x+inner.w-30, y-2, 24, 22)
            for rect, sym in ((minus, "-"), (plus, "+")):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
                pygame.draw.rect(surf, config.COL_BORDER, rect, 1)
                widgets.draw_text(surf, sym, rect.center, fonts.body(bold=True),
                                  config.COL_AMBER, align="center")
                img = fonts.body(bold=True).render(sym, True, config.COL_AMBER)
                surf.blit(img, img.get_rect(center=rect.center))
            self._weight_btns[i] = (minus, plus)
            y += 34

    def _draw_metrics(self, surf):
        panel = pygame.Rect(760, 564, config.SCREEN_WIDTH-800, 106)
        inner = widgets.draw_panel(surf, panel, "Métriques du portefeuille", config.COL_UP)
        r, v, sh = self._metrics(self.weights)
        widgets.draw_text(surf, f"Rendement attendu : {r*100:.2f}%",
                          (inner.x, inner.y), fonts.body(), config.COL_WHITE)
        widgets.draw_text(surf, f"Volatilité        : {v*100:.2f}%",
                          (inner.x, inner.y+26), fonts.body(), config.COL_WHITE)
        sh_col = config.COL_UP if sh > 1 else (config.COL_WARN if sh > 0.5 else config.COL_DOWN)
        widgets.draw_text(surf, f"Ratio de Sharpe   : {sh:.3f}",
                          (inner.x, inner.y+52), fonts.body(bold=True), sh_col)
