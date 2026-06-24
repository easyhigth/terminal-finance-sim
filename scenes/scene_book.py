"""
scene_book.py — Livre de positions (portefeuille réel).

Affiche TOUTES les positions détenues, toutes classes d'actifs confondues
(actions, ETF, obligations, matières premières, crypto, structurés, crédit)
via la table unifiée core.analytics.holdings_table. Clic sur le nom d'une
ligne → fiche d'analyse en popup (clic sur la valeur/P&L d'une action →
graphe). Une barre de trading rapide permet d'acheter/vendre une quantité
exacte de n'importe quel actif directement depuis cette scène, en plus du
trading au clavier depuis le terminal (BUY / SELL / ALLOCATE / HEDGE /
REBALANCE).
"""
import pygame

from core import analytics, config
from core import bonds as B
from core import commodities as CM
from core import crypto as K
from core import etfs as ETF
from core import portfolio as pf
from core import securitisation as SEC
from core import structured as S
from core.scene_manager import Scene
from ui import fonts, widgets
from ui.popups import PopupMixin

KIND_CHIPS = ["Action", "ETF", "Obligation", "Commodity", "Crypto", "Structuré", "Crédit"]
CLS_TO_KIND = {"Actions": "Action", "ETF": "ETF", "Obligations": "Obligation",
               "Matières": "Commodity", "Crypto": "Crypto", "Structurés": "Structuré",
               "Crédit": "Crédit"}
KIND_COLOR = {"Action": config.COL_AMBER, "ETF": config.COL_PRESTIGE,
              "Obligation": config.COL_CYAN, "Commodity": config.COL_WARN,
              "Crypto": config.COL_DOWN, "Structuré": config.COL_PRESTIGE,
              "Crédit": config.COL_PRESTIGE}


class BookScene(Scene, PopupMixin):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.init_popups()
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.analytics_btn = widgets.Button(
            (250, config.SCREEN_HEIGHT - 50, 230, 42), "ANALYSE DÉTAILLÉE (PA)", config.COL_CYAN)
        self.shop_btn = widgets.Button(
            (490, config.SCREEN_HEIGHT - 50, 160, 42), "🛒 SHOP", config.COL_AMBER)
        self._name_rects = {}     # label -> Rect (clic → fiche flottante)
        self._chart_rects = {}    # ticker -> Rect (clic → graphe, actions uniquement)
        self._row_cls = {}
        # ---- barre de trading rapide ----
        self.trade_kind = "Action"
        self.trade_key = ""
        self.qty_text = "10"
        self.text_focus = None    # None / "key" / "qty"
        self._kind_rects = {}
        self._key_box = None
        self._qty_box = None
        self._buy_btn = None
        self._sell_btn = None
        self.msg = ""
        self._t = 0.0
        self._key_suggest_rects = []   # (Rect, ticker, nom) — suggestions sous le champ d'actif
        self._suggest_list_rect = None
        self.suggest_scroll = 0
        self._suggest_max_scroll = 0
        # défilement (molette) de la table de positions et du panneau secteur
        self.scroll_positions = 0
        self.scroll_sector = 0
        self._positions_list_rect = None
        self._sector_list_rect = None
        self._positions_max_scroll = 0
        self._sector_max_scroll = 0

    # --------------------------------------------------------------- trading
    def _qty(self):
        try:
            return float(self.qty_text)
        except ValueError:
            return 0.0

    def _resolve_key(self, kind, key):
        """Résout le texte saisi (nom déformé OU ticker, partiel ou complet) vers
        l'identifiant exact attendu par le module de trading — pour les actions,
        passe par la recherche intelligente du marché (comme dans la scène
        GRAPHES) au lieu d'exiger le ticker exact tapé en majuscules."""
        if kind == "Action":
            return self.market.resolve(key) or key.upper()
        if kind in ("Structuré", "Crédit"):
            return key
        return key.upper()

    def _do_buy(self):
        p, m, kind, raw_key = self.app.gs.player, self.market, self.trade_kind, self.trade_key.strip()
        qty = self._qty()
        if not raw_key or qty <= 0:
            self.msg = "Indiquez un identifiant d'actif et une quantité positive."
            return
        key = self._resolve_key(kind, raw_key)
        if kind == "Action":
            r = pf.buy(p, m, key.upper(), qty)
        elif kind == "ETF":
            r = ETF.buy(p, m, key.upper(), qty)
        elif kind == "Obligation":
            r = B.buy_bond(p, m, key.upper(), qty)
        elif kind == "Commodity":
            r = CM.buy(p, m, key.upper(), qty)
        elif kind == "Crypto":
            r = K.buy(p, m, key.upper(), qty)
        elif kind == "Structuré":
            r = S.invest(p, m, key, qty * S.LOT)
        elif kind == "Crédit":
            r = SEC.invest(p, m, key, qty * SEC.LOT)
        else:
            return
        if r["ok"]:
            self.msg = f"Acheté {qty:g} × {key.upper()} @ {r['price']:.2f}."
            if not p.hardcore:
                self.app.gs.save(config.AUTOSAVE_SLOT)
        else:
            self.msg = f"Achat refusé ({r['reason']})."

    def _do_sell(self):
        p, m, kind, raw_key = self.app.gs.player, self.market, self.trade_kind, self.trade_key.strip()
        qty = self._qty()
        if not raw_key or qty <= 0:
            self.msg = "Indiquez un identifiant d'actif et une quantité positive."
            return
        key = self._resolve_key(kind, raw_key)
        if kind == "Action":
            r = pf.sell(p, m, key.upper(), qty)
        elif kind == "ETF":
            r = ETF.sell(p, m, key.upper(), qty)
        elif kind == "Obligation":
            r = B.sell_bond(p, m, key.upper(), qty)
        elif kind == "Commodity":
            r = CM.sell(p, m, key.upper(), qty)
        elif kind == "Crypto":
            r = K.sell(p, m, key.upper(), qty)
        elif kind == "Structuré":
            r = S.sell_by_type(p, m, key, qty * S.LOT)
        elif kind == "Crédit":
            r = SEC.sell(p, m, key, qty * SEC.LOT)
        else:
            return
        if r["ok"]:
            self.msg = f"Vendu {r['qty']:g} × {key.upper()} @ {r['price']:.2f} (P&L {r['realized']:+.0f})."
            if not p.hardcore:
                self.app.gs.save(config.AUTOSAVE_SLOT)
        else:
            self.msg = f"Vente refusée ({r['reason']})."

    def _open_for(self, cls, label):
        kind = CLS_TO_KIND.get(cls)
        if kind == "Action":
            self.open_company(label)
        elif kind == "ETF":
            self.open_etf(label)
        elif kind == "Obligation":
            self.open_bond(label)
        elif kind == "Commodity":
            self.open_commodity(label)
        elif kind == "Crypto":
            self.open_crypto(label)
        elif kind == "Structuré":
            self.open_structured(label)
        elif kind == "Crédit":
            self.open_credit(label)

    def _draw_key_suggestions(self, surf):
        """Menu déroulant de recherche intelligente (ticker OU nom déformé, partiel)
        sous le champ d'actif de la barre de trading rapide — uniquement pour les
        actions, seule classe dont les ~320 noms ne se mémorisent pas facilement.
        Défilable à la molette dès que plus de lignes que la hauteur visible
        (clic droit sur une ligne → fiche d'analyse en aperçu, sans la sélectionner)."""
        self._key_suggest_rects = []
        if self.trade_kind != "Action" or self.text_focus != "key" or not self.trade_key.strip():
            self._suggest_list_rect = None
            self._suggest_max_scroll = 0
            return
        box = self._key_box
        results = self.market.suggest(self.trade_key, 40)
        if not results:
            self._suggest_list_rect = None
            self._suggest_max_scroll = 0
            return
        row_h = 22
        max_visible = 8
        list_area = pygame.Rect(box.x, box.bottom + 2, 260, min(len(results), max_visible) * row_h)
        self._suggest_list_rect = list_area
        content_h = len(results) * row_h
        self._suggest_max_scroll = max(0, content_h - list_area.h)
        self.suggest_scroll = max(0, min(self._suggest_max_scroll, self.suggest_scroll))
        pygame.draw.rect(surf, config.COL_PANEL, list_area)
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        mp = pygame.mouse.get_pos()
        sy = list_area.y - self.suggest_scroll
        for tk, nm in results:
            if list_area.top - row_h < sy < list_area.bottom:
                rr = pygame.Rect(box.x, sy, 260, row_h)
                self._key_suggest_rects.append((rr, tk, nm))
                hov = rr.collidepoint(mp)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov else config.COL_PANEL, rr)
                pygame.draw.rect(surf, config.COL_CYAN if hov else config.COL_BORDER, rr, 1)
                widgets.draw_text(surf, tk, (rr.x + 8, rr.y + 3), fonts.small(bold=True), config.COL_AMBER)
                widgets.draw_text(surf, widgets.fit_text(nm, fonts.tiny(), rr.w - 90),
                                  (rr.x + 80, rr.y + 4), fonts.tiny(), config.COL_TEXT_DIM)
            sy += row_h
        surf.set_clip(prev_clip)
        pygame.draw.rect(surf, config.COL_BORDER, list_area, 1)
        self.suggest_scroll = widgets.draw_scrollbar(surf, list_area, list_area, self.suggest_scroll,
                               self._suggest_max_scroll, content_h)

    # ----------------------------------------------------------------- events
    def handle_event(self, event):
        if self.popups_handle_event(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.popups_close_top():
                    return
                if self.text_focus:
                    self.text_focus = None
                    return
                self.app.scenes.go(self.return_to)
                return
            if self.text_focus == "key":
                if event.key == pygame.K_BACKSPACE:
                    self.trade_key = self.trade_key[:-1]
                elif event.key == pygame.K_TAB:
                    self.text_focus = "qty"
                elif event.unicode and event.unicode.isprintable():
                    self.trade_key += event.unicode
                return
            if self.text_focus == "qty":
                if event.key == pygame.K_BACKSPACE:
                    self.qty_text = self.qty_text[:-1]
                elif event.key == pygame.K_TAB:
                    self.text_focus = "key"
                elif event.unicode.isdigit() or (event.unicode == "." and "." not in self.qty_text):
                    self.qty_text += event.unicode
                return

        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if self.analytics_btn.handle(event):
            self.app.scenes.go("analytics", return_to="book")
            return
        if self.shop_btn.handle(event):
            self.app.scenes.go("shop", return_to="book")
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            delta = -32 if event.button == 4 else 32
            if self._suggest_list_rect and self._suggest_list_rect.collidepoint(event.pos):
                self.suggest_scroll = max(0, min(self._suggest_max_scroll, self.suggest_scroll + delta))
                return
            if self._positions_list_rect and self._positions_list_rect.collidepoint(event.pos):
                self.scroll_positions = max(0, min(self._positions_max_scroll, self.scroll_positions + delta))
                return
            if self._sector_list_rect and self._sector_list_rect.collidepoint(event.pos):
                self.scroll_sector = max(0, min(self._sector_max_scroll, self.scroll_sector + delta))
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            for rr, tk, nm in self._key_suggest_rects:
                if rr.collidepoint(event.pos):
                    self.open_company(nm)
                    return
            for label, rect in self._name_rects.items():
                if rect.collidepoint(event.pos):
                    self._open_for(self._row_cls.get(label), label)
                    return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rr, tk, nm in self._key_suggest_rects:
                if rr.collidepoint(event.pos):
                    self.trade_key = tk
                    self.text_focus = "qty"
                    return
            for kind, rect in self._kind_rects.items():
                if rect.collidepoint(event.pos):
                    self.trade_kind = kind
                    return
            if self._key_box and self._key_box.collidepoint(event.pos):
                self.text_focus = "key"
                return
            if self._qty_box and self._qty_box.collidepoint(event.pos):
                self.text_focus = "qty"
                return
            if self._buy_btn and self._buy_btn.collidepoint(event.pos):
                self._do_buy()
                return
            if self._sell_btn and self._sell_btn.collidepoint(event.pos):
                self._do_sell()
                return
            self.text_focus = None
            for label, rect in self._name_rects.items():
                if rect.collidepoint(event.pos):
                    self._open_for(self._row_cls.get(label), label)
                    return
            for tk, rect in self._chart_rects.items():
                if rect.collidepoint(event.pos):
                    self.open_chart(tk, kind="change")
                    return

    def update(self, dt):
        self._t += dt
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.analytics_btn.update(mp, dt)
        self.shop_btn.update(mp, dt)

    # ----------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        m = self.market
        cur = config.CONTINENTS[p.continent]["currency"]
        widgets.draw_text(surf, "PORTEFEUILLE", (40, 22), fonts.title(bold=True), config.COL_AMBER)

        nw = pf.net_worth(p, m)
        beta = pf.portfolio_beta(p, m)
        pos_val = nw - p.cash
        widgets.draw_text(surf, f"Valeur nette {widgets.format_money(nw, cur)}",
                          (config.SCREEN_WIDTH - 40, 26), fonts.head(bold=True),
                          config.COL_WHITE, align="right")
        sub = (f"Cash {widgets.format_money(p.cash, cur)} · Titres {widgets.format_money(pos_val, cur)} · "
               f"bêta {beta:.2f} · P&L réalisé {widgets.format_money(p.realized_pnl, cur)}")
        widgets.draw_text(surf, sub, (config.SCREEN_WIDTH - 40, 70), fonts.small(),
                          config.COL_TEXT_DIM, align="right")
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

        # ---- barre de trading rapide ----
        # bar_y laisse une marge sous `marg` (tiny, y=88) pour que son texte
        # (long, aligné à droite) ne soit pas recouvert par les chips/boîtes opaques.
        bar_y = 112
        widgets.draw_text(surf, "TRADING RAPIDE :", (40, bar_y + 3), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        bx = 196
        self._kind_rects = {}
        for kind in KIND_CHIPS:
            w = fonts.tiny(bold=True).size(kind)[0] + 14
            rect = pygame.Rect(bx, bar_y, w, 20)
            self._kind_rects[kind] = rect
            sel = (kind == self.trade_kind)
            kcol = KIND_COLOR.get(kind, config.COL_TEXT)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, kcol if sel else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, kind, rect.center, fonts.tiny(bold=sel),
                              kcol if sel else config.COL_TEXT_DIM, align="center")
            bx += w + 6
        bx += 10
        self._key_box = pygame.Rect(bx, bar_y - 2, 130, 24)
        pygame.draw.rect(surf, config.COL_PANEL, self._key_box, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN if self.text_focus == "key" else config.COL_BORDER,
                          self._key_box, 1, border_radius=4)
        kcursor = "_" if (self.text_focus == "key" and int(self._t * 2) % 2 == 0) else ""
        klabel = (self.trade_key + kcursor) if self.trade_key else (kcursor + "ticker/nom/ID…")
        kcol2 = config.COL_TEXT if self.trade_key else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(klabel, fonts.small(), self._key_box.w - 12),
                          (self._key_box.x + 6, self._key_box.y + 4), fonts.small(), kcol2)
        bx = self._key_box.right + 10
        self._qty_box = pygame.Rect(bx, bar_y - 2, 64, 24)
        pygame.draw.rect(surf, config.COL_PANEL, self._qty_box, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER if self.text_focus == "qty" else config.COL_BORDER,
                          self._qty_box, 1, border_radius=4)
        qcursor = "_" if (self.text_focus == "qty" and int(self._t * 2) % 2 == 0) else ""
        widgets.draw_text(surf, (self.qty_text or "0") + qcursor, (self._qty_box.x + 6, self._qty_box.y + 4),
                          fonts.small(), config.COL_TEXT)
        bx = self._qty_box.right + 10
        self._sell_btn = pygame.Rect(bx, bar_y - 2, 70, 24)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._sell_btn, border_radius=4)
        widgets.draw_text(surf, "VENDRE", self._sell_btn.center, fonts.tiny(bold=True),
                          config.COL_DOWN, align="center")
        bx = self._sell_btn.right + 8
        self._buy_btn = pygame.Rect(bx, bar_y - 2, 70, 24)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._buy_btn, border_radius=4)
        widgets.draw_text(surf, "ACHETER", self._buy_btn.center, fonts.tiny(bold=True),
                          config.COL_UP, align="center")
        if self.msg:
            widgets.draw_text(surf, self.msg, (40, bar_y + 26), fonts.tiny(), config.COL_TEXT_DIM)

        # ---- table des positions (toutes classes) ----
        table_top = bar_y + 48
        ph = config.footer_y() - 8 - table_top
        table = pygame.Rect(40, table_top, 900, ph)
        inner = widgets.draw_panel(surf, table, "Positions (toutes classes)", config.COL_CYAN)
        rows = analytics.holdings_table(p, m)
        if not rows:
            widgets.draw_text_wrapped(
                surf, "Aucune position. Utilisez la barre de trading rapide ci-dessus, le "
                "SHOP, ou le terminal (BUY <ticker> <qté>).",
                (inner.x, inner.y), fonts.body(), config.COL_TEXT_DIM, inner.w)
        else:
            cols = [("ACTIF", inner.x), ("TYPE", inner.x + 220), ("QTÉ", inner.x + 290),
                    ("PRU", inner.x + 360), ("COURS", inner.x + 440), ("VALEUR", inner.x + 530),
                    ("P&L", inner.x + 660)]
            for label, x in cols:
                widgets.draw_text(surf, label, (x, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
            list_top = inner.y + 22
            row_h = 26
            list_area = pygame.Rect(inner.x - 4, list_top, inner.w + 8, inner.bottom - list_top - 16)
            self._positions_list_rect = list_area
            mp = pygame.mouse.get_pos()
            self._name_rects = {}
            self._chart_rects = {}
            self._row_cls = {}
            prev_clip = surf.get_clip()
            surf.set_clip(list_area)
            y = list_top - self.scroll_positions
            for r in rows:
                if list_area.top - row_h < y < list_area.bottom:
                    label = r["label"]
                    kind = CLS_TO_KIND.get(r["cls"], r["cls"])
                    kcol = KIND_COLOR.get(kind, config.COL_TEXT)
                    pcol = config.COL_UP if r["pnl"] >= 0 else config.COL_DOWN
                    name_rect = pygame.Rect(inner.x - 4, y - 2, cols[1][1] - inner.x + 4, 22)
                    self._name_rects[label] = name_rect
                    self._row_cls[label] = r["cls"]
                    is_stock = (r["cls"] == "Actions")
                    if is_stock:
                        chart_rect = pygame.Rect(cols[5][1] - 40, y - 2,
                                                 inner.right - cols[5][1] + 44, 22)
                        self._chart_rects[label] = chart_rect
                    else:
                        chart_rect = None
                    hov = name_rect.collidepoint(mp) or (chart_rect and chart_rect.collidepoint(mp))
                    if hov:
                        pygame.draw.rect(surf, config.COL_PANEL_HEAD, (inner.x - 4, y - 2, inner.w + 8, 22))
                    name_label = widgets.fit_text(r["name"], fonts.small(bold=True), 200) \
                        + (" (S)" if r["short"] else "")
                    name_col = config.COL_DOWN if r["short"] else kcol
                    widgets.draw_text(surf, name_label, (cols[0][1], y), fonts.small(bold=True), name_col)
                    widgets.draw_text(surf, kind, (cols[1][1], y), fonts.tiny(bold=True), kcol)
                    widgets.draw_text(surf, f"{r['qty']:.0f}", (cols[2][1], y), fonts.small(), config.COL_TEXT)
                    widgets.draw_text(surf, f"{r['avg']:.2f}", (cols[3][1], y), fonts.small(), config.COL_TEXT_DIM)
                    widgets.draw_text(surf, f"{r['price']:.2f}", (cols[4][1], y), fonts.small(), config.COL_WHITE)
                    widgets.draw_text(surf, widgets.format_money(r["value"], cur), (cols[5][1], y),
                                      fonts.small(), config.COL_TEXT)
                    widgets.draw_text(surf, f"{'+' if r['pnl']>=0 else ''}{widgets.format_money(r['pnl'], cur)} "
                                            f"({r['pnl_pct']:+.1f}%)", (cols[6][1], y), fonts.small(bold=True), pcol)
                y += row_h
            surf.set_clip(prev_clip)
            content_h = (y + self.scroll_positions) - list_top
            self._positions_max_scroll = max(0, content_h - list_area.h)
            self.scroll_positions = max(0, min(self._positions_max_scroll, self.scroll_positions))
            self.scroll_positions = widgets.draw_scrollbar(surf, table, list_area, self.scroll_positions,
                                   self._positions_max_scroll, content_h)
            widgets.draw_text(surf, "clic/clic droit nom → fiche d'analyse · clic valeur/P&L (actions) → graphe",
                              (inner.x, inner.bottom - 14), fonts.tiny(), config.COL_TEXT_DIM)

        # répartition par secteur
        alloc = pygame.Rect(960, table_top, config.SCREEN_WIDTH - 1000, ph)
        ainner = widgets.draw_panel(surf, alloc, "Répartition par secteur", config.COL_AMBER)
        by_sector = pf.allocation_by(p, m, "sector")
        if not by_sector:
            widgets.draw_text(surf, "—", (ainner.x, ainner.y), fonts.body(), config.COL_TEXT_DIM)
            self._sector_list_rect = None
        else:
            total = sum(by_sector.values()) or 1.0
            top = max(by_sector.values()) / total
            warn = top > 0.4
            list_area = pygame.Rect(ainner.x - 4, ainner.y, ainner.w + 8,
                                    ainner.h - (18 if warn else 0))
            self._sector_list_rect = list_area
            prev_clip = surf.get_clip()
            surf.set_clip(list_area)
            y0 = ainner.y - self.scroll_sector
            y = y0
            for sec, val in sorted(by_sector.items(), key=lambda kv: -kv[1]):
                if list_area.top - 36 < y < list_area.bottom:
                    ratio = val / total
                    widgets.draw_text(surf, sec, (ainner.x, y), fonts.small(), config.COL_TEXT)
                    widgets.draw_text(surf, f"{ratio*100:.0f}%", (ainner.right, y),
                                      fonts.small(bold=True), config.COL_WHITE, align="right")
                    widgets.draw_progress(surf, (ainner.x, y + 18, ainner.w, 6), ratio, config.COL_CYAN)
                y += 36
            surf.set_clip(prev_clip)
            content_h = (y + self.scroll_sector) - ainner.y
            self._sector_max_scroll = max(0, content_h - list_area.h)
            self.scroll_sector = max(0, min(self._sector_max_scroll, self.scroll_sector))
            self.scroll_sector = widgets.draw_scrollbar(surf, alloc, list_area, self.scroll_sector,
                                   self._sector_max_scroll, content_h)
            if warn:
                widgets.draw_text(surf, "⚠ Forte concentration sectorielle.",
                                  (ainner.x, ainner.bottom - 18), fonts.tiny(), config.COL_WARN)

        self.back_btn.draw(surf)
        self.analytics_btn.draw(surf)
        self.shop_btn.draw(surf)
        self._draw_key_suggestions(surf)   # overlay : au-dessus de la table
        self.popups_draw(surf)
