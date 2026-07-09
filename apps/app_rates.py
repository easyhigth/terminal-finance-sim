"""
app_rates.py — Application « Desk Taux » du bureau (NATIVE).

Fixed income de salle des marchés, sur l'univers obligataire RÉEL du jeu
(core/bonds.py) via core/rates_analytics.py :

- **Courbe des taux** souveraine (YTM par maturité) — celle que déforment
  le taux directeur et la prime de terme du moteur macro ;
- **Book obligataire** du joueur : duration modifiée, convexité et DV01
  par ligne + agrégats pondérés — le DV01 (P&L d'1 point de base) est
  l'unité de compte d'un desk de taux ;
- **Chocs de courbe** : P&L du book au 2e ordre (duration + convexité)
  sous des scénarios parallèles ET non parallèles (pentification /
  aplatissement) — deux books de même duration n'y réagissent pas pareil.
"""
import pygame

from apps.base import DesktopApp
from core import config
from core import rates_analytics as RT
from ui import fonts, widgets


class RatesApp(DesktopApp):
    title = "Desk Taux"
    icon_kind = "rates"
    default_size = (1060, 640)
    min_size = (820, 500)

    def on_open(self):
        self.market = self.app.ensure_market()
        self._cache_key = None
        self._curve = None
        self._table = None
        self._bonds_btn = None

    def _ensure_computed(self):
        p = self.app.gs.player
        key = (self.market.step_count, len(getattr(p, "bonds", {}) or {}))
        if key == self._cache_key:
            return
        self._cache_key = key
        self._curve = RT.yield_curve(self.market)
        self._table = RT.scenario_table(p, self.market)

    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        if self._bonds_btn and self._bonds_btn.collidepoint(event.pos):
            if self.desktop is not None:
                self.desktop._open_scene_window("bonds")
            return True
        return False

    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        widgets.draw_text(surf, "DESK TAUX — COURBE · DURATION · DV01 · CHOCS",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        bw = fonts.tiny(bold=True).size("MARCHÉ OBLIGATAIRE →")[0] + 16
        self._bonds_btn = pygame.Rect(rect.right - pad - bw, rect.y + 10, bw, 20)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._bonds_btn, border_radius=3)
        pygame.draw.rect(surf, config.COL_CYAN, self._bonds_btn, 1, border_radius=3)
        widgets.draw_text(surf, "MARCHÉ OBLIGATAIRE →", self._bonds_btn.center,
                          fonts.tiny(bold=True), config.COL_CYAN, align="center")
        body = pygame.Rect(rect.x + pad, rect.y + 40, rect.w - 2 * pad,
                           rect.bottom - pad - rect.y - 40)
        col_w = (body.w - 12) // 2
        left = pygame.Rect(body.x, body.y, col_w, body.h)
        right = pygame.Rect(left.right + 12, body.y, col_w, body.h)
        h_half = (left.h - 10) // 2
        self._draw_curve(surf, pygame.Rect(left.x, left.y, left.w, h_half))
        self._draw_scenarios(surf, pygame.Rect(left.x, left.y + h_half + 10,
                                               left.w, h_half), cur)
        self._draw_book(surf, right, cur)

    def _draw_curve(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Courbe des taux (souverains, YTM)",
                                   config.COL_CYAN)
        pts = self._curve or []
        if len(pts) < 2:
            widgets.draw_text(surf, "Pas assez de points de courbe.",
                              (inner.x, inner.y + 6), fonts.tiny(),
                              config.COL_TEXT_DIM)
            return
        years = [y for y, _ in pts]
        ytms = [v * 100 for _, v in pts]
        lo, hi = min(ytms), max(ytms)
        rng = (hi - lo) or 1.0
        plot = inner.inflate(-30, -26)
        plot.move_ip(10, 2)
        pygame.draw.line(surf, config.COL_BORDER, plot.bottomleft, plot.bottomright)
        pygame.draw.line(surf, config.COL_BORDER, plot.topleft, plot.bottomleft)
        xmax = max(years)
        px_pts = []
        for yy, v in zip(years, ytms):
            x0 = plot.x + int(yy / xmax * plot.w)
            y0 = plot.bottom - int((v - lo) / rng * plot.h)
            px_pts.append((x0, y0))
        if len(px_pts) >= 2:
            pygame.draw.aalines(surf, config.COL_CYAN, False, px_pts)
        for (x0, y0), yy, v in zip(px_pts, years, ytms):
            pygame.draw.circle(surf, config.COL_WHITE, (x0, y0), 3)
            widgets.draw_text(surf, f"{yy:.0f}a", (x0 - 6, plot.bottom + 3),
                              fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{hi:.1f}%", (plot.x - 34, plot.y - 4),
                          fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{lo:.1f}%", (plot.x - 34, plot.bottom - 10),
                          fonts.tiny(), config.COL_TEXT_DIM)
        shape = "pentue" if ytms[-1] > ytms[0] + 0.15 else \
                ("INVERSÉE (signal récession)" if ytms[-1] < ytms[0] - 0.15
                 else "plate")
        widgets.draw_text(surf, f"Courbe {shape} — court {ytms[0]:.2f}% → "
                          f"long {ytms[-1]:.2f}%",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)

    def _draw_scenarios(self, surf, rect, cur):
        inner = widgets.draw_panel(surf, rect,
                                   "Chocs de courbe (duration + convexité)",
                                   config.COL_DOWN)
        t = self._table
        if not t or not t["lines"]:
            widgets.draw_text(surf, "Book obligataire vide.", (inner.x, inner.y + 6),
                              fonts.tiny(), config.COL_TEXT_DIM)
            return
        y = inner.y + 2
        pmax = max(abs(s["pnl"]) for s in t["scenarios"]) or 1.0
        bar_w = inner.w - 260
        for s in t["scenarios"]:
            if y > inner.bottom - 16:
                break
            widgets.draw_text(surf, widgets.fit_text(s["name"], fonts.tiny(bold=True),
                                                     150),
                              (inner.x, y), fonts.tiny(bold=True), config.COL_TEXT)
            bx = inner.x + 155
            mid = bx + bar_w // 2
            frac = s["pnl"] / pmax
            w = int(abs(frac) * bar_w * 0.5)
            col = config.COL_UP if s["pnl"] >= 0 else config.COL_DOWN
            pygame.draw.line(surf, config.COL_BORDER, (mid, y), (mid, y + 12))
            pygame.draw.rect(surf, col,
                             pygame.Rect(mid if frac >= 0 else mid - w, y + 2, w, 10),
                             border_radius=2)
            widgets.draw_text(surf, f"{widgets.format_money(s['pnl'], cur)} "
                              f"({s['pnl_pct']:+.1f}%)",
                              (bx + bar_w + 6, y), fonts.tiny(), col)
            y += 19
        widgets.draw_text(surf, "ΔP ≈ V·(−D·Δy + ½·C·Δy²) — la convexité adoucit "
                          "les hausses de taux.",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)

    def _draw_book(self, surf, rect, cur):
        inner = widgets.draw_panel(surf, rect, "Book obligataire", config.COL_AMBER)
        t = self._table
        if not t or not t["lines"]:
            widgets.draw_text(surf, "Aucune obligation détenue — le desk Taux "
                              "s'anime avec un book (bouton MARCHÉ OBLIGATAIRE).",
                              (inner.x, inner.y + 6), fonts.tiny(),
                              config.COL_TEXT_DIM)
            return
        tot = t["totals"]
        tiles = [
            ("VALEUR", widgets.format_money(tot["value"], cur)),
            ("DURATION MOD.", f"{tot['duration']:.2f}"),
            ("CONVEXITÉ", f"{tot['convexity']:.1f}"),
            ("DV01", widgets.format_money(tot["dv01"], cur)),
        ]
        tx = inner.x
        for lbl, val in tiles:
            tw = max(120, fonts.small(bold=True).size(val)[0] + 18)
            if tx + tw > inner.right:
                break
            tr = pygame.Rect(tx, inner.y, tw, 42)
            pygame.draw.rect(surf, config.COL_PANEL, tr, border_radius=4)
            pygame.draw.rect(surf, config.COL_BORDER, tr, 1, border_radius=4)
            widgets.draw_text(surf, lbl, (tr.x + 7, tr.y + 4), fonts.tiny(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, val, (tr.x + 7, tr.y + 19),
                              fonts.small(bold=True), config.COL_TEXT)
            tx += tw + 8
        y = inner.y + 52
        cols = [("OBLIGATION", 0), ("MAT.", int(inner.w * 0.42)),
                ("YTM", int(inner.w * 0.52)), ("DUR.", int(inner.w * 0.64)),
                ("CONV.", int(inner.w * 0.75)), ("DV01", int(inner.w * 0.87))]
        for lbl, dx in cols:
            widgets.draw_text(surf, lbl, (inner.x + dx, y), fonts.tiny(bold=True),
                              config.COL_TEXT_DIM)
        y += 16
        for x in t["lines"]:
            if y > inner.bottom - 28:
                widgets.draw_text(surf, "…", (inner.x, y), fonts.tiny(),
                                  config.COL_TEXT_DIM)
                break
            widgets.draw_text(surf, widgets.fit_text(x["name"], fonts.small(bold=True),
                                                     int(inner.w * 0.40)),
                              (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"{x['years']:.0f}a",
                              (inner.x + cols[1][1], y), fonts.small(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"{x['ytm'] * 100:.2f}%",
                              (inner.x + cols[2][1], y), fonts.small(),
                              config.COL_CYAN)
            widgets.draw_text(surf, f"{x['duration']:.2f}",
                              (inner.x + cols[3][1], y), fonts.small(),
                              config.COL_TEXT)
            widgets.draw_text(surf, f"{x['convexity']:.0f}",
                              (inner.x + cols[4][1], y), fonts.small(),
                              config.COL_TEXT_DIM)
            widgets.draw_text(surf, widgets.format_money(x["dv01"], cur),
                              (inner.x + cols[5][1], y), fonts.small(),
                              config.COL_AMBER)
            y += 18
        widgets.draw_text(surf, "DV01 = P&L d'une hausse d'1 point de base — "
                          "l'unité de compte du desk.",
                          (inner.x, inner.bottom - 12), fonts.tiny(),
                          config.COL_TEXT_DIM)
