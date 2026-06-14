"""
scene_credit.py — Desk crédit / titrisation : tranches & waterfall.

Le joueur investit dans une tranche (equity / mezzanine / senior) d'un pool de
prêts. À l'échéance, le taux de défaut réalisé détermine la perte du pool,
absorbée de bas en haut (subordination). L'equity paie gros mais saute en
premier ; le senior est protégé. Ouvert via CREDIT.
"""
import pygame
from core import config
from core import securitisation as SEC
from core import unlocks
from core.scene_manager import Scene
from ui import fonts, widgets

LOT = 50_000.0


class CreditScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.invest_rects = {}
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
            for tid, rect in self.invest_rects.items():
                if rect.collidepoint(event.pos):
                    r = SEC.invest(self.app.gs.player, self.app.market, tid, LOT)
                    self.msg = ("Investi dans " + tid if r["ok"]
                                else f"Refusé ({r['reason']}).")
                    if r["ok"] and not self.app.gs.player.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        m, p = self.app.market, self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        widgets.draw_text(surf, "DESK CRÉDIT — TITRISATION", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        el = SEC.expected_pool_loss() * 100
        widgets.draw_text(surf, f"Pool de prêts · perte attendue ≈ {el:.1f}% · cascade : "
                                "l'equity encaisse les premières pertes, le senior est protégé. "
                                + self.msg,
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)
        ph = config.footer_y() - 8 - 100
        panel = pygame.Rect(40, 100, config.SCREEN_WIDTH - 80, ph)
        inner = widgets.draw_panel(surf, panel, "Tranches", config.COL_CYAN)
        cols = [("TRANCHE", inner.x), ("ATTACHE-DÉTACHE", inner.x + 240),
                ("ÉPAISSEUR", inner.x + 440), ("COUPON", inner.x + 560),
                ("RATING", inner.x + 660), ("PERTE ATT.", inner.x + 760)]
        for label, x in cols:
            widgets.draw_text(surf, label, (x, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        self.invest_rects = {}
        y = inner.y + 26
        for q in SEC.all_quotes():
            widgets.draw_text(surf, q["name"], (cols[0][1], y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"{q['attach']*100:.0f}% – {q['detach']*100:.0f}%",
                              (cols[1][1], y), fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, f"{q['thickness']*100:.0f}%", (cols[2][1], y), fonts.small(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"{q['coupon']*100:.1f}%", (cols[3][1], y), fonts.small(bold=True), config.COL_UP)
            rc = config.COL_UP if q["rating"] == "AAA" else config.COL_WARN if q["rating"] == "BB" else config.COL_DOWN
            widgets.draw_text(surf, q["rating"], (cols[4][1], y), fonts.small(bold=True), rc)
            lc = config.COL_DOWN if q["exp_loss"] > 0.1 else config.COL_TEXT_DIM
            widgets.draw_text(surf, f"{q['exp_loss']*100:.0f}%", (cols[5][1], y), fonts.small(), lc)
            if self._can_trade():
                rect = pygame.Rect(cols[5][1] + 90, y - 3, 120, 24)
                self.invest_rects[q["id"]] = rect
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect, border_radius=4)
                pygame.draw.rect(surf, config.COL_UP, rect, 1, border_radius=4)
                widgets.draw_text(surf, f"INVESTIR {LOT/1000:.0f}k", (rect.x + 8, y),
                                  fonts.tiny(bold=True), config.COL_UP)
            y += 36

        hv = SEC.holdings_value(p, m)
        held = SEC.holdings(p, m)
        sub = f"Tranches détenues : {widgets.format_money(hv, cur)}"
        if held:
            sub += "  ·  " + ", ".join(f"{h['name']} ({h['years_left']:.1f}a)" for h in held)
        if not self._can_trade():
            sub = "🔒 trading débloqué au grade Associate."
        widgets.draw_text(surf, sub, (inner.x, inner.bottom - 22), fonts.small(bold=True),
                          config.COL_UP if hv else config.COL_TEXT_DIM)
        self.back_btn.draw(surf)
