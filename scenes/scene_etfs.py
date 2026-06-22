"""
scene_etfs.py — Marché des ETF (fonds indiciels) : cotations, exposition et trading.

Liste tout l'univers d'ETF (core/etfs.py) avec leur NAV, leur catégorie, leur
exposition, leurs frais, leur rendement indicatif et leur niveau de risque.
Recherche libre, filtre par catégorie (broad/monde/régions/pays/secteurs/styles/
thématiques/ESG/REIT/obligataire/commodities/devises/levier-inverse) et tri.
Les ETF à effet de levier / inverses sont signalés en rouge (« risque élevé »).
Achat/vente par paquets ; clic sur le nom = fiche flottante. Ouvert via ETF.
"""
import pygame

from core import config, unlocks
from core import etfs as E
from core.scene_manager import Scene
from ui import fonts, keynav, widgets
from ui.popups import PopupMixin

LOT = 10
ROW_H = 26
SORT_FIELDS = [("name", "NOM"), ("price", "NAV"), ("change_pct", "VAR %"),
               ("change_1y", "1 AN"), ("yield", "RDT"), ("expense", "FRAIS"),
               ("risk", "RISQUE")]


class ETFScene(Scene, PopupMixin):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.init_popups()
        self.msg = ""
        self._t = 0.0
        self.cat_filter = kwargs.get("category", None)
        self.search = ""
        self.sort_key = "change_1y"
        self.sort_dir = -1
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self.row_cursor = 0
        self._row_list = []
        self.buy_rects = {}
        self.sell_rects = {}
        self.name_rects = {}
        self._cat_rects = {}
        self._sort_rects = {}
        self._search_clear_rect = None
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.explore_btn = widgets.Button((220, config.SCREEN_HEIGHT - 50, 160, 42),
                                          "EXPLORER", config.COL_CYAN)

    def _can_trade(self):
        return unlocks.unlocked(self.app.gs.player, "trade")

    # --------------------------------------------------------------- data
    def _filtered_sorted(self):
        q = self.search.strip().lower()
        out = []
        for quote in E.all_quotes(self.market):
            if self.cat_filter and quote["category"] != self.cat_filter:
                continue
            if q:
                hay = f"{quote['name']} {quote['id']} {quote['sub']} {quote['exposure']}".lower()
                if q not in hay:
                    continue
            out.append(quote)
        key = self.sort_key
        rev = self.sort_dir < 0
        if key == "name":
            out.sort(key=lambda r: r["name"].lower(), reverse=rev)
        else:
            out.sort(key=lambda r: (r[key] if r[key] is not None else -1e18), reverse=rev)
        return out

    def _scroll_to_cursor(self):
        """Ajuste le scroll pour garder la ligne sélectionnée au clavier visible."""
        if not self._list_rect:
            return
        row_top = self.row_cursor * ROW_H
        row_bottom = row_top + ROW_H
        if row_top < self.scroll:
            self.scroll = row_top
        elif row_bottom > self.scroll + self._list_rect.h:
            self.scroll = row_bottom - self._list_rect.h
        self.scroll = max(0, min(self._max_scroll, self.scroll))

    # --------------------------------------------------------------- events
    def handle_event(self, event):
        if self.popups_handle_event(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.popups_close_top():
                    return
                if self.search:
                    self.search = ""
                    return
                self.app.scenes.go(self.return_to)
                return
            elif event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                return
            elif event.key == pygame.K_PAGEUP:
                self.scroll = max(0, self.scroll - 200)
                return
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll = min(self._max_scroll, self.scroll + 200)
                return
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.row_cursor, activate = widgets.list_key_nav(
                    event, self.row_cursor, len(self._row_list))
                if self._row_list:
                    self._scroll_to_cursor()
                if activate and self._row_list:
                    self.open_etf(self._row_list[self.row_cursor]["id"])
                return
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search += event.unicode
                self.scroll = 0
                return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if self.explore_btn.handle(event):
            self.app.scenes.go("explorer", return_to="etfs")
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            for eid, rect in self.name_rects.items():
                if rect.collidepoint(event.pos):
                    self.open_etf(eid)
                    return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return
            for val, rect in self._cat_rects.items():
                if rect.collidepoint(event.pos):
                    self.cat_filter = None if self.cat_filter == val else val
                    self.scroll = 0
                    return
            for key, rect in self._sort_rects.items():
                if rect.collidepoint(event.pos):
                    if self.sort_key == key:
                        self.sort_dir *= -1
                    else:
                        self.sort_key = key
                        self.sort_dir = 1 if key == "name" else -1
                    return
            for eid, rect in self.name_rects.items():
                if rect.collidepoint(event.pos):
                    self.open_etf(eid)
                    return
            p, m = self.app.gs.player, self.market
            if not self._can_trade():
                return
            for eid, rect in self.buy_rects.items():
                if rect.collidepoint(event.pos):
                    r = E.buy(p, m, eid, LOT)
                    self.msg = (f"Acheté {LOT} × {eid} @ {r['price']:.2f}"
                                if r["ok"] else f"Achat refusé ({r['reason']}).")
                    if r["ok"] and not p.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)
                    return
            for eid, rect in self.sell_rects.items():
                if rect.collidepoint(event.pos):
                    r = E.sell(p, m, eid, LOT)
                    self.msg = (f"Vendu {min(LOT, r['qty']):.0f} × {eid} (P&L {r['realized']:+.0f})"
                                if r["ok"] else "Aucune position.")
                    if r["ok"] and not p.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)
                    return

    def update(self, dt):
        self._t += dt
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.explore_btn.update(mp, dt)

    # ----------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        m = self.market
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        widgets.draw_text(surf, "ETF", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Fonds indiciels : un panier dont la NAV émerge de son exposition — "
                                "réagit aux mêmes facteurs (monde/secteur/région/taux). "
                                + (self.msg if self.msg else ""),
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)
        mp = pygame.mouse.get_pos()
        self._tooltip = None
        x0 = 40
        top = config.content_top()

        # recherche
        search_rect = pygame.Rect(x0, top, 280, 24)
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else (cursor + "Tapez pour rechercher (nom, ticker, exposition)…")
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 4), fonts.small(),
                          config.COL_TEXT if self.search else config.COL_TEXT_DIM)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 22, search_rect.y, 22, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        # chips catégorie
        cat_chips = [(None, "TOUTES")] + [(k, lbl) for k, lbl in E.CATEGORIES]
        self._cat_rects, ybot = self._draw_chip_row(surf, x0 + 290, top, config.SCREEN_WIDTH - 40,
                                                     cat_chips, self.cat_filter, config.COL_PRESTIGE)
        y = max(ybot, top + 28)

        # tri
        self._sort_rects = {}
        widgets.draw_text(surf, "TRIER :", (x0, y + 3), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        sx0 = x0 + 56
        sx = sx0
        for key, lbl in SORT_FIELDS:
            active = (self.sort_key == key)
            arrow = (" ▲" if self.sort_dir > 0 else " ▼") if active else ""
            full = lbl + arrow
            w = fonts.tiny(bold=True).size(full)[0] + 16
            rect = pygame.Rect(sx, y, w, 20)
            self._sort_rects[key] = rect
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, full, rect.center, fonts.tiny(bold=active),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            sx += w + 6
        y += 28

        rows = self._filtered_sorted()
        self._row_list = rows
        self.row_cursor = min(self.row_cursor, len(rows) - 1) if rows else 0
        panel = pygame.Rect(x0, y, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - y)
        inner = widgets.draw_panel(surf, panel, f"ETF ({len(rows)})", config.COL_PRESTIGE)
        self.cols = {"name": inner.x, "tk": inner.x + 235, "cat": inner.x + 295,
                     "expo": inner.x + 410, "risk": inner.x + 645, "nav": inner.x + 705,
                     "var": inner.x + 775, "y1": inner.x + 845, "yld": inner.x + 910,
                     "exp": inner.x + 970, "you": inner.x + 1030, "act": inner.x + 1075}
        heads = [("NOM", "name"), ("TICK", "tk"), ("CAT.", "cat"), ("EXPOSITION", "expo"),
                 ("RISQ", "risk"), ("NAV", "nav"), ("VAR%", "var"), ("1AN", "y1"),
                 ("RDT", "yld"), ("FRAIS", "exp"), ("VOUS", "you")]
        for lbl, key in heads:
            widgets.draw_text(surf, lbl, (self.cols[key], inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        if self._can_trade():
            widgets.draw_text(surf, "TRADE", (self.cols["act"], inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)

        list_top = inner.y + 22
        list_area = pygame.Rect(inner.x - 6, list_top, inner.w + 12, inner.bottom - list_top - 24)
        self._list_rect = list_area
        self.buy_rects, self.sell_rects, self.name_rects = {}, {}, {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        ry = list_top - self.scroll
        for i, q in enumerate(rows):
            if (list_area.top - ROW_H) < ry < list_area.bottom:
                self._draw_row(surf, q, ry, p, mp, i == self.row_cursor)
            ry += ROW_H
        surf.set_clip(prev_clip)

        content_h = (ry + self.scroll) - list_top
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        if self._max_scroll > 0:
            track = pygame.Rect(panel.right - 8, list_area.y, 6, list_area.h)
            pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=3)
            frac = list_area.h / (content_h or 1)
            bar_h = max(24, int(list_area.h * frac))
            bar_y = list_area.y + int((list_area.h - bar_h) * (self.scroll / self._max_scroll))
            pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 6, bar_h), border_radius=3)

        hv = E.holdings_value(p, m)
        widgets.draw_text(surf, f"Valeur ETF détenue : {widgets.format_money(hv, cur)}"
                          + ("" if self._can_trade() else "   ⊘ trading débloqué au grade Associate"),
                          (inner.x, inner.bottom - 18), fonts.small(bold=True),
                          config.COL_UP if hv else config.COL_TEXT_DIM)
        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14),
                              [("↑↓", "actifs"), ("ENTRÉE", "ouvrir")])
        self.back_btn.draw(surf)
        self.explore_btn.draw(surf)
        self.popups_draw(surf)
        if self._tooltip:
            widgets.draw_tooltip(surf, *self._tooltip)

    def _truncated_hover(self, text, font, max_width, rect, mp):
        fitted = widgets.fit_text(text, font, max_width)
        if fitted != text and rect.collidepoint(mp):
            self._tooltip = (text, mp)
        return fitted

    def _draw_row(self, surf, q, y, p, mp, cursor=False):
        cols = self.cols
        row_rect = pygame.Rect(cols["name"] - 4, y - 2, 1180, ROW_H)
        if row_rect.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
        keynav.draw_focus_ring(surf, row_rect, cursor)
        risky = q["leveraged"]
        ncol = config.COL_DOWN if risky else config.COL_TEXT
        name_w = min(225, fonts.small(bold=True).size(q["name"])[0])
        self.name_rects[q["id"]] = pygame.Rect(cols["name"] - 2, y - 2, name_w + 4, ROW_H - 4)
        widgets.draw_text(surf, widgets.fit_text(q["name"], fonts.small(bold=True), 225),
                          (cols["name"], y), fonts.small(bold=True), ncol)
        widgets.draw_text(surf, q["id"], (cols["tk"], y), fonts.tiny(bold=True), config.COL_AMBER)
        cat_rect = pygame.Rect(cols["cat"], y + 1, 110, ROW_H - 4)
        cat_label = self._truncated_hover(q["category_label"], fonts.tiny(), 110, cat_rect, mp)
        widgets.draw_text(surf, cat_label, (cols["cat"], y + 1), fonts.tiny(), config.COL_PRESTIGE)
        expo_rect = pygame.Rect(cols["expo"], y + 1, 230, ROW_H - 4)
        expo_label = self._truncated_hover(q["exposure"], fonts.tiny(), 230, expo_rect, mp)
        widgets.draw_text(surf, expo_label, (cols["expo"], y + 1), fonts.tiny(), config.COL_TEXT_DIM)
        rcol = (config.COL_UP if q["risk"] <= 2 else config.COL_WARN if q["risk"] == 3 else config.COL_DOWN)
        widgets.draw_text(surf, "●" * q["risk"], (cols["risk"], y), fonts.tiny(bold=True), rcol)
        widgets.draw_text(surf, f"{q['price']:,.1f}".replace(",", " "), (cols["nav"], y),
                          fonts.small(bold=True), config.COL_WHITE)
        vcol = config.COL_UP if q["change_pct"] >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"{q['change_pct']:+.1f}", (cols["var"], y), fonts.small(), vcol)
        ycol = config.COL_UP if q["change_1y"] >= 0 else config.COL_DOWN
        widgets.draw_text(surf, f"{q['change_1y']:+.0f}%", (cols["y1"], y), fonts.small(), ycol)
        widgets.draw_text(surf, f"{q['yield']*100:.1f}", (cols["yld"], y), fonts.small(), config.COL_CYAN)
        widgets.draw_text(surf, f"{q['expense']*100:.2f}", (cols["exp"], y), fonts.tiny(), config.COL_TEXT_DIM)
        pos = p.etfs.get(q["id"])
        held = pos["qty"] if pos else 0
        widgets.draw_text(surf, f"{held:.0f}", (cols["you"], y), fonts.small(),
                          config.COL_UP if held else config.COL_TEXT_DIM)
        if self._can_trade():
            br = pygame.Rect(cols["act"], y - 2, 42, 20)
            sr = pygame.Rect(cols["act"] + 48, y - 2, 42, 20)
            self.buy_rects[q["id"]] = br
            self.sell_rects[q["id"]] = sr
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, br, border_radius=3)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, sr, border_radius=3)
            widgets.draw_text(surf, f"+{LOT}", (br.x + 6, y), fonts.tiny(bold=True), config.COL_UP)
            widgets.draw_text(surf, f"-{LOT}", (sr.x + 7, y), fonts.tiny(bold=True), config.COL_DOWN)

    def _draw_chip_row(self, surf, x0, y0, x_max, chips, current, accent):
        rects = {}
        x, y = x0, y0
        for value, label in chips:
            w = fonts.tiny(bold=True).size(label)[0] + 14
            if x + w > x_max and x > x0:
                x = x0
                y += 24
            rect = pygame.Rect(x, y, w, 20)
            rects[value] = rect
            sel = (value == current)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, accent if sel else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, label, rect.center, fonts.tiny(bold=sel),
                              accent if sel else config.COL_TEXT_DIM, align="center")
            x += w + 6
        return rects, y + 24
