"""
scene_shop.py — Boutique unifiée : achat de tout actif investissable en un
seul écran (actions, ETF, obligations souveraines/corporate, commodities,
crypto, produits structurés/titrisation). Recherche, filtre par type, tri,
quantité libre (pas seulement des paquets fixes), indicateurs clés par
ligne (dont la quantité déjà possédée). Cliquer sur le NOM d'un actif
ouvre uniquement sa fiche d'analyse en popup, jamais une scène dédiée.
Une rangée de boutons en bas mène vers les scènes dédiées par type
d'actif, et un bouton permet d'aller/revenir vers l'EXPLORATEUR en
conservant la recherche et le filtre de type. Ouvert via SHOP.
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
from core.scene_manager import Scene
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


class ShopScene(Scene, PopupMixin):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.init_popups()
        self.rows = self._build_dataset()
        self.search = kwargs.get("search", "")
        self.text_focus = "search"     # "search" ou "qty"
        self.qty_text = "10"
        self._t = 0.0
        self.type_filter = kwargs.get("type_filter")
        self.sub_filter = kwargs.get("sub_filter")
        self.sort_key = "value"
        self.sort_dir = -1
        self.scroll = 0
        self._max_scroll = 0
        self.row_cursor = 0  # curseur clavier dans la liste filtrée/triée
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
        # flash vert/rouge des cours en direct (tickers animés intraday)
        self._flash = widgets.TickFlash()
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.explorer_btn = widgets.Button((config.back_button_rect(160)[0] + 170,
                                            config.back_button_rect(160)[1], 170, 42),
                                           "EXPLORATEUR", config.COL_CYAN)

    def refresh_data(self):
        """Reconstruit le catalogue (cours/positions à jour) sans toucher à
        la recherche/au filtre/au tri/au scroll en cours."""
        self.market = self.app.ensure_market()
        self.rows = self._build_dataset()

    # --------------------------------------------------------------- live data
    def _live_quote(self, r):
        """Retourne les valeurs live (prix animé, valeur, rendement, var) pour
        une ligne du catalogue. Les actions utilisent le chemin de prix
        canonique intraday ; les autres classes retombent sur leur quote
        officielle (rafraîchie à chaque pas). Le tri reste figé sur les
        valeurs de `self.rows` pour éviter une liste qui oscille."""
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
        # Structuré / Crédit : prix fixes par lot, pas de live
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
        """Options de filtre secondaire (secteur/catégorie) selon le TYPE choisi
        (même logique que scenes/scene_explorer.py::_sub_options)."""
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
        """Ajuste le scroll pour garder la ligne sélectionnée au clavier visible."""
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
    def handle_event(self, event):
        if self.popups_handle_event(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f and (event.mod & pygame.KMOD_CTRL):
                # CTRL+F façon navigateur : (re)donne le focus de saisie au
                # champ de recherche (utile si on tapait dans QUANTITÉ) et
                # remonte en haut de la liste filtrée.
                self.text_focus = "search"
                self.scroll = 0
                return
            if event.key == pygame.K_ESCAPE:
                if self.popups_close_top():
                    return
                if self.text_focus == "qty":
                    self.text_focus = "search"
                    return
                if self.search:
                    self.search = ""
                    return
                self.app.scenes.back(self.return_to)
                return
            elif event.key == pygame.K_BACKSPACE:
                if self.text_focus == "qty":
                    self.qty_text = self.qty_text[:-1]
                else:
                    self.search = self.search[:-1]
                return
            elif event.key == pygame.K_PAGEUP:
                self.scroll = max(0, self.scroll - 200)
                return
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll = min(self._max_scroll, self.scroll + 200)
                return
            elif event.key == pygame.K_TAB:
                self.text_focus = "qty" if self.text_focus == "search" else "search"
                return
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER) \
                    and self.text_focus != "qty":
                self.row_cursor, activate = widgets.list_key_nav(
                    event, self.row_cursor, len(self._row_list))
                if self._row_list:
                    self._scroll_to_cursor()
                if activate and self._row_list:
                    r = self._row_list[self.row_cursor]
                    self._open_detail(r["kind"], r["key"])
                return
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                if self.text_focus == "qty":
                    if event.unicode.isdigit() or (event.unicode == "." and "." not in self.qty_text):
                        self.qty_text += event.unicode
                else:
                    self.search += event.unicode
                    self.scroll = 0
                return

        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
            return
        if self.explorer_btn.handle(event):
            self.app.scenes.go("explorer", return_to="shop", search=self.search,
                               type_filter=self.type_filter, sub_filter=self.sub_filter)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for scene_name, rect in self._scene_link_rects.items():
                if rect.collidepoint(event.pos):
                    self.app.scenes.go(scene_name, return_to="shop")
                    return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            for ident, rect in self._name_rects.items():
                if rect.collidepoint(event.pos):
                    self._open_detail(*ident)
                    return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return
            if self._qty_box and self._qty_box.collidepoint(event.pos):
                self.text_focus = "qty"
                return
            if self._qty_minus and self._qty_minus.collidepoint(event.pos):
                self.qty_text = f"{max(0.0, self._qty() - 1):g}"
                return
            if self._qty_plus and self._qty_plus.collidepoint(event.pos):
                self.qty_text = f"{self._qty() + 1:g}"
                return
            for val, rect in self._preset_rects.items():
                if rect.collidepoint(event.pos):
                    self.qty_text = f"{val:g}"
                    return
            self.text_focus = "search"
            for val, rect in self._type_rects.items():
                if rect.collidepoint(event.pos):
                    self.type_filter = val
                    self.sub_filter = None
                    self.scroll = 0
                    return
            for val, rect in self._sub_rects.items():
                if rect.collidepoint(event.pos):
                    self.sub_filter = None if self.sub_filter == val else val
                    self.scroll = 0
                    return
            for key, rect in self._sort_rects.items():
                if rect.collidepoint(event.pos):
                    if self.sort_key == key:
                        self.sort_dir *= -1
                    else:
                        self.sort_key = key
                        self.sort_dir = 1 if key == "name" else -1
                    return
            for ident, rect in self._name_rects.items():
                if rect.collidepoint(event.pos):
                    self._open_detail(*ident)
                    return
            for ident, rect in self._buy_rects.items():
                if rect.collidepoint(event.pos):
                    self._do_buy(*ident)
                    return
            for ident, rect in self._sell_rects.items():
                if rect.collidepoint(event.pos):
                    self._do_sell(*ident)
                    return

    def _focus_hints(self):
        enter_key = _L("ENTRÉE", "ENTER")
        esc_key = _L("ÉCHAP", "ESC")
        if self.text_focus == "qty":
            return [("TAB", _L("recherche", "search")), (_L("chiffres", "digits"), _L("quantité", "quantity")),
                    (esc_key, _L("recherche", "search"))]
        return [("↑↓", _L("actifs", "assets")), (enter_key, _L("ouvrir", "open")),
                ("TAB", _L("quantité", "quantity")), (_L("lettres", "letters"), _L("filtrer", "filter"))]

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)
        self.explorer_btn.update(pygame.mouse.get_pos(), dt)

    # ----------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        widgets.draw_text(surf, "BOUTIQUE — TOUS LES ACTIFS", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Actions · ETF · obligations · commodities · crypto · structurés · crédit — "
                                "clic sur le nom = fiche d'analyse · choisissez une quantité puis ACHETER "
                                "ou VENDRE (positions détenues). "
                                + (self.msg if self.msg else ""),
                          (42, 72), fonts.tiny(), config.COL_TEXT_DIM)
        st = PM.margin_status(p, self.market)
        widgets.draw_text(surf, f"Pouvoir d'achat {widgets.format_money(st['buying_power'], cur)}"
                                f" · levier {st['leverage']:.2f}x / {st['max_leverage']:.1f}x max",
                          (config.SCREEN_WIDTH - 40, 26), fonts.small(bold=True),
                          config.COL_DOWN if st["margin_call"] else config.COL_TEXT_DIM, align="right")

        mp = pygame.mouse.get_pos()
        self._tooltip = None
        x0 = 40
        top = config.content_top()

        # ---- recherche ----
        search_rect = pygame.Rect(x0, top, 280, 24)
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN if self.text_focus == "search" else config.COL_BORDER,
                          search_rect, 1, border_radius=4)
        cursor = "_" if (self.text_focus == "search" and int(self._t * 2) % 2 == 0) else " "
        label = (self.search + cursor) if self.search else (cursor + "Tapez pour rechercher (nom, ticker, secteur)…")
        scol = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 4), fonts.small(), scol)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 22, search_rect.y,
                                                   22, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        # ---- quantité ----
        qx = search_rect.right + 20
        widgets.draw_text(surf, "QUANTITÉ :", (qx, top + 4), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        qx += 78
        self._qty_minus = pygame.Rect(qx, top, 22, 24)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._qty_minus, border_radius=3)
        widgets.draw_text(surf, "-", self._qty_minus.center, fonts.small(bold=True),
                          config.COL_AMBER, align="center")
        self._qty_box = pygame.Rect(qx + 26, top, 70, 24)
        pygame.draw.rect(surf, config.COL_PANEL, self._qty_box, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER if self.text_focus == "qty" else config.COL_BORDER,
                          self._qty_box, 1, border_radius=4)
        qcursor = "_" if (self.text_focus == "qty" and int(self._t * 2) % 2 == 0) else ""
        widgets.draw_text(surf, (self.qty_text or "0") + qcursor, (self._qty_box.x + 8, self._qty_box.y + 4),
                          fonts.small(), config.COL_TEXT)
        self._qty_plus = pygame.Rect(self._qty_box.right + 4, top, 22, 24)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._qty_plus, border_radius=3)
        widgets.draw_text(surf, "+", self._qty_plus.center, fonts.small(bold=True),
                          config.COL_AMBER, align="center")
        px = self._qty_plus.right + 16
        self._preset_rects = {}
        for val in QTY_PRESETS:
            wlabel = f"x{val}"
            w = fonts.tiny(bold=True).size(wlabel)[0] + 14
            rect = pygame.Rect(px, top + 1, w, 22)
            self._preset_rects[val] = rect
            pygame.draw.rect(surf, config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, wlabel, rect.center, fonts.tiny(bold=True),
                              config.COL_TEXT_DIM, align="center")
            px += w + 6

        # ---- chips TYPE ----
        self._type_rects, y = self._draw_chip_row(surf, x0, top + 30, config.SCREEN_WIDTH - 40,
                                                   TYPE_CHIPS, self.type_filter, config.COL_AMBER)

        # ---- chips SECTEUR / CATÉGORIE (dynamiques selon le TYPE) ----
        sub_opts = self._sub_options()
        if sub_opts:
            sub_chips = [(s, s) for s in sub_opts]
            self._sub_rects, y = self._draw_chip_row(surf, x0, y + 4, config.SCREEN_WIDTH - 40,
                                                      sub_chips, self.sub_filter, config.COL_WARN)
        else:
            self._sub_rects = {}

        # ---- boutons de tri ----
        y += 6
        self._sort_rects = {}
        widgets.draw_text(surf, "TRIER :", (x0, y + 3), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        sx0 = x0 + 56
        sx = sx0
        for key, lbl in SORT_FIELDS:
            active = (self.sort_key == key)
            arrow = (" ▲" if self.sort_dir > 0 else " ▼") if active else ""
            full = lbl + arrow
            w = fonts.tiny(bold=True).size(full)[0] + 16
            rect = pygame.Rect(sx, y, w, 20)
            self._sort_rects[key] = rect
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, full, rect.center, fonts.tiny(bold=active),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            sx += w + 6
        y += 28

        rows = self._filtered_sorted()
        panel_bottom_reserve = 8 + 34  # place pour la rangée de boutons "scènes liées"
        panel = pygame.Rect(x0, y, config.SCREEN_WIDTH - 80,
                            config.footer_y() - panel_bottom_reserve - y)
        inner = widgets.draw_panel(surf, panel, f"Catalogue ({len(rows)})", config.COL_CYAN)
        cols = [("NOM", 0), ("TYPE", 240), ("SECTEUR / CAT.", 310), ("POSSÉDÉ", 470),
                ("COURS", 560), ("VALEUR", 650), ("RENDEMENT", 750), ("VAR %", 860)]
        for lbl, dx in cols:
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
                self._draw_row(surf, r, ry, inner, cols, cur, mp, i == self.row_cursor)
            ry += ROW_H
        surf.set_clip(prev_clip)

        content_h = (ry + self.scroll) - list_top
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, panel, list_area, self.scroll, self._max_scroll, content_h)

        if not self._can_trade():
            widgets.draw_text(surf, "⊘ Trading débloqué au grade Associate.",
                              (inner.x, inner.bottom - 4), fonts.tiny(), config.COL_TEXT_DIM)

        # ---- rangée de liens vers les scènes dédiées par type d'actif ----
        link_y = panel.bottom + 4
        lx = x0
        self._scene_link_rects = {}
        for scene_name, label in SCENE_LINKS:
            w = fonts.tiny(bold=True).size(label)[0] + 18
            rect = pygame.Rect(lx, link_y, w, 24)
            self._scene_link_rects[scene_name] = rect
            hov = rect.collidepoint(mp)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov else config.COL_PANEL, rect, border_radius=4)
            pygame.draw.rect(surf, config.COL_CYAN, rect, 1, border_radius=4)
            widgets.draw_text(surf, label, rect.center, fonts.tiny(bold=True), config.COL_CYAN, align="center")
            lx += w + 8

        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14), self._focus_hints())
        self.back_btn.draw(surf)
        self.explorer_btn.draw(surf)
        self.popups_draw(surf)
        if self._tooltip:
            widgets.draw_tooltip(surf, *self._tooltip)

    def _draw_row(self, surf, r, y, inner, cols, cur, mp, cursor=False):
        kind, key = r["kind"], r["key"]
        ident = (kind, key)
        live = self._live_quote(r)
        row_rect = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, ROW_H)
        if row_rect.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
        keynav.draw_focus_ring(surf, row_rect, cursor)
        kcol = KIND_COLOR.get(kind, config.COL_TEXT)
        name_w = min(225, fonts.small(bold=True).size(r["name"])[0])
        self._name_rects[ident] = pygame.Rect(inner.x - 2, y - 2, name_w + 4, ROW_H - 4)
        widgets.draw_text(surf, widgets.fit_text(r["name"], fonts.small(bold=True), 225),
                          (inner.x, y), fonts.small(bold=True), kcol)
        widgets.draw_text(surf, KIND_LABEL.get(kind, kind), (inner.x + cols[1][1], y),
                          fonts.tiny(bold=True), kcol)
        sub_txt = str(r["sub"])
        sub_fitted = widgets.fit_text(sub_txt, fonts.tiny(), 150)
        if sub_fitted != sub_txt:
            sub_rect = pygame.Rect(inner.x + cols[2][1], y + 1, 150, ROW_H - 4)
            if sub_rect.collidepoint(mp):
                self._tooltip = (sub_txt, mp)
        widgets.draw_text(surf, sub_fitted,
                          (inner.x + cols[2][1], y + 1), fonts.tiny(), config.COL_TEXT_DIM)
        held = self._held_qty(kind, key)
        held_txt = f"{held:g}" if held else "—"
        widgets.draw_text(surf, held_txt, (inner.x + cols[3][1], y), fonts.small(bold=held > 0),
                          config.COL_AMBER if held > 0 else config.COL_TEXT_DIM)
        price = live["price"]
        price_txt = f"{price:,.2f}".replace(",", " ") if price is not None else "—"
        price_col = self._flash.tick(ident, price, config.COL_UP, config.COL_DOWN, config.COL_WHITE)
        widgets.draw_text(surf, price_txt, (inner.x + cols[4][1], y), fonts.small(), price_col)
        if kind == "Action":
            price_rect = pygame.Rect(inner.x + cols[4][1] - 4, y - 2, 80, ROW_H - 4)
            if price_rect.collidepoint(mp):
                tier = LIQ.equity_tier(self.market, key)
                self._tooltip = (f"Liquidité : {tier} (selon la capitalisation). "
                                  "Tier moins liquide = spread et impact de marché plus élevés "
                                  "sur les gros ordres.", mp)
        value_txt = widgets.format_money(live["value"], cur) if live["value"] is not None else "—"
        widgets.draw_text(surf, value_txt, (inner.x + cols[5][1], y), fonts.small(bold=True), config.COL_TEXT)
        if live["yield_pct"] is not None:
            ycol = config.COL_UP if live["yield_pct"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{live['yield_pct']:+.2f}%", (inner.x + cols[6][1], y), fonts.small(), ycol)
        else:
            widgets.draw_text(surf, "—", (inner.x + cols[6][1], y), fonts.small(), config.COL_TEXT_DIM)
        if live["change_pct"] is not None:
            vcol = config.COL_UP if live["change_pct"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{live['change_pct']:+.1f}%", (inner.x + cols[7][1], y), fonts.small(bold=True), vcol)
        else:
            widgets.draw_text(surf, "—", (inner.x + cols[7][1], y), fonts.small(), config.COL_TEXT_DIM)
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
            rect = pygame.Rect(x, y, w, 20)
            rects[value] = rect
            sel = (value == current)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, accent if sel else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, label, rect.center, fonts.tiny(bold=sel),
                              accent if sel else config.COL_TEXT_DIM, align="center")
            x += w + 6
        return rects, y + 24
