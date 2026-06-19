"""
scene_alerts.py — Pose d'alertes de prix : recherche d'un actif, saisie d'un
seuil et liste des alertes actives (avec suppression). Réutilise la même
logique de validation/création que la commande ALERT du terminal. Ouvert via
ALERT/ALERTE/ALERTS/ALERTES sans argument (ou ALERT <tk> <prix> garde le
raccourci CLI rapide).
"""
import pygame

from core import config, unlocks
from core.scene_manager import Scene
from ui import fonts, widgets

ROW_H = 24


class AlertsScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.market = self.app.ensure_market()
        self.rows = self._build_dataset()
        self.search = ""
        self.text_focus = "search"   # "search" ou "price"
        self.price_text = ""
        self.sel_ticker = kwargs.get("ticker")
        self._t = 0.0
        self.scroll = 0
        self._max_scroll = 0
        self.row_cursor = 0
        self._row_list = []
        self._list_rect = None
        self._name_rects = {}
        self._search_box = None
        self._search_clear_rect = None
        self._price_box = None
        self._post_btn = None
        self._alerts_list_rect = None
        self._alerts_scroll = 0
        self._alerts_max_scroll = 0
        self._delete_rects = {}
        self.msg = ""
        self.back_btn = widgets.Button(config.back_button_rect(200),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    # --------------------------------------------------------------- helpers
    def _can_alert(self):
        return unlocks.unlocked(self.app.gs.player, "analyst")

    def _build_dataset(self):
        m = self.market
        rows = []
        for c in m.companies:
            tk = c["ticker"]
            mt = m.metrics(tk)
            if not mt:
                continue
            rows.append({"ticker": tk, "name": mt["name"], "sector": mt["sector"],
                        "price": mt["price"], "change_pct": mt["change_pct"]})
        rows.sort(key=lambda r: r["name"].lower())
        return rows

    def _filtered(self):
        q = self.search.strip().lower()
        if not q:
            return self.rows
        out = []
        for r in self.rows:
            hay = f"{r['name']} {r['ticker']} {r['sector']}".lower()
            if q in hay:
                out.append(r)
        return out

    def _post_alert(self):
        if not self._can_alert():
            self.msg = "⊘ Alertes débloquées au grade Analyst."
            return
        if not self.sel_ticker:
            self.msg = "Sélectionnez d'abord un actif dans la liste."
            return
        try:
            price = float(self.price_text.replace(",", "."))
        except ValueError:
            self.msg = "Seuil invalide : indiquez un nombre positif."
            return
        if price <= 0:
            self.msg = "Seuil invalide : indiquez un nombre positif."
            return
        cur_price = self.market.price_of(self.sel_ticker)
        if cur_price is None:
            self.msg = f"Aucune cotation pour {self.sel_ticker}."
            return
        self.market.track_company(self.sel_ticker)
        p = self.app.gs.player
        p.alerts.append({"ticker": self.sel_ticker, "price": price, "above": price > cur_price})
        sens = "au-dessus de" if price > cur_price else "en-dessous de"
        self.msg = f"Alerte posée : {self.sel_ticker} {sens} {price:.2f} (cours {cur_price:.2f})."
        self.price_text = ""

    def _remove_alert(self, idx):
        p = self.app.gs.player
        if 0 <= idx < len(p.alerts):
            a = p.alerts.pop(idx)
            self.msg = f"Alerte {a['ticker']} supprimée."

    def _select(self, ticker):
        self.sel_ticker = ticker
        self.text_focus = "price"

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
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.text_focus == "price" and self.price_text:
                    self.price_text = ""
                    return
                if self.search:
                    self.search = ""
                    return
                self.app.scenes.go(self.return_to)
                return
            elif event.key == pygame.K_TAB:
                self.text_focus = "price" if self.text_focus == "search" else "search"
                return
            elif event.key == pygame.K_BACKSPACE:
                if self.text_focus == "price":
                    self.price_text = self.price_text[:-1]
                else:
                    self.search = self.search[:-1]
                return
            elif event.key == pygame.K_PAGEUP:
                self.scroll = max(0, self.scroll - 200)
                return
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll = min(self._max_scroll, self.scroll + 200)
                return
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.text_focus == "price":
                self._post_alert()
                return
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER) \
                    and self.text_focus != "price":
                self.row_cursor, activate = widgets.list_key_nav(
                    event, self.row_cursor, len(self._row_list))
                if self._row_list:
                    self._scroll_to_cursor()
                if activate and self._row_list:
                    self._select(self._row_list[self.row_cursor]["ticker"])
                return
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                if self.text_focus == "price":
                    if event.unicode.isdigit() or (event.unicode in ".," and "." not in self.price_text
                                                    and "," not in self.price_text):
                        self.price_text += event.unicode
                else:
                    self.search += event.unicode
                    self.scroll = 0
                return

        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
            elif self._alerts_list_rect and self._alerts_list_rect.collidepoint(event.pos):
                self._alerts_scroll = max(0, min(self._alerts_max_scroll,
                                          self._alerts_scroll + (-48 if event.button == 4 else 48)))
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return
            if self._search_box and self._search_box.collidepoint(event.pos):
                self.text_focus = "search"
                return
            if self._price_box and self._price_box.collidepoint(event.pos):
                self.text_focus = "price"
                return
            if self._post_btn and self._post_btn.collidepoint(event.pos):
                self._post_alert()
                return
            for ticker, rect in self._name_rects.items():
                if rect.collidepoint(event.pos):
                    self._select(ticker)
                    return
            for idx, rect in self._delete_rects.items():
                if rect.collidepoint(event.pos):
                    self._remove_alert(idx)
                    return

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    # ----------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "ALERTES DE PRIX", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Choisissez un actif dans la liste, indiquez un seuil de cours, "
                                "puis posez l'alerte. " + (self.msg if self.msg else ""),
                          (42, 72), fonts.tiny(), config.COL_TEXT_DIM)

        mp = pygame.mouse.get_pos()
        x0 = 40
        top = config.content_top()

        # ---- recherche ----
        self._search_box = pygame.Rect(x0, top, 280, 24)
        pygame.draw.rect(surf, config.COL_PANEL, self._search_box, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN if self.text_focus == "search" else config.COL_BORDER,
                          self._search_box, 1, border_radius=4)
        cursor = "_" if (self.text_focus == "search" and int(self._t * 2) % 2 == 0) else " "
        label = (self.search + cursor) if self.search else (cursor + "Rechercher un actif (nom, ticker, secteur)…")
        scol = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), self._search_box.w - 30),
                          (self._search_box.x + 8, self._search_box.y + 4), fonts.small(), scol)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(self._search_box.right - 22, self._search_box.y,
                                                   22, self._search_box.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        # ---- actif sélectionné + seuil ----
        sx = self._search_box.right + 20
        if self.sel_ticker:
            sel_price = self.market.price_of(self.sel_ticker)
            ptxt = f"{sel_price:.2f}" if sel_price is not None else "—"
            widgets.draw_text(surf, f"ACTIF : {self.sel_ticker} (cours {ptxt})", (sx, top + 4),
                              fonts.tiny(bold=True), config.COL_WHITE)
        else:
            widgets.draw_text(surf, "ACTIF : aucun — cliquez une ligne ci-dessous", (sx, top + 4),
                              fonts.tiny(bold=True), config.COL_TEXT_DIM)
        sx2 = sx + 320
        widgets.draw_text(surf, "SEUIL :", (sx2, top + 4), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        self._price_box = pygame.Rect(sx2 + 56, top, 100, 24)
        pygame.draw.rect(surf, config.COL_PANEL, self._price_box, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER if self.text_focus == "price" else config.COL_BORDER,
                          self._price_box, 1, border_radius=4)
        pcursor = "_" if (self.text_focus == "price" and int(self._t * 2) % 2 == 0) else ""
        widgets.draw_text(surf, (self.price_text or "0") + pcursor,
                          (self._price_box.x + 8, self._price_box.y + 4), fonts.small(), config.COL_TEXT)

        self._post_btn = pygame.Rect(self._price_box.right + 16, top, 170, 24)
        can = self._can_alert()
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._post_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER if can else config.COL_BORDER, self._post_btn, 1, border_radius=4)
        widgets.draw_text(surf, "POSER L'ALERTE", self._post_btn.center, fonts.tiny(bold=True),
                          config.COL_AMBER if can else config.COL_TEXT_DIM, align="center")
        if not can:
            widgets.draw_text(surf, "⊘ Alertes débloquées au grade Analyst.",
                              (self._post_btn.right + 16, top + 4), fonts.tiny(), config.COL_TEXT_DIM)

        ph = config.footer_y() - 8 - (top + 36)
        ptop = top + 36

        # ---- liste des actifs (gauche) ----
        listp = pygame.Rect(x0, ptop, 700, ph)
        linner = widgets.draw_panel(surf, listp, "Actifs", config.COL_CYAN)
        rows = self._filtered()
        list_area = pygame.Rect(linner.x - 6, linner.y, linner.w + 12, linner.h)
        self._list_rect = list_area
        self._row_list = rows
        self.row_cursor = min(self.row_cursor, len(rows) - 1) if rows else 0
        self._name_rects = {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        ry = linner.y - self.scroll
        for i, r in enumerate(rows):
            if (list_area.top - ROW_H) < ry < list_area.bottom:
                self._draw_row(surf, r, ry, linner, mp, i == self.row_cursor)
            ry += ROW_H
        surf.set_clip(prev_clip)
        content_h = (ry + self.scroll) - linner.y
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        widgets.draw_scrollbar(surf, listp, list_area, self.scroll, self._max_scroll, content_h)

        # ---- alertes actives (droite) ----
        p = self.app.gs.player
        rightp = pygame.Rect(x0 + 720, ptop, config.SCREEN_WIDTH - 40 - (x0 + 720), ph)
        rinner = widgets.draw_panel(surf, rightp, f"Alertes actives ({len(p.alerts)})", config.COL_AMBER)
        self._delete_rects = {}
        if not p.alerts:
            widgets.draw_text(surf, "Aucune alerte active.", (rinner.x, rinner.y),
                              fonts.small(), config.COL_TEXT_DIM)
            self._alerts_list_rect = None
            self._alerts_max_scroll = 0
        else:
            alerts_area = pygame.Rect(rinner.x - 6, rinner.y, rinner.w + 12, rinner.h)
            self._alerts_list_rect = alerts_area
            prev_clip2 = surf.get_clip()
            surf.set_clip(alerts_area)
            ay = rinner.y - self._alerts_scroll
            for idx, a in enumerate(p.alerts):
                if (alerts_area.top - ROW_H) < ay < alerts_area.bottom:
                    self._draw_alert_row(surf, idx, a, ay, rinner, mp)
                ay += ROW_H
            surf.set_clip(prev_clip2)
            acontent_h = (ay + self._alerts_scroll) - rinner.y
            self._alerts_max_scroll = max(0, acontent_h - alerts_area.h)
            self._alerts_scroll = min(self._alerts_scroll, self._alerts_max_scroll)
            widgets.draw_scrollbar(surf, rightp, alerts_area, self._alerts_scroll,
                                   self._alerts_max_scroll, acontent_h)

        self.back_btn.draw(surf)

    def _draw_row(self, surf, r, y, inner, mp, cursor=False):
        tk = r["ticker"]
        row_rect = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, ROW_H)
        if row_rect.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
        if tk == self.sel_ticker:
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect)
            pygame.draw.rect(surf, config.COL_AMBER, (row_rect.x, row_rect.y, 3, row_rect.h))
        widgets.draw_row_selection(surf, row_rect, cursor)
        self._name_rects[tk] = row_rect
        widgets.draw_text(surf, tk, (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, widgets.fit_text(r["name"], fonts.small(), 220),
                          (inner.x + 60, y), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, widgets.fit_text(r["sector"], fonts.tiny(), 150),
                          (inner.x + 300, y + 1), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{r['price']:,.2f}".replace(",", " "), (inner.x + 460, y),
                          fonts.small(), config.COL_WHITE)
        if r["change_pct"] is not None:
            vcol = config.COL_UP if r["change_pct"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{r['change_pct']:+.1f}%", (inner.x + 560, y),
                              fonts.small(bold=True), vcol)

    def _draw_alert_row(self, surf, idx, a, y, inner, mp):
        row_rect = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, ROW_H)
        if row_rect.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row_rect, border_radius=3)
        widgets.draw_text(surf, a["ticker"], (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
        sens = "↑" if a["above"] else "↓"
        widgets.draw_text(surf, f"{sens} {a['price']:.2f}", (inner.x + 70, y),
                          fonts.small(), config.COL_TEXT)
        cur = self.market.price_of(a["ticker"])
        ctxt = f"{cur:.2f}" if cur is not None else "—"
        widgets.draw_text(surf, f"cours {ctxt}", (inner.x + 170, y), fonts.small(), config.COL_TEXT_DIM)
        del_rect = pygame.Rect(inner.right - 26, y - 2, 22, 20)
        self._delete_rects[idx] = del_rect
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, del_rect, border_radius=3)
        widgets.draw_text(surf, "✕", del_rect.center, fonts.small(bold=True), config.COL_DOWN, align="center")
