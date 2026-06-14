"""
scene_bonds.py — Marché obligataire : cotations, YTM, duration, et trading.

Liste les obligations souveraines et corporate avec leur prix (sensible aux
taux), leur rendement (YTM), leur rating et leur duration modifiée. Achat/vente
par paquets. Les prix bougent quand le taux directeur (ECO) évolue : duration et
convexité deviennent jouables. Ouvert via BONDS.
"""
import pygame
from core import config
from core import bonds as B
from core import portfolio as pf
from core import unlocks
from core.scene_manager import Scene
from ui import fonts, widgets

LOT = 10   # taille d'un paquet d'achat/vente


class BondsScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.buy_rects = {}
        self.sell_rects = {}
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def _can_trade(self):
        return unlocks.unlocked(self.app.gs.player, "trade")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p, m = self.app.gs.player, self.app.market
            if not self._can_trade():
                return
            for bid, rect in self.buy_rects.items():
                if rect.collidepoint(event.pos):
                    r = B.buy_bond(p, m, bid, LOT)
                    self.msg = (f"Acheté {LOT} × {bid} @ {r['price']:.2f}"
                                if r["ok"] else
                                f"Achat refusé ({r['reason']}).")
                    if r["ok"] and not p.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)
            for bid, rect in self.sell_rects.items():
                if rect.collidepoint(event.pos):
                    r = B.sell_bond(p, m, bid, LOT)
                    self.msg = (f"Vendu {min(LOT, r['qty']):.0f} × {bid} "
                                f"(P&L {r['realized']:+.0f})"
                                if r["ok"] else "Aucune position.")
                    if r["ok"] and not p.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        m = self.app.market
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        widgets.draw_text(surf, "MARCHÉ OBLIGATAIRE", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        lvl = B.base_yield_level(m) * 100
        widgets.draw_text(surf, f"Niveau de courbe ≈ {lvl:.2f}% (taux directeur) · "
                                "les prix montent quand les taux baissent (duration). "
                                + (self.msg if self.msg else ""),
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        ph = config.footer_y() - 8 - 100
        panel = pygame.Rect(40, 100, config.SCREEN_WIDTH - 80, ph)
        inner = widgets.draw_panel(surf, panel, "Obligations", config.COL_CYAN)
        cols = [("OBLIGATION", inner.x), ("RATING", inner.x + 300),
                ("COUPON", inner.x + 380), ("MAT.", inner.x + 460),
                ("YTM", inner.x + 540), ("PRIX", inner.x + 620),
                ("DUR.", inner.x + 720), ("VOUS", inner.x + 800)]
        for label, x in cols:
            widgets.draw_text(surf, label, (x, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        self.buy_rects, self.sell_rects = {}, {}
        y = inner.y + 24
        for q in B.all_quotes(m):
            pos = p.bonds.get(q["id"])
            held = pos["qty"] if pos else 0
            widgets.draw_text(surf, q["name"], (cols[0][1], y), fonts.small(bold=True), config.COL_TEXT)
            rc = (config.COL_UP if q["rating"] in ("AAA", "AA", "A") else
                  config.COL_WARN if q["rating"] == "BBB" else config.COL_DOWN)
            widgets.draw_text(surf, q["rating"], (cols[1][1], y), fonts.small(bold=True), rc)
            widgets.draw_text(surf, f"{q['coupon']*100:.1f}%", (cols[2][1], y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, f"{q['years']}a", (cols[3][1], y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, f"{q['ytm']*100:.2f}%", (cols[4][1], y), fonts.small(), config.COL_CYAN)
            widgets.draw_text(surf, f"{q['price']:.2f}", (cols[5][1], y), fonts.small(bold=True), config.COL_WHITE)
            widgets.draw_text(surf, f"{q['mod_duration']:.1f}", (cols[6][1], y), fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"{held:.0f}", (cols[7][1], y), fonts.small(),
                              config.COL_UP if held else config.COL_TEXT_DIM)
            if self._can_trade():
                br = pygame.Rect(cols[7][1] + 60, y - 2, 46, 20)
                sr = pygame.Rect(cols[7][1] + 112, y - 2, 46, 20)
                self.buy_rects[q["id"]] = br
                self.sell_rects[q["id"]] = sr
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, br, border_radius=3)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, sr, border_radius=3)
                widgets.draw_text(surf, f"+{LOT}", (br.x + 8, y), fonts.tiny(bold=True), config.COL_UP)
                widgets.draw_text(surf, f"-{LOT}", (sr.x + 8, y), fonts.tiny(bold=True), config.COL_DOWN)
            y += 30

        # synthèse position obligataire
        hv = B.holdings_value(p, m)
        widgets.draw_text(surf, f"Valeur obligataire détenue : {widgets.format_money(hv, cur)}"
                          + ("" if self._can_trade() else "   🔒 trading débloqué au grade Associate"),
                          (inner.x, inner.bottom - 22), fonts.small(bold=True),
                          config.COL_UP if hv else config.COL_TEXT_DIM)
        self.back_btn.draw(surf)
