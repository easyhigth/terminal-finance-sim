"""
scene_markethub.py — Vue MARCHÉ regroupée.

Rassemble en un seul écran ce qui était dispersé en plusieurs fenêtres
flottantes du terminal : indices mondiaux, top sociétés (par région),
plus forts mouvements (variations), indicateurs macro (éco), performance
sectorielle et watchlist du joueur. Ouvert via MARKETHUB / le rail
latéral « MARCHÉ ».
"""
import pygame

from core import config
from core.scene_manager import Scene
from ui import fonts, widgets
from ui.popups import PopupMixin

_ECO_NOTES = {
    "rate": "coût de l'argent ; ↑ pèse sur actions/immo",
    "inflation": "hausse des prix ; guide la banque centrale",
    "growth": "PIB ; ↑ soutient les bénéfices",
    "unemployment": "↑ = ralentissement",
    "confidence": "moral des marchés",
    "credit_ig": "coût d'emprunt des émetteurs Investment Grade ; ↑ = stress",
    "credit_hy": "coût d'emprunt des émetteurs High Yield ; ↑ = stress marqué",
    "liquidity": "facilité d'exécution du marché ; ↓ = conditions tendues",
}

_TABS = [("overview", "Vue d'ensemble"), ("sectors", "Secteurs"), ("watchlist", "Watchlist")]
_SECTOR_BAR_MAX = 1.5    # % de variation correspondant à une jauge pleine


class MarketHubScene(Scene, PopupMixin):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.top_region = self.app.gs.player.continent
        self.tab = "overview"
        self.init_popups()
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self._tab_rects = {}
        self._ticker_rects = {}
        self._region_rects = {}
        self._index_row_rects = {}
        self._eco_row_rects = {}
        self._sector_row_rects = {}
        self._regime_rect = None

    def handle_event(self, event):
        if self.popups_handle_event(event):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.popups_close_top():
                return
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tab_id, rect in self._tab_rects.items():
                if rect.collidepoint(event.pos):
                    self.tab = tab_id
                    return
            for region, rect in self._region_rects.items():
                if rect.collidepoint(event.pos):
                    self.top_region = region
                    return
            for tk, rect in self._ticker_rects.items():
                if rect.collidepoint(event.pos):
                    self.app.scenes.go("company", ticker=tk, return_to="markethub")
                    return
            for name, rect in self._index_row_rects.items():
                if rect.collidepoint(event.pos):
                    chg = self.market.index_change_pct(name)
                    col = config.COL_UP if chg >= 0 else config.COL_DOWN
                    self._open_series_popup(f"INDICE — {name}", self.market.index_history(name), col)
                    return
            if self._regime_rect and self._regime_rect.collidepoint(event.pos):
                reg_good = self.market.regime in ("Expansion", "Calme")
                self._open_series_popup("RÉGIME — taux directeur",
                                        self.market.macro_hist.get("rate", []),
                                        config.COL_UP if reg_good else config.COL_DOWN)
                return
            for key, rect in self._eco_row_rects.items():
                if rect.collidepoint(event.pos):
                    ch = self.market.macro_change(key)
                    col = config.COL_UP if ch >= 0 else config.COL_DOWN
                    label = self.market.macro[key]["label"]
                    self._open_series_popup(f"ÉCO — {label}", self.market.macro_hist.get(key, []), col)
                    return
            for sector, rect in self._sector_row_rects.items():
                if rect.collidepoint(event.pos):
                    self._open_sector_popup(sector)
                    return

    def _open_series_popup(self, title, series, color):
        def render(surf, rect):
            if len(series) < 2:
                widgets.draw_text(surf, "Historique insuffisant (avancez le temps).",
                                  (rect.x, rect.y), fonts.small(), config.COL_TEXT_DIM)
                return
            widgets.draw_series(surf, rect, series, color, baseline=False)
            widgets.draw_text(surf, f"Dernier : {series[-1]:,.2f}", (rect.x, rect.bottom - 16),
                              fonts.tiny(), config.COL_TEXT_DIM)
        self.open_custom_chart(title, render, accent=color)

    def _open_sector_popup(self, sector):
        comps = self.market.top_companies(sector=sector, n=10)
        cur = self._cur()
        def render(surf, rect):
            y = rect.y
            widgets.draw_text(surf, f"Top capitalisations — {sector}", (rect.x, y),
                              fonts.small(bold=True), config.COL_TEXT)
            y += 24
            for c in comps:
                ccol = config.COL_UP if c["change_pct"] >= 0 else config.COL_DOWN
                widgets.draw_text(surf, c["ticker"], (rect.x, y), fonts.small(bold=True), config.COL_AMBER)
                widgets.draw_text(surf, c["name"][:22], (rect.x + 64, y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, widgets.format_money(c["mktcap"] * 1e6, cur),
                                  (rect.x + rect.w - 90, y), fonts.tiny(), config.COL_TEXT_DIM, align="right")
                widgets.draw_text(surf, f"{'+' if c['change_pct']>=0 else ''}{c['change_pct']:.2f}%",
                                  (rect.right, y), fonts.tiny(bold=True), ccol, align="right")
                y += 24
            if y == rect.y + 24:
                widgets.draw_text(surf, "Aucune société dans ce secteur.", (rect.x, y),
                                  fonts.small(), config.COL_TEXT_DIM)
        self.open_custom_chart(f"SECTEUR — {sector}", render, accent=config.COL_PRESTIGE, size=(460, 360))

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "MARCHÉ", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Indices, top sociétés, variations, macro-économie, secteurs et watchlist.",
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        self._draw_tabs(surf)

        M = config.MARGIN
        top = config.content_top() + 30
        bottom = config.footer_y() - 8
        self._ticker_rects = {}
        self._region_rects = {}

        if self.tab == "overview":
            colw = (config.SCREEN_WIDTH - 3 * M) // 2
            row_h = (bottom - top - M) // 2
            x1, x2 = M, M * 2 + colw
            y1, y2 = top, top + row_h + M
            self._draw_indices(surf, pygame.Rect(x1, y1, colw, row_h))
            self._draw_top(surf, pygame.Rect(x2, y1, colw, row_h))
            self._draw_movers(surf, pygame.Rect(x1, y2, colw, row_h))
            self._draw_eco(surf, pygame.Rect(x2, y2, colw, row_h))
        elif self.tab == "sectors":
            self._draw_sectors(surf, pygame.Rect(M, top, config.SCREEN_WIDTH - 2 * M, bottom - top))
        else:
            self._draw_watchlist(surf, pygame.Rect(M, top, config.SCREEN_WIDTH - 2 * M, bottom - top))

        self.back_btn.draw(surf)
        self.popups_draw(surf)

    def _draw_tabs(self, surf):
        self._tab_rects = {}
        x = 40
        y = config.content_top()
        for tab_id, label in _TABS:
            w = fonts.small(bold=True).size(label)[0] + 22
            rect = pygame.Rect(x, y, w, 24)
            active = (tab_id == self.tab)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL, rect, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, rect, 1, border_radius=4)
            widgets.draw_text(surf, label, rect.center, fonts.small(bold=active),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            self._tab_rects[tab_id] = rect
            x = rect.right + 8

    def _draw_indices(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Indices mondiaux", config.COL_AMBER)
        mp = pygame.mouse.get_pos()
        self._index_row_rects = {}
        y = inner.y
        for name, *_ in self.market.index_defs:
            v = self.market.index_value(name)
            chg = self.market.index_change_pct(name)
            ccol = config.COL_UP if chg >= 0 else config.COL_DOWN
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 22)
            self._index_row_rects[name] = row
            if row.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
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
        mp = pygame.mouse.get_pos()
        m = self.market.macro
        reg_good = self.market.regime in ("Expansion", "Calme")
        y = inner.y
        self._regime_rect = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 22)
        if self._regime_rect.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._regime_rect, border_radius=3)
        widgets.draw_text(surf, "Régime de marché", (inner.x, y), fonts.small(), config.COL_TEXT)
        age = self.market.regime_age()
        widgets.draw_text(surf, f"{self.market.regime_label()} (depuis {age} sem.)",
                          (inner.right, y), fonts.small(bold=True),
                          config.COL_UP if reg_good else config.COL_DOWN, align="right")
        if hasattr(self.market, "curve_slope"):
            slope = self.market.curve_slope()
            phase = self.market.curve_phase()
            scol = config.COL_DOWN if slope < 0 else config.COL_UP
            widgets.draw_text(surf, "Courbe des taux (10Y-2Y)", (inner.x, y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, f"{phase} ({'+' if slope>=0 else ''}{slope:.2f}pb)",
                              (inner.right, y), fonts.small(bold=True), scol, align="right")
            y += 26
        self._eco_row_rects = {}
        for key in ["rate", "inflation", "growth", "unemployment", "confidence",
                    "credit_ig", "credit_hy", "liquidity"]:
            d = m[key]
            ch = self.market.macro_change(key)
            ccol = config.COL_UP if ch >= 0 else config.COL_DOWN
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 40)
            self._eco_row_rects[key] = row
            if row.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
            widgets.draw_text(surf, d["label"], (inner.x, y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, f"{d['v']:.2f}{d['unit']}", (inner.x + inner.w - 90, y),
                              fonts.small(bold=True), config.COL_WHITE, align="right")
            widgets.draw_text(surf, f"{'+' if ch>=0 else ''}{ch:.2f}", (inner.right, y),
                              fonts.small(), ccol, align="right")
            y += 22
            widgets.draw_text(surf, _ECO_NOTES.get(key, ""), (inner.x, y),
                              fonts.tiny(), config.COL_TEXT_DIM)
            y += 18

    def _draw_sectors(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Performance sectorielle (dernier pas, pondérée par capitalisation)",
                                   config.COL_PRESTIGE)
        widgets.draw_text(surf, "Cliquez un secteur pour voir ses plus fortes capitalisations.",
                          (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
        cur = self._cur()
        mp = pygame.mouse.get_pos()
        self._sector_row_rects = {}
        y = inner.y + 22
        row_h = 28
        bar_w = 160
        for s in self.market.sector_performance():
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, row_h - 2)
            self._sector_row_rects[s["sector"]] = row
            if row.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
            ccol = config.COL_UP if s["change_pct"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, s["sector"], (inner.x, y), fonts.small(bold=True), config.COL_TEXT)
            bar_rect = pygame.Rect(inner.x + 160, y + 2, bar_w, 14)
            ratio = min(1.0, abs(s["change_pct"]) / _SECTOR_BAR_MAX)
            widgets.draw_progress(surf, bar_rect, ratio, accent=ccol)
            widgets.draw_text(surf, f"{'+' if s['change_pct']>=0 else ''}{s['change_pct']:.2f}%",
                              (bar_rect.right + 12, y), fonts.small(bold=True), ccol)
            widgets.draw_text(surf, f"{s['n']} sociétés", (inner.x + inner.w - 200, y),
                              fonts.tiny(), config.COL_TEXT_DIM, align="right")
            widgets.draw_text(surf, widgets.format_money(s["mktcap"] * 1e6, cur), (inner.right, y),
                              fonts.tiny(bold=True), config.COL_WHITE, align="right")
            y += row_h

    def _draw_watchlist(self, surf, rect):
        p = self.app.gs.player
        inner = widgets.draw_panel(surf, rect, f"Votre watchlist ({len(p.watchlist)}/10)", config.COL_CYAN)
        if not p.watchlist:
            widgets.draw_text(surf, "Aucune valeur suivie. Utilisez WATCHLIST ADD <ticker> au terminal,",
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, "ou ouvrez une société puis ajoutez-la à vos favoris.",
                              (inner.x, inner.y + 20), fonts.small(), config.COL_TEXT_DIM)
            return
        mp = pygame.mouse.get_pos()
        cur = self._cur()
        y = inner.y
        row_h = 30
        for tk in p.watchlist:
            mt = self.market.metrics(tk)
            if mt is None:
                continue
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, row_h - 2)
            self._ticker_rects[tk] = row
            if row.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
            ccol = config.COL_UP if mt["change_pct"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, tk, (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
            widgets.draw_text(surf, mt["name"][:24], (inner.x + 64, y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, mt["sector"], (inner.x + inner.w // 2, y),
                              fonts.tiny(), config.COL_TEXT_DIM, align="right")
            widgets.draw_text(surf, widgets.format_money(mt["price"], cur), (inner.right - 90, y),
                              fonts.small(bold=True), config.COL_WHITE, align="right")
            widgets.draw_text(surf, f"{'+' if mt['change_pct']>=0 else ''}{mt['change_pct']:.2f}% (1an)",
                              (inner.right, y), fonts.small(bold=True), ccol, align="right")
            y += row_h
