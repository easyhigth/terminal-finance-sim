"""
app_book.py — Application « Portefeuille » du bureau (NATIVE).

Migration de `scenes/scene_book.py` (rendu hébergé 1280×720 réduit par
smoothscale → flou, cf. apps/scene_host.py) vers une app dessinée à la
résolution de sa fenêtre — même principe que Inbox/Alertes (étape « apps
natives Inbox/Alertes ») et Trading/Recherche/Tableur avant elles. Toutes les
positions sont désormais relatives au `rect` de la fenêtre plutôt qu'à
`config.SCREEN_WIDTH`/`footer_y()`. Réutilise `core.analytics.holdings_table`
et les mêmes modules de trading (achat/vente toutes classes d'actifs) que la
scène d'origine ; les fiches d'analyse (société/ETF/obligation/matière
première/crypto/structuré/crédit) restent des popups flottants
(`ui/popups.py::PopupMixin`), repositionnés relativement à LA FENÊTRE plutôt
qu'à l'écran entier (`_popup_pos` surchargée). La scène plein écran reste
enregistrée (navigation hors bureau) ; l'ouverture EN FENÊTRE de "book" est
redirigée ici (cf. DesktopScene._open_scene_window).
"""
import pygame

from apps.base import DesktopApp
from core import analytics, config
from core import bonds as B
from core import commodities as CM
from core import crypto as K
from core import etfs as ETF
from core import firms as firms_mod
from core import liquidity as liq
from core import portfolio as pf
from core import securitisation as SEC
from core import structured as S
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
ROW_H = 24


class BookApp(DesktopApp, PopupMixin):
    title = "Portefeuille"
    icon_kind = "book"
    default_size = (980, 600)
    min_size = (720, 420)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.init_popups()
        self._name_rects = {}
        self._chart_rects = {}
        self._row_cls = {}
        self.trade_kind = "Action"
        self.trade_key = ""
        self.qty_text = "10"
        self.text_focus = None
        self._kind_rects = {}
        self._key_box = None
        self._qty_box = None
        self._buy_btn = None
        self._sell_btn = None
        self._pa_btn = None
        self._shop_btn = None
        self.msg = ""
        self._t = 0.0
        self._key_suggest_rects = []
        self._suggest_list_rect = None
        self.suggest_scroll = 0
        self._suggest_max_scroll = 0
        self.scroll_positions = 0
        self.scroll_sector = 0
        self._positions_list_rect = None
        self._sector_list_rect = None
        self._positions_max_scroll = 0
        self._sector_max_scroll = 0
        self._tooltip = None
        self._flash = widgets.TickFlash()
        self.side_mode = "sector"
        self._side_mode_rects = {}
        self._last_rect = pygame.Rect(0, 0, 1, 1)   # pour positionner les popups (cf. _popup_pos)

    # ------------------------------------------------------- popups (fiches)
    def _popup_pos(self):
        """Cascade relative à CETTE fenêtre (pas à l'écran entier, contrairement
        au défaut de PopupMixin) : la fiche s'ouvre près de la fenêtre qui l'a
        déclenchée plutôt qu'à un endroit fixe du bureau."""
        n = len(self.popups)
        offset = 24 * (n % 6)
        r = self._last_rect
        return (r.x + 30 + offset, r.y + 30 + offset)

    # --------------------------------------------------------------- trading
    def _live_price(self, label, cls):
        if cls != "Actions":
            return None
        sim_clock = getattr(self.app, "sim_clock", None)
        day = getattr(self.app.gs.player, "day", None)
        if sim_clock is None or day is None:
            return None
        hist = self.market.history_of(label, 1, sim_clock=sim_clock, day=day)
        return hist[-1] if hist else self.market.price_of(label)

    def _qty(self):
        try:
            return float(self.qty_text)
        except ValueError:
            return 0.0

    def _resolve_key(self, kind, key):
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
            self.msg = f"Acheté {qty:g} × {key.upper()} @ {r['price']:.2f}." + self._slip_suffix(r)
            if kind == "Action":
                self.msg += f" Liquidité {liq.equity_tier(m, key.upper())}."
            if not p.hardcore:
                self.app.gs.save(config.AUTOSAVE_SLOT)
        elif r["reason"] == "sector_excluded":
            firm = firms_mod.get(p.firm)
            fname = firm["name"] if firm else "votre firme"
            self.msg = f"Achat refusé : secteur {r.get('sector', '?')} exclu par l'ADN « {fname} »."
        else:
            self.msg = f"Achat refusé ({r['reason']})."

    def _slip_suffix(self, r):
        slip = r.get("slippage")
        if slip is None:
            return ""
        mid = r["price"] - slip
        pct = (slip / mid * 100.0) if mid else 0.0
        return f" Glissement {pct:+.2f}%."

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
            self.msg = (f"Vendu {r['qty']:g} × {key.upper()} @ {r['price']:.2f} "
                       f"(P&L {r['realized']:+.0f})." + self._slip_suffix(r))
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
        row_h = 20
        max_visible = 6
        list_area = pygame.Rect(box.x, box.bottom + 2, 240, min(len(results), max_visible) * row_h)
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
                rr = pygame.Rect(box.x, sy, 240, row_h)
                self._key_suggest_rects.append((rr, tk, nm))
                hov = rr.collidepoint(mp)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov else config.COL_PANEL, rr)
                pygame.draw.rect(surf, config.COL_CYAN if hov else config.COL_BORDER, rr, 1)
                widgets.draw_text(surf, tk, (rr.x + 6, rr.y + 2), fonts.tiny(bold=True), config.COL_AMBER)
                widgets.draw_text(surf, widgets.fit_text(nm, fonts.tiny(), rr.w - 74),
                                  (rr.x + 68, rr.y + 3), fonts.tiny(), config.COL_TEXT_DIM)
            sy += row_h
        surf.set_clip(prev_clip)
        pygame.draw.rect(surf, config.COL_BORDER, list_area, 1)
        self.suggest_scroll = widgets.draw_scrollbar(surf, list_area, list_area, self.suggest_scroll,
                               self._suggest_max_scroll, content_h)

    # ----------------------------------------------------------------- events
    def handle_event(self, event, rect):
        self._last_rect = rect
        if self.popups_handle_event(event):
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.popups_close_top():
                    return True
                if self.text_focus:
                    self.text_focus = None
                    return True
                return False
            if self.text_focus == "key":
                if event.key == pygame.K_BACKSPACE:
                    self.trade_key = self.trade_key[:-1]
                elif event.key == pygame.K_TAB:
                    self.text_focus = "qty"
                elif event.unicode and event.unicode.isprintable():
                    self.trade_key += event.unicode
                return True
            if self.text_focus == "qty":
                if event.key == pygame.K_BACKSPACE:
                    self.qty_text = self.qty_text[:-1]
                elif event.key == pygame.K_TAB:
                    self.text_focus = "key"
                elif event.unicode.isdigit() or (event.unicode == "." and "." not in self.qty_text):
                    self.qty_text += event.unicode
                return True
            return False

        if self._pa_btn and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 \
                and self._pa_btn.collidepoint(event.pos):
            if self.desktop is not None:
                self.desktop._open_scene_window("analytics")
            return True
        if self._shop_btn and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 \
                and self._shop_btn.collidepoint(event.pos):
            if self.desktop is not None:
                self.desktop._open_scene_window("shop")
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            delta = -32 if event.button == 4 else 32
            if self._suggest_list_rect and self._suggest_list_rect.collidepoint(event.pos):
                self.suggest_scroll = max(0, min(self._suggest_max_scroll, self.suggest_scroll + delta))
                return True
            if self._positions_list_rect and self._positions_list_rect.collidepoint(event.pos):
                self.scroll_positions = max(0, min(self._positions_max_scroll, self.scroll_positions + delta))
                return True
            if self._sector_list_rect and self._sector_list_rect.collidepoint(event.pos):
                self.scroll_sector = max(0, min(self._sector_max_scroll, self.scroll_sector + delta))
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            for rr, tk, nm in self._key_suggest_rects:
                if rr.collidepoint(event.pos):
                    self.open_company(nm)
                    return True
            for label, r in self._name_rects.items():
                if r.collidepoint(event.pos):
                    self._open_for(self._row_cls.get(label), label)
                    return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rr, tk, nm in self._key_suggest_rects:
                if rr.collidepoint(event.pos):
                    self.trade_key = tk
                    self.text_focus = "qty"
                    return True
            for kind, r in self._kind_rects.items():
                if r.collidepoint(event.pos):
                    self.trade_kind = kind
                    return True
            if self._key_box and self._key_box.collidepoint(event.pos):
                self.text_focus = "key"
                return True
            if self._qty_box and self._qty_box.collidepoint(event.pos):
                self.text_focus = "qty"
                return True
            if self._buy_btn and self._buy_btn.collidepoint(event.pos):
                self._do_buy()
                return True
            if self._sell_btn and self._sell_btn.collidepoint(event.pos):
                self._do_sell()
                return True
            self.text_focus = None
            for mode, r in self._side_mode_rects.items():
                if r.collidepoint(event.pos):
                    self.side_mode = mode
                    return True
            for label, r in self._name_rects.items():
                if r.collidepoint(event.pos):
                    self._open_for(self._row_cls.get(label), label)
                    return True
            for tk, r in self._chart_rects.items():
                if r.collidepoint(event.pos):
                    self.open_chart(tk, kind="change")
                    return True
        return False

    def update(self, dt):
        self._t += dt

    # ----------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._last_rect = rect
        surf.fill(config.COL_PANEL, rect)
        pad = 10
        p = self.app.gs.player
        m = self.market
        cur = config.CONTINENTS[p.continent]["currency"]

        nw = pf.net_worth(p, m)
        beta = pf.portfolio_beta(p, m)
        pos_val = nw - p.cash
        widgets.draw_text(surf, f"Valeur nette {widgets.format_money(nw, cur)}",
                          (rect.x + pad, rect.y + pad), fonts.head(bold=True), config.COL_WHITE)
        sub = (f"Cash {widgets.format_money(p.cash, cur)} · Titres {widgets.format_money(pos_val, cur)} · "
               f"bêta {beta:.2f} · P&L réalisé {widgets.format_money(p.realized_pnl, cur)}")
        widgets.draw_text(surf, widgets.fit_text(sub, fonts.tiny(), rect.w - 2 * pad),
                          (rect.x + pad, rect.y + pad + 24), fonts.tiny(), config.COL_TEXT_DIM)
        st = pf.margin_status(p, m)
        lev = "∞" if st["leverage"] == float("inf") else f"{st['leverage']:.2f}x"
        lev_col = config.COL_DOWN if st["margin_call"] else (
            config.COL_WARN if st["leverage"] != float("inf") and st["leverage"] > st["max_leverage"] * 0.8
            else config.COL_TEXT_DIM)
        marg = (f"Levier {lev}/{st['max_leverage']:.1f}x · exposition {widgets.format_money(st['gross'], cur)} · "
                f"PA {widgets.format_money(st['buying_power'], cur)}"
                + ("  ⚠ APPEL DE MARGE" if st["margin_call"] else ""))
        widgets.draw_text(surf, widgets.fit_text(marg, fonts.tiny(), rect.w - 2 * pad - 170),
                          (rect.x + pad, rect.y + pad + 40), fonts.tiny(), lev_col)

        self._pa_btn = pygame.Rect(rect.right - pad - 160, rect.y + pad, 78, 20)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._pa_btn, border_radius=3)
        pygame.draw.rect(surf, config.COL_CYAN, self._pa_btn, 1, border_radius=3)
        widgets.draw_text(surf, "ANALYSE (PA)", self._pa_btn.center, fonts.tiny(bold=True),
                          config.COL_CYAN, align="center")
        self._shop_btn = pygame.Rect(self._pa_btn.right + 6, rect.y + pad, 60, 20)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._shop_btn, border_radius=3)
        pygame.draw.rect(surf, config.COL_AMBER, self._shop_btn, 1, border_radius=3)
        widgets.draw_text(surf, "SHOP", self._shop_btn.center, fonts.tiny(bold=True),
                          config.COL_AMBER, align="center")

        # ---- barre de trading rapide ----
        bar_y = rect.y + pad + 62
        bx = rect.x + pad
        self._kind_rects = {}
        for kind in KIND_CHIPS:
            w = fonts.tiny(bold=True).size(kind)[0] + 12
            r2 = pygame.Rect(bx, bar_y, w, 20)
            self._kind_rects[kind] = r2
            sel = (kind == self.trade_kind)
            kcol = KIND_COLOR.get(kind, config.COL_TEXT)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_BG, r2, border_radius=3)
            pygame.draw.rect(surf, kcol if sel else config.COL_BORDER, r2, 1, border_radius=3)
            widgets.draw_text(surf, kind, r2.center, fonts.tiny(bold=sel),
                              kcol if sel else config.COL_TEXT_DIM, align="center")
            bx += w + 5
            if bx > rect.right - pad - 300:   # fenêtre étroite : arrête d'ajouter des puces
                break
        bar_y2 = bar_y + 24
        bx = rect.x + pad
        self._key_box = pygame.Rect(bx, bar_y2, 120, 22)
        pygame.draw.rect(surf, config.COL_BG, self._key_box, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN if self.text_focus == "key" else config.COL_BORDER,
                          self._key_box, 1, border_radius=4)
        kcursor = "_" if (self.text_focus == "key" and int(self._t * 2) % 2 == 0) else ""
        klabel = (self.trade_key + kcursor) if self.trade_key else "ticker/nom…"
        kcol2 = config.COL_TEXT if self.trade_key else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(klabel, fonts.small(), self._key_box.w - 10),
                          (self._key_box.x + 5, self._key_box.y + 3), fonts.small(), kcol2)
        bx = self._key_box.right + 6
        self._qty_box = pygame.Rect(bx, bar_y2, 56, 22)
        pygame.draw.rect(surf, config.COL_BG, self._qty_box, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER if self.text_focus == "qty" else config.COL_BORDER,
                          self._qty_box, 1, border_radius=4)
        qcursor = "_" if (self.text_focus == "qty" and int(self._t * 2) % 2 == 0) else ""
        widgets.draw_text(surf, (self.qty_text or "0") + qcursor, (self._qty_box.x + 5, self._qty_box.y + 3),
                          fonts.small(), config.COL_TEXT)
        bx = self._qty_box.right + 6
        self._sell_btn = pygame.Rect(bx, bar_y2, 62, 22)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._sell_btn, border_radius=4)
        widgets.draw_text(surf, "VENDRE", self._sell_btn.center, fonts.tiny(bold=True),
                          config.COL_DOWN, align="center")
        bx = self._sell_btn.right + 6
        self._buy_btn = pygame.Rect(bx, bar_y2, 62, 22)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._buy_btn, border_radius=4)
        widgets.draw_text(surf, "ACHETER", self._buy_btn.center, fonts.tiny(bold=True),
                          config.COL_UP, align="center")
        if self.msg:
            widgets.draw_text(surf, widgets.fit_text(self.msg, fonts.tiny(), rect.w - 2 * pad),
                              (rect.x + pad, bar_y2 + 24), fonts.tiny(), config.COL_TEXT_DIM)

        # ---- table des positions + panneau latéral ----
        table_top = bar_y2 + 44
        content_h = rect.bottom - pad - table_top
        side_w = min(260, max(200, int(rect.w * 0.28)))
        table_w = rect.w - 2 * pad - side_w - 10
        if table_w < 340:   # fenêtre trop étroite pour 2 colonnes : empile
            table = pygame.Rect(rect.x + pad, table_top, rect.w - 2 * pad, int(content_h * 0.62))
            side = pygame.Rect(rect.x + pad, table.bottom + 8, rect.w - 2 * pad,
                               content_h - table.h - 8)
        else:
            table = pygame.Rect(rect.x + pad, table_top, table_w, content_h)
            side = pygame.Rect(table.right + 10, table_top, side_w, content_h)

        inner = widgets.draw_panel(surf, table, "Positions (toutes classes)", config.COL_CYAN)
        rows = analytics.holdings_table(p, m)
        if not rows:
            widgets.draw_text_wrapped(
                surf, "Aucune position. Utilisez la barre de trading rapide ci-dessus, le "
                "SHOP, ou le terminal (BUY <ticker> <qté>).",
                (inner.x, inner.y), fonts.body(), config.COL_TEXT_DIM, inner.w)
        else:
            name_w = max(90, int(inner.w * 0.30))
            cols = [("ACTIF", inner.x), ("TYPE", inner.x + name_w),
                    ("QTÉ", inner.x + name_w + 55), ("PRU", inner.x + name_w + 105),
                    ("COURS", inner.x + name_w + 165), ("VALEUR", inner.x + name_w + 225),
                    ("P&L", min(inner.right - 90, inner.x + name_w + 320))]
            for label, x in cols:
                widgets.draw_text(surf, label, (x, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
            list_top = inner.y + 20
            list_area = pygame.Rect(inner.x - 4, list_top, inner.w + 8, inner.bottom - list_top - 14)
            self._positions_list_rect = list_area
            mp = pygame.mouse.get_pos()
            self._name_rects = {}
            self._chart_rects = {}
            self._row_cls = {}
            self._tooltip = None
            prev_clip = surf.get_clip()
            surf.set_clip(list_area)
            y = list_top - self.scroll_positions
            for r in rows:
                if list_area.top - ROW_H < y < list_area.bottom:
                    label = r["label"]
                    kind = CLS_TO_KIND.get(r["cls"], r["cls"])
                    kcol = KIND_COLOR.get(kind, config.COL_TEXT)
                    is_stock = (r["cls"] == "Actions")
                    live_price = self._live_price(label, r["cls"])
                    if live_price is not None and r["avg"]:
                        live_value = r["qty"] * live_price
                        live_pnl = live_value - r["qty"] * r["avg"]
                        live_pnl_pct = ((live_price / r["avg"] - 1.0) * 100.0
                                        if r["qty"] > 0
                                        else (r["avg"] / live_price - 1.0) * 100.0)
                    else:
                        live_price = r["price"]
                        live_value = r["value"]
                        live_pnl = r["pnl"]
                        live_pnl_pct = r["pnl_pct"]
                    pcol = self._flash.tick(label, live_price, config.COL_UP, config.COL_DOWN,
                                            config.COL_UP if live_pnl >= 0 else config.COL_DOWN)
                    name_rect = pygame.Rect(inner.x - 4, y - 1, cols[1][1] - inner.x + 4, ROW_H - 2)
                    self._name_rects[label] = name_rect
                    self._row_cls[label] = r["cls"]
                    if is_stock:
                        chart_rect = pygame.Rect(cols[5][1] - 20, y - 1,
                                                 inner.right - cols[5][1] + 24, ROW_H - 2)
                        self._chart_rects[label] = chart_rect
                    else:
                        chart_rect = None
                    hov = name_rect.collidepoint(mp) or (chart_rect and chart_rect.collidepoint(mp))
                    if hov:
                        pygame.draw.rect(surf, config.COL_PANEL_HEAD, (inner.x - 4, y - 1, inner.w + 8, ROW_H - 2))
                        if is_stock:
                            dy = m.metrics(label)["div_yield"]
                            if dy:
                                sign = -1.0 if r["short"] else 1.0
                                income = sign * live_value * dy
                                verb = "perçu" if income >= 0 else "payé (short)"
                                self._tooltip = (
                                    f"Dividende estimé : {widgets.format_money(abs(income), cur)}/an "
                                    f"{verb} ({dy*100:.1f}% de rendement).", mp)
                    name_label = widgets.fit_text(r["name"], fonts.small(bold=True), name_w - 4) \
                        + (" (S)" if r["short"] else "")
                    name_col = config.COL_DOWN if r["short"] else kcol
                    widgets.draw_text(surf, name_label, (cols[0][1], y), fonts.small(bold=True), name_col)
                    widgets.draw_text(surf, kind[:4], (cols[1][1], y), fonts.tiny(bold=True), kcol)
                    widgets.draw_text(surf, f"{r['qty']:.0f}", (cols[2][1], y), fonts.tiny(), config.COL_TEXT)
                    widgets.draw_text(surf, f"{r['avg']:.2f}", (cols[3][1], y), fonts.tiny(), config.COL_TEXT_DIM)
                    widgets.draw_text(surf, f"{live_price:.2f}", (cols[4][1], y), fonts.tiny(), pcol)
                    widgets.draw_text(surf, widgets.fit_text(widgets.format_money(live_value, cur), fonts.tiny(), 90),
                                      (cols[5][1], y), fonts.tiny(), config.COL_TEXT)
                    widgets.draw_text(surf, f"{'+' if live_pnl>=0 else ''}{live_pnl_pct:+.1f}%",
                                      (cols[6][1], y), fonts.tiny(bold=True), pcol)
                y += ROW_H
            surf.set_clip(prev_clip)
            content_h_rows = (y + self.scroll_positions) - list_top
            self._positions_max_scroll = max(0, content_h_rows - list_area.h)
            self.scroll_positions = max(0, min(self._positions_max_scroll, self.scroll_positions))
            self.scroll_positions = widgets.draw_scrollbar(surf, table, list_area, self.scroll_positions,
                                   self._positions_max_scroll, content_h_rows)

        self._draw_side_panel(surf, side)
        self._draw_key_suggestions(surf)
        self.popups_draw(surf)
        if self._tooltip:
            widgets.draw_tooltip(surf, *self._tooltip)

    def _draw_side_panel(self, surf, rect):
        p = self.app.gs.player
        inner = widgets.draw_panel(surf, rect, "Analyse globale", config.COL_AMBER)
        sub_rect = self._draw_side_tabs(surf, inner)
        if self.side_mode == "sector":
            self._draw_sector_panel(surf, sub_rect)
        else:
            self._draw_history_panel(surf, sub_rect)

    def _draw_side_tabs(self, surf, inner):
        btn_h, gap = 20, 6
        btn_w = (inner.w - gap) // 2
        self._side_mode_rects = {}
        x = inner.x
        for mode, label in (("sector", "SECTEUR"), ("history", "ÉVOLUTION")):
            btn = pygame.Rect(x, inner.y, btn_w, btn_h)
            active = self.side_mode == mode
            accent = config.COL_AMBER if active else config.COL_TEXT_DIM
            pygame.draw.rect(surf, config.COL_PANEL, btn)
            pygame.draw.rect(surf, accent, btn, 2 if active else 1)
            widgets.draw_text(surf, label, btn.center, fonts.tiny(bold=active),
                              accent, align="center")
            self._side_mode_rects[mode] = btn
            x += btn_w + gap
        return pygame.Rect(inner.x, inner.y + btn_h + gap, inner.w,
                           inner.h - btn_h - gap)

    def _draw_sector_panel(self, surf, rect):
        p = self.app.gs.player
        by_sector = pf.allocation_by(p, self.market, "sector")
        if not by_sector:
            widgets.draw_text(surf, "—", (rect.x, rect.y), fonts.body(), config.COL_TEXT_DIM)
            self._sector_list_rect = None
            return
        total = sum(by_sector.values()) or 1.0
        top = max(by_sector.values()) / total
        warn = top > 0.4
        list_area = pygame.Rect(rect.x - 4, rect.y, rect.w + 8,
                                rect.h - (16 if warn else 0))
        self._sector_list_rect = list_area
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = rect.y - self.scroll_sector
        for sec, val in sorted(by_sector.items(), key=lambda kv: -kv[1]):
            if list_area.top - 32 < y < list_area.bottom:
                ratio = val / total
                widgets.draw_text(surf, widgets.fit_text(sec, fonts.tiny(), rect.w - 40),
                                  (rect.x, y), fonts.tiny(), config.COL_TEXT)
                widgets.draw_text(surf, f"{ratio*100:.0f}%", (rect.right, y),
                                  fonts.tiny(bold=True), config.COL_WHITE, align="right")
                widgets.draw_progress(surf, (rect.x, y + 15, rect.w, 5), ratio, config.COL_CYAN)
            y += 32
        surf.set_clip(prev_clip)
        content_h = (y + self.scroll_sector) - rect.y
        self._sector_max_scroll = max(0, content_h - list_area.h)
        self.scroll_sector = max(0, min(self._sector_max_scroll, self.scroll_sector))
        self.scroll_sector = widgets.draw_scrollbar(surf, rect, list_area, self.scroll_sector,
                               self._sector_max_scroll, content_h)
        if warn:
            widgets.draw_text(surf, "⚠ Forte concentration.", (rect.x, rect.bottom - 14),
                              fonts.tiny(), config.COL_WARN)

    def _draw_history_panel(self, surf, rect):
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        series = getattr(p, "cash_history", []) or []
        if len(series) < 2:
            widgets.draw_text_wrapped(surf, "Historique insuffisant — revenez après quelques pas de marché.",
                              (rect.x, rect.y), fonts.tiny(), config.COL_TEXT_DIM, rect.w)
            self._sector_list_rect = None
            return
        start_val = series[0]
        current = series[-1]
        total_pnl = current - start_val
        total_pct = ((current / start_val) - 1.0) * 100.0 if start_val else 0.0
        col = config.COL_UP if total_pnl >= 0 else config.COL_DOWN

        widgets.draw_text(surf, f"Actuel : {widgets.format_money(current, cur)}",
                          (rect.x, rect.y), fonts.small(bold=True), config.COL_WHITE)
        widgets.draw_text(surf, f"P&L : {widgets.format_money(total_pnl, cur)} ({total_pct:+.1f}%)",
                          (rect.x, rect.y + 16), fonts.tiny(bold=True), col)

        chart_top = rect.y + 40
        chart_rect = pygame.Rect(rect.x, chart_top, rect.w, rect.bottom - chart_top - 16)
        if chart_rect.h < 30:
            return
        y_fmt = lambda v: widgets.format_money(v, cur)
        widgets.draw_chart_axes(surf, chart_rect, min(series), max(series), y_fmt=y_fmt, rows=3)
        widgets.draw_series(surf, chart_rect, series, color=col, baseline=True,
                            mouse_pos=pygame.mouse.get_pos(), y_fmt=y_fmt,
                            show_current_line=True, line_width=2)
