"""
app_analytics.py — Application « Analyse du portefeuille » du bureau (NATIVE).

Migration de `scenes/scene_analytics.py` (rendu hébergé 1280×720 réduit par
smoothscale → flou, cf. apps/scene_host.py) vers une app dessinée à la
résolution de sa fenêtre — l'écran est lié en permanence via le bouton
« ANALYSE (PA) » de Trading et du Portefeuille. Toutes les positions sont
relatives au `rect` de la fenêtre : tuiles adaptatives, 3 colonnes qui
s'empilent en fenêtre étroite. Réutilise `core/analytics.py` tel quel ;
fiches d'analyse en popups flottants (`ui/popups.py::PopupMixin`,
repositionnés relativement à LA FENÊTRE). La scène plein écran reste
enregistrée (fallback/tests) ; l'ouverture EN FENÊTRE de "analytics" est
redirigée ici (cf. DesktopScene._open_scene_window).
"""
import pygame

from apps.base import DesktopApp
from core import analytics, config, i18n
from ui import fonts, widgets
from ui.popups import PopupMixin


def _L(fr, en):
    return en if i18n.get_lang() == "en" else fr


_LIQ_EN = {"Liquide": "Liquid", "Peu liquide": "Illiquid-ish",
           "Illiquide": "Illiquid"}


def _liq_label(v):
    return _LIQ_EN.get(v, v) if i18n.get_lang() == "en" else v


_CLASS_COL = {"Actions": config.COL_AMBER, "Obligations": config.COL_CYAN,
              "Matières": config.COL_WARN, "Crypto": config.COL_PRESTIGE,
              "ETF": config.COL_PRESTIGE, "Structurés": config.COL_PRESTIGE,
              "Crédit": config.COL_PRESTIGE}

_alert_color = widgets.alert_color


class AnalyticsApp(DesktopApp, PopupMixin):
    title = "Analyse du portefeuille"
    icon_kind = "graph"
    default_size = (1120, 680)
    min_size = (720, 480)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.init_popups()
        self._holding_rects = {}
        self._chart_rects = {}
        self._row_cls = {}
        self._frontier_rect = None
        self._corr_rect = None
        self.scroll_holdings = 0
        self.scroll_alloc = 0
        self._holdings_list_rect = None
        self._alloc_list_rect = None
        self._holdings_max_scroll = 0
        self._alloc_max_scroll = 0
        self._flash = widgets.TickFlash()
        self._book_btn = None
        self._stress_btn = None
        self._shop_btn = None
        self._last_rect = pygame.Rect(0, 0, 1, 1)

    def _popup_pos(self):
        """Cascade relative à CETTE fenêtre plutôt qu'à l'écran entier."""
        n = len(self.popups)
        offset = 24 * (n % 6)
        r = self._last_rect
        return (r.x + 30 + offset, r.y + 30 + offset)

    def _live_price(self, h):
        if h.get("cls") != "Actions":
            return None
        sim_clock = getattr(self.app, "sim_clock", None)
        day = getattr(self.app.gs.player, "day", None)
        if sim_clock is None or day is None:
            return None
        hist = self.market.history_of(h["label"], 1, sim_clock=sim_clock, day=day)
        return hist[-1] if hist else self.market.price_of(h["label"])

    def _open_holding(self, label):
        kind = self._row_cls.get(label)
        if kind == "Actions":
            self.open_company(label)
        elif kind == "ETF":
            self.open_etf(label)
        elif kind == "Obligations":
            self.open_bond(label)
        elif kind == "Matières":
            self.open_commodity(label)
        elif kind == "Crypto":
            self.open_crypto(label)
        elif kind == "Structurés":
            self.open_structured(label)
        elif kind == "Crédit":
            self.open_credit(label)

    # ------------------------------------------------------------- events
    def handle_event(self, event, rect):
        self._last_rect = rect
        if self.popups_handle_event(event):
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return self.popups_close_top()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._book_btn and self._book_btn.collidepoint(event.pos):
                if self.desktop is not None:
                    self.desktop._open_scene_window("book")
                return True
            if self._stress_btn and self._stress_btn.collidepoint(event.pos):
                if self.desktop is not None:
                    self.desktop._open_scene_window("stresstest")
                return True
            if self._shop_btn and self._shop_btn.collidepoint(event.pos):
                if self.desktop is not None:
                    self.desktop._open_scene_window("shop")
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            delta = -32 if event.button == 4 else 32
            if self._holdings_list_rect and self._holdings_list_rect.collidepoint(event.pos):
                self.scroll_holdings = max(0, min(self._holdings_max_scroll, self.scroll_holdings + delta))
                return True
            if self._alloc_list_rect and self._alloc_list_rect.collidepoint(event.pos):
                self.scroll_alloc = max(0, min(self._alloc_max_scroll, self.scroll_alloc + delta))
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            for tk, r in self._holding_rects.items():
                if r.collidepoint(event.pos):
                    self._open_holding(tk)
                    return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tk, r in self._holding_rects.items():
                if r.collidepoint(event.pos):
                    self._open_holding(tk)
                    return True
            for tk, r in self._chart_rects.items():
                if r.collidepoint(event.pos):
                    self.open_chart(tk, kind="change")
                    return True
            if self._frontier_rect and self._frontier_rect.collidepoint(event.pos):
                # frontière INTERACTIVE en fenêtre (apps/app_frontier.py) —
                # `self.app` d'une app native est le VRAI App, open_popup
                # ouvrirait un popup-page par-dessus tout l'écran.
                if self.desktop is not None:
                    self.desktop._open_scene_window("frontier")
                else:
                    self.app.pages.open_popup("frontier_lab", return_to="analytics")
                return True
            if self._corr_rect and self._corr_rect.collidepoint(event.pos):
                p, m = self.app.gs.player, self.market
                self.open_custom_chart(_L("CORRÉLATIONS — actions", "CORRELATIONS — equities"),
                                       lambda surf, r: self._draw_corr(surf, r, p, m, max_labels=None),
                                       accent=config.COL_DOWN, size=(560, 420))
                return True
            return False
        return False

    def update(self, dt):
        pass

    # -------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._last_rect = rect
        surf.fill(config.COL_BG, rect)
        p = self.app.gs.player
        m = self.market
        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")
        s = analytics.summary(p, m)
        pad = 14

        widgets.draw_text(surf, _L("ANALYSE DU PORTEFEUILLE", "PORTFOLIO ANALYSIS"), (rect.x + pad, rect.y + 8),
                          fonts.head(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, _L(f"{s['n_positions']} positions · "
                          f"{config.GRADES[p.grade_index]} · valeur nette en {cur}",
                          f"{s['n_positions']} positions · "
                          f"{config.GRADES[p.grade_index]} · net worth in {cur}"),
                          (rect.x + pad, rect.y + 34), fonts.tiny(), config.COL_TEXT_DIM)
        # liens (haut-droit) : Portefeuille / Stress test / Shop
        bx = rect.right - pad
        self._book_btn = self._link_btn(surf, bx - 88, rect.y + 8, 88, _L("PORTEF.", "PORTF."), config.COL_AMBER)
        self._stress_btn = self._link_btn(surf, self._book_btn.x - 82, rect.y + 8, 76, _L("STRESS", "STRESS"), config.COL_DOWN)
        self._shop_btn = self._link_btn(surf, self._stress_btn.x - 66, rect.y + 8, 60, _L("SHOP", "SHOP"), config.COL_CYAN)

        if s["n_positions"] == 0:
            widgets.draw_text_wrapped(surf, _L("Portefeuille vide. Achetez des actifs (Boutique, "
                              "Trading, terminal) pour voir l'analyse détaillée.",
                              "Empty portfolio. Buy assets (Shop, "
                              "Trading, terminal) to see the detailed analysis."),
                              (rect.x + pad, rect.y + 70), fonts.small(), config.COL_TEXT_DIM,
                              rect.w - 2 * pad)
            self.popups_draw(surf)
            return

        tile_y = rect.y + 54
        self._draw_tile_row(surf, rect, tile_y, self._tiles(s, cur), pad)
        self._draw_tile_row(surf, rect, tile_y + 50, self._risk_tiles(s), pad)
        top = tile_y + 104
        h = rect.bottom - pad - top
        if h < 80:
            self.popups_draw(surf)
            return
        stacked = rect.w < 980
        if stacked:
            # 2 colonnes : positions | répartition ; graphes de risque omis
            lw = int((rect.w - 3 * pad) * 0.6)
            mw = rect.w - 3 * pad - lw
            self._draw_holdings(surf, pygame.Rect(rect.x + pad, top, lw, h), s, cur)
            self._draw_allocations(surf, pygame.Rect(rect.x + pad + lw + pad, top, mw, h), s, cur)
            self._frontier_rect = None
            self._corr_rect = None
        else:
            lw = int(rect.w * 0.42)
            mw = int(rect.w * 0.24)
            rw = rect.w - 4 * pad - lw - mw
            x1 = rect.x + pad
            x2 = x1 + lw + pad
            x3 = x2 + mw + pad
            self._draw_holdings(surf, pygame.Rect(x1, top, lw, h), s, cur)
            self._draw_allocations(surf, pygame.Rect(x2, top, mw, h), s, cur)
            self._draw_risk_charts(surf, pygame.Rect(x3, top, rw, h), p, m, s)
        self.popups_draw(surf)

    def _link_btn(self, surf, x, y, w, label, accent):
        r = pygame.Rect(x, y, w, 22)
        hov = r.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_PANEL if hov else config.COL_PANEL_HEAD, r, border_radius=3)
        pygame.draw.rect(surf, accent, r, 1, border_radius=3)
        widgets.draw_text(surf, label, r.center, fonts.tiny(bold=True), accent, align="center")
        return r

    def _draw_tile_row(self, surf, rect, y, tiles, pad, row_h=46):
        n = len(tiles)
        gap = 6
        tw = (rect.w - 2 * pad - gap * (n - 1)) // n
        x = rect.x + pad
        for label, val, col in tiles:
            widgets.draw_tile(surf, pygame.Rect(x, y, tw, row_h), label, "", config.COL_AMBER)
            widgets.draw_text(surf, widgets.fit_text(val, fonts.small(bold=True), tw - 12),
                              (x + 7, y + 22), fonts.small(bold=True), col)
            x += tw + gap

    def _tiles(self, s, cur):
        fm = lambda v: widgets.format_money(v, cur)
        lev = "∞" if s["leverage"] == float("inf") else f"{s['leverage']:.2f}x"
        return [
            (_L("Valeur nette", "Net worth"), fm(s["net_worth"]), config.COL_WHITE),
            (_L("Trésorerie", "Cash"), fm(s["cash"]), config.COL_TEXT),
            (_L("P&L latent", "Unrealized P&L"), fm(s["unrealized_pnl"]),
             config.COL_UP if s["unrealized_pnl"] >= 0 else config.COL_DOWN),
            (_L("P&L réalisé", "Realized P&L"), fm(s["realized_pnl"]),
             config.COL_UP if s["realized_pnl"] >= 0 else config.COL_DOWN),
            (_L("Bêta", "Beta"), f"{s['beta']:.2f}", config.COL_CYAN),
            (_L("Levier", "Leverage"), lev, config.COL_WARN if s["leverage"] > 1.5 else config.COL_TEXT),
            (_L("Vol. annu.", "Ann. vol."), f"{s['volatility']:.1f}%", config.COL_WARN),
            ("Max DD", f"{s['max_drawdown']:.1f}%",
             _alert_color(s["max_drawdown"], "max_drawdown")),
            (_L("Concentration", "Concentration"), f"top {s['top_weight']:.0f}%",
             _alert_color(s["top_weight"], "top_weight")),
            (_L("Expo. nette", "Net expo."), fm(s["net_exposure"]),
             config.COL_UP if s["net_exposure"] >= 0 else config.COL_DOWN),
        ]

    def _risk_tiles(self, s):
        return [
            (_L("Rdt annualisé", "Ann. return"), f"{s['annualized_return']:+.1f}%",
             config.COL_UP if s["annualized_return"] >= 0 else config.COL_DOWN),
            ("Sharpe", f"{s['sharpe']:.2f}",
             config.COL_UP if s["sharpe"] >= 0 else config.COL_DOWN),
            ("Sortino", f"{s['sortino']:.2f}",
             config.COL_UP if s["sortino"] >= 0 else config.COL_DOWN),
            ("Treynor", f"{s['treynor']:.2f}",
             config.COL_UP if s["treynor"] >= 0 else config.COL_DOWN),
            ("Calmar", f"{s['calmar']:.2f}",
             config.COL_UP if s["calmar"] >= 0 else config.COL_DOWN),
            ("VaR 95%", f"{s['var95']:.1f}%", config.COL_DOWN),
            ("CVaR 95%", f"{s['cvar95']:.1f}%", config.COL_DOWN),
            (_L("Tracking err.", "Tracking err."), f"{s['tracking_error']:.1f}%", config.COL_TEXT),
            (_L("Récup.", "Recovery"), "—" if s["recovery_time"] is None else _L(f"{s['recovery_time']} pas", f"{s['recovery_time']} steps"),
             config.COL_WARN if s["recovery_time"] is None else config.COL_TEXT),
            (_L("Lignes eff.", "Eff. lines"), f"{s['effective_positions']:.1f}", config.COL_TEXT),
        ]

    def _draw_holdings(self, surf, rect, s, cur):
        inner = widgets.draw_panel(surf, rect, _L("Positions détaillées", "Detailed positions"), config.COL_CYAN)
        # colonnes proportionnelles à la largeur du panneau (l'original
        # utilisait des offsets fixes calibrés pour 560 px)
        w = inner.w
        c_qty = inner.x + int(w * 0.54)
        c_price = inner.x + int(w * 0.70)
        c_value = inner.x + int(w * 0.87)
        cols = [(_L("Cl.", "Cl."), inner.x, "left"), (_L("Actif", "Asset"), inner.x + 46, "left"),
                (_L("Qté", "Qty"), c_qty, "right"), (_L("Cours", "Price"), c_price, "right"),
                (_L("Valeur", "Value"), c_value, "right"), (_L("Poids", "Weight"), inner.right, "right")]
        for label, cx, al in cols:
            widgets.draw_text(surf, label, (cx, inner.y), fonts.tiny(bold=True),
                              config.COL_TEXT_DIM, align=al)
        list_top = inner.y + 20
        row_h = 26
        list_area = pygame.Rect(inner.x - 4, list_top, inner.w + 8, inner.bottom - list_top - 16)
        self._holdings_list_rect = list_area
        mp = pygame.mouse.get_pos()
        self._holding_rects = {}
        self._chart_rects = {}
        self._row_cls = {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_top - self.scroll_holdings
        name_zone_w = c_qty - inner.x - 10
        for h in s["rows"]:
            if list_area.top - row_h < y < list_area.bottom:
                ccol = _CLASS_COL.get(h["cls"], config.COL_TEXT)
                tk = h["label"]
                self._row_cls[tk] = h["cls"]
                live_price = self._live_price(h)
                if live_price is not None and h["avg"]:
                    live_value = h["qty"] * live_price
                    live_pnl = live_value - h["qty"] * h["avg"]
                    live_pnl_pct = ((live_price / h["avg"] - 1.0) * 100.0
                                    if h["qty"] > 0
                                    else (h["avg"] / live_price - 1.0) * 100.0)
                else:
                    live_price = h["price"]
                    live_value = h["value"]
                    live_pnl = h["pnl"]
                    live_pnl_pct = h["pnl_pct"]
                pcol = self._flash.tick(tk, live_price, config.COL_UP, config.COL_DOWN,
                                        config.COL_UP if live_pnl >= 0 else config.COL_DOWN)
                name_rect = pygame.Rect(inner.x, y - 2, name_zone_w, row_h - 2)
                self._holding_rects[tk] = name_rect
                if h["cls"] == "Actions":
                    value_rect = pygame.Rect(inner.x + name_zone_w, y - 2,
                                             inner.w - name_zone_w, row_h - 2)
                    self._chart_rects[tk] = value_rect
                if name_rect.collidepoint(mp) or (h["cls"] == "Actions" and
                                                  self._chart_rects[tk].collidepoint(mp)):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, (inner.x, y - 2, inner.w, row_h - 2))
                pygame.draw.rect(surf, ccol, (inner.x, y + 2, 6, 14))
                tag = "S" if h["short"] else " "
                widgets.draw_text(surf, tag, (inner.x + 10, y), fonts.tiny(bold=True), config.COL_DOWN)
                name = widgets.fit_text(f"{h['label']}", fonts.small(bold=True), name_zone_w - 60)
                widgets.draw_text(surf, name, (inner.x + 46, y), fonts.small(bold=True), config.COL_WHITE)
                widgets.draw_text(surf, f"{h['qty']:,.0f}".replace(",", " "),
                                  (c_qty, y), fonts.small(), config.COL_TEXT, align="right")
                widgets.draw_text(surf, f"{live_price:.2f}", (c_price, y),
                                  fonts.small(), pcol, align="right")
                widgets.draw_text(surf, widgets.fit_text(widgets.format_money(live_value, cur),
                                                         fonts.small(bold=True), c_value - c_price - 4),
                                  (c_value, y), fonts.small(bold=True), config.COL_WHITE, align="right")
                widgets.draw_text(surf, f"{h['weight']:.1f}%", (inner.right, y),
                                  fonts.small(), pcol, align="right")
                widgets.draw_text(surf, widgets.fit_text(h["name"], fonts.tiny(), name_zone_w - 60),
                                  (inner.x + 46, y + 13), fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, f"PM {h['avg']:.2f}", (c_price, y + 13),
                                  fonts.tiny(), config.COL_TEXT_DIM, align="right")
                liq_col = {"Liquide": config.COL_UP, "Peu liquide": config.COL_WARN,
                           "Illiquide": config.COL_DOWN}.get(h["liquidity"], config.COL_TEXT_DIM)
                widgets.draw_text(surf, _liq_label(h["liquidity"]), (c_value, y + 13),
                                  fonts.tiny(), liq_col, align="right")
                sign = "+" if live_pnl_pct >= 0 else ""
                widgets.draw_text(surf, f"{sign}{live_pnl_pct:.1f}%", (inner.right, y + 13),
                                  fonts.tiny(), pcol, align="right")
            y += row_h
        surf.set_clip(prev_clip)
        content_h = (y + self.scroll_holdings) - list_top
        self._holdings_max_scroll = max(0, content_h - list_area.h)
        self.scroll_holdings = max(0, min(self._holdings_max_scroll, self.scroll_holdings))
        self.scroll_holdings = widgets.draw_scrollbar(surf, rect, list_area, self.scroll_holdings,
                               self._holdings_max_scroll, content_h)
        widgets.draw_text(surf, widgets.fit_text(
            _L("clic actif → fiche · clic cours/valeur (actions) → graphe", "click asset → sheet · click price/value (equities) → chart"), fonts.tiny(), inner.w),
                          (inner.x, inner.bottom - 12), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_allocations(self, surf, rect, s, cur):
        inner = widgets.draw_panel(surf, rect, _L("Répartition & diversification", "Allocation & diversification"), config.COL_AMBER)
        self._alloc_list_rect = inner
        prev_clip = surf.get_clip()
        surf.set_clip(inner)
        y0 = inner.y - self.scroll_alloc
        y = y0
        y = self._alloc_block(surf, inner, y, _L("Par classe d'actifs", "By asset class"), s["by_class"],
                              lambda k: _CLASS_COL.get(k, config.COL_TEXT))
        y += 6
        y = self._alloc_block(surf, inner, y, _L("Par secteur", "By sector"), s["by_sector"],
                              lambda k: config.COL_CYAN)
        y += 6
        y = self._alloc_block(surf, inner, y, _L("Par région", "By region"), s["by_region"],
                              lambda k: config.COL_PRESTIGE)
        y += 6
        liq_col = {"Liquide": config.COL_UP, "Peu liquide": config.COL_WARN,
                   "Illiquide": config.COL_DOWN}
        y = self._alloc_block(surf, inner, y, _L("Par liquidité", "By liquidity"), s["by_liquidity"],
                              lambda k: liq_col.get(k, config.COL_TEXT))
        y += 4
        pygame.draw.line(surf, config.COL_BORDER, (inner.x, y), (inner.right, y), 1)
        y += 6
        widgets.draw_text(surf, _L(f"Lignes effectives (1/HHI) : {s['effective_positions']:.1f}", f"Effective lines (1/HHI): {s['effective_positions']:.1f}"),
                          (inner.x, y), fonts.tiny(), config.COL_TEXT)
        y += 15
        red, amber = widgets.ALERT_THRESHOLDS["top_weight"]
        conc = _L("forte", "high") if s["top_weight"] > red else _L("modérée", "moderate") if s["top_weight"] > amber else _L("saine", "healthy")
        ccol = _alert_color(s["top_weight"], "top_weight")
        widgets.draw_text(surf, _L(f"Concentration : {conc} (top {s['top_weight']:.0f}%)", f"Concentration: {conc} (top {s['top_weight']:.0f}%)"),
                          (inner.x, y), fonts.tiny(bold=True), ccol)
        y += 18
        top_risk = sorted(s["rows"], key=lambda r: -r["risk_contribution_pct"])[:3]
        if top_risk:
            widgets.draw_text(surf, _L("Top contributeurs au risque", "Top risk contributors"),
                              (inner.x, y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
            y += 16
            for r in top_risk:
                widgets.draw_text(surf, widgets.fit_text(r["label"], fonts.tiny(), 110),
                                  (inner.x, y), fonts.tiny(), config.COL_TEXT)
                widgets.draw_text(surf, f"{r['risk_contribution_pct']:.0f}%",
                                  (inner.right, y), fonts.tiny(bold=True), config.COL_WARN, align="right")
                y += 14
        surf.set_clip(prev_clip)
        content_h = y - y0
        self._alloc_max_scroll = max(0, content_h - inner.h)
        self.scroll_alloc = max(0, min(self._alloc_max_scroll, self.scroll_alloc))
        self.scroll_alloc = widgets.draw_scrollbar(surf, rect, inner, self.scroll_alloc,
                                                    self._alloc_max_scroll, content_h)

    def _alloc_block(self, surf, inner, y, title, data, colfn):
        widgets.draw_text(surf, title, (inner.x, y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 16
        total = sum(data.values()) or 1.0
        items = sorted(data.items(), key=lambda kv: -kv[1])
        label_w = min(110, max(60, int(inner.w * 0.4)))
        for k, v in items:
            frac = v / total
            widgets.draw_text(surf, widgets.fit_text(str(k), fonts.tiny(), label_w),
                              (inner.x, y), fonts.tiny(), config.COL_TEXT)
            bar_x = inner.x + label_w + 6
            bar_w = max(10, inner.w - label_w - 6 - 42)
            widgets.draw_progress(surf, (bar_x, y + 2, bar_w, 9), frac, colfn(k))
            widgets.draw_text(surf, f"{frac*100:.0f}%", (inner.right, y),
                              fonts.tiny(bold=True), config.COL_WHITE, align="right")
            y += 16
        return y

    def _draw_risk_charts(self, surf, rect, p, m, s):
        gap = 10
        half = (rect.h - gap) // 2
        self._frontier_rect = pygame.Rect(rect.x, rect.y, rect.w, half)
        self._corr_rect = pygame.Rect(rect.x, rect.y + half + gap, rect.w, half)
        self._draw_frontier(surf, self._frontier_rect, p, m)
        self._draw_corr(surf, self._corr_rect, p, m)
        mp = pygame.mouse.get_pos()
        for r in (self._frontier_rect, self._corr_rect):
            if r.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_WHITE, r, 1)
                widgets.draw_text(surf, _L("clic → agrandir", "click → enlarge"), (r.right - 6, r.bottom - 14),
                                  fonts.tiny(bold=True), config.COL_WHITE, align="right")

    def _draw_frontier(self, surf, rect, p, m):
        inner = widgets.draw_panel(surf, rect, _L("Frontière efficiente (actions)", "Efficient frontier (equities)"), config.COL_UP)
        fr = analytics.equity_frontier(p, m)
        if not fr:
            widgets.draw_text(surf, _L("≥ 2 actions longues requises.", "≥ 2 long equities required."), (inner.x, inner.y),
                              fonts.tiny(), config.COL_TEXT_DIM)
            return
        vols, rets = fr["vols"], fr["rets"]
        cvol, cret = fr["cur"]
        xs = list(vols) + [cvol]
        ys = list(rets) + [cret]
        lo_x, hi_x = min(xs), max(xs)
        lo_y, hi_y = min(ys), max(ys)
        sx = (hi_x - lo_x) or 1.0
        sy = (hi_y - lo_y) or 1.0
        plot = inner.inflate(-30, -28)
        plot.move_ip(10, 6)

        def px(v, r):
            return (plot.x + int((v - lo_x) / sx * plot.w),
                    plot.bottom - int((r - lo_y) / sy * plot.h))
        pts = [px(v, r) for v, r in zip(vols, rets)]
        if len(pts) >= 2:
            pygame.draw.aalines(surf, config.COL_CYAN, False, pts)
        cp = px(cvol, cret)
        pygame.draw.circle(surf, config.COL_AMBER, cp, 4)
        widgets.draw_text(surf, _L("VOUS", "YOU"), (cp[0] + 6, cp[1] - 6), fonts.tiny(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, _L(f"vol {cvol:.0f}%  ·  rdt att. {cret:.0f}%", f"vol {cvol:.0f}%  ·  exp. ret. {cret:.0f}%"),
                          (inner.x, inner.bottom - 14), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_corr(self, surf, rect, p, m, max_labels=8):
        inner = widgets.draw_panel(surf, rect, _L("Corrélations (actions)", "Correlations (equities)"), config.COL_DOWN)
        labels, corr = analytics.correlation(p, m)
        if len(labels) < 2:
            widgets.draw_text(surf, _L("≥ 2 actions requises.", "≥ 2 equities required."), (inner.x, inner.y),
                              fonts.tiny(), config.COL_TEXT_DIM)
            return
        labels = labels[:max_labels] if max_labels else labels
        nlab = len(labels)
        cell = max(8, min((inner.h - 16) // nlab, (inner.w - 70) // nlab, 30))
        x0, y0 = inner.x + 62, inner.y + 14
        for r in range(nlab):
            widgets.draw_text(surf, widgets.fit_text(labels[r], fonts.tiny(), 58),
                              (inner.x, y0 + r * cell + cell // 2 - 5), fonts.tiny(), config.COL_TEXT)
            for c in range(nlab):
                v = float(corr[r, c])
                col = (widgets._lerp_col(config.COL_PANEL, config.COL_UP, v) if v >= 0
                       else widgets._lerp_col(config.COL_PANEL, config.COL_DOWN, -v))
                cr = pygame.Rect(x0 + c * cell, y0 + r * cell, cell - 1, cell - 1)
                pygame.draw.rect(surf, col, cr)
        for c in range(nlab):
            widgets.draw_text(surf, widgets.fit_text(labels[c], fonts.tiny(), cell + 6),
                              (x0 + c * cell + cell // 2, y0 - 12), fonts.tiny(),
                              config.COL_TEXT_DIM, align="center")
