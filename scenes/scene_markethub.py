"""
scene_markethub.py — Vue MARCHÉ regroupée.

Rassemble en un seul écran ce qui était dispersé en plusieurs fenêtres
flottantes du terminal : indices mondiaux, top sociétés (par région),
plus forts mouvements (variations) et indicateurs macro (éco).
Ouvert via MARKETHUB / le rail latéral « MARCHÉ ».
"""
import pygame
from core import config
from core.scene_manager import Scene
from ui import fonts, widgets

_ECO_NOTES = {
    "rate": "coût de l'argent ; ↑ pèse sur actions/immo",
    "inflation": "hausse des prix ; guide la banque centrale",
    "growth": "PIB ; ↑ soutient les bénéfices",
    "unemployment": "↑ = ralentissement",
    "confidence": "moral des marchés",
}


class MarketHubScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.top_region = self.app.gs.player.continent
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self._ticker_rects = {}
        self._region_rects = {}

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for region, rect in self._region_rects.items():
                if rect.collidepoint(event.pos):
                    self.top_region = region
                    return
            for tk, rect in self._ticker_rects.items():
                if rect.collidepoint(event.pos):
                    self.app.scenes.go("company", ticker=tk, return_to="markethub")
                    return

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "MARCHÉ", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Indices, top sociétés, variations et macro-économie — réunis ici.",
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        M = config.MARGIN
        top = config.content_top()
        bottom = config.footer_y() - 8
        colw = (config.SCREEN_WIDTH - 3 * M) // 2
        row_h = (bottom - top - M) // 2
        x1, x2 = M, M * 2 + colw
        y1, y2 = top, top + row_h + M

        self._ticker_rects = {}
        self._region_rects = {}
        self._draw_indices(surf, pygame.Rect(x1, y1, colw, row_h))
        self._draw_top(surf, pygame.Rect(x2, y1, colw, row_h))
        self._draw_movers(surf, pygame.Rect(x1, y2, colw, row_h))
        self._draw_eco(surf, pygame.Rect(x2, y2, colw, row_h))

        self.back_btn.draw(surf)

    def _draw_indices(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Indices mondiaux", config.COL_AMBER)
        y = inner.y
        for name, *_ in self.market.index_defs:
            v = self.market.index_value(name)
            chg = self.market.index_change_pct(name)
            ccol = config.COL_UP if chg >= 0 else config.COL_DOWN
            widgets.draw_text(surf, name, (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
            widgets.draw_text(surf, f"{v:,.0f}", (inner.x + inner.w // 2, y),
                              fonts.small(), config.COL_TEXT, align="right")
            widgets.draw_text(surf, f"{'+' if chg>=0 else ''}{chg:.2f}%", (inner.right, y),
                              fonts.small(bold=True), ccol, align="right")
            y += 24

    def _draw_top(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Top sociétés", config.COL_CYAN)
        cur = config.CONTINENTS[self.top_region]["currency"]
        mp = pygame.mouse.get_pos()
        # onglets de région
        x = inner.x
        y = inner.y
        for region in self.market.regions:
            label = region
            w = fonts.tiny(bold=True).size(label)[0] + 14
            r = pygame.Rect(x, y, w, 18)
            self._region_rects[region] = r
            active = (region == self.top_region)
            col = config.COL_AMBER if active else config.COL_TEXT_DIM
            if r.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, label, (r.x + 7, r.y + 1), fonts.tiny(bold=active), col)
            x = r.right + 6
        y += 26
        n = max(1, (inner.bottom - y) // 26)
        for c in self.market.top_companies(region=self.top_region, n=n):
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 24)
            self._ticker_rects[c["ticker"]] = row
            if row.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
            widgets.draw_text(surf, c["ticker"], (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
            widgets.draw_text(surf, c["name"][:16], (inner.x + 58, y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, widgets.format_money(c["mktcap"] * 1e6, cur), (inner.right, y),
                              fonts.tiny(bold=True), config.COL_WHITE, align="right")
            y += 26

    def _draw_movers(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Variations — plus forts mouvements", config.COL_DEAL)
        mp = pygame.mouse.get_pos()
        y = inner.y
        n = max(1, (inner.h // 2 - 18) // 24)
        widgets.draw_text(surf, "HAUSSES", (inner.x, y), fonts.tiny(bold=True), config.COL_UP)
        y += 18
        for c in self.market.top_companies(n=n, by="gain"):
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 22)
            self._ticker_rects[c["ticker"]] = row
            if row.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
            widgets.draw_text(surf, "↑ " + c["ticker"], (inner.x, y), fonts.small(bold=True), config.COL_UP)
            widgets.draw_text(surf, c["name"][:18], (inner.x + 70, y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, c["sector"], (inner.right, y),
                              fonts.tiny(), config.COL_TEXT_DIM, align="right")
            y += 24
        y += 8
        widgets.draw_text(surf, "BAISSES", (inner.x, y), fonts.tiny(bold=True), config.COL_DOWN)
        y += 18
        for c in self.market.top_companies(n=n, by="loss"):
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 22)
            self._ticker_rects[c["ticker"]] = row
            if row.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
            widgets.draw_text(surf, "↓ " + c["ticker"], (inner.x, y), fonts.small(bold=True), config.COL_DOWN)
            widgets.draw_text(surf, c["name"][:18], (inner.x + 70, y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, c["sector"], (inner.right, y),
                              fonts.tiny(), config.COL_TEXT_DIM, align="right")
            y += 24

    def _draw_eco(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Éco — macro-économie", config.COL_PRESTIGE)
        m = self.market.macro
        reg_good = self.market.regime in ("Expansion", "Calme")
        y = inner.y
        widgets.draw_text(surf, "Régime de marché", (inner.x, y), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, self.market.regime_label(), (inner.right, y),
                          fonts.small(bold=True), config.COL_UP if reg_good else config.COL_DOWN,
                          align="right")
        y += 26
        for key in ["rate", "inflation", "growth", "unemployment", "confidence"]:
            d = m[key]
            ch = self.market.macro_change(key)
            ccol = config.COL_UP if ch >= 0 else config.COL_DOWN
            widgets.draw_text(surf, d["label"], (inner.x, y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, f"{d['v']:.2f}{d['unit']}", (inner.x + inner.w - 90, y),
                              fonts.small(bold=True), config.COL_WHITE, align="right")
            widgets.draw_text(surf, f"{'+' if ch>=0 else ''}{ch:.2f}", (inner.right, y),
                              fonts.small(), ccol, align="right")
            y += 22
            widgets.draw_text(surf, _ECO_NOTES.get(key, ""), (inner.x, y),
                              fonts.tiny(), config.COL_TEXT_DIM)
            y += 18
