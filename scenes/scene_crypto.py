"""
scene_crypto.py — Crypto-actifs & stablecoin : spot, volatilité, trading.

Classe d'actifs très volatile. Le stablecoin (USDX) vise 1.0 mais peut DÉCROCHER
(depeg). Achat/vente au spot. Ouvert via CRYPTO.
"""
import pygame
from core import config
from core import crypto as K
from core import unlocks
from core.scene_manager import Scene
from ui import fonts, widgets

LOT = 1


class CryptoScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.buy_rects, self.sell_rects = {}, {}
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def _can_trade(self):
        return unlocks.unlocked(self.app.gs.player, "trade")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
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
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        m, p = self.app.market, self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        widgets.draw_text(surf, "CRYPTO-ACTIFS", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Classe très volatile, sans flux. Le stablecoin vise 1.0 mais "
                                "peut DÉCROCHER (depeg). " + self.msg,
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)
        ph = config.footer_y() - 8 - 100
        panel = pygame.Rect(40, 100, config.SCREEN_WIDTH - 80, ph)
        inner = widgets.draw_panel(surf, panel, "Marché crypto", config.COL_CYAN)
        cols = [("ACTIF", inner.x), ("SPOT", inner.x + 300), ("VOL/AN", inner.x + 470),
                ("TYPE", inner.x + 580), ("VOUS", inner.x + 760)]
        for label, x in cols:
            widgets.draw_text(surf, label, (x, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        self.buy_rects, self.sell_rects = {}, {}
        y = inner.y + 26
        for q in K.all_quotes(m):
            pos = p.crypto.get(q["id"])
            held = pos["qty"] if pos else 0
            widgets.draw_text(surf, f"{q['name']} ({q['id']})", (cols[0][1], y),
                              fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"{q['spot']:,.2f}".replace(",", " "), (cols[1][1], y),
                              fonts.small(bold=True), config.COL_WHITE)
            widgets.draw_text(surf, f"{q['vol']*100:.0f}%", (cols[2][1], y), fonts.small(),
                              config.COL_DOWN if q["vol"] > 1.0 else config.COL_WARN)
            depeg = q["stable"] and q["spot"] < 0.95
            label = ("Stablecoin" + (" ⚠ DEPEG" if depeg else "")) if q["stable"] else "Crypto"
            widgets.draw_text(surf, label, (cols[3][1], y), fonts.small(bold=True),
                              config.COL_DOWN if depeg else (config.COL_CYAN if q["stable"] else config.COL_TEXT_DIM))
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
                          + ("" if self._can_trade() else "   🔒 trading débloqué au grade Associate"),
                          (inner.x, inner.bottom - 22), fonts.small(bold=True),
                          config.COL_UP if hv else config.COL_TEXT_DIM)
        self.back_btn.draw(surf)
