"""
scene_quant.py — Module Quant : pricing d'options en direct.
Le joueur ajuste les paramètres (spot, strike, maturité, taux, volatilité)
et voit en temps réel :
  - le prix Black-Scholes (call & put)
  - les Greeks (delta, gamma, vega, theta, rho)
  - la courbe de prix en fonction du spot
  - le diagramme de payoff à l'échéance
Basé sur core.finmath (black_scholes, bs_greeks).
"""
import numpy as np
import pygame
from core import config
from core.scene_manager import Scene
from core import finmath as fm
from ui import fonts, widgets


class QuantScene(Scene):
    def on_enter(self, **kwargs):
        self.S = 100.0     # spot
        self.K = 100.0     # strike
        self.T = 1.0       # maturité (années)
        self.r = 0.05      # taux sans risque
        self.sigma = 0.20  # volatilité
        self.option = "call"
        self.back_btn = widgets.Button(
            (40, config.SCREEN_HEIGHT-66, 160, 44), "← TERMINAL", config.COL_TEXT_DIM)
        self.toggle_btn = widgets.Button(
            (220, config.SCREEN_HEIGHT-66, 200, 44), "TYPE : CALL", config.COL_UP)
        self._params = {}

    def _adj(self, key, delta):
        bounds = {
            "S": (10, 200, 5), "K": (10, 200, 5),
            "T": (0.05, 3.0, 0.05), "r": (0.0, 0.15, 0.005),
            "sigma": (0.05, 0.80, 0.01),
        }
        lo, hi, _ = bounds[key]
        setattr(self, key, max(lo, min(hi, round(getattr(self, key)+delta, 4))))

    def handle_event(self, event):
        if self.back_btn.handle(event):
            self.app.scenes.go("terminal")
        if self.toggle_btn.handle(event):
            self.option = "put" if self.option == "call" else "call"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, (minus, plus, step) in self._params.items():
                if minus.collidepoint(event.pos):
                    self._adj(key, -step)
                elif plus.collidepoint(event.pos):
                    self._adj(key, +step)

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp)
        self.toggle_btn.label = f"TYPE : {self.option.upper()}"
        self.toggle_btn.accent = config.COL_UP if self.option == "call" else config.COL_DOWN
        self.toggle_btn.update(mp)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "MODULE QUANT — PRICING D'OPTIONS (BLACK-SCHOLES)",
                          (40, 24), fonts.title(bold=True), config.COL_AMBER)
        self._params = {}
        self._draw_inputs(surf)
        self._draw_outputs(surf)
        self._draw_price_curve(surf)
        self._draw_payoff(surf)
        self.back_btn.draw(surf)
        self.toggle_btn.draw(surf)

    def _slider(self, surf, x, y, label, value, key, step, fmt="{:.2f}"):
        widgets.draw_text(surf, label, (x, y), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, fmt.format(value), (x+170, y),
                          fonts.small(bold=True), config.COL_WHITE)
        minus = pygame.Rect(x+260, y-2, 24, 22)
        plus = pygame.Rect(x+288, y-2, 24, 22)
        for rect, sym in ((minus, "-"), (plus, "+")):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
            pygame.draw.rect(surf, config.COL_BORDER, rect, 1)
            img = fonts.body(bold=True).render(sym, True, config.COL_AMBER)
            surf.blit(img, img.get_rect(center=rect.center))
        self._params[key] = (minus, plus, step)

    def _draw_inputs(self, surf):
        panel = pygame.Rect(40, 110, 340, 280)
        inner = widgets.draw_panel(surf, panel, "Paramètres", config.COL_CYAN)
        x, y = inner.x, inner.y
        self._slider(surf, x, y, "Spot (S)", self.S, "S", 5, "{:.0f}"); y += 44
        self._slider(surf, x, y, "Strike (K)", self.K, "K", 5, "{:.0f}"); y += 44
        self._slider(surf, x, y, "Maturité T (ans)", self.T, "T", 0.05, "{:.2f}"); y += 44
        self._slider(surf, x, y, "Taux r", self.r, "r", 0.005, "{:.1%}"); y += 44
        self._slider(surf, x, y, "Volatilité σ", self.sigma, "sigma", 0.01, "{:.0%}"); y += 44

    def _draw_outputs(self, surf):
        panel = pygame.Rect(396, 110, 340, 280)
        inner = widgets.draw_panel(surf, panel, "Prix & Greeks", config.COL_AMBER)
        price = fm.black_scholes(self.S, self.K, self.T, self.r, self.sigma, self.option)
        greeks = fm.bs_greeks(self.S, self.K, self.T, self.r, self.sigma, self.option)
        # prix mis en avant
        col = config.COL_UP if self.option == "call" else config.COL_DOWN
        widgets.draw_text(surf, f"Prix {self.option.upper()}", (inner.x, inner.y),
                          fonts.small(), config.COL_TEXT_DIM)
        # autre type, en haut à droite (hors de portée du gros prix)
        other = "put" if self.option == "call" else "call"
        other_price = fm.black_scholes(self.S, self.K, self.T, self.r, self.sigma, other)
        widgets.draw_text(surf, f"{other.upper()} : {other_price:.4f}",
                          (inner.right, inner.y), fonts.small(), config.COL_TEXT_DIM, align="right")
        widgets.draw_text(surf, f"{price:.4f}", (inner.x, inner.y+22),
                          fonts.title(bold=True), col)
        # greeks
        y = inner.y+80
        greek_rows = [
            ("Delta (Δ)", greeks["delta"], "sensibilité au spot"),
            ("Gamma (Γ)", greeks["gamma"], "variation du delta"),
            ("Vega (ν)", greeks["vega"], "par +1% de vol"),
            ("Theta (Θ)", greeks["theta"], "par jour"),
            ("Rho (ρ)", greeks["rho"], "par +1% de taux"),
        ]
        for label, val, note in greek_rows:
            widgets.draw_text(surf, label, (inner.x, y), fonts.small(bold=True), config.COL_CYAN)
            widgets.draw_text(surf, f"{val:+.4f}", (inner.x+110, y),
                              fonts.small(bold=True), config.COL_WHITE)
            widgets.draw_text(surf, note, (inner.x+200, y), fonts.tiny(), config.COL_TEXT_DIM)
            y += 30

    def _draw_price_curve(self, surf):
        panel = pygame.Rect(752, 110, config.SCREEN_WIDTH-792, 280)
        inner = widgets.draw_panel(surf, panel, "Prix de l'option vs Spot", config.COL_AMBER)
        spots = np.linspace(self.K*0.4, self.K*1.6, 80)
        prices = [fm.black_scholes(s, self.K, self.T, self.r, self.sigma, self.option)
                  for s in spots]
        intrinsics = [max(0, (s-self.K) if self.option == "call" else (self.K-s))
                      for s in spots]
        self._plot_lines(surf, inner, spots,
                         [(prices, config.COL_AMBER, "Valeur BS"),
                          (intrinsics, config.COL_TEXT_DIM, "Valeur intrinsèque")],
                         vline=self.S, vlabel="Spot")

    def _draw_payoff(self, surf):
        panel = pygame.Rect(40, 400, config.SCREEN_WIDTH-80, 270)
        inner = widgets.draw_panel(surf, panel, "Diagramme de payoff à l'échéance (net de prime)",
                                   config.COL_UP)
        spots = np.linspace(self.K*0.4, self.K*1.6, 120)
        premium = fm.black_scholes(self.S, self.K, self.T, self.r, self.sigma, self.option)
        if self.option == "call":
            payoff = [max(0, s-self.K) - premium for s in spots]
        else:
            payoff = [max(0, self.K-s) - premium for s in spots]
        self._plot_lines(surf, inner, spots,
                         [(payoff, config.COL_UP, "P&L à maturité")],
                         vline=self.S, vlabel="Spot actuel", zero_line=True)

    def _plot_lines(self, surf, inner, xs, series, vline=None, vlabel="",
                    zero_line=False):
        all_y = [v for data, _, _ in series for v in data]
        ymin, ymax = min(all_y), max(all_y)
        if ymax == ymin:
            ymax += 1
        pad = (ymax-ymin)*0.1
        ymin -= pad; ymax += pad
        xmin, xmax = xs[0], xs[-1]
        x0, y0 = inner.x+34, inner.bottom-20
        w, h = inner.w-44, inner.h-34

        def to_px(x, y):
            px = x0 + (x-xmin)/(xmax-xmin)*w
            py = y0 - (y-ymin)/(ymax-ymin)*h
            return int(px), int(py)

        # axes / grille
        pygame.draw.line(surf, config.COL_BORDER, (x0, y0), (x0+w, y0), 1)
        pygame.draw.line(surf, config.COL_BORDER, (x0, y0), (x0, y0-h), 1)
        if zero_line and ymin < 0 < ymax:
            zy = y0 - (0-ymin)/(ymax-ymin)*h
            pygame.draw.line(surf, config.COL_NEUTRAL, (x0, zy), (x0+w, zy), 1)
        # y labels
        for k in range(5):
            yv = ymin + (ymax-ymin)*k/4
            py = y0 - (yv-ymin)/(ymax-ymin)*h
            widgets.draw_text(surf, f"{yv:.1f}", (inner.x, py-6),
                              fonts.tiny(), config.COL_TEXT_DIM)
        # courbes
        for data, col, label in series:
            pts = [to_px(x, y) for x, y in zip(xs, data)]
            if len(pts) > 1:
                pygame.draw.lines(surf, col, False, pts, 2)
        # ligne verticale (spot)
        if vline is not None and xmin <= vline <= xmax:
            vx = x0 + (vline-xmin)/(xmax-xmin)*w
            pygame.draw.line(surf, config.COL_WHITE, (vx, y0-h), (vx, y0), 1)
            widgets.draw_text(surf, vlabel, (vx+4, y0-h), fonts.tiny(), config.COL_WHITE)
        # légende
        lx = x0 + w - 160
        ly = y0 - h + 6
        for data, col, label in series:
            pygame.draw.line(surf, col, (lx, ly+6), (lx+20, ly+6), 2)
            widgets.draw_text(surf, label, (lx+26, ly), fonts.tiny(), col)
            ly += 16
