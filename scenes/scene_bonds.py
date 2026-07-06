"""
scene_bonds.py — Marché obligataire : cotations, YTM, duration, et trading.

Liste les obligations SOUVERAINES (émises par les gouvernements, cf. GOV) et
CORPORATE (émises par de vraies sociétés du roster) avec leur prix (sensible aux
taux), leur rendement (YTM), leur rating et leur duration modifiée. Achat/vente
par paquets. Les prix bougent quand le taux directeur (ECO) évolue — duration et
convexité deviennent jouables — et quand un événement politique régional élargit
les spreads de la zone. Liste DÉFILABLE. Ouvert via BONDS.
"""
import pygame

from core import bonds as B
from core import config, unlocks
from core.scene_manager import Scene
from ui import fonts, keynav, widgets
from ui.popups import PopupMixin

LOT = 10   # taille d'un paquet d'achat/vente
ROW_H = 28
SORT_FIELDS = [("name", "NOM"), ("price", "COURS"), ("value", "VALEUR"),
               ("ytm", "RENDEMENT"), ("mod_duration", "DURATION")]


class BondsScene(Scene, PopupMixin):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.init_popups()
        self.msg = ""
        self.buy_rects = {}
        self.sell_rects = {}
        self.name_rects = {}
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self.row_cursor = 0
        self._row_list = []
        self._row_offsets = {}
        self.search_box = widgets.SearchBox((40, 100, 280, 24),
                                             "Tapez pour rechercher (nom, émetteur)…")
        self.sort_key = "ytm"
        self.sort_dir = -1
        self._sort_rects = {}
        self.kind_filter = kwargs.get("kind_filter")
        self._kind_rects = {}
        self._flash = widgets.TickFlash()
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.gov_btn = widgets.Button((220, config.SCREEN_HEIGHT - 50, 160, 42),
                                      "PAYS / GOV", config.COL_CYAN)

    def _can_trade(self):
        return unlocks.unlocked(self.app.gs.player, "trade")

    def _scroll_to_cursor(self):
        if not self._list_rect or not self._row_list:
            return
        bid = self._row_list[self.row_cursor]
        row_top = self._row_offsets.get(bid)
        if row_top is None:
            return
        row_bottom = row_top + ROW_H
        if row_top < self.scroll:
            self.scroll = row_top
        elif row_bottom > self.scroll + self._list_rect.h:
            self.scroll = row_bottom - self._list_rect.h
        self.scroll = max(0, min(self._max_scroll, self.scroll))

    def handle_event(self, event):
        if self.popups_handle_event(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.popups_close_top():
                    return
                if self.search_box.text:
                    self.search_box.text = ""
                    return
                self.app.scenes.back(self.return_to)
                return
            elif event.key == pygame.K_BACKSPACE:
                self.search_box.handle_typing(event)
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
                    self.open_bond(self._row_list[self.row_cursor])
                return
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search_box.handle_typing(event)
                self.scroll = 0
                return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if self.gov_btn.handle(event):
            self.app.scenes.go("governments", return_to="bonds")
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            for bid, rect in self.name_rects.items():
                if rect.collidepoint(event.pos):
                    self.open_bond(bid)
                    return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.search_box.handle_clear_click(event):
                return
            for key, rect in self._sort_rects.items():
                if rect.collidepoint(event.pos):
                    if self.sort_key == key:
                        self.sort_dir *= -1
                    else:
                        self.sort_key = key
                        self.sort_dir = 1 if key == "name" else -1
                    return
            for val, rect in self._kind_rects.items():
                if rect.collidepoint(event.pos):
                    self.kind_filter = None if self.kind_filter == val else val
                    self.scroll = 0
                    return
            for bid, rect in self.name_rects.items():
                if rect.collidepoint(event.pos):
                    self.open_bond(bid)
                    return
            p, m = self.app.gs.player, self.app.market
            if not self._can_trade():
                return
            for bid, rect in self.buy_rects.items():
                if rect.collidepoint(event.pos):
                    r = B.buy_bond(p, m, bid, LOT)
                    self.msg = (f"Acheté {LOT} × {bid} @ {r['price']:.2f}"
                                if r["ok"] else f"Achat refusé ({r['reason']}).")
                    if r["ok"] and not p.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)
            for bid, rect in self.sell_rects.items():
                if rect.collidepoint(event.pos):
                    r = B.sell_bond(p, m, bid, LOT)
                    self.msg = (f"Vendu {min(LOT, r['qty']):.0f} × {bid} (P&L {r['realized']:+.0f})"
                                if r["ok"] else "Aucune position.")
                    if r["ok"] and not p.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)

    def update(self, dt):
        self.search_box.update(dt)
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.gov_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        m = self.app.market
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        widgets.draw_text(surf, "MARCHÉ OBLIGATAIRE", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        lvl = B.base_yield_level(m) * 100
        widgets.draw_text(surf, f"Niveau de courbe ≈ {lvl:.2f}% (taux directeur) · prix ↑ quand les "
                                "taux ↓ (duration) · souverains (GOV) & corporate. "
                                + (self.msg if self.msg else ""),
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        # ---- recherche ----
        self.search_box.draw(surf)
        sort_y = self.search_box.rect.bottom + 8
        self._sort_rects = {}
        widgets.draw_text(surf, "TRIER :", (40, sort_y + 3), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        sx = 40 + 56
        for key, lbl in SORT_FIELDS:
            active = (self.sort_key == key)
            arrow = (" ▲" if self.sort_dir > 0 else " ▼") if active else ""
            full = lbl + arrow
            w = fonts.tiny(bold=True).size(full)[0] + 16
            rect = pygame.Rect(sx, sort_y, w, 20)
            self._sort_rects[key] = rect
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, full, rect.center, fonts.tiny(bold=active),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            sx += w + 6

        self._kind_rects = {}
        kx = sx + 20
        widgets.draw_text(surf, "TYPE :", (kx, sort_y + 3), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        kx += 48
        for val, lbl in (("Souverain", "SOUVERAINS"), ("Corporate", "CORPORATE")):
            active = (self.kind_filter == val)
            w = fonts.tiny(bold=True).size(lbl)[0] + 16
            rect = pygame.Rect(kx, sort_y, w, 20)
            self._kind_rects[val] = rect
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN if active else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, lbl, rect.center, fonts.tiny(bold=active),
                              config.COL_CYAN if active else config.COL_TEXT_DIM, align="center")
            kx += w + 6

        top = sort_y + 28
        ph = config.footer_y() - 8 - top
        panel = pygame.Rect(40, top, config.SCREEN_WIDTH - 80, ph)
        inner = widgets.draw_panel(surf, panel, "Obligations", config.COL_CYAN)

        # colonnes (x relatifs à inner.x)
        self.cols = {"name": inner.x, "type": inner.x + 270, "issuer": inner.x + 350,
                     "rating": inner.x + 560, "coupon": inner.x + 620,
                     "mat": inner.x + 690, "ytm": inner.x + 745, "price": inner.x + 820,
                     "dur": inner.x + 900, "you": inner.x + 960, "act": inner.x + 1010}
        heads = [("OBLIGATION", "name"), ("TYPE", "type"), ("ÉMETTEUR / PAYS", "issuer"),
                 ("RATING", "rating"), ("CPN", "coupon"), ("MAT", "mat"), ("YTM", "ytm"),
                 ("PRIX", "price"), ("DUR", "dur"), ("VOUS", "you")]
        for label, key in heads:
            widgets.draw_text(surf, label, (self.cols[key], inner.y), fonts.tiny(bold=True),
                              config.COL_TEXT_DIM)
        if self._can_trade():
            widgets.draw_text(surf, "TRADE", (self.cols["act"], inner.y), fonts.tiny(bold=True),
                              config.COL_TEXT_DIM)

        # zone de liste défilable (sous l'en-tête)
        list_top = inner.y + 22
        list_area = pygame.Rect(inner.x - 6, list_top, inner.w + 12, inner.bottom - list_top - 26)
        self._list_rect = list_area
        self.buy_rects, self.sell_rects, self.name_rects = {}, {}, {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)

        quotes = B.all_quotes(m)
        q_filter = self.search_box.query
        if q_filter:
            quotes = [q for q in quotes
                      if q_filter in q["name"].lower() or q_filter in q["issuer"].lower()]
        def sort_value(q):
            if self.sort_key == "name":
                return q["name"].lower()
            if self.sort_key == "value":
                pos = p.bonds.get(q["id"])
                return (pos["qty"] if pos else 0) * q["price"]
            return q[self.sort_key]
        sov = sorted([q for q in quotes if q["kind"] == "Souverain"],
                     key=sort_value, reverse=(self.sort_dir < 0))
        corp = sorted([q for q in quotes if q["kind"] == "Corporate"],
                      key=sort_value, reverse=(self.sort_dir < 0))
        if self.kind_filter == "Souverain":
            corp = []
        elif self.kind_filter == "Corporate":
            sov = []
        mp = pygame.mouse.get_pos()
        self._tooltip = None
        self._row_list = [q["id"] for q in sov] + [q["id"] for q in corp]
        self._row_offsets = {}
        self.row_cursor = min(self.row_cursor, len(self._row_list) - 1) if self._row_list else 0
        cursor_id = self._row_list[self.row_cursor] if self._row_list else None
        y = list_top - self.scroll
        if sov:
            y = self._draw_group(surf, "SOUVERAINS", sov, y, p, m, list_area, mp, cursor_id)
        if corp:
            y = self._draw_group(surf, "CORPORATE", corp, y, p, m, list_area, mp, cursor_id)
        surf.set_clip(prev_clip)

        content_h = (y + self.scroll) - list_top
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, panel, list_area, self.scroll, self._max_scroll, content_h)

        # synthèse position obligataire
        hv = B.holdings_value(p, m)
        widgets.draw_text(surf, f"Valeur obligataire détenue : {widgets.format_money(hv, cur)}"
                          + ("" if self._can_trade() else "   ⊘ trading débloqué au grade Associate"),
                          (inner.x, inner.bottom - 20), fonts.small(bold=True),
                          config.COL_UP if hv else config.COL_TEXT_DIM)
        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14),
                              [("↑↓", "obligations"), ("ENTRÉE", "ouvrir")])
        self.back_btn.draw(surf)
        self.gov_btn.draw(surf)
        self.popups_draw(surf)
        if self._tooltip:
            widgets.draw_tooltip(surf, *self._tooltip)

    def _draw_group(self, surf, title, quotes, y, p, m, list_area, mp, cursor_id=None):
        cols = self.cols
        widgets.draw_text(surf, f"— {title} ({len(quotes)})", (cols["name"], y),
                          fonts.tiny(bold=True), config.COL_AMBER)
        y += 20
        for q in quotes:
            self._row_offsets[q["id"]] = y - list_area.top + self.scroll
            visible = (list_area.top - ROW_H) < y < list_area.bottom
            if visible:
                row_rect = pygame.Rect(cols["name"] - 4, y - 2, list_area.w - 8, ROW_H)
                if row_rect.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
                keynav.draw_focus_ring(surf, row_rect, q["id"] == cursor_id)
                name_w = min(260, fonts.small(bold=True).size(q["name"])[0])
                self.name_rects[q["id"]] = pygame.Rect(cols["name"] - 2, y - 2, name_w + 4, ROW_H - 4)
                widgets.draw_text(surf, widgets.fit_text(q["name"], fonts.small(bold=True), 260),
                                  (cols["name"], y), fonts.small(bold=True), config.COL_TEXT)
                tcol = config.COL_CYAN if q["kind"] == "Souverain" else config.COL_PRESTIGE
                widgets.draw_text(surf, "Souv." if q["kind"] == "Souverain" else "Corp.",
                                  (cols["type"], y), fonts.tiny(bold=True), tcol)
                issuer = widgets.fit_text(q["issuer"], fonts.tiny(), 200)
                if issuer != q["issuer"]:
                    issuer_rect = pygame.Rect(cols["issuer"], y + 1, 200, ROW_H - 4)
                    if issuer_rect.collidepoint(mp):
                        self._tooltip = (q["issuer"], mp)
                widgets.draw_text(surf, issuer, (cols["issuer"], y + 1), fonts.tiny(), config.COL_TEXT_DIM)
                rc = widgets.rating_color(q["rating"])
                widgets.draw_text(surf, q["rating"], (cols["rating"], y), fonts.small(bold=True), rc)
                widgets.draw_text(surf, f"{q['coupon']*100:.1f}", (cols["coupon"], y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, f"{q['years']}a", (cols["mat"], y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, f"{q['ytm']*100:.2f}%", (cols["ytm"], y), fonts.small(), config.COL_CYAN)
                price_col = self._flash.tick(q["id"], q["price"], config.COL_UP, config.COL_DOWN, config.COL_WHITE)
                widgets.draw_text(surf, f"{q['price']:.1f}", (cols["price"], y), fonts.small(bold=True), price_col)
                if self._can_trade():
                    price_rect = pygame.Rect(cols["price"] - 2, y - 2, 70, ROW_H - 4)
                    if price_rect.collidepoint(mp):
                        fb = B.fill_price(m, q["id"], LOT, "buy")
                        fs = B.fill_price(m, q["id"], LOT, "sell")
                        if fb and fs and q["price"]:
                            spread_pct = (fb - fs) / q["price"] * 100
                            self._tooltip = (f"Achat ~{fb:.2f} / Vente ~{fs:.2f} "
                                              f"(spread {spread_pct:.2f}% pour {LOT} unités)", mp)
                widgets.draw_text(surf, f"{q['mod_duration']:.1f}", (cols["dur"], y), fonts.small(), config.COL_TEXT_DIM)
                pos = p.bonds.get(q["id"])
                held = pos["qty"] if pos else 0
                widgets.draw_text(surf, f"{held:.0f}", (cols["you"], y), fonts.small(),
                                  config.COL_UP if held else config.COL_TEXT_DIM)
                if self._can_trade():
                    br = pygame.Rect(cols["act"], y - 2, 44, 20)
                    sr = pygame.Rect(cols["act"] + 50, y - 2, 44, 20)
                    self.buy_rects[q["id"]] = br
                    self.sell_rects[q["id"]] = sr
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, br, border_radius=3)
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, sr, border_radius=3)
                    widgets.draw_text(surf, f"+{LOT}", (br.x + 7, y), fonts.tiny(bold=True), config.COL_UP)
                    widgets.draw_text(surf, f"-{LOT}", (sr.x + 8, y), fonts.tiny(bold=True), config.COL_DOWN)
            y += ROW_H
        return y + 8
