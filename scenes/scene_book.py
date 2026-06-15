"""
scene_book.py — Livre de positions (portefeuille réel).

Affiche les positions détenues (P&L latent par ligne), la valeur nette, la
répartition par secteur et le bêta. Le trading se fait au clavier depuis le
terminal (BUY / SELL / ALLOCATE / HEDGE / REBALANCE).
"""
import pygame
from core import config
from core import portfolio as pf
from core.scene_manager import Scene
from ui import fonts, widgets


class BookScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.analytics_btn = widgets.Button(
            (250, config.SCREEN_HEIGHT - 50, 230, 42), "ANALYSE DÉTAILLÉE (PA)", config.COL_CYAN)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if self.analytics_btn.handle(event):
            self.app.scenes.go("analytics", return_to="terminal")

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.analytics_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        m = self.market
        cur = config.CONTINENTS[p.continent]["currency"]
        widgets.draw_text(surf, "PORTEFEUILLE", (40, 22), fonts.title(bold=True), config.COL_AMBER)

        pos_val = pf.positions_value(p, m)
        nw = p.cash + pos_val
        upnl = pf.unrealized_pnl(p, m)
        beta = pf.portfolio_beta(p, m)
        # bandeau de synthèse
        widgets.draw_text(surf, f"Valeur nette {widgets.format_money(nw, cur)}",
                          (config.SCREEN_WIDTH - 40, 26), fonts.head(bold=True),
                          config.COL_WHITE, align="right")
        sub = (f"Cash {widgets.format_money(p.cash, cur)} · Titres {widgets.format_money(pos_val, cur)} · "
               f"bêta {beta:.2f} · P&L réalisé {widgets.format_money(p.realized_pnl, cur)}")
        widgets.draw_text(surf, sub, (config.SCREEN_WIDTH - 40, 70), fonts.small(),
                          config.COL_TEXT_DIM, align="right")
        # ligne de marge / levier
        st = pf.margin_status(p, m)
        lev = "∞" if st["leverage"] == float("inf") else f"{st['leverage']:.2f}x"
        lev_col = config.COL_DOWN if st["margin_call"] else (
            config.COL_WARN if st["leverage"] != float("inf") and st["leverage"] > st["max_leverage"] * 0.8
            else config.COL_TEXT_DIM)
        marg = (f"Levier {lev} / max {st['max_leverage']:.1f}x · "
                f"exposition {widgets.format_money(st['gross'], cur)} · "
                f"pouvoir d'achat {widgets.format_money(st['buying_power'], cur)}"
                + ("  ⚠ APPEL DE MARGE" if st["margin_call"] else ""))
        widgets.draw_text(surf, marg, (config.SCREEN_WIDTH - 40, 88), fonts.tiny(),
                          lev_col, align="right")

        # table des positions
        ph = config.footer_y() - 8 - 100
        table = pygame.Rect(40, 100, 900, ph)
        inner = widgets.draw_panel(surf, table, "Positions", config.COL_CYAN)
        holds = pf.holdings(p, m)
        if not holds:
            widgets.draw_text_wrapped(
                surf, "Aucune position. Depuis le terminal : BUY <ticker> <qté> "
                "(ex: BUY MVC 100). SELL pour vendre, ALLOCATE pour viser un %.",
                (inner.x, inner.y), fonts.body(), config.COL_TEXT_DIM, inner.w)
        else:
            # en-têtes
            cols = [("TICKER", inner.x), ("QTÉ", inner.x + 130), ("PRU", inner.x + 220),
                    ("COURS", inner.x + 320), ("VALEUR", inner.x + 440), ("P&L", inner.x + 600)]
            for label, x in cols:
                widgets.draw_text(surf, label, (x, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
            y = inner.y + 22
            for h in holds:
                pcol = config.COL_UP if h["pnl"] >= 0 else config.COL_DOWN
                tk_label = h["ticker"] + (" (S)" if h["short"] else "")
                tk_col = config.COL_DOWN if h["short"] else config.COL_AMBER
                widgets.draw_text(surf, tk_label, (cols[0][1], y), fonts.small(bold=True), tk_col)
                widgets.draw_text(surf, f"{h['shares']:.0f}", (cols[1][1], y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, f"{h['avg']:.2f}", (cols[2][1], y), fonts.small(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, f"{h['price']:.2f}", (cols[3][1], y), fonts.small(), config.COL_WHITE)
                widgets.draw_text(surf, widgets.format_money(h["value"], cur), (cols[4][1], y),
                                  fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, f"{'+' if h['pnl']>=0 else ''}{widgets.format_money(h['pnl'], cur)} "
                                        f"({h['pnl_pct']:+.1f}%)", (cols[5][1], y), fonts.small(bold=True), pcol)
                y += 26
                if y > inner.bottom - 20:
                    break

        # répartition par secteur
        alloc = pygame.Rect(960, 100, config.SCREEN_WIDTH - 1000, ph)
        ainner = widgets.draw_panel(surf, alloc, "Répartition par secteur", config.COL_AMBER)
        by_sector = pf.allocation_by(p, m, "sector")
        if not by_sector:
            widgets.draw_text(surf, "—", (ainner.x, ainner.y), fonts.body(), config.COL_TEXT_DIM)
        else:
            total = sum(by_sector.values()) or 1.0
            y = ainner.y
            for sec, val in sorted(by_sector.items(), key=lambda kv: -kv[1]):
                ratio = val / total
                widgets.draw_text(surf, sec, (ainner.x, y), fonts.small(), config.COL_TEXT)
                widgets.draw_text(surf, f"{ratio*100:.0f}%", (ainner.right, y),
                                  fonts.small(bold=True), config.COL_WHITE, align="right")
                widgets.draw_progress(surf, (ainner.x, y + 18, ainner.w, 6), ratio, config.COL_CYAN)
                y += 36
            # concentration : alerte si une ligne > 40%
            top = max(by_sector.values()) / total
            if top > 0.4:
                widgets.draw_text(surf, "⚠ Forte concentration sectorielle.",
                                  (ainner.x, ainner.bottom - 18), fonts.tiny(), config.COL_WARN)

        self.back_btn.draw(surf)
        self.analytics_btn.draw(surf)
