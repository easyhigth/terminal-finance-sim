"""
app_explorer.py — Application « Explorateur de marché » du bureau (NATIVE).

Migration de `scenes/scene_explorer.py` (rendu hébergé 1280×720 réduit par
smoothscale → flou, cf. apps/scene_host.py) vers une app dessinée à la
résolution de sa fenêtre — la vue unifiée de tout l'univers investissable
(actions, ETF, obligations, commodities, crypto, FX, gouvernements) avec
recherche/filtres/tri et sélection multiple vers les listes de suivi. Comme
Boutique/Fiche société, CHAQUE ouverture RECONFIGURE la fenêtre existante
(`configure(**kwargs)` — recherche/filtres pré-remplis si fournis, ex. le
lien croisé Boutique ↔ Explorateur qui conserve le contexte). Les fiches
d'actif restent des popups flottants (`ui/popups.py::PopupMixin`,
repositionnés relativement à LA FENÊTRE) ; FX et Gouvernements ouvrent leurs
écrans dédiés (encore hébergés) EN FENÊTRE via `desktop._open_scene_window`.
La scène plein écran reste enregistrée (fallback/tests) ; l'ouverture EN
FENÊTRE de "explorer" est redirigée ici (cf. DesktopScene._open_scene_window).
"""
import pygame

from core import bonds as B
from core import commodities as C
from core import config, intraday
from core import crypto as CRY
from core import etfs as ETF
from core import fx as FX
from core import governments as GOV
from core import unlocks as unlocks_mod

from apps.base import DesktopApp
from ui import fonts, keynav, widgets
from ui.popups import PopupMixin

ROW_H = 24
SORT_FIELDS = [("name", "NOM"), ("price", "COURS"), ("value", "VALEUR"),
               ("yield_pct", "RENDEMENT"), ("change_pct", "VAR %")]
TYPE_CHIPS = [(None, "TOUTES"), ("Action", "ACTIONS"), ("ETF", "ETF"),
              ("Obligation", "OBLIGATIONS"), ("Commodity", "COMMODITIES"),
              ("Crypto", "CRYPTO"), ("FX", "FX"), ("Gouvernement", "GOUVERNEMENTS")]
KIND_COLOR = {"Action": config.COL_AMBER, "ETF": config.COL_PRESTIGE,
              "Obligation": config.COL_CYAN,
              "Commodity": config.COL_WARN, "Crypto": config.COL_UP,
              "FX": config.COL_DOWN, "Gouvernement": config.COL_PRESTIGE}
KIND_LABEL = {"Action": "Action", "ETF": "ETF", "Obligation": "Oblig.",
              "Commodity": "Cmdty", "Crypto": "Crypto", "FX": "FX",
              "Gouvernement": "Gouv."}
WATCHLIST_ATTR = {"Action": "watchlist", "Obligation": "bond_watchlist",
                   "Commodity": "commodity_watchlist", "Gouvernement": "gov_watchlist"}
WATCHLIST_CAP = {"Action": 10}


class ExplorerApp(DesktopApp, PopupMixin):
    title = "Explorateur de marché"
    icon_kind = "explorer"
    default_size = (1120, 680)
    min_size = (760, 480)

    def on_open(self):
        self.configure()

    def reenter(self, **kwargs):
        self.configure(**kwargs)

    def configure(self, search="", type_filter=None, region_filter=None,
                  sub_filter=None, **_kwargs):
        # **_kwargs absorbe silencieusement un éventuel "return_to" hérité
        # des anciens appelants de la scène hébergée.
        self.market = self.app.ensure_market()
        self.init_popups()
        self.rows = self._build_dataset()
        self.search = search
        self._t = 0.0
        self.type_filter = type_filter
        self.region_filter = region_filter
        self.sub_filter = sub_filter
        self.sort_key = "value"
        self.sort_dir = -1
        self.selected = set()
        self.last_idx = None
        self.row_cursor = 0
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self._row_rects = {}
        self._row_list = []
        self._row_index = {}
        self._type_rects = {}
        self._region_rects = {}
        self._sub_rects = {}
        self._sort_rects = {}
        self._search_clear_rect = None
        self._add_rect = None
        self._shop_rect = None
        self._flash = widgets.TickFlash()
        self._last_rect = pygame.Rect(0, 0, 1, 1)

    def _popup_pos(self):
        """Cascade relative à CETTE fenêtre plutôt qu'à l'écran entier."""
        n = len(self.popups)
        offset = 24 * (n % 6)
        r = self._last_rect
        return (r.x + 30 + offset, r.y + 30 + offset)

    def refresh_data(self):
        self.market = self.app.ensure_market()
        self.rows = self._build_dataset()

    # ------------------------------------------------------------- dataset
    def _build_dataset(self):
        m = self.market
        rows = []
        for c in m.companies:
            tk = c["ticker"]
            mt = m.metrics(tk)
            if not mt:
                continue
            rows.append({
                "kind": "Action", "key": tk, "ticker": tk, "name": mt["name"],
                "sub": mt["sector"], "region": mt["region"],
                "price": mt["price"], "value": mt["mktcap"] * 1e6,
                "yield_pct": mt["div_yield"] * 100.0, "change_pct": mt["change_pct"],
            })
        for q in B.all_quotes(m):
            rows.append({
                "kind": "Obligation", "key": q["id"], "ticker": None, "name": q["name"],
                "sub": q["kind"], "region": q["region"],
                "price": q["price"], "value": q["price"],
                "yield_pct": q["ytm"] * 100.0, "change_pct": None,
            })
        for q in C.all_quotes(m):
            rows.append({
                "kind": "Commodity", "key": q["id"], "ticker": None, "name": q["name"],
                "sub": q["category"], "region": None,
                "price": q["front"], "value": q["front"] * C.MULTIPLIER,
                "yield_pct": q["roll_yield"] * 100.0, "change_pct": None,
            })
        for q in ETF.all_quotes(m):
            rows.append({
                "kind": "ETF", "key": q["id"], "ticker": q["id"], "name": q["name"],
                "sub": q["category_label"], "region": None,
                "price": q["price"], "value": q["price"],
                "yield_pct": q["yield"] * 100.0, "change_pct": q["change_pct"],
            })
        for q in CRY.all_quotes(m):
            rows.append({
                "kind": "Crypto", "key": q["id"], "ticker": None, "name": q["name"],
                "sub": "Stablecoin" if q["stable"] else "Crypto-actif", "region": None,
                "price": q["spot"], "value": q["spot"],
                "yield_pct": (q["yield"] * 100.0) if q["yield"] else None, "change_pct": None,
            })
        for q in FX.all_quotes(m):
            if not q["ok"]:
                continue
            rows.append({
                "kind": "FX", "key": q["pair"], "ticker": None, "name": q["pair"],
                "sub": "Paire de change", "region": None,
                "price": q["spot"], "value": q["spot"],
                "yield_pct": None, "change_pct": None,
            })
        best_by_gov = {}
        for q in B.all_quotes(m):
            if q["kind"] != "Souverain" or not q["gov"]:
                continue
            cur = best_by_gov.get(q["gov"])
            if cur is None or q["years"] > cur["years"]:
                best_by_gov[q["gov"]] = q
        for g in GOV.GOVERNMENTS:
            rep = best_by_gov.get(g["code"])
            rows.append({
                "kind": "Gouvernement", "key": g["code"], "ticker": None, "name": g["name"],
                "sub": g["rating"], "region": g["region"],
                "price": None, "value": None,
                "yield_pct": (rep["ytm"] * 100.0) if rep else None, "change_pct": None,
            })
        return rows

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
            q = C.quote(m, key)
            if q:
                price = q["front"]
                value = q["front"] * C.MULTIPLIER
                yield_pct = q["roll_yield"] * 100.0
        elif kind == "Crypto":
            q = CRY.quote(m, key)
            if q:
                price = q["spot"]
                value = q["spot"]
                yield_pct = (q["yield"] * 100.0) if q["yield"] else None
        return {"price": price, "value": value, "yield_pct": yield_pct,
                "change_pct": change_pct}

    # --------------------------------------------------------------- helpers
    def _can_watch(self):
        return unlocks_mod.unlocked(self.app.gs.player, "analyst")

    def _sub_options(self):
        if self.type_filter == "Action":
            return list(self.market.sectors)
        if self.type_filter == "Commodity":
            seen = []
            for cid, name, sp, dr, vol, sl, cat in C.COMMODITIES:
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
            if self.region_filter and r["region"] != self.region_filter:
                continue
            if self.sub_filter and r["sub"] != self.sub_filter:
                continue
            if q:
                hay = f"{r['name']} {r['key']} {r['sub']} {r['region'] or ''}".lower()
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

    def _quick_add(self, kind, key):
        p = self.app.gs.player
        if not self._can_watch():
            g = unlocks_mod.effective_required_grade(p, "analyst")
            self.app.notify(f"Watchlist verrouillée (débloqué au grade {config.GRADES[g]}).", "warn")
            return
        attr = WATCHLIST_ATTR.get(kind)
        if attr is None:
            self.app.notify(f"{kind} se consulte via sa fiche (clic), pas de watchlist dédiée.", "info")
            return
        lst = getattr(p, attr)
        if key in lst:
            self.app.notify(f"{key} est déjà dans la liste de suivi.", "info")
            return
        cap = WATCHLIST_CAP.get(kind)
        if cap and len(lst) >= cap:
            self.app.notify(f"Limite de {cap} atteinte — retirez-en un avant d'en ajouter un autre.", "warn")
            return
        lst.append(key)
        if kind == "Action":
            self.market.track_company(key)
        self.app.notify(f"{key} ajouté à la liste de suivi.", "good")

    def _bulk_add(self):
        p = self.app.gs.player
        if not self._can_watch():
            g = unlocks_mod.effective_required_grade(p, "analyst")
            self.app.notify(f"Watchlist verrouillée (débloqué au grade {config.GRADES[g]}).", "warn")
            return
        added, dup, capped = 0, 0, 0
        for kind, key in sorted(self.selected):
            attr = WATCHLIST_ATTR.get(kind)
            if attr is None:
                continue
            lst = getattr(p, attr)
            if key in lst:
                dup += 1
                continue
            cap = WATCHLIST_CAP.get(kind)
            if cap and len(lst) >= cap:
                capped += 1
                continue
            lst.append(key)
            if kind == "Action":
                self.market.track_company(key)
            added += 1
        self.selected.clear()
        if added:
            extra = []
            if dup:
                extra.append(f"{dup} déjà présente(s)")
            if capped:
                extra.append(f"{capped} refusée(s) (limite atteinte)")
            suffix = f" ({', '.join(extra)})" if extra else ""
            self.app.notify(f"{added} actif(s) ajouté(s) à la liste de suivi.{suffix}", "good")
        elif capped:
            self.app.notify("Limite de watchlist atteinte pour la sélection.", "warn")
        elif dup:
            self.app.notify("Sélection déjà entièrement suivie.", "info")

    # --------------------------------------------------------------- events
    def handle_event(self, event, rect):
        self._last_rect = rect
        if self.popups_handle_event(event):
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f and (event.mod & pygame.KMOD_CTRL):
                self.scroll = 0
                return True
            if event.key == pygame.K_ESCAPE:
                if self.popups_close_top():
                    return True
                if self.search:
                    self.search = ""
                    return True
                if self.selected:
                    self.selected.clear()
                    return True
                return False
            if event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                return True
            if event.key == pygame.K_PAGEUP:
                self.scroll = max(0, self.scroll - 200)
                return True
            if event.key == pygame.K_PAGEDOWN:
                self.scroll = min(self._max_scroll, self.scroll + 200)
                return True
            if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.row_cursor, activate = widgets.list_key_nav(
                    event, self.row_cursor, len(self._row_list))
                if self._row_list:
                    self._scroll_to_cursor()
                if activate and self._row_list:
                    r = self._row_list[self.row_cursor]
                    self._handle_row_click((r["kind"], r["key"]), 1)
                return True
            from core import clipboard
            if clipboard.is_paste_shortcut(event):
                self.search += clipboard.paste().replace("\n", " ").strip()
                self.scroll = 0
                return True
            if event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search += event.unicode
                self.scroll = 0
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            if event.button == 1 and self._add_rect and self._add_rect.collidepoint(event.pos):
                if self.selected:
                    self._bulk_add()
                return True
            if event.button == 1 and self._shop_rect and self._shop_rect.collidepoint(event.pos):
                if self.desktop is not None:
                    self.desktop._open_scene_window("shop", search=self.search,
                                                    type_filter=self.type_filter,
                                                    sub_filter=self.sub_filter)
                return True
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return True
            for val, r in self._type_rects.items():
                if r.collidepoint(event.pos):
                    self.type_filter = val
                    self.sub_filter = None
                    self.scroll = 0
                    return True
            for val, r in self._region_rects.items():
                if r.collidepoint(event.pos):
                    self.region_filter = val
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
            for ident, r in self._row_rects.items():
                if r.collidepoint(event.pos):
                    self._handle_row_click(ident, event.button)
                    return True
            return False
        return False

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

    def _handle_row_click(self, ident, button):
        kind, key = ident
        idx = self._row_index.get(ident)
        if button == 3:
            self._quick_add(kind, key)
            return
        mods = pygame.key.get_mods()
        if mods & pygame.KMOD_CTRL:
            if ident in self.selected:
                self.selected.discard(ident)
            else:
                self.selected.add(ident)
            self.last_idx = idx
            return
        if mods & pygame.KMOD_SHIFT and self.last_idx is not None and idx is not None:
            lo, hi = sorted((self.last_idx, idx))
            for r in self._row_list[lo:hi + 1]:
                self.selected.add((r["kind"], r["key"]))
            self.last_idx = idx
            return
        self.last_idx = idx
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
        elif kind == "FX":
            if self.desktop is not None:
                self.desktop._open_scene_window("fx")
        elif kind == "Gouvernement":
            if self.desktop is not None:
                self.desktop._open_scene_window("governments", focus=key)

    def update(self, dt):
        self._t += dt

    # ----------------------------------------------------------------- draw
    def draw(self, surf, rect):
        self._last_rect = rect
        surf.fill(config.COL_BG, rect)
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        pad = 14
        widgets.draw_text(surf, "EXPLORATEUR DE MARCHÉ", (rect.x + pad, rect.y + 8),
                          fonts.head(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, widgets.fit_text(
            "clic = détail · Ctrl+clic / Shift+clic = sélection · clic droit = ajout rapide",
            fonts.tiny(), rect.w - 2 * pad - 240),
                          (rect.x + pad, rect.y + 34), fonts.tiny(), config.COL_TEXT_DIM)
        # boutons haut-droit : + AJOUTER (sélection) et SHOP (contexte conservé)
        self._shop_rect = pygame.Rect(rect.right - pad - 60, rect.y + 8, 60, 22)
        hov = self._shop_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_PANEL if hov else config.COL_PANEL_HEAD,
                         self._shop_rect, border_radius=3)
        pygame.draw.rect(surf, config.COL_CYAN, self._shop_rect, 1, border_radius=3)
        widgets.draw_text(surf, "SHOP", self._shop_rect.center, fonts.tiny(bold=True),
                          config.COL_CYAN, align="center")
        add_label = f"+ AJOUTER ({len(self.selected)})" if self.selected else "+ AJOUTER"
        aw = fonts.tiny(bold=True).size(add_label)[0] + 16
        self._add_rect = pygame.Rect(self._shop_rect.x - aw - 8, rect.y + 8, aw, 22)
        acol = config.COL_UP if self.selected else config.COL_TEXT_DIM
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._add_rect, border_radius=3)
        pygame.draw.rect(surf, acol, self._add_rect, 1, border_radius=3)
        widgets.draw_text(surf, add_label, self._add_rect.center, fonts.tiny(bold=True),
                          acol, align="center")

        mp = pygame.mouse.get_pos()
        x0 = rect.x + pad
        top = rect.y + 58

        search_rect = pygame.Rect(x0, top, min(260, rect.w // 3), 24)
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else (cursor + "Rechercher…")
        col = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 4), fonts.small(), col)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 22, search_rect.y, 22, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        self._type_rects, y = self._draw_chip_row(surf, search_rect.right + 12, top,
                                                   rect.right - pad, TYPE_CHIPS,
                                                   self.type_filter, config.COL_AMBER)
        y = max(y, top + 28)
        region_chips = [(None, "TOUTES")] + [(r, r) for r in self.market.regions]
        self._region_rects, y = self._draw_chip_row(surf, x0, y + 2, rect.right - pad,
                                                     region_chips, self.region_filter, config.COL_CYAN)
        sub_opts = self._sub_options()
        if sub_opts:
            sub_chips = [(s, s) for s in sub_opts]
            self._sub_rects, y = self._draw_chip_row(surf, x0, y + 2, rect.right - pad,
                                                      sub_chips, self.sub_filter, config.COL_WARN)
        else:
            self._sub_rects = {}

        y += 6
        self._sort_rects = {}
        widgets.draw_text(surf, "TRIER :", (x0, y + 3), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        sx = x0 + 52
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
        y += 26

        filtered = self._filtered_sorted()
        panel = pygame.Rect(x0, y, rect.right - pad - x0, rect.bottom - pad - y)
        if panel.h < 50:
            self.popups_draw(surf)
            return
        inner = widgets.draw_panel(surf, panel, f"Résultats ({len(filtered)})", config.COL_CYAN)
        wide = inner.w >= 900
        if wide:
            cols = [("NOM", 0), ("TYPE", 270), ("SECTEUR / CAT.", 350), ("RÉGION", 540),
                    ("COURS", 650), ("VALEUR", 750), ("RENDEMENT", 870), ("VAR %", 990)]
        else:
            cols = [("NOM", 0), ("TYPE", 210), ("RÉGION", 280),
                    ("COURS", 380), ("VALEUR", 470), ("RENDEMENT", 580), ("VAR %", 670)]
        for lbl, dx in cols:
            if inner.x + dx < inner.right - 40:
                widgets.draw_text(surf, lbl, (inner.x + dx, inner.y), fonts.tiny(bold=True),
                                  config.COL_TEXT_DIM)

        list_top = inner.y + 22
        list_area = pygame.Rect(inner.x - 6, list_top, inner.w + 12, inner.bottom - list_top - 20)
        self._list_rect = list_area
        self._row_list = filtered
        self._row_index = {(r["kind"], r["key"]): i for i, r in enumerate(filtered)}
        self.row_cursor = min(self.row_cursor, len(filtered) - 1) if filtered else 0
        self._row_rects = {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        ry = list_top - self.scroll
        for i, r in enumerate(filtered):
            visible = (list_area.top - ROW_H) < ry < list_area.bottom
            if visible:
                self._draw_row(surf, r, ry, inner, cols, cur, mp, wide, i == self.row_cursor)
            ry += ROW_H
        surf.set_clip(prev_clip)

        content_h = (ry + self.scroll) - list_top
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, panel, list_area, self.scroll,
                                              self._max_scroll, content_h)

        sel_txt = (f"{len(self.selected)} sélectionnée(s)" if self.selected
                   else "Aucune sélection" if self._can_watch()
                   else f"Sélection : débloqué au grade "
                        f"{config.GRADES[unlocks_mod.effective_required_grade(p, 'analyst')]}")
        widgets.draw_text(surf, sel_txt, (inner.x, inner.bottom - 6), fonts.tiny(), config.COL_TEXT_DIM)
        self.popups_draw(surf)

    def _draw_row(self, surf, r, y, inner, cols, cur, mp, wide, cursor=False):
        kind, key = r["kind"], r["key"]
        ident = (kind, key)
        live = self._live_quote(r)
        row_rect = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, ROW_H)
        self._row_rects[ident] = row_rect
        selected = ident in self.selected
        if selected:
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_UP, row_rect, 1, border_radius=3)
        elif row_rect.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
        keynav.draw_focus_ring(surf, row_rect, cursor)
        kcol = KIND_COLOR.get(kind, config.COL_TEXT)
        col_map = {lbl: dx for lbl, dx in cols}
        name_w = col_map["TYPE"] - 10
        widgets.draw_text(surf, widgets.fit_text(r["name"], fonts.small(bold=True), name_w),
                          (inner.x, y), fonts.small(bold=True), kcol)
        widgets.draw_text(surf, KIND_LABEL.get(kind, kind), (inner.x + col_map["TYPE"], y),
                          fonts.tiny(bold=True), kcol)
        if wide:
            widgets.draw_text(surf, widgets.fit_text(str(r["sub"]), fonts.tiny(), 180),
                              (inner.x + col_map["SECTEUR / CAT."], y + 1), fonts.tiny(),
                              config.COL_TEXT_DIM)
        widgets.draw_text(surf, r["region"] or "—", (inner.x + col_map["RÉGION"], y),
                          fonts.tiny(), config.COL_TEXT)
        price = live["price"]
        price_txt = f"{price:,.2f}".replace(",", " ") if price is not None else "—"
        price_col = self._flash.tick(ident, price, config.COL_UP, config.COL_DOWN, config.COL_WHITE)
        widgets.draw_text(surf, price_txt, (inner.x + col_map["COURS"], y), fonts.small(), price_col)
        value_txt = widgets.format_money(live["value"], cur) if live["value"] is not None else "—"
        widgets.draw_text(surf, value_txt, (inner.x + col_map["VALEUR"], y),
                          fonts.small(bold=True), config.COL_TEXT)
        if live["yield_pct"] is not None:
            ycol = config.COL_UP if live["yield_pct"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{live['yield_pct']:+.2f}%", (inner.x + col_map["RENDEMENT"], y),
                              fonts.small(), ycol)
        else:
            widgets.draw_text(surf, "—", (inner.x + col_map["RENDEMENT"], y), fonts.small(),
                              config.COL_TEXT_DIM)
        if live["change_pct"] is not None:
            vcol = config.COL_UP if live["change_pct"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{live['change_pct']:+.1f}%", (inner.x + col_map["VAR %"], y),
                              fonts.small(bold=True), vcol)
        else:
            widgets.draw_text(surf, "—", (inner.x + col_map["VAR %"], y), fonts.small(),
                              config.COL_TEXT_DIM)

    def _draw_chip_row(self, surf, x0, y0, x_max, chips, current, accent):
        rects = {}
        x, y = x0, y0
        for value, label in chips:
            w = fonts.tiny(bold=True).size(label)[0] + 16
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
