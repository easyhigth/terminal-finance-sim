"""
scene_portfolio_unified.py — Portefeuille unifié : une seule table agrégeant
toutes les positions du joueur (actions, obligations, commodities, crypto,
ETF) avec valeur de marché et P&L latent par ligne, triable par colonne.
Ne couvre pas les produits structurés/titrisés/couvertures/options (formes de
données trop hétérogènes pour une ligne de table simple) ; ces classes restent
consultables depuis leurs propres écrans (menu PLUS).
"""
import math

import pygame

from core import bonds, commodities, config, crypto, etfs, portfolio_views
from core.scene_manager import Scene
from ui import fonts, widgets

ROW_H = 26
_CLASS_LABEL = {
    "equity": "Action", "bond": "Obligation", "commodity": "Commodity",
    "crypto": "Crypto", "etf": "ETF",
}
_CLASS_SCENE = {
    "bond": "bonds", "commodity": "commodities", "crypto": "crypto", "etf": "etfs",
}


class PortfolioUnifiedScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.sort_key = "value_abs"
        self.sort_rev = True
        self.scroll = 0
        self._max_scroll = 0
        self._row_rects = []     # [(Rect, row)] lignes visibles (clic -> ouvrir l'actif)
        self._pnl_rects = []     # [(Rect, row)] cellules valeur/P&L (clic -> graphe pnl(t))
        self._sort_rects = {}    # key -> Rect (en-têtes cliquables)
        self.chart_row = None    # row sélectionnée pour le graphe pnl(t), ou None (vue liste)
        self.chart_mode = "pnl"  # "pnl" ou "ytm" (obligations uniquement, cf. _draw_chart_view)
        self._mode_rects = {}    # mode -> Rect (boutons P&L/YTM en vue graphe, obligations)
        self.heat_mode = "sector"  # "sector" ou "corr" (panneau latéral, cf. _draw_side_panel)
        self._heat_mode_rects = {}
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.chart_back_btn = widgets.Button(
            config.back_button_rect(200), "← LISTE", config.COL_TEXT_DIM)

    def _rows(self):
        p = self.app.gs.player
        m = self.market
        out = []
        for h in portfolio_views.holdings(p, m):
            out.append({"cls": "equity", "id": h["ticker"], "name": h["ticker"],
                        "qty": h["shares"], "avg": h["avg"], "price": h["price"],
                        "value": h["value"], "pnl": h["pnl"], "value_abs": abs(h["value"])})
        for h in bonds.holdings(p, m):
            out.append({"cls": "bond", "id": h["id"], "name": h["name"],
                        "qty": h["qty"], "avg": h["avg"], "price": h["price"],
                        "value": h["value"], "pnl": h["pnl"], "value_abs": abs(h["value"])})
        for h in commodities.holdings(p, m):
            out.append({"cls": "commodity", "id": h["id"], "name": h["name"],
                        "qty": h["qty"], "avg": h["avg"], "price": h["price"],
                        "value": h["value"], "pnl": h["pnl"], "value_abs": abs(h["value"])})
        for h in crypto.holdings(p, m):
            out.append({"cls": "crypto", "id": h["id"], "name": h["name"],
                        "qty": h["qty"], "avg": h["avg"], "price": h["price"],
                        "value": h["value"], "pnl": h["pnl"], "value_abs": abs(h["value"])})
        for h in etfs.holdings(p, m):
            out.append({"cls": "etf", "id": h["id"], "name": h["name"],
                        "qty": h["qty"], "avg": h["avg"], "price": h["price"],
                        "value": h["value"], "pnl": h["pnl"], "value_abs": abs(h["value"])})
        out.sort(key=lambda r: r[self.sort_key] if isinstance(r[self.sort_key], (int, float))
                  else str(r[self.sort_key]).lower(), reverse=self.sort_rev)
        return out

    def _open_row(self, row):
        if row["cls"] == "equity":
            self.app.scenes.go("company", ticker=row["id"], return_to="portfolio_unified")
        else:
            self.app.scenes.go(_CLASS_SCENE[row["cls"]], return_to="portfolio_unified")

    def _pnl_series(self, row):
        """Historique du P&L latent de la position depuis l'achat, dans la
        même unité que `row["pnl"]` (cf. core/portfolio_views.py, core/bonds.py,
        core/commodities.py, core/crypto.py, core/etfs.py ::holdings). Le PM
        est supposé constant sur l'historique (approximation MVP, cohérente
        avec l'affichage : seul le prix courant fait varier la qté/PM réels).

        Cas particulier commodities : `row["avg"]`/`row["price"]` sont au
        prix du future « front » (pas le spot) et value/pnl appliquent
        `MULTIPLIER` (taille de contrat) — `commodities.history()` ne
        renvoie que le spot. Comme la pente de la courbe (slope) est
        constante dans le temps pour une commodity donnée, le ratio
        front/spot est lui aussi constant : on reconstruit le front
        historique en appliquant ce ratio au spot historique."""
        m = self.market
        cls, rid = row["cls"], row["id"]
        if cls == "equity":
            hist = m.history_of(rid)
        elif cls == "bond":
            hist = bonds.price_history(m, rid)
        elif cls == "commodity":
            spot_hist = commodities.history(m, rid)
            ratio = math.exp(-commodities.roll_yield(m, rid) / 12.0)
            hist = [s * ratio for s in spot_hist]
            return [(price - row["avg"]) * commodities.MULTIPLIER * row["qty"] for price in hist]
        elif cls == "crypto":
            hist = crypto.history(m, rid)
        elif cls == "etf":
            hist = etfs.nav_history(m, rid)
        else:
            hist = []
        return [(price - row["avg"]) * row["qty"] for price in hist]

    def _ytm_series(self, row):
        """Historique du rendement exigé (YTM, en %) d'une obligation détenue
        (cf. core/bonds.py::ytm_history) — courbe de taux/spread plutôt que
        P&L, pour comprendre POURQUOI le prix de la position a bougé."""
        return [y * 100.0 for y in bonds.ytm_history(self.market, row["id"])]

    def _click_sort(self, key):
        if self.sort_key == key:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_key = key
            self.sort_rev = True

    def handle_event(self, event):
        if self.chart_row is not None:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for mode, rect in self._mode_rects.items():
                    if rect.collidepoint(event.pos):
                        self.chart_mode = mode
                        return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.chart_row = None
                return
            if self.chart_back_btn.handle(event):
                self.chart_row = None
                return
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.back(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 4:
            self.scroll = max(0, self.scroll - 40)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 5:
            self.scroll = min(self._max_scroll, self.scroll + 40)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for mode, rect in self._heat_mode_rects.items():
                if rect.collidepoint(event.pos):
                    self.heat_mode = mode
                    return
            for key, rect in self._sort_rects.items():
                if rect.collidepoint(event.pos):
                    self._click_sort(key)
                    return
            for rect, row in self._pnl_rects:
                if rect.collidepoint(event.pos):
                    self.chart_row = row
                    self.chart_mode = "pnl"
                    return
            for rect, row in self._row_rects:
                if rect.collidepoint(event.pos):
                    self._open_row(row)
                    return

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        if self.chart_row is not None:
            self.chart_back_btn.update(mp, dt)
        else:
            self.back_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        if self.chart_row is not None:
            self._draw_chart_view(surf)
            return
        widgets.draw_text(surf, "PORTEFEUILLE UNIFIÉ", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Toutes vos positions (actions, obligations, commodities, "
                                "crypto, ETF) dans une table triable. Clic colonne = trier, "
                                "clic ligne = ouvrir, clic valeur/P&L = graphe pnl(t).",
                          (42, 72), fonts.tiny(), config.COL_TEXT_DIM)

        top = config.content_top()
        total_h = config.footer_y() - 8 - top
        heat_w = 300
        gap = 12
        table_w = config.SCREEN_WIDTH - 80 - heat_w - gap
        panel = pygame.Rect(40, top, table_w, total_h)
        inner = widgets.draw_panel(surf, panel, "Positions", config.COL_CYAN)
        heat_rect = pygame.Rect(40 + table_w + gap, top, heat_w, total_h)
        self._draw_heat_panel(surf, heat_rect)

        rows = self._rows()
        cols = [("cls", "Classe", 110), ("id", "Actif", 130), ("qty", "Qté", 110),
                ("avg", "PM", 110), ("price", "Cours", 110), ("value", "Valeur", 140),
                ("pnl", "P&L latent", 140)]
        head_y = inner.y
        self._sort_rects = {}
        x = inner.x
        for key, label, w in cols:
            arrow = ""
            if self.sort_key == key or (key == "value" and self.sort_key == "value_abs"):
                arrow = " ▾" if self.sort_rev else " ▴"
            col = config.COL_CYAN if (self.sort_key == key or
                                      (key == "value" and self.sort_key == "value_abs")) else config.COL_TEXT_DIM
            sort_target = "value_abs" if key == "value" else key
            rect = pygame.Rect(x, head_y - 2, w, 18)
            self._sort_rects[sort_target] = rect
            widgets.draw_text(surf, label + arrow, (x, head_y), fonts.tiny(bold=True), col)
            x += w

        list_top = head_y + 22
        list_area = pygame.Rect(inner.x, list_top, inner.w, inner.bottom - list_top)
        if not rows:
            widgets.draw_text(surf, "Aucune position. Achetez des actifs depuis le marché ou la boutique.",
                              (inner.x, list_top + 6), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            return

        mp = pygame.mouse.get_pos()
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_area.y - self.scroll
        self._row_rects = []
        self._pnl_rects = []
        for row in rows:
            visible = (list_area.top - ROW_H) < y < list_area.bottom
            if visible:
                rect = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, ROW_H - 2)
                self._row_rects.append((rect, row))
                pnl_rect = pygame.Rect(inner.x + 570 - 4, y - 2, 280 + 8, ROW_H - 2)
                self._pnl_rects.append((pnl_rect, row))
                hov_pnl = pnl_rect.collidepoint(mp)
                if hov_pnl:
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, pnl_rect, border_radius=3)
                elif rect.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect, border_radius=3)
                x = inner.x
                widgets.draw_text(surf, _CLASS_LABEL[row["cls"]], (x, y), fonts.small(), config.COL_TEXT_DIM)
                x += 110
                widgets.draw_text(surf, widgets.fit_text(str(row["id"]), fonts.small(bold=True), 124),
                                  (x, y), fonts.small(bold=True), config.COL_AMBER)
                x += 130
                widgets.draw_text(surf, f"{row['qty']:,.2f}", (x, y), fonts.small(), config.COL_TEXT)
                x += 110
                widgets.draw_text(surf, f"{row['avg']:,.2f}", (x, y), fonts.small(), config.COL_TEXT)
                x += 110
                widgets.draw_text(surf, f"{row['price']:,.2f}", (x, y), fonts.small(), config.COL_TEXT)
                x += 110
                widgets.draw_text(surf, f"{row['value']:,.0f}", (x, y), fonts.small(bold=True), config.COL_WHITE)
                x += 140
                pcol = config.COL_UP if row["pnl"] >= 0 else config.COL_DOWN
                widgets.draw_text(surf, f"{row['pnl']:+,.0f}", (x, y), fonts.small(bold=True), pcol)
            y += ROW_H
        surf.set_clip(prev_clip)

        content_h = (y + self.scroll) - list_area.y
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, panel, list_area, self.scroll, self._max_scroll, content_h)

        self.back_btn.draw(surf)

    def _draw_heat_panel(self, surf, rect):
        """Panneau latéral à trois modes : heatmap sectorielle, matrice de
        corrélation multi-classes, ou évolution de la valeur nette totale du
        portefeuille dans le temps."""
        btn_h, gap_b = 22, 6
        n = 3
        btn_w = (rect.w - (n - 1) * gap_b) // n
        self._heat_mode_rects = {}
        x = rect.x
        for mode, label in (("sector", "SECTEUR"), ("corr", "CORRÉL."), ("history", "ÉVOLUTION")):
            btn = pygame.Rect(x, rect.y, btn_w, btn_h)
            active = self.heat_mode == mode
            accent = config.COL_AMBER if active else config.COL_TEXT_DIM
            pygame.draw.rect(surf, config.COL_PANEL, btn)
            pygame.draw.rect(surf, accent, btn, 2 if active else 1)
            widgets.draw_text(surf, label, btn.center, fonts.tiny(bold=active), accent, align="center")
            self._heat_mode_rects[mode] = btn
            x += btn_w + gap_b

        sub_rect = pygame.Rect(rect.x, rect.y + btn_h + gap_b, rect.w, rect.h - btn_h - gap_b)
        if self.heat_mode == "corr":
            self._draw_corr_heatmap(surf, sub_rect)
        elif self.heat_mode == "history":
            self._draw_history_panel(surf, sub_rect)
        else:
            self._draw_sector_heatmap(surf, sub_rect)

    def _draw_corr_heatmap(self, surf, rect):
        """Matrice de corrélation multi-classes des positions RÉELLEMENT
        détenues (actions, obligations, commodities, crypto, ETF), cf.
        `portfolio_views.holdings_correlation`. Même convention de couleur
        que `scene_analytics.py::_draw_corr` (lerp COL_PANEL -> COL_UP/DOWN),
        limitée aux N plus grosses positions pour tenir dans le panneau."""
        p = self.app.gs.player
        inner = widgets.draw_panel(surf, rect, "Corrélation (multi-actifs)", config.COL_AMBER)
        labels, corr = portfolio_views.holdings_correlation(p, self.market)
        if len(labels) < 2:
            widgets.draw_text(surf, "Pas assez de positions avec un historique exploitable.",
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            return
        max_labels = min(len(labels), 6)
        labels = labels[:max_labels]
        corr = corr[:max_labels, :max_labels]
        n = len(labels)
        cell = inner.w // (n + 1)
        cell = max(18, min(cell, (inner.h // (n + 1)) if n else cell))
        lbl_font = fonts.tiny()
        for j, lab in enumerate(labels):
            ly = inner.y + (j + 1) * cell + cell // 2
            widgets.draw_text(surf, widgets.fit_text(str(lab), lbl_font, cell),
                              (inner.x, ly), lbl_font, config.COL_TEXT_DIM, align="left")
        for i, lab in enumerate(labels):
            lx = inner.x + cell + i * cell + cell // 2
            widgets.draw_text(surf, widgets.fit_text(str(lab), lbl_font, cell),
                              (lx, inner.y + cell // 2), lbl_font, config.COL_TEXT_DIM, align="center")
        for i in range(n):
            for j in range(n):
                v = float(corr[i, j])
                cx = inner.x + cell + i * cell
                cy = inner.y + (j + 1) * cell
                cell_rect = pygame.Rect(cx, cy, cell - 1, cell - 1)
                col = (widgets._lerp_col(config.COL_PANEL, config.COL_UP, v) if v >= 0
                       else widgets._lerp_col(config.COL_PANEL, config.COL_DOWN, -v))
                pygame.draw.rect(surf, col, cell_rect)
                widgets.draw_text(surf, f"{v:+.1f}", cell_rect.center, fonts.tiny(), config.COL_TEXT, align="center")

    def _draw_sector_heatmap(self, surf, rect):
        """Heatmap sectorielle (actions uniquement) : une cellule par secteur,
        hauteur proportionnelle à |exposition|, couleur = P&L % du coût de
        base (lerp COL_PANEL -> COL_UP/COL_DOWN, saturée à ±30%, même
        convention que `scene_analytics.py::_draw_corr`)."""
        p = self.app.gs.player
        inner = widgets.draw_panel(surf, rect, "Heatmap sectorielle (actions)", config.COL_AMBER)
        heat = portfolio_views.sector_heatmap(p, self.market)
        if not heat:
            widgets.draw_text(surf, "Aucune position en actions.",
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            return
        total_abs = sum(abs(a["value"]) for a in heat) or 1.0
        gap = 4
        y = inner.y
        avail_h = inner.h - gap * (len(heat) - 1)
        for a in heat:
            h = max(20, int(avail_h * (abs(a["value"]) / total_abs)))
            cell = pygame.Rect(inner.x, y, inner.w, h)
            t = max(-1.0, min(1.0, a["pnl_pct"] / 30.0))
            col = (widgets._lerp_col(config.COL_PANEL, config.COL_UP, t) if t >= 0
                   else widgets._lerp_col(config.COL_PANEL, config.COL_DOWN, -t))
            pygame.draw.rect(surf, col, cell, border_radius=3)
            widgets.draw_text(surf, widgets.fit_text(a["sector"], fonts.small(bold=True), inner.w - 16),
                              (cell.x + 8, cell.y + 4), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"{a['value']:+,.0f}  ·  {a['pnl_pct']:+.1f}%",
                              (cell.x + 8, cell.y + h - 18), fonts.tiny(), config.COL_TEXT_DIM)
            y += h + gap

    def _draw_history_panel(self, surf, rect):
        """Contenu de l'onglet Évolution : graphe de la valeur nette totale
        du portefeuille dans le temps (`player.cash_history`)."""
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        series = getattr(p, "cash_history", []) or []
        if len(series) < 2:
            widgets.draw_text(surf, "Historique insuffisant — revenez après quelques pas de marché.",
                              (rect.x, rect.y), fonts.small(), config.COL_TEXT_DIM)
            return
        start_val = series[0]
        current = series[-1]
        total_pnl = current - start_val
        total_pct = ((current / start_val) - 1.0) * 100.0 if start_val else 0.0
        col = config.COL_UP if total_pnl >= 0 else config.COL_DOWN

        widgets.draw_text(surf, f"Valeur nette : {widgets.format_money(current, cur)}",
                          (rect.x, rect.y), fonts.small(bold=True), config.COL_WHITE)
        widgets.draw_text(surf, f"Départ : {widgets.format_money(start_val, cur)}",
                          (rect.x, rect.y + 18), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"P&L total : {widgets.format_money(total_pnl, cur)} ({total_pct:+.1f}%)",
                          (rect.x, rect.y + 36), fonts.small(bold=True), col)

        chart_top = rect.y + 66
        chart_rect = pygame.Rect(rect.x, chart_top, rect.w, rect.bottom - chart_top - 20)
        if chart_rect.h < 40:
            return
        y_fmt = lambda v: widgets.format_money(v, cur)
        lo, hi, span = widgets.draw_chart_axes(surf, chart_rect, min(series), max(series),
                                               y_fmt=y_fmt, rows=4)
        widgets.draw_series(surf, chart_rect, series, color=col, baseline=True,
                            mouse_pos=pygame.mouse.get_pos(), y_fmt=y_fmt,
                            show_current_line=True, line_width=2)
        widgets.draw_chart_x_labels(surf, chart_rect, [(0.0, "début"), (1.0, "auj.")])

    def _draw_chart_view(self, surf):
        row = self.chart_row
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        is_bond = row["cls"] == "bond"
        if is_bond and self.chart_mode == "ytm":
            title = f"Taux exigé (YTM) — {row['id']} ({_CLASS_LABEL[row['cls']]})"
        else:
            title = f"P&L — {row['id']} ({_CLASS_LABEL[row['cls']]})"
        widgets.draw_text(surf, title, (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"Qté {row['qty']:+,.2f}  ·  PM {row['avg']:,.2f}  ·  "
                                f"Cours {row['price']:,.2f}  ·  P&L latent "
                                f"{row['pnl']:+,.0f} {cur}",
                          (42, 72), fonts.tiny(), config.COL_TEXT_DIM)

        self._mode_rects = {}
        if is_bond:
            btn_w, btn_h, gap = 110, 28, 8
            x = config.SCREEN_WIDTH - 40 - 2 * btn_w - gap
            for mode, label in (("pnl", "P&L"), ("ytm", "TAUX (YTM)")):
                rect = pygame.Rect(x, 18, btn_w, btn_h)
                active = self.chart_mode == mode
                accent = config.COL_AMBER if active else config.COL_TEXT_DIM
                pygame.draw.rect(surf, config.COL_PANEL, rect)
                pygame.draw.rect(surf, accent, rect, 2 if active else 1)
                widgets.draw_text(surf, label, rect.center, fonts.tiny(), accent, align="center")
                self._mode_rects[mode] = rect
                x += btn_w + gap

        top = config.content_top()
        panel = pygame.Rect(40, top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - top)
        panel_title = "Taux exigé (YTM) dans le temps" if (is_bond and self.chart_mode == "ytm") \
            else "P&L latent dans le temps"
        inner = widgets.draw_panel(surf, panel, panel_title, config.COL_CYAN)

        if is_bond and self.chart_mode == "ytm":
            series = self._ytm_series(row)
        else:
            series = self._pnl_series(row)
        if len(series) < 2:
            widgets.draw_text(surf, "Historique insuffisant pour tracer ce graphe.",
                              (inner.x, inner.y), fonts.small(), config.COL_TEXT_DIM)
            self.chart_back_btn.draw(surf)
            return

        chart_rect = pygame.Rect(inner.x + 80, inner.y + 8, inner.w - 100, inner.h - 30)
        if is_bond and self.chart_mode == "ytm":
            y_fmt = lambda v: f"{v:.2f}%"
        else:
            y_fmt = lambda v: widgets.format_money(v, cur)
        lo, hi, span = widgets.draw_chart_axes(
            surf, chart_rect, min(series), max(series), y_fmt=y_fmt, rows=5)
        if is_bond and self.chart_mode == "ytm":
            col = config.COL_CYAN
        else:
            col = config.COL_UP if series[-1] >= 0 else config.COL_DOWN
        widgets.draw_series(surf, chart_rect, series, col, baseline=False,
                            mouse_pos=pygame.mouse.get_pos())
        if not (is_bond and self.chart_mode == "ytm"):
            widgets.draw_chart_zero_line(surf, chart_rect, lo, span)

        self.chart_back_btn.draw(surf)
