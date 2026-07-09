"""
app_crisislab.py — Application « Labo de crise » du bureau (NATIVE).

Le simulateur de crise INTERACTIF (core/crisis_lab.py) : contrairement au
Stress test et à ses scénarios nommés, ICI c'est le joueur qui règle le
choc — curseur actions (0 à −40 %), curseur taux (−100 à +300 bp) et
l'interrupteur « CORRÉLATIONS → 1 » (en crise, tout tombe ensemble : la
diversification disparaît précisément quand on en a besoin, et la vol
implicite explose — les puts prennent de la valeur par le vega). Le book
est réévalué ligne par ligne à chaque réglage, avec la comparaison
« diversifié vs corrélations à 1 » affichée en clair.
"""
import pygame

from apps.base import DesktopApp
from core import config
from core import crisis_lab as CL
from ui import fonts, widgets

EQ_MIN, EQ_MAX = -0.40, 0.0
DY_MIN, DY_MAX = -0.010, 0.030


class CrisisLabApp(DesktopApp):
    title = "Labo de crise"
    icon_kind = "alert"
    default_size = (1040, 620)
    min_size = (780, 480)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.eq_shock = -0.20
        self.dy = 0.010
        self.crunch = False
        self._cache_key = None
        self._res = None
        self._eq_rect = None
        self._dy_rect = None
        self._crunch_rect = None
        self._drag = None

    def _ensure_computed(self):
        p = self.app.gs.player
        key = (self.market.step_count, round(self.eq_shock, 3),
               round(self.dy, 4), self.crunch, len(p.portfolio),
               len(getattr(p, "bonds", {}) or {}),
               len(getattr(p, "options", []) or []),
               len(getattr(p, "hedges", []) or []))
        if key == self._cache_key:
            return
        self._cache_key = key
        self._res = CL.reprice(p, self.market, self.eq_shock, self.dy,
                               self.crunch)

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag = None
            return False
        if event.type == pygame.MOUSEMOTION and self._drag:
            self._slide(self._drag, event.pos[0])
            return True
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        for name, r in (("eq", self._eq_rect), ("dy", self._dy_rect)):
            if r and r.inflate(0, 12).collidepoint(pos):
                self._drag = name
                self._slide(name, pos[0])
                return True
        if self._crunch_rect and self._crunch_rect.collidepoint(pos):
            self.crunch = not self.crunch
            return True
        return False

    def _slide(self, name, x):
        r = self._eq_rect if name == "eq" else self._dy_rect
        if r is None or r.w <= 0:
            return
        t = max(0.0, min(1.0, (x - r.x) / r.w))
        if name == "eq":
            self.eq_shock = EQ_MIN + t * (EQ_MAX - EQ_MIN)
        else:
            self.dy = DY_MIN + t * (DY_MAX - DY_MIN)

    # ---------------------------------------------------------------- draw
    def _slider(self, surf, rect, t, label, col):
        pygame.draw.rect(surf, config.COL_PANEL, rect, border_radius=4)
        pygame.draw.rect(surf, col, pygame.Rect(rect.x, rect.y,
                                                int(rect.w * t), rect.h),
                         border_radius=4)
        knob = pygame.Rect(0, 0, 10, 18)
        knob.center = (rect.x + int(rect.w * t), rect.centery)
        pygame.draw.rect(surf, config.COL_WHITE, knob, border_radius=3)
        widgets.draw_text(surf, label, (rect.right + 12, rect.y - 4),
                          fonts.small(bold=True), col)

    def draw(self, surf, rect):
        self._ensure_computed()
        surf.fill(config.COL_BG, rect)
        pad = 14
        cur = config.CONTINENTS[self.app.gs.player.continent]["currency"]
        widgets.draw_text(surf, "LABO DE CRISE — RÉGLEZ VOTRE PROPRE SCÉNARIO",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        y = rect.y + 38
        slider_w = min(380, rect.w - 320)
        self._eq_rect = pygame.Rect(rect.x + pad, y + 4, slider_w, 8)
        t_eq = (self.eq_shock - EQ_MIN) / (EQ_MAX - EQ_MIN)
        self._slider(surf, self._eq_rect, t_eq,
                     f"Actions {self.eq_shock * 100:+.0f}%", config.COL_DOWN)
        y += 30
        self._dy_rect = pygame.Rect(rect.x + pad, y + 4, slider_w, 8)
        t_dy = (self.dy - DY_MIN) / (DY_MAX - DY_MIN)
        self._slider(surf, self._dy_rect, t_dy,
                     f"Taux {self.dy * 10000:+.0f} bp", config.COL_AMBER)
        y += 30
        lbl = "CORRÉLATIONS → 1 (+10 pts de vol)"
        w = fonts.tiny(bold=True).size(lbl)[0] + 30
        self._crunch_rect = pygame.Rect(rect.x + pad, y, w, 22)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if self.crunch
                         else config.COL_PANEL, self._crunch_rect, border_radius=3)
        pygame.draw.rect(surf, config.COL_DOWN if self.crunch else config.COL_BORDER,
                         self._crunch_rect, 1, border_radius=3)
        widgets.draw_text(surf, ("[x] " if self.crunch else "[ ] ") + lbl,
                          (self._crunch_rect.x + 8, self._crunch_rect.y + 5),
                          fonts.tiny(bold=self.crunch),
                          config.COL_DOWN if self.crunch else config.COL_TEXT_DIM)
        res = self._res
        if res is None or not res["lines"]:
            widgets.draw_text(surf, "Book vide — le labo réévalue VOS positions "
                              "sous le scénario réglé.",
                              (rect.x + pad, y + 40), fonts.small(),
                              config.COL_TEXT_DIM)
            return
        # totaux (à droite des curseurs)
        tx = rect.x + pad + slider_w + 170
        tcol = config.COL_DOWN if res["total"] < 0 else config.COL_UP
        widgets.draw_text(surf, "P&L DU SCÉNARIO", (tx, rect.y + 40),
                          fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, widgets.format_money(res["total"], cur),
                          (tx, rect.y + 56), fonts.title(bold=True), tcol)
        widgets.draw_text(surf, f"{res['net_worth_pct']:+.1f}% du patrimoine",
                          (tx, rect.y + 84), fonts.small(), tcol)
        if self.crunch:
            gap = res["total"] - res["total_normal"]
            widgets.draw_text(surf, widgets.fit_text(
                f"Coût de l'illusion de diversification : "
                f"{widgets.format_money(gap, cur)} (vs corrélations normales)",
                fonts.tiny(), rect.right - pad - tx),
                (tx, rect.y + 104), fonts.tiny(), config.COL_AMBER)
        # table des lignes
        body = pygame.Rect(rect.x + pad, y + 34, rect.w - 2 * pad,
                           rect.bottom - pad - y - 34)
        inner = widgets.draw_panel(surf, body, "Réévaluation ligne par ligne",
                                   config.COL_CYAN)
        yy = inner.y + 2
        pmax = max(abs(x["pnl"]) for x in res["lines"]) or 1.0
        bar_w = inner.w - 380
        for x in res["lines"]:
            if yy > inner.bottom - 28:
                widgets.draw_text(surf, "…", (inner.x, yy), fonts.tiny(),
                                  config.COL_TEXT_DIM)
                break
            widgets.draw_text(surf, widgets.fit_text(x["label"],
                                                     fonts.small(bold=True), 130),
                              (inner.x, yy), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, x["kind"], (inner.x + 140, yy), fonts.tiny(),
                              config.COL_TEXT_DIM)
            bx = inner.x + 220
            mid = bx + bar_w // 2
            frac = x["pnl"] / pmax
            w = int(abs(frac) * bar_w * 0.5)
            col = config.COL_UP if x["pnl"] >= 0 else config.COL_DOWN
            pygame.draw.line(surf, config.COL_BORDER, (mid, yy), (mid, yy + 12))
            pygame.draw.rect(surf, col,
                             pygame.Rect(mid if frac >= 0 else mid - w, yy + 2, w, 9),
                             border_radius=2)
            widgets.draw_text(surf, widgets.format_money(x["pnl"], cur),
                              (bx + bar_w + 8, yy), fonts.tiny(bold=True), col)
            yy += 19
        widgets.draw_text(surf, "En crise, les corrélations montent vers 1 et la "
                          "vol explose — activez l'interrupteur pour voir la "
                          "différence.", (inner.x, inner.bottom - 12),
                          fonts.tiny(), config.COL_TEXT_DIM)
