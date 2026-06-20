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

_TABS = [("overview", "Vue d'ensemble"), ("sectors", "Secteurs"), ("topflop", "Top/Flop"),
         ("heatmap", "Heatmap"), ("watchlist", "Watchlist")]
_SECTOR_BAR_MAX = 1.5    # % de variation correspondant à une jauge pleine

_TOPFLOP_PERIODS = [("1 pas", 1), ("1 mois", 6), ("3 mois", 18), ("1 an", 73)]
_HEATMAP_MAX = 1.5       # % de variation correspondant à une teinte pleine


class MarketHubScene(Scene, PopupMixin):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.top_region = self.app.gs.player.continent
        self.tab = "overview"
        self.topflop_steps = _TOPFLOP_PERIODS[0][1]
        self._period_rects = {}
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
        # une ScrollState indépendante par panneau défilant (clé = id de panneau).
        self._scrolls = {}

    def _scroll(self, key):
        return self._scrolls.setdefault(key, widgets.ScrollState())

    def handle_event(self, event):
        if self.popups_handle_event(event):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.popups_close_top():
                return
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            for st in self._scrolls.values():
                if st.handle_wheel(event):
                    return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tab_id, rect in self._tab_rects.items():
                if rect.collidepoint(event.pos):
                    self.tab = tab_id
                    return
            for steps, rect in self._period_rects.items():
                if rect.collidepoint(event.pos):
                    self.topflop_steps = steps
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
        elif self.tab == "topflop":
            self._draw_topflop(surf, pygame.Rect(M, top, config.SCREEN_WIDTH - 2 * M, bottom - top))
        elif self.tab == "heatmap":
            self._draw_heatmap(surf, pygame.Rect(M, top, config.SCREEN_WIDTH - 2 * M, bottom - top))
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
        st = self._scroll("indices")
        list_area = pygame.Rect(inner.x - 6, inner.y, inner.w + 12, inner.h)
        self._index_row_rects = {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = inner.y - st.scroll
        for name, *_ in self.market.index_defs:
            v = self.market.index_value(name)
            chg = self.market.index_change_pct(name)
            ccol = config.COL_UP if chg >= 0 else config.COL_DOWN
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 22)
            visible = list_area.top - 24 < y < list_area.bottom
            if visible:
                self._index_row_rects[name] = row
                if row.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
                widgets.draw_text(surf, name, (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
                widgets.draw_text(surf, f"{v:,.0f}", (inner.x + inner.w // 2, y),
                                  fonts.small(), config.COL_TEXT, align="right")
                widgets.draw_text(surf, f"{'+' if chg>=0 else ''}{chg:.2f}%", (inner.right, y),
                                  fonts.small(bold=True), ccol, align="right")
            y += 24
        surf.set_clip(prev_clip)
        content_h = (y + st.scroll) - inner.y
        st.set_bounds(list_area, content_h)
        widgets.draw_scrollbar(surf, rect, list_area, st.scroll, st.max_scroll, content_h)

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
        list_top = y
        list_area = pygame.Rect(inner.x - 6, list_top, inner.w + 12, inner.bottom - list_top)
        st = self._scroll("top")
        # demande large : la liste défile, donc on n'a plus besoin de borner n à la hauteur visible.
        companies = self.market.top_companies(region=self.top_region, n=40)
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_top - st.scroll
        for c in companies:
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 24)
            visible = list_area.top - 26 < y < list_area.bottom
            if visible:
                self._ticker_rects[c["ticker"]] = row
                if row.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
                widgets.draw_text(surf, c["ticker"], (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
                widgets.draw_text(surf, c["name"][:16], (inner.x + 58, y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, widgets.format_money(c["mktcap"] * 1e6, cur), (inner.right, y),
                                  fonts.tiny(bold=True), config.COL_WHITE, align="right")
            y += 26
        surf.set_clip(prev_clip)
        content_h = (y + st.scroll) - list_top
        st.set_bounds(list_area, content_h)
        widgets.draw_scrollbar(surf, rect, list_area, st.scroll, st.max_scroll, content_h)

    def _draw_movers(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Variations — plus forts mouvements", config.COL_DEAL)
        mp = pygame.mouse.get_pos()
        colw = (inner.w - 16) // 2
        col_x1, col_x2 = inner.x, inner.x + colw + 16
        list_top = inner.y + 18
        list_area1 = pygame.Rect(col_x1 - 4, list_top, colw + 8, inner.bottom - list_top)
        list_area2 = pygame.Rect(col_x2 - 4, list_top, colw + 8, inner.bottom - list_top)

        widgets.draw_text(surf, "HAUSSES", (col_x1, inner.y), fonts.tiny(bold=True), config.COL_UP)
        widgets.draw_text(surf, "BAISSES", (col_x2, inner.y), fonts.tiny(bold=True), config.COL_DOWN)

        self._draw_mover_column(surf, self._scroll("movers_up"), list_area1, col_x1, colw,
                                self.market.top_companies(n=40, by="gain"), "↑", config.COL_UP, mp)
        self._draw_mover_column(surf, self._scroll("movers_down"), list_area2, col_x2, colw,
                                self.market.top_companies(n=40, by="loss"), "↓", config.COL_DOWN, mp)

    def _draw_mover_column(self, surf, st, list_area, col_x, colw, companies, arrow, col, mp):
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_area.y - st.scroll
        for c in companies:
            row = pygame.Rect(col_x - 4, y - 2, colw + 8, 22)
            visible = list_area.top - 24 < y < list_area.bottom
            if visible:
                self._ticker_rects[c["ticker"]] = row
                if row.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
                widgets.draw_text(surf, f"{arrow} " + c["ticker"], (col_x, y), fonts.small(bold=True), col)
                widgets.draw_text(surf, c["name"][:18], (col_x + 70, y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, c["sector"], (col_x + colw, y),
                                  fonts.tiny(), config.COL_TEXT_DIM, align="right")
            y += 24
        surf.set_clip(prev_clip)
        content_h = (y + st.scroll) - list_area.y
        st.set_bounds(list_area, content_h)
        widgets.draw_scrollbar(surf, pygame.Rect(col_x - 4, list_area.y, colw + 12, list_area.h),
                               list_area, st.scroll, st.max_scroll, content_h)

    def _draw_eco(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Éco — macro-économie", config.COL_PRESTIGE)
        mp = pygame.mouse.get_pos()
        m = self.market.macro
        reg_good = self.market.regime in ("Expansion", "Calme")

        # Le régime + la courbe des taux restent fixes en tête de panneau (peu de
        # contenu, pas besoin de défilement) ; seule la liste d'indicateurs défile,
        # ce qui évite le chevauchement constaté quand tout était empilé dans la
        # même hauteur fixe sans clipping ni espacement suffisant.
        y = inner.y
        self._regime_rect = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 22)
        if self._regime_rect.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._regime_rect, border_radius=3)
        widgets.draw_text(surf, "Régime de marché", (inner.x, y), fonts.small(), config.COL_TEXT)
        age = self.market.regime_age()
        widgets.draw_text(surf, f"{self.market.regime_label()} (depuis {age} sem.)",
                          (inner.right, y), fonts.small(bold=True),
                          config.COL_UP if reg_good else config.COL_DOWN, align="right")
        y += 26
        if hasattr(self.market, "curve_slope"):
            slope = self.market.curve_slope()
            phase = self.market.curve_phase()
            scol = config.COL_DOWN if slope < 0 else config.COL_UP
            widgets.draw_text(surf, "Courbe des taux (10Y-2Y)", (inner.x, y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, f"{phase} ({'+' if slope>=0 else ''}{slope:.2f}pb)",
                              (inner.right, y), fonts.small(bold=True), scol, align="right")
            y += 26
        if hasattr(self.market, "curve_curvature"):
            curv = self.market.curve_curvature()
            ccol = config.COL_DOWN if curv > 0.3 else config.COL_TEXT_DIM
            widgets.draw_text(surf, "Courbure (bosse mi-courbe)", (inner.x, y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, f"{curv:.2f}pb", (inner.right, y),
                              fonts.small(bold=True), ccol, align="right")
            y += 26

        list_top = y
        list_area = pygame.Rect(inner.x - 6, list_top, inner.w + 12, inner.bottom - list_top)
        st = self._scroll("eco")
        self._eco_row_rects = {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_top - st.scroll
        for key in ["rate", "inflation", "growth", "unemployment", "confidence",
                    "credit_ig", "credit_hy", "liquidity"]:
            d = m[key]
            ch = self.market.macro_change(key)
            ccol = config.COL_UP if ch >= 0 else config.COL_DOWN
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, 40)
            visible = list_area.top - 44 < y < list_area.bottom
            if visible:
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
            else:
                y += 40
        surf.set_clip(prev_clip)
        content_h = (y + st.scroll) - list_top
        st.set_bounds(list_area, content_h)
        widgets.draw_scrollbar(surf, rect, list_area, st.scroll, st.max_scroll, content_h)

    def _draw_sectors(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Performance sectorielle (dernier pas, pondérée par capitalisation)",
                                   config.COL_PRESTIGE)
        widgets.draw_text(surf, "Cliquez un secteur pour voir ses plus fortes capitalisations.",
                          (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
        cur = self._cur()
        mp = pygame.mouse.get_pos()
        self._sector_row_rects = {}
        list_top = inner.y + 22
        list_area = pygame.Rect(inner.x - 6, list_top, inner.w + 12, inner.bottom - list_top)
        st = self._scroll("sectors")
        row_h = 28
        bar_w = 160
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_top - st.scroll
        for s in self.market.sector_performance():
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, row_h - 2)
            visible = list_area.top - row_h < y < list_area.bottom
            if visible:
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
        surf.set_clip(prev_clip)
        content_h = (y + st.scroll) - list_top
        st.set_bounds(list_area, content_h)
        widgets.draw_scrollbar(surf, rect, list_area, st.scroll, st.max_scroll, content_h)

    def _draw_topflop(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Top/Flop — plus forts mouvements sur la période", config.COL_DEAL)
        mp = pygame.mouse.get_pos()
        x = inner.x
        y = inner.y
        self._period_rects = {}
        for label, steps in _TOPFLOP_PERIODS:
            w = fonts.tiny(bold=True).size(label)[0] + 14
            r = pygame.Rect(x, y, w, 18)
            self._period_rects[steps] = r
            active = (steps == self.topflop_steps)
            col = config.COL_AMBER if active else config.COL_TEXT_DIM
            if r.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, r, border_radius=3)
            widgets.draw_text(surf, label, (r.x + 7, r.y + 1), fonts.tiny(bold=active), col)
            x = r.right + 6

        b = self.market.breadth(period_steps=self.topflop_steps)
        y += 26
        widgets.draw_text(surf,
                          f"Pouls du marché : {b['advancers']} hausses / {b['decliners']} baisses "
                          f"/ {b['unchanged']} stables  ·  {b['pct_above_ma']:.0f}% au-dessus de leur "
                          f"moyenne mobile  ·  {b['new_highs']} plus-hauts / {b['new_lows']} plus-bas (1 an)",
                          (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        y += 22

        colw = (inner.w - 16) // 2
        col_x1, col_x2 = inner.x, inner.x + colw + 16

        widgets.draw_text(surf, "HAUSSES", (col_x1, y), fonts.tiny(bold=True), config.COL_UP)
        widgets.draw_text(surf, "BAISSES", (col_x2, y), fonts.tiny(bold=True), config.COL_DOWN)
        list_top = y + 18
        list_area1 = pygame.Rect(col_x1 - 4, list_top, colw + 8, inner.bottom - list_top)
        list_area2 = pygame.Rect(col_x2 - 4, list_top, colw + 8, inner.bottom - list_top)

        gainers = self.market.top_movers(self.topflop_steps, n=40, by="gain")
        losers = self.market.top_movers(self.topflop_steps, n=40, by="loss")
        self._draw_topflop_column(surf, self._scroll("topflop_up"), list_area1, col_x1, colw,
                                  gainers, "↑", config.COL_UP, mp)
        self._draw_topflop_column(surf, self._scroll("topflop_down"), list_area2, col_x2, colw,
                                  losers, "↓", config.COL_DOWN, mp)

    def _draw_topflop_column(self, surf, st, list_area, col_x, colw, companies, arrow, col, mp):
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y_rows = list_area.y - st.scroll
        for c in companies:
            row = pygame.Rect(col_x - 4, y_rows - 2, colw + 8, 22)
            visible = list_area.top - 24 < y_rows < list_area.bottom
            if visible:
                self._ticker_rects[c["ticker"]] = row
                if row.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
                widgets.draw_text(surf, f"{arrow} " + c["ticker"], (col_x, y_rows), fonts.small(bold=True), col)
                widgets.draw_text(surf, c["name"][:16], (col_x + 70, y_rows), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, f"{'+' if c['change_pct']>=0 else ''}{c['change_pct']:.2f}%",
                                  (col_x + colw, y_rows), fonts.tiny(bold=True), col, align="right")
            y_rows += 24
        surf.set_clip(prev_clip)
        content_h = (y_rows + st.scroll) - list_area.y
        st.set_bounds(list_area, content_h)
        widgets.draw_scrollbar(surf, pygame.Rect(col_x - 4, list_area.y, colw + 12, list_area.h),
                               list_area, st.scroll, st.max_scroll, content_h)

    def _draw_heatmap(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Heatmap secteur × région (dernier pas, pondérée par capitalisation)",
                                   config.COL_PRESTIGE)
        grid = self.market.heatmap()
        regions = self.market.regions

        label_w = 110
        col_w = max(70, (inner.w - label_w) // max(1, len(regions)))
        row_h = max(20, (inner.h - 24) // max(1, len(grid)))

        def cell_color(v):
            if v is None:
                return config.COL_PANEL
            ratio = max(-1.0, min(1.0, v / _HEATMAP_MAX))
            base = config.COL_UP if ratio >= 0 else config.COL_DOWN
            t = abs(ratio)
            return tuple(int(config.COL_PANEL[i] + (base[i] - config.COL_PANEL[i]) * t) for i in range(3))

        y = inner.y + 20
        x0 = inner.x + label_w
        for ci, region in enumerate(regions):
            widgets.draw_text(surf, region[:8], (x0 + ci * col_w, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        for row in grid:
            widgets.draw_text(surf, row["sector"], (inner.x, y + 4), fonts.small(), config.COL_TEXT)
            for ci, region in enumerate(regions):
                v = row["regions"].get(region)
                cell = pygame.Rect(x0 + ci * col_w, y, col_w - 4, row_h - 4)
                pygame.draw.rect(surf, cell_color(v), cell)
                pygame.draw.rect(surf, config.COL_BORDER, cell, 1)
                if v is not None:
                    txt_col = config.COL_BG if abs(v) / _HEATMAP_MAX > 0.5 else config.COL_TEXT
                    widgets.draw_text(surf, f"{'+' if v>=0 else ''}{v:.2f}%", cell.center,
                                      fonts.tiny(bold=True), txt_col, align="center")
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
        list_area = pygame.Rect(inner.x - 6, inner.y, inner.w + 12, inner.h)
        st = self._scroll("watchlist")
        row_h = 30
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = inner.y - st.scroll
        for tk in p.watchlist:
            mt = self.market.metrics(tk)
            if mt is None:
                continue
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, row_h - 2)
            visible = list_area.top - row_h < y < list_area.bottom
            if visible:
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
        surf.set_clip(prev_clip)
        content_h = (y + st.scroll) - inner.y
        st.set_bounds(list_area, content_h)
        widgets.draw_scrollbar(surf, rect, list_area, st.scroll, st.max_scroll, content_h)
