"""
scene_crypto.py — Crypto-actifs & stablecoin : spot, volatilité, trading.

Classe d'actifs très volatile. Le stablecoin (USDX) vise 1.0 mais peut DÉCROCHER
(depeg). Achat/vente au spot. Ouvert via CRYPTO.
"""
import pygame

from core import config, unlocks
from core import crypto as K
from core.scene_manager import Scene
from ui import fonts, keynav, widgets
from ui.popups import PopupMixin

LOT = 1


class CryptoScene(Scene, PopupMixin):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.search_box = widgets.SearchBox((40, 100, 280, 24), "Rechercher un actif…")
        self.buy_rects, self.sell_rects = {}, {}
        self.name_rects = {}
        self.row_cursor = 0
        self._row_list = []
        self.init_popups()
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button((config.back_button_rect(160)[0] + 170,
                                        config.back_button_rect(160)[1], 150, 42),
                                       "📘 TUTO", config.COL_CYAN)

    def _can_trade(self):
        return unlocks.unlocked(self.app.gs.player, "trade")

    def handle_event(self, event):
        if self.popups_handle_event(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search_box.text:
                    self.search_box.text = ""
                    return
                self.app.scenes.back(self.return_to)
                return
            elif event.key == pygame.K_BACKSPACE:
                self.search_box.handle_typing(event)
                return
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.row_cursor, activate = widgets.list_key_nav(
                    event, self.row_cursor, len(self._row_list))
                if activate and self._row_list:
                    self.open_crypto(self._row_list[self.row_cursor])
                return
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search_box.handle_typing(event)
                return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="crypto", return_to="crypto")
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.search_box.handle_clear_click(event):
                return
            for cid, rect in self.name_rects.items():
                if rect.collidepoint(event.pos):
                    self.open_crypto(cid)
                    return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            for cid, rect in self.name_rects.items():
                if rect.collidepoint(event.pos):
                    self.open_crypto(cid)
                    return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self._can_trade():
            p, m = self.app.gs.player, self.app.market
            for cid, rect in self.buy_rects.items():
                if rect.collidepoint(event.pos):
                    r = K.buy(p, m, cid, LOT)
                    self.msg = f"Acheté {LOT} {cid}" if r["ok"] else f"Refusé ({r['reason']})."
                    if r["ok"] and not p.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)
            for cid, rect in self.sell_rects.items():
                if rect.collidepoint(event.pos):
                    r = K.sell(p, m, cid, LOT)
                    self.msg = (f"Vendu {cid} (P&L {r['realized']:+.0f})" if r["ok"]
                                else "Aucune position.")
                    if r["ok"] and not p.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)

    def update(self, dt):
        self.search_box.update(dt)
        self.back_btn.update(pygame.mouse.get_pos(), dt)
        self.tuto_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        m, p = self.app.market, self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        widgets.draw_text(surf, "CRYPTO-ACTIFS", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        depegs = K.active_depegs(m)
        if depegs:
            names = ", ".join(K.name(d) for d in depegs)
            warn = (f"⚠ DEPEG en cours sur {names} — risque de CONTAGION sur les "
                    "crypto-actifs corrélés. " + self.msg)
            wcol = config.COL_DOWN
        else:
            warn = ("Classe très volatile, sans flux. Le stablecoin vise 1.0 mais "
                    "peut DÉCROCHER (depeg). " + self.msg)
            wcol = config.COL_TEXT_DIM
        widgets.draw_text(surf, warn, (42, 74), fonts.small(), wcol)

        # ---- recherche ----
        self.search_box.draw(surf)
        top = self.search_box.rect.bottom + 8
        ph = config.footer_y() - 8 - top
        panel = pygame.Rect(40, top, config.SCREEN_WIDTH - 80, ph)
        inner = widgets.draw_panel(surf, panel, "Marché crypto", config.COL_CYAN)
        cols = [("ACTIF", inner.x), ("SPOT", inner.x + 300), ("VOL/AN", inner.x + 470),
                ("TYPE", inner.x + 580), ("VOUS", inner.x + 760)]
        for label, x in cols:
            widgets.draw_text(surf, label, (x, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        self.buy_rects, self.sell_rects = {}, {}
        self.name_rects = {}
        y = inner.y + 26
        q_filter = self.search_box.query
        quotes = [q for q in K.all_quotes(m)
                  if not q_filter or q_filter in q["name"].lower() or q_filter in q["id"].lower()]
        mp = pygame.mouse.get_pos()
        self._row_list = [q["id"] for q in quotes]
        self.row_cursor = min(self.row_cursor, len(quotes) - 1) if quotes else 0
        for i, q in enumerate(quotes):
            pos = p.crypto.get(q["id"])
            held = pos["qty"] if pos else 0
            row_rect = pygame.Rect(cols[0][1] - 4, y - 2, inner.w - 8, 28)
            if row_rect.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
            keynav.draw_focus_ring(surf, row_rect, i == self.row_cursor)
            name_rect = pygame.Rect(cols[0][1], y - 2, 280, 22)
            self.name_rects[q["id"]] = name_rect
            widgets.draw_text(surf, f"{q['name']} ({q['id']})", (cols[0][1], y),
                              fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"{q['spot']:,.2f}".replace(",", " "), (cols[1][1], y),
                              fonts.small(bold=True), config.COL_WHITE)
            widgets.draw_text(surf, f"{q['vol']*100:.0f}%", (cols[2][1], y), fonts.small(),
                              config.COL_DOWN if q["vol"] > 1.0 else config.COL_WARN)
            depeg = q["stable"] and q["spot"] < 0.95
            risk = K.contagion_risk(m, q["id"])
            if q.get("cbdc"):
                label = f"CBDC +{q['yield']*100:.1f}%/an"
                lcol = config.COL_UP
            elif q["stable"]:
                label = "Stablecoin" + (" ⚠ DEPEG" if depeg else "")
                lcol = config.COL_DOWN if depeg else config.COL_CYAN
            elif risk > 0.02:
                label = f"Crypto ⚡ contagion {risk*100:.0f}%"
                lcol = config.COL_DOWN if risk > 0.15 else config.COL_WARN
            else:
                label, lcol = "Crypto", config.COL_TEXT_DIM
            widgets.draw_text(surf, label, (cols[3][1], y), fonts.small(bold=True), lcol)
            widgets.draw_text(surf, f"{held:g}", (cols[4][1], y), fonts.small(),
                              config.COL_UP if held else config.COL_TEXT_DIM)
            if self._can_trade():
                br = pygame.Rect(cols[4][1] + 56, y - 2, 42, 20)
                sr = pygame.Rect(cols[4][1] + 104, y - 2, 42, 20)
                self.buy_rects[q["id"]] = br
                self.sell_rects[q["id"]] = sr
                for rect, sym, c2 in ((br, f"+{LOT}", config.COL_UP), (sr, f"-{LOT}", config.COL_DOWN)):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect, border_radius=3)
                    widgets.draw_text(surf, sym, (rect.x + 6, y), fonts.tiny(bold=True), c2)
            y += 32
        hv = K.holdings_value(p, m)
        widgets.draw_text(surf, f"Valeur crypto détenue : {widgets.format_money(hv, cur)}"
                          + ("" if self._can_trade() else "   ⊘ trading débloqué au grade Associate"),
                          (inner.x, inner.bottom - 22), fonts.small(bold=True),
                          config.COL_UP if hv else config.COL_TEXT_DIM)
        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14),
                              [("↑↓", "actifs"), ("ENTRÉE", "ouvrir")])
        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
        self.popups_draw(surf)
