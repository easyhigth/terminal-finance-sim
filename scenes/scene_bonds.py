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
from ui import fonts, widgets
from ui.popups import PopupMixin

LOT = 10   # taille d'un paquet d'achat/vente
ROW_H = 28


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
        self.search_box = widgets.SearchBox((40, 100, 280, 24),
                                             "Tapez pour rechercher (nom, émetteur)…")
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.gov_btn = widgets.Button((220, config.SCREEN_HEIGHT - 50, 160, 42),
                                      "PAYS / GOV", config.COL_CYAN)

    def _can_trade(self):
        return unlocks.unlocked(self.app.gs.player, "trade")

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
                self.app.scenes.go(self.return_to)
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
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search_box.handle_typing(event)
                self.scroll = 0
                return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
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
        top = self.search_box.rect.bottom + 8
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
        sov = sorted([q for q in quotes if q["kind"] == "Souverain"], key=lambda q: (q["region"], q["years"]))
        corp = sorted([q for q in quotes if q["kind"] == "Corporate"], key=lambda q: (q["region"], q["name"]))
        mp = pygame.mouse.get_pos()
        y = list_top - self.scroll
        y = self._draw_group(surf, "SOUVERAINS", sov, y, p, list_area, mp)
        y = self._draw_group(surf, "CORPORATE", corp, y, p, list_area, mp)
        surf.set_clip(prev_clip)

        content_h = (y + self.scroll) - list_top
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        widgets.draw_scrollbar(surf, panel, list_area, self.scroll, self._max_scroll, content_h)

        # synthèse position obligataire
        hv = B.holdings_value(p, m)
        widgets.draw_text(surf, f"Valeur obligataire détenue : {widgets.format_money(hv, cur)}"
                          + ("" if self._can_trade() else "   ⊘ trading débloqué au grade Associate"),
                          (inner.x, inner.bottom - 20), fonts.small(bold=True),
                          config.COL_UP if hv else config.COL_TEXT_DIM)
        self.back_btn.draw(surf)
        self.gov_btn.draw(surf)
        self.popups_draw(surf)

    def _draw_group(self, surf, title, quotes, y, p, list_area, mp):
        cols = self.cols
        widgets.draw_text(surf, f"— {title} ({len(quotes)})", (cols["name"], y),
                          fonts.tiny(bold=True), config.COL_AMBER)
        y += 20
        for q in quotes:
            visible = (list_area.top - ROW_H) < y < list_area.bottom
            if visible:
                row_rect = pygame.Rect(cols["name"] - 4, y - 2, list_area.w - 8, ROW_H)
                if row_rect.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
                name_w = min(260, fonts.small(bold=True).size(q["name"])[0])
                self.name_rects[q["id"]] = pygame.Rect(cols["name"] - 2, y - 2, name_w + 4, ROW_H - 4)
                widgets.draw_text(surf, widgets.fit_text(q["name"], fonts.small(bold=True), 260),
                                  (cols["name"], y), fonts.small(bold=True), config.COL_TEXT)
                tcol = config.COL_CYAN if q["kind"] == "Souverain" else config.COL_PRESTIGE
                widgets.draw_text(surf, "Souv." if q["kind"] == "Souverain" else "Corp.",
                                  (cols["type"], y), fonts.tiny(bold=True), tcol)
                issuer = widgets.fit_text(q["issuer"], fonts.tiny(), 200)
                widgets.draw_text(surf, issuer, (cols["issuer"], y + 1), fonts.tiny(), config.COL_TEXT_DIM)
                rc = (config.COL_UP if q["rating"] in ("AAA", "AA", "A") else
                      config.COL_WARN if q["rating"] == "BBB" else config.COL_DOWN)
                widgets.draw_text(surf, q["rating"], (cols["rating"], y), fonts.small(bold=True), rc)
                widgets.draw_text(surf, f"{q['coupon']*100:.1f}", (cols["coupon"], y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, f"{q['years']}a", (cols["mat"], y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, f"{q['ytm']*100:.2f}%", (cols["ytm"], y), fonts.small(), config.COL_CYAN)
                widgets.draw_text(surf, f"{q['price']:.1f}", (cols["price"], y), fonts.small(bold=True), config.COL_WHITE)
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
