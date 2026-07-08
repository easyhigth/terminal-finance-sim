"""
app_shop.py — Application « Boutique » du bureau (NATIVE).

Migration de `scenes/scene_shop.py` (rendu hébergé 1280×720 réduit par
smoothscale → flou, cf. apps/scene_host.py) vers une app dessinée à la
résolution de sa fenêtre — le guichet unique pour acheter n'importe quel
actif, référencé en permanence par le bouton SHOP de Trading et Portefeuille.
Comme la fiche société (apps/app_company.py), CHAQUE ouverture RECONFIGURE
la fenêtre existante (`configure(**kwargs)`) plutôt que de la préserver en
l'état — reproduit le comportement de la scène d'origine, où `on_enter`
réinitialisait toujours l'écran (recherche/filtre pré-remplis si fournis par
l'appelant, ex. le lien retour de l'Explorateur, sinon vierges). Les fiches
d'analyse restent des popups flottants (`ui/popups.py::PopupMixin`,
repositionnés relativement à LA FENÊTRE). Les liens vers les scènes dédiées
par type d'actif (ETF/obligations/…) et l'Explorateur restent hébergés
(hors scope de cette migration), ouverts EN FENÊTRE via
`desktop._open_scene_window`. La scène plein écran reste enregistrée
(fallback/tests) ; l'ouverture EN FENÊTRE de "shop" est redirigée ici
(cf. DesktopScene._open_scene_window).
"""
import pygame

from core import bonds as B
from core import commodities as CM
from core import config, intraday, unlocks
from core import crypto as K
from core import etfs as ETF
from core import liquidity as LIQ
from core import portfolio as PF
from core import portfolio_margin as PM
from core import securitisation as SEC
from core import structured as S
from core.i18n import get_lang

from apps.base import DesktopApp
from ui import fonts, keynav, widgets
from ui.popups import PopupMixin


def _L(fr, en):
    return en if get_lang() == "en" else fr

ROW_H = 26
SORT_FIELDS = [("name", "NOM"), ("price", "COURS"), ("value", "VALEUR"),
               ("yield_pct", "RENDEMENT"), ("change_pct", "VAR %")]
TYPE_CHIPS = [(None, "TOUTES"), ("Action", "ACTIONS"), ("ETF", "ETF"),
              ("Obligation", "OBLIGATIONS"), ("Commodity", "COMMODITIES"),
              ("Crypto", "CRYPTO"), ("Structuré", "STRUCTURÉS"), ("Crédit", "CRÉDIT")]
KIND_COLOR = {"Action": config.COL_AMBER, "ETF": config.COL_PRESTIGE,
              "Obligation": config.COL_CYAN, "Commodity": config.COL_WARN,
              "Crypto": config.COL_DOWN, "Structuré": config.COL_PRESTIGE,
              "Crédit": config.COL_PRESTIGE}
KIND_LABEL = {"Action": "Action", "ETF": "ETF", "Obligation": "Oblig.",
              "Commodity": "Cmdty", "Crypto": "Crypto", "Structuré": "Struct.",
              "Crédit": "Crédit"}
QTY_PRESETS = [1, 5, 10, 25, 100]
SCENE_LINKS = [("etfs", "■ ETF"), ("bonds", "▫ OBLIGATIONS"), ("commodities", "▲ COMMODITIES"),
               ("crypto", "₿ CRYPTO"), ("structured", "◆ STRUCTURÉS"), ("credit", "● CRÉDIT")]


class ShopApp(DesktopApp, PopupMixin):
    title = "Boutique"
    icon_kind = "shop"
    default_size = (1100, 680)
    min_size = (700, 460)

    def on_open(self):
        self.configure()

    def reenter(self, **kwargs):
        self.configure(**kwargs)

    def configure(self, search="", type_filter=None, sub_filter=None, **_kwargs):
        # **_kwargs absorbe silencieusement un éventuel "return_to" hérité
        # des anciens appelants de la scène hébergée (plus de bouton retour
        # sur une fenêtre native).
        self.market = self.app.ensure_market()
        self.init_popups()
        self.rows = self._build_dataset()
        self.search = search
        self.text_focus = "search"
        self.qty_text = "10"
        self._t = 0.0
        self.type_filter = type_filter
        self.sub_filter = sub_filter
        self.sort_key = "value"
        self.sort_dir = -1
        self.scroll = 0
        self._max_scroll = 0
        self.row_cursor = 0
        self._row_list = []
        self._list_rect = None
        self._name_rects = {}
        self._buy_rects = {}
        self._sell_rects = {}
        self._type_rects = {}
        self._sub_rects = {}
        self._sort_rects = {}
        self._qty_box = None
        self._qty_minus = None
        self._qty_plus = None
        self._preset_rects = {}
        self._search_clear_rect = None
        self._scene_link_rects = {}
        self.msg = ""
        self._tooltip = None
        self._flash = widgets.TickFlash()
        self._last_rect = pygame.Rect(0, 0, 1, 1)   # pour positionner les popups (cf. _popup_pos)

    def _popup_pos(self):
        """Cascade relative à CETTE fenêtre plutôt qu'à l'écran entier."""
        n = len(self.popups)
        offset = 24 * (n % 6)
        r = self._last_rect
        return (r.x + 30 + offset, r.y + 30 + offset)

    def refresh_data(self):
        self.market = self.app.ensure_market()
        self.rows = self._build_dataset()

    # --------------------------------------------------------------- live data
    def _live_quote(self, r):
        m = self.market
        kind, key = r["kind"], r["key"]
        price = r["price"]
        value = r["value"]
        yield_pct = r["yield_pct"]
        change_pct = r["change_pct"]

        if kind == "Action":
            i = m.ticker_idx.get(key)
            if i is not None:
                region = m.companies[i].get("region")
                vol_mult = intraday.vol_mult_for_sigma(float(m.sigma[i]))
                hist = m.history_of(key, 2)
                target = m.next_price_of(key)
                day = self.app.gs.player.day
                live = intraday.live_point(m, self.app.sim_clock, day, key, hist,
                                            region=region, vol_mult=vol_mult, target=target)
                if live is not None:
                    price = live
                mt = m.metrics(key)
                if mt:
                    value = price * mt["shares"]
                    change_pct = mt["change_pct"]
        elif kind == "ETF":
            q = ETF.quote(m, key)
            if q:
                price = q["price"]
                value = q["price"]
                yield_pct = q["yield"] * 100.0
                change_pct = q["change_pct"]
        elif kind == "Obligation":
            q = B.quote(m, key)
            if q:
                price = q["price"]
                value = q["price"]
                yield_pct = q["ytm"] * 100.0
        elif kind == "Commodity":
            q = CM.quote(m, key)
            if q:
                price = q["front"]
                value = q["front"] * CM.MULTIPLIER
                yield_pct = q["roll_yield"] * 100.0
        elif kind == "Crypto":
            q = K.quote(m, key)
            if q:
                price = q["spot"]
                value = q["spot"]
                yield_pct = (q["yield"] * 100.0) if q["yield"] else None
        return {"price": price, "value": value, "yield_pct": yield_pct,
                "change_pct": change_pct}

    # --------------------------------------------------------------- helpers
    def _can_trade(self):
        return unlocks.unlocked(self.app.gs.player, "trade")

    def _qty(self):
        try:
            q = float(self.qty_text)
        except ValueError:
            return 0.0
        return q

    # ----------------------------------------------------------- dataset
    def _build_dataset(self):
        m = self.market
        rows = []
        for c in m.companies:
            tk = c["ticker"]
            mt = m.metrics(tk)
            if not mt:
                continue
            rows.append({"kind": "Action", "key": tk, "name": mt["name"],
                         "sub": mt["sector"], "price": mt["price"],
                         "value": mt["mktcap"] * 1e6, "yield_pct": mt["div_yield"] * 100.0,
                         "change_pct": mt["change_pct"]})
        for q in ETF.all_quotes(m):
            rows.append({"kind": "ETF", "key": q["id"], "name": q["name"],
                         "sub": q["category_label"], "price": q["price"], "value": q["price"],
                         "yield_pct": q["yield"] * 100.0, "change_pct": q["change_pct"]})
        for q in B.all_quotes(m):
            rows.append({"kind": "Obligation", "key": q["id"], "name": q["name"],
                         "sub": f"{q['kind']} · {q['rating']}", "price": q["price"],
                         "value": q["price"], "yield_pct": q["ytm"] * 100.0, "change_pct": None})
        for q in CM.all_quotes(m):
            rows.append({"kind": "Commodity", "key": q["id"], "name": q["name"],
                         "sub": q["category"], "price": q["front"],
                         "value": q["front"] * CM.MULTIPLIER, "yield_pct": q["roll_yield"] * 100.0,
                         "change_pct": None})
        for q in K.all_quotes(m):
            rows.append({"kind": "Crypto", "key": q["id"], "name": q["name"],
                         "sub": "Stablecoin" if q["stable"] else ("CBDC" if q["cbdc"] else "Volatil"),
                         "price": q["spot"], "value": q["spot"], "yield_pct": q["yield"] * 100.0,
                         "change_pct": None})
        for tpl in S.all_templates():
            coupon = tpl.get("coupon") or tpl.get("vol_strike")
            rows.append({"kind": "Structuré", "key": tpl["id"], "name": tpl["name"],
                         "sub": f"{tpl['family']} · {tpl['years']} ans", "price": S.LOT,
                         "value": S.LOT, "yield_pct": coupon * 100.0 if coupon is not None else None,
                         "change_pct": None})
        for q in SEC.all_quotes(m):
            rows.append({"kind": "Crédit", "key": q["id"], "name": q["name"],
                         "sub": f"{q['attach']*100:.0f}-{q['detach']*100:.0f}% · {q['rating']}",
                         "price": SEC.LOT, "value": SEC.LOT,
                         "yield_pct": q["coupon"] * 100.0, "change_pct": None})
        return rows

    def _sub_options(self):
        if self.type_filter == "Action":
            return list(self.market.sectors)
        if self.type_filter == "Commodity":
            seen = []
            for cid, name, sp, dr, vol, sl, cat in CM.COMMODITIES:
                if cat not in seen:
                    seen.append(cat)
            return seen
        if self.type_filter == "Obligation":
            return ["Souverain", "Corporate"]
        if self.type_filter == "ETF":
            return [lbl for _, lbl in ETF.CATEGORIES]
        return []

    def _filtered_sorted(self):
        q = self.search.strip().lower()
        out = []
        for r in self.rows:
            if self.type_filter and r["kind"] != self.type_filter:
                continue
            if self.sub_filter and not str(r["sub"]).startswith(self.sub_filter):
                continue
            if q:
                hay = f"{r['name']} {r['key']} {r['sub']}".lower()
                if q not in hay:
                    continue
            out.append(r)
        key = self.sort_key
        have = [r for r in out if r.get(key) is not None]
        none_rows = [r for r in out if r.get(key) is None]
        if key == "name":
            have.sort(key=lambda r: r["name"].lower(), reverse=(self.sort_dir < 0))
        else:
            have.sort(key=lambda r: r[key], reverse=(self.sort_dir < 0))
        return have + none_rows

    # --------------------------------------------------------------- actions
    def _open_detail(self, kind, key):
        if kind == "Action":
            self.open_company(key)
        elif kind == "ETF":
            self.open_etf(key)
        elif kind == "Obligation":
            self.open_bond(key)
        elif kind == "Commodity":
            self.open_commodity(key)
        elif kind == "Crypto":
            self.open_crypto(key)
        elif kind == "Structuré":
            self.open_structured(key)
        elif kind == "Crédit":
            self.open_credit(key)

    def _held_qty(self, kind, key):
        p = self.app.gs.player
        if kind == "Action":
            pos = p.portfolio.get(key)
            return pos["shares"] if pos else 0.0
        if kind == "ETF":
            pos = p.etfs.get(key)
            return pos["qty"] if pos else 0.0
        if kind == "Obligation":
            pos = p.bonds.get(key)
            return pos["qty"] if pos else 0.0
        if kind == "Commodity":
            pos = p.commodities.get(key)
            return pos["qty"] if pos else 0.0
        if kind == "Crypto":
            pos = p.crypto.get(key)
            return pos["qty"] if pos else 0.0
        if kind == "Structuré":
            return S.held_notional(p, key) / S.LOT
        if kind == "Crédit":
            return SEC.held_notional(p, key) / SEC.LOT
        return 0.0

    def _do_sell(self, kind, key):
        if not self._can_trade():
            return
        held = self._held_qty(kind, key)
        if held <= 0:
            return
        qty = min(self._qty(), held)
        if qty <= 0:
            self.msg = "Quantité invalide : indiquez un nombre positif."
            return
        p, m = self.app.gs.player, self.market
        if kind == "Action":
            r = PF.sell(p, m, key, qty)
        elif kind == "ETF":
            r = ETF.sell(p, m, key, qty)
        elif kind == "Obligation":
            r = B.sell_bond(p, m, key, qty)
        elif kind == "Commodity":
            r = CM.sell(p, m, key, qty)
        elif kind == "Crypto":
            r = K.sell(p, m, key, qty)
        elif kind == "Structuré":
            r = S.sell_by_type(p, m, key, qty * S.LOT)
        elif kind == "Crédit":
            r = SEC.sell(p, m, key, qty * SEC.LOT)
        else:
            return
        if r["ok"]:
            self.msg = f"Vendu {r['qty']:g} × {key} @ {r['price']:.2f} (P&L {r['realized']:+.0f})." \
                + self._slip_suffix(r)
            if not p.hardcore:
                self.app.gs.save(config.AUTOSAVE_SLOT)
        else:
            self.msg = f"Vente refusée ({r['reason']})."

    def _slip_suffix(self, r):
        slip = r.get("slippage")
        if slip is None:
            return ""
        mid = r["price"] - slip
        pct = (slip / mid * 100.0) if mid else 0.0
        return f" Glissement {pct:+.2f}%."

    def _do_buy(self, kind, key):
        if not self._can_trade():
            return
        qty = self._qty()
        if qty <= 0:
            self.msg = "Quantité invalide : indiquez un nombre positif."
            return
        p, m = self.app.gs.player, self.market
        if kind == "Action":
            r = PF.buy(p, m, key, qty)
        elif kind == "ETF":
            r = ETF.buy(p, m, key, qty)
        elif kind == "Obligation":
            r = B.buy_bond(p, m, key, qty)
        elif kind == "Commodity":
            r = CM.buy(p, m, key, qty)
        elif kind == "Crypto":
            r = K.buy(p, m, key, qty)
        elif kind == "Structuré":
            r = S.invest(p, m, key, qty * S.LOT)
        elif kind == "Crédit":
            r = SEC.invest(p, m, key, qty * SEC.LOT)
        else:
            return
        if r["ok"]:
            self.msg = f"Acheté {qty:g} × {key} @ {r['price']:.2f}." + self._slip_suffix(r)
            if not p.hardcore:
                self.app.gs.save(config.AUTOSAVE_SLOT)
        else:
            self.msg = f"Achat refusé ({r['reason']})."

    def _scroll_to_cursor(self):
        if not self._list_rect:
            return
        row_top = self.row_cursor * ROW_H
        row_bottom = row_top + ROW_H
        if row_top < self.scroll:
            self.scroll = row_top
        elif row_bottom > self.scroll + self._list_rect.h:
            self.scroll = row_bottom - self._list_rect.h
        self.scroll = max(0, min(self._max_scroll, self.scroll))

    # --------------------------------------------------------------- events
    def handle_event(self, event, rect):
        self._last_rect = rect
        if self.popups_handle_event(event):
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f and (event.mod & pygame.KMOD_CTRL):
                self.text_focus = "search"
                self.scroll = 0
                return True
            if event.key == pygame.K_ESCAPE:
                if self.popups_close_top():
                    return True
                if self.text_focus == "qty":
                    self.text_focus = "search"
                    return True
                if self.search:
                    self.search = ""
                    return True
                return False
            if event.key == pygame.K_BACKSPACE:
                if self.text_focus == "qty":
                    self.qty_text = self.qty_text[:-1]
                else:
                    self.search = self.search[:-1]
                return True
            if event.key == pygame.K_PAGEUP:
                self.scroll = max(0, self.scroll - 200)
                return True
            if event.key == pygame.K_PAGEDOWN:
                self.scroll = min(self._max_scroll, self.scroll + 200)
                return True
            if event.key == pygame.K_TAB:
                self.text_focus = "qty" if self.text_focus == "search" else "search"
                return True
            if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER) \
                    and self.text_focus != "qty":
                self.row_cursor, activate = widgets.list_key_nav(
                    event, self.row_cursor, len(self._row_list))
                if self._row_list:
                    self._scroll_to_cursor()
                if activate and self._row_list:
                    r = self._row_list[self.row_cursor]
                    self._open_detail(r["kind"], r["key"])
                return True
            from core import clipboard
            if clipboard.is_paste_shortcut(event):
                pasted = clipboard.paste().replace("\n", " ").strip()
                if self.text_focus == "qty":
                    self.qty_text += "".join(ch for ch in pasted if ch.isdigit() or ch == ".")
                else:
                    self.search += pasted
                    self.scroll = 0
                return True
            if event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                if self.text_focus == "qty":
                    if event.unicode.isdigit() or (event.unicode == "." and "." not in self.qty_text):
                        self.qty_text += event.unicode
                else:
                    self.search += event.unicode
                    self.scroll = 0
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for scene_name, r in self._scene_link_rects.items():
                if r.collidepoint(event.pos):
                    if self.desktop is not None:
                        self.desktop._open_scene_window(scene_name)
                    return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            for ident, r in self._name_rects.items():
                if r.collidepoint(event.pos):
                    self._open_detail(*ident)
                    return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return True
            if self._qty_box and self._qty_box.collidepoint(event.pos):
                self.text_focus = "qty"
                return True
            if self._qty_minus and self._qty_minus.collidepoint(event.pos):
                self.qty_text = f"{max(0.0, self._qty() - 1):g}"
                return True
            if self._qty_plus and self._qty_plus.collidepoint(event.pos):
                self.qty_text = f"{self._qty() + 1:g}"
                return True
            for val, r in self._preset_rects.items():
                if r.collidepoint(event.pos):
                    self.qty_text = f"{val:g}"
                    return True
            self.text_focus = "search"
            for val, r in self._type_rects.items():
                if r.collidepoint(event.pos):
                    self.type_filter = val
                    self.sub_filter = None
                    self.scroll = 0
                    return True
            for val, r in self._sub_rects.items():
                if r.collidepoint(event.pos):
                    self.sub_filter = None if self.sub_filter == val else val
                    self.scroll = 0
                    return True
            for key, r in self._sort_rects.items():
                if r.collidepoint(event.pos):
                    if self.sort_key == key:
                        self.sort_dir *= -1
                    else:
                        self.sort_key = key
                        self.sort_dir = 1 if key == "name" else -1
                    return True
            for ident, r in self._name_rects.items():
                if r.collidepoint(event.pos):
                    self._open_detail(*ident)
                    return True
            for ident, r in self._buy_rects.items():
                if r.collidepoint(event.pos):
                    self._do_buy(*ident)
                    return True
            for ident, r in self._sell_rects.items():
                if r.collidepoint(event.pos):
                    self._do_sell(*ident)
                    return True
            return False
        return False

    def update(self, dt):
        self._t += dt

    # ----------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._last_rect = rect
        surf.fill(config.COL_BG, rect)
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        pad = 16
        widgets.draw_text(surf, "BOUTIQUE — TOUS LES ACTIFS", (rect.x + pad, rect.y + 8),
                          fonts.head(bold=True), config.COL_AMBER)
        msg_line = ("Clic sur le nom = fiche · quantité puis ACHETER/VENDRE. " + self.msg) \
            if self.msg else "Clic sur le nom = fiche d'analyse · quantité puis ACHETER ou VENDRE."
        widgets.draw_text(surf, widgets.fit_text(msg_line, fonts.tiny(), rect.w - 2 * pad - 260),
                          (rect.x + pad, rect.y + 34), fonts.tiny(), config.COL_TEXT_DIM)
        st = PM.margin_status(p, self.market)
        widgets.draw_text(surf, f"PA {widgets.format_money(st['buying_power'], cur)}"
                                f" · levier {st['leverage']:.2f}x/{st['max_leverage']:.1f}x",
                          (rect.right - pad, rect.y + 10), fonts.tiny(bold=True),
                          config.COL_DOWN if st["margin_call"] else config.COL_TEXT_DIM, align="right")

        mp = pygame.mouse.get_pos()
        self._tooltip = None
        x0 = rect.x + pad
        top = rect.y + 54

        search_rect = pygame.Rect(x0, top, min(260, rect.w // 3), 24)
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN if self.text_focus == "search" else config.COL_BORDER,
                          search_rect, 1, border_radius=4)
        cursor = "_" if (self.text_focus == "search" and int(self._t * 2) % 2 == 0) else " "
        label = (self.search + cursor) if self.search else (cursor + "Rechercher…")
        scol = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 4), fonts.small(), scol)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 22, search_rect.y,
                                                   22, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        qx = search_rect.right + 16
        if qx < rect.right - 260:
            widgets.draw_text(surf, "QTÉ", (qx, top + 4), fonts.tiny(bold=True), config.COL_TEXT_DIM)
            qx += 34
            self._qty_minus = pygame.Rect(qx, top, 22, 24)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._qty_minus, border_radius=3)
            widgets.draw_text(surf, "-", self._qty_minus.center, fonts.small(bold=True),
                              config.COL_AMBER, align="center")
            self._qty_box = pygame.Rect(qx + 26, top, 60, 24)
            pygame.draw.rect(surf, config.COL_PANEL, self._qty_box, border_radius=4)
            pygame.draw.rect(surf, config.COL_AMBER if self.text_focus == "qty" else config.COL_BORDER,
                              self._qty_box, 1, border_radius=4)
            qcursor = "_" if (self.text_focus == "qty" and int(self._t * 2) % 2 == 0) else ""
            widgets.draw_text(surf, (self.qty_text or "0") + qcursor,
                              (self._qty_box.x + 6, self._qty_box.y + 4), fonts.small(), config.COL_TEXT)
            self._qty_plus = pygame.Rect(self._qty_box.right + 4, top, 22, 24)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._qty_plus, border_radius=3)
            widgets.draw_text(surf, "+", self._qty_plus.center, fonts.small(bold=True),
                              config.COL_AMBER, align="center")
            px = self._qty_plus.right + 12
            self._preset_rects = {}
            for val in QTY_PRESETS:
                wlabel = f"x{val}"
                w = fonts.tiny(bold=True).size(wlabel)[0] + 12
                if px + w > rect.right - pad:
                    break
                r = pygame.Rect(px, top + 1, w, 22)
                self._preset_rects[val] = r
                pygame.draw.rect(surf, config.COL_PANEL, r, border_radius=3)
                pygame.draw.rect(surf, config.COL_BORDER, r, 1, border_radius=3)
                widgets.draw_text(surf, wlabel, r.center, fonts.tiny(bold=True),
                                  config.COL_TEXT_DIM, align="center")
                px += w + 6
        else:
            self._qty_minus = self._qty_box = self._qty_plus = None
            self._preset_rects = {}

        self._type_rects, y = self._draw_chip_row(surf, x0, top + 30, rect.right - pad,
                                                   TYPE_CHIPS, self.type_filter, config.COL_AMBER)

        sub_opts = self._sub_options()
        if sub_opts:
            sub_chips = [(s, s) for s in sub_opts]
            self._sub_rects, y = self._draw_chip_row(surf, x0, y + 4, rect.right - pad,
                                                      sub_chips, self.sub_filter, config.COL_WARN)
        else:
            self._sub_rects = {}

        y += 6
        self._sort_rects = {}
        widgets.draw_text(surf, "TRIER :", (x0, y + 3), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        sx = x0 + 50
        for key, lbl in SORT_FIELDS:
            active = (self.sort_key == key)
            arrow = (" ▲" if self.sort_dir > 0 else " ▼") if active else ""
            full = lbl + arrow
            w = fonts.tiny(bold=True).size(full)[0] + 14
            if sx + w > rect.right - pad:
                break
            r = pygame.Rect(sx, y, w, 20)
            self._sort_rects[key] = r
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, full, r.center, fonts.tiny(bold=active),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            sx += w + 6
        y += 28

        rows = self._filtered_sorted()
        link_row_h = 32
        panel = pygame.Rect(x0, y, rect.right - pad - x0, rect.bottom - pad - link_row_h - y)
        if panel.h < 40:
            return
        inner = widgets.draw_panel(surf, panel, f"Catalogue ({len(rows)})", config.COL_CYAN)
        wide = inner.w >= 820
        cols = [("NOM", 0), ("TYPE", 200), ("POSSÉDÉ", 260), ("COURS", 340),
                ("VALEUR", 420), ("RENDEMENT", 520), ("VAR %", 610)]
        if wide:
            cols = [("NOM", 0), ("TYPE", 240), ("SECTEUR / CAT.", 310), ("POSSÉDÉ", 470),
                    ("COURS", 560), ("VALEUR", 650), ("RENDEMENT", 750), ("VAR %", 860)]
        for lbl, dx in cols:
            if inner.x + dx < inner.right - 140:
                widgets.draw_text(surf, lbl, (inner.x + dx, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)

        list_top = inner.y + 22
        list_area = pygame.Rect(inner.x - 6, list_top, inner.w + 12, inner.bottom - list_top - 22)
        self._list_rect = list_area
        self._row_list = rows
        self.row_cursor = min(self.row_cursor, len(rows) - 1) if rows else 0
        self._name_rects, self._buy_rects, self._sell_rects = {}, {}, {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        ry = list_top - self.scroll
        for i, r in enumerate(rows):
            if (list_area.top - ROW_H) < ry < list_area.bottom:
                self._draw_row(surf, r, ry, inner, cols, cur, mp, wide, i == self.row_cursor)
            ry += ROW_H
        surf.set_clip(prev_clip)

        content_h = (ry + self.scroll) - list_top
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, panel, list_area, self.scroll, self._max_scroll, content_h)

        if not self._can_trade():
            widgets.draw_text(surf, "⊘ Trading débloqué au grade Associate.",
                              (inner.x, inner.bottom - 4), fonts.tiny(), config.COL_TEXT_DIM)

        link_y = panel.bottom + 4
        lx = x0
        self._scene_link_rects = {}
        for scene_name, label in SCENE_LINKS:
            w = fonts.tiny(bold=True).size(label)[0] + 16
            if lx + w > rect.right - pad:
                break
            r = pygame.Rect(lx, link_y, w, 22)
            self._scene_link_rects[scene_name] = r
            hov = r.collidepoint(mp)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov else config.COL_PANEL, r, border_radius=4)
            pygame.draw.rect(surf, config.COL_CYAN, r, 1, border_radius=4)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=True), config.COL_CYAN, align="center")
            lx += w + 6

        self.popups_draw(surf)
        if self._tooltip:
            widgets.draw_tooltip(surf, *self._tooltip)

    def _draw_row(self, surf, r, y, inner, cols, cur, mp, wide, cursor=False):
        kind, key = r["kind"], r["key"]
        ident = (kind, key)
        live = self._live_quote(r)
        row_rect = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, ROW_H)
        if row_rect.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
        keynav.draw_focus_ring(surf, row_rect, cursor)
        kcol = KIND_COLOR.get(kind, config.COL_TEXT)
        name_w = min(cols[1][1] - 4, fonts.small(bold=True).size(r["name"])[0])
        self._name_rects[ident] = pygame.Rect(inner.x - 2, y - 2, name_w + 4, ROW_H - 4)
        widgets.draw_text(surf, widgets.fit_text(r["name"], fonts.small(bold=True), cols[1][1] - 4),
                          (inner.x, y), fonts.small(bold=True), kcol)
        col_map = {lbl: dx for lbl, dx in cols}
        widgets.draw_text(surf, KIND_LABEL.get(kind, kind), (inner.x + col_map["TYPE"], y),
                          fonts.tiny(bold=True), kcol)
        if wide:
            sub_txt = str(r["sub"])
            sub_fitted = widgets.fit_text(sub_txt, fonts.tiny(), 150)
            if sub_fitted != sub_txt:
                sub_rect = pygame.Rect(inner.x + col_map["SECTEUR / CAT."], y + 1, 150, ROW_H - 4)
                if sub_rect.collidepoint(mp):
                    self._tooltip = (sub_txt, mp)
            widgets.draw_text(surf, sub_fitted,
                              (inner.x + col_map["SECTEUR / CAT."], y + 1), fonts.tiny(), config.COL_TEXT_DIM)
        held = self._held_qty(kind, key)
        held_txt = f"{held:g}" if held else "—"
        widgets.draw_text(surf, held_txt, (inner.x + col_map["POSSÉDÉ"], y), fonts.small(bold=held > 0),
                          config.COL_AMBER if held > 0 else config.COL_TEXT_DIM)
        price = live["price"]
        price_txt = f"{price:,.2f}".replace(",", " ") if price is not None else "—"
        price_col = self._flash.tick(ident, price, config.COL_UP, config.COL_DOWN, config.COL_WHITE)
        widgets.draw_text(surf, price_txt, (inner.x + col_map["COURS"], y), fonts.small(), price_col)
        if kind == "Action":
            price_rect = pygame.Rect(inner.x + col_map["COURS"] - 4, y - 2, 80, ROW_H - 4)
            if price_rect.collidepoint(mp):
                tier = LIQ.equity_tier(self.market, key)
                self._tooltip = (f"Liquidité : {tier}.", mp)
        value_txt = widgets.format_money(live["value"], cur) if live["value"] is not None else "—"
        widgets.draw_text(surf, value_txt, (inner.x + col_map["VALEUR"], y), fonts.small(bold=True), config.COL_TEXT)
        if live["yield_pct"] is not None:
            ycol = config.COL_UP if live["yield_pct"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{live['yield_pct']:+.2f}%", (inner.x + col_map["RENDEMENT"], y), fonts.small(), ycol)
        else:
            widgets.draw_text(surf, "—", (inner.x + col_map["RENDEMENT"], y), fonts.small(), config.COL_TEXT_DIM)
        if live["change_pct"] is not None:
            vcol = config.COL_UP if live["change_pct"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{live['change_pct']:+.1f}%", (inner.x + col_map["VAR %"], y), fonts.small(bold=True), vcol)
        else:
            widgets.draw_text(surf, "—", (inner.x + col_map["VAR %"], y), fonts.small(), config.COL_TEXT_DIM)
        if self._can_trade():
            if held > 0:
                sr = pygame.Rect(inner.right - 138, y - 2, 60, 20)
                self._sell_rects[ident] = sr
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, sr, border_radius=3)
                widgets.draw_text(surf, "VENDRE", sr.center, fonts.tiny(bold=True), config.COL_DOWN, align="center")
            br = pygame.Rect(inner.right - 70, y - 2, 70, 20)
            self._buy_rects[ident] = br
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, br, border_radius=3)
            widgets.draw_text(surf, "ACHETER", br.center, fonts.tiny(bold=True), config.COL_UP, align="center")

    def _draw_chip_row(self, surf, x0, y0, x_max, chips, current, accent):
        rects = {}
        x, y = x0, y0
        for value, label in chips:
            w = fonts.tiny(bold=True).size(label)[0] + 14
            if x + w > x_max and x > x0:
                x = x0
                y += 24
            r = pygame.Rect(x, y, w, 20)
            rects[value] = r
            sel = (value == current)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, r, border_radius=3)
            pygame.draw.rect(surf, accent if sel else config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=sel),
                              accent if sel else config.COL_TEXT_DIM, align="center")
            x += w + 6
        return rects, y + 24
