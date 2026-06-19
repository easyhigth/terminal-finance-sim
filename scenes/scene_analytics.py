"""
scene_analytics.py — Analyse DÉTAILLÉE du portefeuille (toutes classes d'actifs).

Tableau de bord complet : indicateurs clés (valeur nette, P&L, bêta, levier,
volatilité, drawdown, concentration), table des positions avec poids et P&L,
répartitions (classe / secteur / région), matrice de corrélation des actions et
frontière efficiente estimée sur l'historique réel avec la position courante.
Ouvert via la commande PA (ou le bouton ANALYSE du livre de positions).
"""
import pygame

from core import analytics, config
from core.scene_manager import Scene
from ui import fonts, widgets
from ui.popups import PopupMixin

_CLASS_COL = {"Actions": config.COL_AMBER, "Obligations": config.COL_CYAN,
              "Matières": config.COL_WARN, "Crypto": config.COL_PRESTIGE}


class AnalyticsScene(Scene, PopupMixin):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.init_popups()
        self.back_btn = widgets.Button(
            config.back_button_rect(180), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self._holding_rects = {}    # ticker -> Rect (clic → fiche flottante)
        self._chart_rects = {}      # ticker -> Rect (clic → graphe flottant, rendement)
        self._frontier_rect = None
        self._corr_rect = None

    def handle_event(self, event):
        if self.popups_handle_event(event):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if not self.popups_close_top():
                self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tk, rect in self._holding_rects.items():
                if rect.collidepoint(event.pos):
                    self.open_company(tk)
                    return
            for tk, rect in self._chart_rects.items():
                if rect.collidepoint(event.pos):
                    self.open_chart(tk, kind="change")
                    return
            if self._frontier_rect and self._frontier_rect.collidepoint(event.pos):
                p, m = self.app.gs.player, self.market
                self.open_custom_chart("FRONTIÈRE EFFICIENTE — actions",
                                       lambda surf, rect: self._draw_frontier(surf, rect, p, m),
                                       accent=config.COL_UP, size=(560, 420))
                return
            if self._corr_rect and self._corr_rect.collidepoint(event.pos):
                p, m = self.app.gs.player, self.market
                self.open_custom_chart("CORRÉLATIONS — actions",
                                       lambda surf, rect: self._draw_corr(surf, rect, p, m),
                                       accent=config.COL_DOWN, size=(560, 420))
                return

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    # -------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        m = self.market
        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")
        s = analytics.summary(p, m)

        widgets.draw_text(surf, "ANALYSE DU PORTEFEUILLE", (40, 20),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"{s['n_positions']} positions · "
                          f"{config.GRADES[p.grade_index]} · valeur nette en {cur}",
                          (42, 64), fonts.small(), config.COL_TEXT_DIM)

        if s["n_positions"] == 0:
            widgets.draw_text(surf, "Portefeuille vide. Achetez des actifs (BUY, BUYBOND, "
                              "BUYCMDTY…) pour voir l'analyse détaillée.",
                              (40, 120), fonts.body(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            self.popups_draw(surf)
            return

        self._draw_tiles(surf, s, cur)
        top = 176
        M = config.MARGIN
        bottom = config.footer_y() - 8
        h = bottom - top
        # 3 colonnes
        lw = 560
        mw = 330
        rw = config.SCREEN_WIDTH - 2 * M - lw - mw - 2 * M
        x1 = M
        x2 = M + lw + M
        x3 = x2 + mw + M
        self._draw_holdings(surf, pygame.Rect(x1, top, lw, h), s, cur)
        self._draw_allocations(surf, pygame.Rect(x2, top, mw, h), s, cur)
        self._draw_risk_charts(surf, pygame.Rect(x3, top, rw, h), p, m, s)
        self.back_btn.draw(surf)
        self.popups_draw(surf)

    def _draw_tiles(self, surf, s, cur):
        fm = lambda v: widgets.format_money(v, cur)
        lev = "∞" if s["leverage"] == float("inf") else f"{s['leverage']:.2f}x"
        tiles = [
            ("Valeur nette", fm(s["net_worth"]), config.COL_WHITE),
            ("Trésorerie", fm(s["cash"]), config.COL_TEXT),
            ("P&L latent", fm(s["unrealized_pnl"]),
             config.COL_UP if s["unrealized_pnl"] >= 0 else config.COL_DOWN),
            ("P&L réalisé", fm(s["realized_pnl"]),
             config.COL_UP if s["realized_pnl"] >= 0 else config.COL_DOWN),
            ("Bêta", f"{s['beta']:.2f}", config.COL_CYAN),
            ("Levier", lev, config.COL_WARN if s["leverage"] > 1.5 else config.COL_TEXT),
            ("Vol. annu.", f"{s['volatility']:.1f}%", config.COL_WARN),
            ("Max DD", f"{s['max_drawdown']:.1f}%",
             config.COL_DOWN if s["max_drawdown"] > 15 else config.COL_TEXT),
            ("Concentration", f"top {s['top_weight']:.0f}%", config.COL_TEXT),
            ("Exposition nette", fm(s["net_exposure"]),
             config.COL_UP if s["net_exposure"] >= 0 else config.COL_DOWN),
        ]
        n = len(tiles)
        gap = 8
        tw = (config.SCREEN_WIDTH - 2 * config.MARGIN - gap * (n - 1)) // n
        x = config.MARGIN
        for label, val, col in tiles:
            widgets.draw_tile(surf, pygame.Rect(x, 96, tw, 64), label, "", config.COL_AMBER)
            widgets.draw_text(surf, widgets.fit_text(val, fonts.body(bold=True), tw - 14),
                              (x + 8, 96 + 30), fonts.body(bold=True), col)
            x += tw + gap

    def _draw_holdings(self, surf, rect, s, cur):
        inner = widgets.draw_panel(surf, rect, "Positions détaillées", config.COL_CYAN)
        cols = [("Cl.", inner.x, "left"), ("Actif", inner.x + 46, "left"),
                ("Qté", inner.x + 300, "right"), ("Cours", inner.x + 390, "right"),
                ("Valeur", inner.x + 490, "right"), ("Poids", inner.right, "right")]
        for label, cx, al in cols:
            widgets.draw_text(surf, label, (cx, inner.y), fonts.tiny(bold=True),
                              config.COL_TEXT_DIM, align=al)
        y = inner.y + 20
        row_h = 26
        maxrows = (inner.h - 28) // row_h
        mp = pygame.mouse.get_pos()
        self._holding_rects = {}
        self._chart_rects = {}
        for h in s["rows"][:maxrows]:
            ccol = _CLASS_COL.get(h["cls"], config.COL_TEXT)
            clickable = h["cls"] == "Actions"     # tickers d'actions = sociétés du marché
            if clickable:
                tk = h["label"]
                name_rect = pygame.Rect(inner.x, y - 2, 300, row_h - 2)
                value_rect = pygame.Rect(inner.x + 300, y - 2, inner.w - 300, row_h - 2)
                self._holding_rects[tk] = name_rect
                self._chart_rects[tk] = value_rect
                if name_rect.collidepoint(mp) or value_rect.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, (inner.x, y - 2, inner.w, row_h - 2))
            pygame.draw.rect(surf, ccol, (inner.x, y + 2, 6, 14))
            tag = "S" if h["short"] else " "
            widgets.draw_text(surf, tag, (inner.x + 10, y), fonts.tiny(bold=True), config.COL_DOWN)
            name = widgets.fit_text(f"{h['label']}", fonts.small(bold=True), 200)
            widgets.draw_text(surf, name, (inner.x + 46, y), fonts.small(bold=True), config.COL_WHITE)
            widgets.draw_text(surf, f"{h['qty']:,.0f}".replace(",", " "),
                              (inner.x + 300, y), fonts.small(), config.COL_TEXT, align="right")
            widgets.draw_text(surf, f"{h['price']:.2f}", (inner.x + 390, y),
                              fonts.small(), config.COL_TEXT, align="right")
            widgets.draw_text(surf, widgets.format_money(h["value"], cur),
                              (inner.x + 490, y), fonts.small(bold=True), config.COL_WHITE, align="right")
            pcol = config.COL_UP if h["pnl"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{h['weight']:.1f}%", (inner.right, y),
                              fonts.small(), pcol, align="right")
            # 2e ligne fine : nom + coût moyen + liquidité + P&L %
            widgets.draw_text(surf, widgets.fit_text(h["name"], fonts.tiny(), 240),
                              (inner.x + 46, y + 13), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"PM {h['avg']:.2f}", (inner.x + 390, y + 13),
                              fonts.tiny(), config.COL_TEXT_DIM, align="right")
            liq_col = {"Liquide": config.COL_UP, "Peu liquide": config.COL_WARN,
                       "Illiquide": config.COL_DOWN}.get(h["liquidity"], config.COL_TEXT_DIM)
            widgets.draw_text(surf, h["liquidity"], (inner.x + 490, y + 13),
                              fonts.tiny(), liq_col, align="right")
            sign = "+" if h["pnl_pct"] >= 0 else ""
            widgets.draw_text(surf, f"{sign}{h['pnl_pct']:.1f}%", (inner.right, y + 13),
                              fonts.tiny(), pcol, align="right")
            y += row_h
        if len(s["rows"]) > maxrows:
            widgets.draw_text(surf, f"… +{len(s['rows'])-maxrows} autres",
                              (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, "clic action → fiche · clic cours/valeur/P&L → graphe",
                          (inner.x, inner.bottom - 12), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_allocations(self, surf, rect, s, cur):
        inner = widgets.draw_panel(surf, rect, "Répartition & diversification", config.COL_AMBER)
        y = inner.y
        y = self._alloc_block(surf, inner, y, "Par classe d'actifs", s["by_class"],
                              lambda k: _CLASS_COL.get(k, config.COL_TEXT))
        y += 6
        y = self._alloc_block(surf, inner, y, "Par secteur", s["by_sector"],
                              lambda k: config.COL_CYAN, limit=6)
        y += 6
        y = self._alloc_block(surf, inner, y, "Par région", s["by_region"],
                              lambda k: config.COL_PRESTIGE, limit=5)
        y += 6
        liq_col = {"Liquide": config.COL_UP, "Peu liquide": config.COL_WARN,
                   "Illiquide": config.COL_DOWN}
        y = self._alloc_block(surf, inner, y, "Par liquidité", s["by_liquidity"],
                              lambda k: liq_col.get(k, config.COL_TEXT))
        # diversification
        y += 4
        pygame.draw.line(surf, config.COL_BORDER, (inner.x, y), (inner.right, y), 1)
        y += 6
        widgets.draw_text(surf, f"Lignes effectives (1/HHI) : {s['effective_positions']:.1f}",
                          (inner.x, y), fonts.tiny(), config.COL_TEXT)
        y += 15
        conc = ("forte" if s["top_weight"] > 35 else "modérée" if s["top_weight"] > 20 else "saine")
        ccol = config.COL_DOWN if s["top_weight"] > 35 else config.COL_WARN if s["top_weight"] > 20 else config.COL_UP
        widgets.draw_text(surf, f"Concentration : {conc} (top {s['top_weight']:.0f}%)",
                          (inner.x, y), fonts.tiny(bold=True), ccol)
        y += 18
        top_risk = sorted(s["rows"], key=lambda r: -r["risk_contribution_pct"])[:3]
        if top_risk:
            widgets.draw_text(surf, "Top contributeurs au risque",
                              (inner.x, y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
            y += 16
            for r in top_risk:
                widgets.draw_text(surf, widgets.fit_text(r["label"], fonts.tiny(), 110),
                                  (inner.x, y), fonts.tiny(), config.COL_TEXT)
                widgets.draw_text(surf, f"{r['risk_contribution_pct']:.0f}%",
                                  (inner.right, y), fonts.tiny(bold=True), config.COL_WARN, align="right")
                y += 14

    def _alloc_block(self, surf, inner, y, title, data, colfn, limit=None):
        widgets.draw_text(surf, title, (inner.x, y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 16
        total = sum(data.values()) or 1.0
        items = sorted(data.items(), key=lambda kv: -kv[1])
        if limit:
            items = items[:limit]
        for k, v in items:
            frac = v / total
            widgets.draw_text(surf, widgets.fit_text(str(k), fonts.tiny(), 110),
                              (inner.x, y), fonts.tiny(), config.COL_TEXT)
            widgets.draw_progress(surf, (inner.x + 116, y + 2, inner.w - 116 - 42, 9),
                                  frac, colfn(k))
            widgets.draw_text(surf, f"{frac*100:.0f}%", (inner.right, y),
                              fonts.tiny(bold=True), config.COL_WHITE, align="right")
            y += 16
        return y

    def _draw_risk_charts(self, surf, rect, p, m, s):
        half = (rect.h - config.MARGIN) // 2
        self._frontier_rect = pygame.Rect(rect.x, rect.y, rect.w, half)
        self._corr_rect = pygame.Rect(rect.x, rect.y + half + config.MARGIN, rect.w, half)
        self._draw_frontier(surf, self._frontier_rect, p, m)
        self._draw_corr(surf, self._corr_rect, p, m)
        mp = pygame.mouse.get_pos()
        for r in (self._frontier_rect, self._corr_rect):
            if r.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_WHITE, r, 1)
                widgets.draw_text(surf, "clic → agrandir ⤢", (r.right - 6, r.bottom - 14),
                                  fonts.tiny(bold=True), config.COL_WHITE, align="right")

    def _draw_frontier(self, surf, rect, p, m):
        inner = widgets.draw_panel(surf, rect, "Frontière efficiente (actions)", config.COL_UP)
        fr = analytics.equity_frontier(p, m)
        if not fr:
            widgets.draw_text(surf, "≥ 2 actions longues requises.", (inner.x, inner.y),
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
        # position courante
        cp = px(cvol, cret)
        pygame.draw.circle(surf, config.COL_AMBER, cp, 4)
        widgets.draw_text(surf, "VOUS", (cp[0] + 6, cp[1] - 6), fonts.tiny(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"vol {cvol:.0f}%  ·  rdt att. {cret:.0f}%",
                          (inner.x, inner.bottom - 14), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_corr(self, surf, rect, p, m):
        inner = widgets.draw_panel(surf, rect, "Corrélations (actions)", config.COL_DOWN)
        labels, corr = analytics.correlation(p, m)
        if len(labels) < 2:
            widgets.draw_text(surf, "≥ 2 actions requises.", (inner.x, inner.y),
                              fonts.tiny(), config.COL_TEXT_DIM)
            return
        labels = labels[:8]
        nlab = len(labels)
        cell = min((inner.h - 16) // nlab, (inner.w - 70) // nlab, 30)
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
