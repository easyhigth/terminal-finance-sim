"""
scene_commodities.py — Matières premières : spot, courbe de futures, roll yield.

Affiche pour chaque commodity le spot, le contrat de premier mois, la structure
de courbe (contango/backwardation) et le roll yield. Achat/vente de contrats.
Le roulement (roll) coûte en contango et rapporte en backwardation, prélevé à
chaque tour. Ouvert via CMDTY.
"""
import pygame
from core import config
from core import commodities as C
from core import unlocks
from core.scene_manager import Scene
from ui import fonts, widgets

LOT = 5


class CommoditiesScene(Scene):
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
                    r = C.buy(p, m, cid, LOT)
                    self.msg = (f"Acheté {LOT} {cid}" if r["ok"]
                                else f"Achat refusé ({r['reason']}).")
                    if r["ok"] and not p.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)
            for cid, rect in self.sell_rects.items():
                if rect.collidepoint(event.pos):
                    r = C.sell(p, m, cid, LOT)
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
        widgets.draw_text(surf, "MATIÈRES PREMIÈRES — FUTURES", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Contango = futures > spot (roll négatif) · "
                                "backwardation = futures < spot (roll positif). " + self.msg,
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)
        ph = config.footer_y() - 8 - 100
        panel = pygame.Rect(40, 100, config.SCREEN_WIDTH - 80, ph)
        inner = widgets.draw_panel(surf, panel, "Contrats", config.COL_CYAN)
        cols = [("COMMODITY", inner.x), ("SPOT", inner.x + 260), ("FUTURE 1M", inner.x + 360),
                ("STRUCTURE", inner.x + 480), ("ROLL/AN", inner.x + 640),
                ("VOL", inner.x + 730), ("VOUS", inner.x + 800)]
        for label, x in cols:
            widgets.draw_text(surf, label, (x, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        self.buy_rects, self.sell_rects = {}, {}
        y = inner.y + 26
        for q in C.all_quotes(m):
            pos = p.commodities.get(q["id"])
            held = pos["qty"] if pos else 0
            widgets.draw_text(surf, q["name"], (cols[0][1], y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"{q['spot']:,.2f}".replace(",", " "), (cols[1][1], y), fonts.small(), config.COL_WHITE)
            widgets.draw_text(surf, f"{q['front']:,.2f}".replace(",", " "), (cols[2][1], y), fonts.small(bold=True), config.COL_WHITE)
            scol = config.COL_DOWN if q["structure"] == "Contango" else config.COL_UP if q["structure"] == "Backwardation" else config.COL_TEXT_DIM
            widgets.draw_text(surf, q["structure"], (cols[3][1], y), fonts.small(bold=True), scol)
            rcol = config.COL_UP if q["roll_yield"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{q['roll_yield']*100:+.1f}%", (cols[4][1], y), fonts.small(), rcol)
            widgets.draw_text(surf, f"{q['vol']*100:.0f}%", (cols[5][1], y), fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"{held:.0f}", (cols[6][1], y), fonts.small(),
                              config.COL_UP if held else config.COL_TEXT_DIM)
            if self._can_trade():
                br = pygame.Rect(cols[6][1] + 56, y - 2, 42, 20)
                sr = pygame.Rect(cols[6][1] + 104, y - 2, 42, 20)
                self.buy_rects[q["id"]] = br
                self.sell_rects[q["id"]] = sr
                for rect, sym, c2 in ((br, f"+{LOT}", config.COL_UP), (sr, f"-{LOT}", config.COL_DOWN)):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect, border_radius=3)
                    widgets.draw_text(surf, sym, (rect.x + 6, y), fonts.tiny(bold=True), c2)
            y += 32
        hv = C.holdings_value(p, m)
        widgets.draw_text(surf, f"Valeur commodities détenue : {widgets.format_money(hv, cur)}"
                          + ("" if self._can_trade() else "   ⊘ trading débloqué au grade Associate"),
                          (inner.x, inner.bottom - 22), fonts.small(bold=True),
                          config.COL_UP if hv else config.COL_TEXT_DIM)
        self.back_btn.draw(surf)
