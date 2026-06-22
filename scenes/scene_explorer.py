"""
scene_explorer.py — Explorateur de marché global ("univers d'investissement").

Vue unifiée et filtrable de TOUT l'univers investissable : actions (roster de
sociétés), ETF (dont les familles thématiques/ESG, cf. core/etfs.py CATEGORIES),
obligations (souverains + corporate = crédit), commodities (futures), crypto
et FX (paires de change), ainsi que les gouvernements (souverains). Recherche
libre, filtres (type / continent / secteur ou catégorie selon le type) et tri
(nom / cours / valeur / rendement / variation, croissant ou décroissant).

Interactions sur n'importe quelle ligne (Action / ETF / Obligation / Commodity /
Crypto / FX / Gouvernement) :
  - clic gauche  : ouvre la fiche flottante de l'actif (PopupMixin) — pour un
                   gouvernement, ouvre directement l'écran GOV (fiche pays déjà
                   riche, pas besoin de popup) ;
  - Ctrl+clic     : ajoute/retire la ligne de la sélection multiple ;
  - Shift+clic    : sélectionne toute la plage entre le dernier clic et celui-ci ;
  - clic droit    : ajoute directement l'actif à la liste de suivi correspondante
                   (watchlist actions/obligations/commodities/pays).
Le bouton « + AJOUTER » envoie toute la sélection courante vers ces listes.
La watchlist actions est plafonnée à 10 lignes (accès rapide, cf. WATCHLIST
dans le terminal) ; les autres listes ne sont pas plafonnées.

Ouvert via EXPLORE, ou en cliquant le titre du panneau « Entreprises » du
terminal.
"""
import pygame

from core import bonds as B
from core import commodities as C
from core import config
from core import crypto as CRY
from core import etfs as ETF
from core import fx as FX
from core import governments as GOV
from core import unlocks as unlocks_mod
from core.scene_manager import Scene
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


class MarketExplorerScene(Scene, PopupMixin):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.init_popups()
        self.rows = self._build_dataset()
        self.search = kwargs.get("search", "")
        self._t = 0.0
        self.type_filter = kwargs.get("type_filter")
        self.region_filter = kwargs.get("region_filter")
        self.sub_filter = kwargs.get("sub_filter")
        self.sort_key = "value"
        self.sort_dir = -1
        self.selected = set()
        self.last_idx = None
        self.row_cursor = 0  # curseur clavier dans la liste filtrée/triée
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
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.add_btn = widgets.Button((220, config.SCREEN_HEIGHT - 50, 220, 42),
                                      "+ AJOUTER", config.COL_UP, enabled=False)
        self.shop_btn = widgets.Button((460, config.SCREEN_HEIGHT - 50, 180, 42),
                                       "🛒 SHOP", config.COL_CYAN)

    def refresh_data(self):
        """Reconstruit le catalogue (cours/positions à jour) sans toucher à
        la recherche/aux filtres/au tri/au scroll en cours."""
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

    # --------------------------------------------------------------- helpers
    def _can_watch(self):
        return unlocks_mod.unlocked(self.app.gs.player, "analyst")

    def _sub_options(self):
        """Options de filtre secondaire (secteur/catégorie/type) selon le TYPE choisi."""
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
    def handle_event(self, event):
        if self.popups_handle_event(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.popups_close_top():
                    return
                if self.search:
                    self.search = ""
                    return
                if self.selected:
                    self.selected.clear()
                    return
                self.app.scenes.go(self.return_to)
                return
            elif event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                return
            elif event.key == pygame.K_PAGEUP:
                self.scroll = max(0, self.scroll - 200)
                return
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll = min(self._max_scroll, self.scroll + 200)
                return
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.row_cursor, activate = widgets.list_key_nav(
                    event, self.row_cursor, len(self._row_list))
                if self._row_list:
                    self._scroll_to_cursor()
                if activate and self._row_list:
                    r = self._row_list[self.row_cursor]
                    self._handle_row_click((r["kind"], r["key"]), 1)
                return
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search += event.unicode
                self.scroll = 0
                return

        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if self.add_btn.handle(event):
            self._bulk_add()
            return
        if self.shop_btn.handle(event):
            self.app.scenes.go("shop", return_to="explorer", search=self.search,
                               type_filter=self.type_filter)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return
            for val, rect in self._type_rects.items():
                if rect.collidepoint(event.pos):
                    self.type_filter = val
                    self.sub_filter = None
                    self.scroll = 0
                    return
            for val, rect in self._region_rects.items():
                if rect.collidepoint(event.pos):
                    self.region_filter = val
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
            for ident, rect in self._row_rects.items():
                if rect.collidepoint(event.pos):
                    self._handle_row_click(ident, event.button)
                    return

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
            self.app.scenes.go("fx", return_to="explorer")
        elif kind == "Gouvernement":
            self.app.scenes.go("governments", return_to="explorer", focus=key)

    def update(self, dt):
        self._t += dt
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.add_btn.label = f"+ AJOUTER ({len(self.selected)})" if self.selected else "+ AJOUTER"
        self.add_btn.enabled = bool(self.selected)
        self.add_btn.update(mp, dt)
        self.shop_btn.update(mp, dt)

    # ----------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        widgets.draw_text(surf, "EXPLORATEUR DE MARCHÉ", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Actions · ETF (dont thèmes ESG) · obligations/crédit/souverains · "
                                "commodities · crypto · FX — clic = détail · "
                                "Ctrl+clic / Shift+clic = sélection · clic droit = ajout rapide",
                          (42, 72), fonts.tiny(), config.COL_TEXT_DIM)

        mp = pygame.mouse.get_pos()
        x0 = 40
        top = config.content_top()

        # ---- recherche ----
        search_rect = pygame.Rect(x0, top, 300, 24)
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else (cursor + "Tapez pour rechercher (nom, ticker, secteur)…")
        col = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 4), fonts.small(), col)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 22, search_rect.y, 22, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        # ---- chips TYPE ----
        self._type_rects, _ = self._draw_chip_row(surf, x0 + 310, top, config.SCREEN_WIDTH - 40,
                                                   TYPE_CHIPS, self.type_filter, config.COL_AMBER)

        # ---- chips RÉGION ----
        region_chips = [(None, "TOUTES")] + [(r, r) for r in self.market.regions]
        self._region_rects, y = self._draw_chip_row(surf, x0, top + 30, config.SCREEN_WIDTH - 40,
                                                     region_chips, self.region_filter, config.COL_CYAN)

        # ---- chips SECTEUR / CATÉGORIE (dynamiques selon le TYPE) ----
        sub_opts = self._sub_options()
        if sub_opts:
            sub_chips = [(s, s) for s in sub_opts]
            self._sub_rects, y = self._draw_chip_row(surf, x0, y + 4, config.SCREEN_WIDTH - 40,
                                                      sub_chips, self.sub_filter, config.COL_WARN)
        else:
            self._sub_rects = {}

        # ---- boutons de tri ----
        y += 8
        self._sort_rects = {}
        x_max = config.SCREEN_WIDTH - 40
        widgets.draw_text(surf, "TRIER :", (x0, y + 3), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        sx0 = x0 + 56
        sx, sy = sx0, y
        for key, label in SORT_FIELDS:
            active = (self.sort_key == key)
            arrow = (" ▲" if self.sort_dir > 0 else " ▼") if active else ""
            full = label + arrow
            w = fonts.tiny(bold=True).size(full)[0] + 16
            if sx + w > x_max and sx > sx0:
                sx = sx0
                sy += 24
            rect = pygame.Rect(sx, sy, w, 20)
            self._sort_rects[key] = rect
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, full, rect.center, fonts.tiny(bold=active),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            sx += w + 6
        y = sy + 28

        # ---- panneau résultats ----
        filtered = self._filtered_sorted()
        panel = pygame.Rect(x0, y, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - y)
        inner = widgets.draw_panel(surf, panel, f"Résultats ({len(filtered)})", config.COL_CYAN)
        cols = [("NOM", 0), ("TYPE", 270), ("SECTEUR / CAT.", 350), ("RÉGION", 540),
                ("COURS", 650), ("VALEUR", 750), ("RENDEMENT", 870), ("VAR %", 990)]
        for label, dx in cols:
            widgets.draw_text(surf, label, (inner.x + dx, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)

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
                self._draw_row(surf, r, ry, inner, cols, cur, mp, i == self.row_cursor)
            ry += ROW_H
        surf.set_clip(prev_clip)

        content_h = (ry + self.scroll) - list_top
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        if self._max_scroll > 0:
            track = pygame.Rect(panel.right - 8, list_area.y, 6, list_area.h)
            pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=3)
            frac = list_area.h / (content_h or 1)
            bar_h = max(24, int(list_area.h * frac))
            bar_y = list_area.y + int((list_area.h - bar_h) * (self.scroll / self._max_scroll))
            pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 6, bar_h), border_radius=3)

        sel_txt = (f"{len(self.selected)} sélectionnée(s)" if self.selected
                   else "Aucune sélection" if self._can_watch()
                   else f"Sélection : débloqué au grade "
                        f"{config.GRADES[unlocks_mod.effective_required_grade(self.app.gs.player, 'analyst')]}")
        widgets.draw_text(surf, sel_txt, (inner.x, inner.bottom - 6), fonts.tiny(), config.COL_TEXT_DIM)

        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14),
                              [("↑↓", "naviguer"), ("ENTRÉE", "détail")])
        self.back_btn.draw(surf)
        self.add_btn.draw(surf)
        self.shop_btn.draw(surf)
        self.popups_draw(surf)

    def _draw_row(self, surf, r, y, inner, cols, cur, mp, cursor=False):
        kind, key = r["kind"], r["key"]
        row_rect = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, ROW_H)
        self._row_rects[(kind, key)] = row_rect
        selected = (kind, key) in self.selected
        if selected:
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_UP, row_rect, 1, border_radius=3)
        elif row_rect.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
        keynav.draw_focus_ring(surf, row_rect, cursor)
        kcol = KIND_COLOR.get(kind, config.COL_TEXT)
        c0 = cols[0][1]
        widgets.draw_text(surf, widgets.fit_text(r["name"], fonts.small(bold=True), 260),
                          (inner.x + c0, y), fonts.small(bold=True), kcol)
        widgets.draw_text(surf, KIND_LABEL.get(kind, kind), (inner.x + cols[1][1], y),
                          fonts.tiny(bold=True), kcol)
        widgets.draw_text(surf, widgets.fit_text(str(r["sub"]), fonts.tiny(), 180),
                          (inner.x + cols[2][1], y + 1), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, r["region"] or "—", (inner.x + cols[3][1], y), fonts.small(), config.COL_TEXT)
        price_txt = f"{r['price']:,.2f}".replace(",", " ") if r["price"] is not None else "—"
        widgets.draw_text(surf, price_txt, (inner.x + cols[4][1], y), fonts.small(), config.COL_WHITE)
        value_txt = widgets.format_money(r["value"], cur) if r["value"] is not None else "—"
        widgets.draw_text(surf, value_txt, (inner.x + cols[5][1], y), fonts.small(bold=True), config.COL_TEXT)
        if r["yield_pct"] is not None:
            ycol = config.COL_UP if r["yield_pct"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{r['yield_pct']:+.2f}%", (inner.x + cols[6][1], y), fonts.small(), ycol)
        else:
            widgets.draw_text(surf, "—", (inner.x + cols[6][1], y), fonts.small(), config.COL_TEXT_DIM)
        if r["change_pct"] is not None:
            vcol = config.COL_UP if r["change_pct"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{r['change_pct']:+.1f}%", (inner.x + cols[7][1], y), fonts.small(bold=True), vcol)
        else:
            widgets.draw_text(surf, "—", (inner.x + cols[7][1], y), fonts.small(), config.COL_TEXT_DIM)

    def _draw_chip_row(self, surf, x0, y0, x_max, chips, current, accent):
        """Dessine une rangée de chips (avec retour à la ligne). Retourne (rects, bottom_y)."""
        rects = {}
        x, y = x0, y0
        for value, label in chips:
            w = fonts.tiny(bold=True).size(label)[0] + 16
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
