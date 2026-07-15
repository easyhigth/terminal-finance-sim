"""
app_themes.py — Application « Thématiques » du bureau (NATIVE).

Investir par TENDANCE (core/themes.py) : panneau gauche = classement de
ROTATION des thèmes (du plus chaud au plus froid, force relative au marché),
panneau droit = détail du thème sélectionné (récit, constituants, exposition
actuelle) avec achat du PANIER équipondéré en un clic.
"""
import pygame

from apps.base import DesktopApp
from core import config
from core import themes as T
from ui import fonts, widgets

BUDGET_CHOICES = [50_000, 100_000, 250_000, 500_000]


class ThemesApp(DesktopApp):
    title = "Thématiques"
    icon_kind = "graph"
    default_size = (1040, 620)
    min_size = (820, 480)

    def on_open(self):
        self.selected = T.THEMES[0][0]
        self.budget = BUDGET_CHOICES[1]
        self._cache_key = None
        self._ranking = None
        self._theme_rects = {}
        self._budget_rects = {}
        self._buy_btn = None
        self._msg = ""

    def _ensure(self):
        market = self.app.ensure_market()
        if self._cache_key == market.step_count:
            return
        self._cache_key = market.step_count
        self._ranking = T.heat_ranking(market)

    def _cur(self):
        try:
            return config.CONTINENTS[self.app.gs.player.continent]["currency"]
        except Exception:
            return "$"

    # -------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        for tid, r in self._theme_rects.items():
            if r.collidepoint(pos):
                self.selected = tid
                return True
        for b, r in self._budget_rects.items():
            if r.collidepoint(pos):
                self.budget = b
                return True
        if self._buy_btn and self._buy_btn.collidepoint(pos):
            market = self.app.ensure_market()
            p = self.app.gs.player
            res = T.buy_basket(p, market, self.selected, self.budget)
            if res["ok"]:
                self._msg = f"{len(res['bought'])} lignes achetées " \
                            f"({res['spent']:,.0f})."
            else:
                self._msg = "Achat impossible (budget/trésorerie insuffisants)."
            self._cache_key = None
            return True
        return False

    # ---------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._ensure()
        surf.fill(config.COL_BG, rect)
        pad = 14
        widgets.draw_text(surf, "THÉMATIQUES — investir par tendance",
                          (rect.x + pad, rect.y + 8), fonts.head(bold=True),
                          config.COL_AMBER)
        col_w = int((rect.w - 3 * pad) * 0.46)
        left = pygame.Rect(rect.x + pad, rect.y + 34, col_w, rect.h - 34 - pad)
        right = pygame.Rect(left.right + pad, rect.y + 34,
                            rect.w - col_w - 3 * pad, left.h)
        self._draw_ranking(surf, left)
        self._draw_detail(surf, right)

    def _draw_ranking(self, surf, body):
        inner = widgets.draw_panel(surf, body, "Rotation des thèmes (chaud → froid)",
                                   config.COL_CYAN)
        self._theme_rects = {}
        yy = inner.y
        rows = self._ranking or []
        rels = [r["strength"]["relative"] for r in rows] or [0.0]
        vmax = max(abs(min(rels)), abs(max(rels)), 0.01)
        for r in rows:
            if yy > inner.bottom - 40:
                break
            sel = r["id"] == self.selected
            row = pygame.Rect(inner.x, yy, inner.w, 38)
            self._theme_rects[r["id"]] = row
            if sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=4)
                pygame.draw.rect(surf, config.COL_AMBER, row, 1, border_radius=4)
            rel = r["strength"]["relative"]
            col = config.COL_UP if rel >= 0 else config.COL_DOWN
            widgets.draw_text(surf, r["label"], (row.x + 8, row.y + 3),
                              fonts.small(bold=sel), config.COL_TEXT)
            widgets.draw_text(surf, f"{rel * 100:+.1f}% vs marché",
                              (row.x + 8, row.y + 21), fonts.tiny(), col)
            # barre de force relative (centrée)
            bar_cx = row.right - 90
            w = int(rel / vmax * 70)
            bar = pygame.Rect(bar_cx, row.y + 14, abs(w), 8)
            if w < 0:
                bar.right = bar_cx
            pygame.draw.line(surf, config.COL_BORDER, (bar_cx, row.y + 6),
                             (bar_cx, row.y + 30), 1)
            pygame.draw.rect(surf, col, bar, border_radius=2)
            yy += 44

    def _draw_detail(self, surf, body):
        cur = self._cur()
        market = self.app.ensure_market()
        p = self.app.gs.player
        inner = widgets.draw_panel(surf, body, T.theme_label(self.selected), config.COL_AMBER)
        y = inner.y
        widgets.draw_text_wrapped(surf, T.theme_desc(self.selected), (inner.x, y),
                                  fonts.tiny(), config.COL_TEXT_DIM, inner.w, line_gap=3)
        y += 34
        s = T.theme_strength(market, self.selected)
        scol = config.COL_UP if s["relative"] >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"Momentum panier : {s['basket_return'] * 100:+.1f}% "
                          f"(marché {s['market_return'] * 100:+.1f}%)",
                          (inner.x, y), fonts.small(bold=True), scol)
        y += 24
        exposure = T.basket_exposure(p, market, self.selected)
        widgets.draw_text(surf, f"Votre exposition au thème : {widgets.format_money(exposure, cur)}",
                          (inner.x, y), fonts.tiny(), config.COL_TEXT)
        y += 22
        widgets.draw_text(surf, "Constituants du panier :", (inner.x, y),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 18
        for tk in T.constituents(market, self.selected):
            if y > inner.bottom - 90:
                break
            comp = next((c for c in market.companies if c["ticker"] == tk), None)
            name = comp["name"] if comp else tk
            price = market.price_of(tk)
            held = p.portfolio.get(tk, {}).get("shares", 0) > 0
            widgets.draw_text(surf, f"{'✓ ' if held else '  '}{tk} — {widgets.fit_text(name, fonts.tiny(), 150)}",
                              (inner.x + 4, y), fonts.tiny(),
                              config.COL_UP if held else config.COL_TEXT)
            if price:
                widgets.draw_text(surf, widgets.format_money(price, cur),
                                  (inner.right - 8, y), fonts.tiny(), config.COL_TEXT_DIM,
                                  align="right")
            y += 16
        # barre d'achat
        by = inner.bottom - 60
        widgets.draw_text(surf, "Budget du panier :", (inner.x, by), fonts.tiny(bold=True),
                          config.COL_TEXT_DIM)
        x = inner.x + 120
        self._budget_rects = {}
        for b in BUDGET_CHOICES:
            lbl = f"{b // 1000}k"
            w = fonts.tiny(bold=True).size(lbl)[0] + 14
            r = pygame.Rect(x, by - 2, w, 20)
            self._budget_rects[b] = r
            sel = b == self.budget
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL,
                             r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER,
                             r, 1, border_radius=3)
            widgets.draw_text(surf, lbl, r.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM, align="center")
            x += w + 6
        self._buy_btn = pygame.Rect(inner.x, by + 26, 180, 24)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._buy_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._buy_btn, 1, border_radius=4)
        widgets.draw_text(surf, "ACHETER LE PANIER", self._buy_btn.center,
                          fonts.small(bold=True), config.COL_UP, align="center")
        if self._msg:
            widgets.draw_text(surf, widgets.fit_text(self._msg, fonts.tiny(), inner.w - 200),
                              (self._buy_btn.right + 10, by + 30), fonts.tiny(), config.COL_CYAN)
