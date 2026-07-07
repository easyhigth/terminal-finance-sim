"""
app_alerts.py — Application « Alertes de prix » du bureau (NATIVE).

Même refonte que l'Inbox (apps/app_inbox.py) : la scène plein écran
`scenes/scene_alerts.py` hébergée en fenêtre était rendue en 1280×720 puis
réduite (floue) ; cette app dessine à la résolution de la fenêtre. Reprend
la même logique de pose/suppression (core/alerts, verrou de grade
« analyst ») et le même vocabulaire (PRIX ABS. / VARIATION % / TRAILING %).
La scène reste enregistrée (compat hors bureau) ; l'ouverture EN FENÊTRE
est redirigée ici (cf. DesktopScene._open_scene_window).
"""
import pygame

from apps.base import DesktopApp
from core import alerts as ALERTS
from core import config, unlocks
from scenes.scene_alerts import _ALERT_KINDS
from ui import fonts, widgets

ROW_H = 24


class AlertsApp(DesktopApp):
    title = "Alertes de prix"
    icon_kind = "alert"
    default_size = (900, 540)
    min_size = (560, 340)

    def on_open(self):
        self.market = self.app.ensure_market()
        self.rows = self._build_dataset()
        self.search = ""
        self.text_focus = "search"     # "search" ou "price"
        self.price_text = ""
        self.kind = "level"            # "level" | "pct" | "trailing"
        self.sel_ticker = None
        self.msg = ""
        self._t = 0.0
        self.scroll = 0
        self._max_scroll = 0
        self._alerts_scroll = 0
        self._alerts_max_scroll = 0
        self._list_rect = None
        self._alerts_list_rect = None
        self._name_rects = {}
        self._delete_rects = {}
        self._kind_rects = {}
        self._search_box = None
        self._search_clear_rect = None
        self._price_box = None
        self._post_btn = None

    def preselect(self, ticker):
        """Pré-sélectionne un actif (navigation `alerts` avec ticker)."""
        if ticker:
            self.sel_ticker = ticker
            self.text_focus = "price"

    # --------------------------------------------------------------- données
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
        return [r for r in self.rows
                if q in f"{r['name']} {r['ticker']} {r['sector']}".lower()]

    def _post_alert(self):
        if not self._can_alert():
            g = unlocks.effective_required_grade(self.app.gs.player, "analyst")
            self.msg = f"⊘ Alertes débloquées au grade {config.GRADES[g]}."
            return
        if not self.sel_ticker:
            self.msg = "Sélectionnez d'abord un actif dans la liste."
            return
        value = self.price_text.replace(",", ".")
        r = ALERTS.place(self.app.gs.player, self.market, self.sel_ticker, self.kind, value)
        if not r["ok"]:
            self.msg = {
                "ticker": "Ticker inconnu.",
                "price": "Aucune cotation pour cet actif.",
                "value": "Seuil invalide : indiquez un nombre positif.",
                "kind": "Type d'alerte invalide.",
            }.get(r["reason"], f"Refusé ({r['reason']}).")
            return
        a = r["alert"]
        self.market.track_company(self.sel_ticker)
        if self.kind == "level":
            sens = "au-dessus de" if a["above"] else "en-dessous de"
            self.msg = f"Alerte posée : {a['ticker']} {sens} {a['value']:.2f}."
        elif self.kind == "pct":
            sign = "hausse" if a["above"] else "baisse"
            self.msg = f"Alerte posée : {a['ticker']} sur {sign} de {a['value']:.1f}%."
        else:
            self.msg = f"Stop suiveur posé sur {a['ticker']} à {a['value']:.1f}%."
        self.price_text = ""

    def update(self, dt):
        self._t += dt

    # --------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.text_focus == "price" and self.price_text:
                    self.price_text = ""
                    return True
                if self.search:
                    self.search = ""
                    return True
                return False
            if event.key == pygame.K_TAB:
                self.text_focus = "price" if self.text_focus == "search" else "search"
                return True
            if event.key == pygame.K_BACKSPACE:
                if self.text_focus == "price":
                    self.price_text = self.price_text[:-1]
                else:
                    self.search = self.search[:-1]
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.text_focus == "price":
                self._post_alert()
                return True
            if event.unicode and event.unicode.isprintable():
                if self.text_focus == "price":
                    allow_minus = self.kind == "pct"
                    valid = (event.unicode.isdigit()
                             or (event.unicode in ".," and "." not in self.price_text
                                 and "," not in self.price_text)
                             or (allow_minus and event.unicode == "-" and not self.price_text))
                    if valid:
                        self.price_text += event.unicode
                else:
                    self.search += event.unicode
                    self.scroll = 0
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            delta = -48 if event.button == 4 else 48
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll, self.scroll + delta))
                return True
            if self._alerts_list_rect and self._alerts_list_rect.collidepoint(event.pos):
                self._alerts_scroll = max(0, min(self._alerts_max_scroll,
                                                 self._alerts_scroll + delta))
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return True
            if self._search_box and self._search_box.collidepoint(event.pos):
                self.text_focus = "search"
                return True
            if self._price_box and self._price_box.collidepoint(event.pos):
                self.text_focus = "price"
                return True
            if self._post_btn and self._post_btn.collidepoint(event.pos):
                self._post_alert()
                return True
            for kind, r in self._kind_rects.items():
                if r.collidepoint(event.pos):
                    self.kind = kind
                    self.price_text = ""
                    return True
            for tk, r in self._name_rects.items():
                if r.collidepoint(event.pos):
                    self.sel_ticker = tk
                    self.text_focus = "price"
                    return True
            for aid, r in self._delete_rects.items():
                if r.collidepoint(event.pos):
                    self.msg = ("Alerte supprimée." if ALERTS.cancel(self.app.gs.player, aid)
                                else "Alerte introuvable.")
                    return True
        return False

    # ----------------------------------------------------------------- draw
    def draw(self, surf, rect):
        surf.fill(config.COL_PANEL, rect)
        pad = 10
        p = self.app.gs.player
        mp = pygame.mouse.get_pos()
        widgets.draw_text(surf, "ALERTES DE PRIX", (rect.x + pad, rect.y + pad),
                          fonts.small(bold=True), config.COL_AMBER)
        if self.sel_ticker:
            price = self.market.price_of(self.sel_ticker)
            ptxt = f"{price:.2f}" if price is not None else "—"
            widgets.draw_text(surf, f"ACTIF : {self.sel_ticker} (cours {ptxt})",
                              (rect.x + pad + 150, rect.y + pad), fonts.tiny(bold=True),
                              config.COL_WHITE)
        else:
            widgets.draw_text(surf, "ACTIF : aucun — cliquez une ligne",
                              (rect.x + pad + 150, rect.y + pad), fonts.tiny(),
                              config.COL_TEXT_DIM)

        # ligne 1 : recherche + type d'alerte
        y1 = rect.y + pad + 20
        self._search_box = pygame.Rect(rect.x + pad, y1, min(240, rect.w // 3), 24)
        pygame.draw.rect(surf, config.COL_BG, self._search_box, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN if self.text_focus == "search" else config.COL_BORDER,
                         self._search_box, 1, border_radius=4)
        cursor = "_" if (self.text_focus == "search" and int(self._t * 2) % 2 == 0) else " "
        label = (self.search + cursor) if self.search else (cursor + "Rechercher un actif…")
        scol = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), self._search_box.w - 30),
                          (self._search_box.x + 8, self._search_box.y + 4), fonts.small(), scol)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(self._search_box.right - 22,
                                                  self._search_box.y, 22, self._search_box.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center,
                              fonts.small(bold=True), config.COL_TEXT_DIM, align="center")
        self._kind_rects = {}
        kx = self._search_box.right + 10
        for kind, klabel in _ALERT_KINDS:
            w = max(70, fonts.tiny(bold=True).size(klabel)[0] + 12)
            r = pygame.Rect(kx, y1 + 2, w, 20)
            self._kind_rects[kind] = r
            active = self.kind == kind
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if active else config.COL_BG, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, klabel, r.center, fonts.tiny(bold=True),
                              config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
            kx += w + 6

        # ligne 2 : seuil + POSER + message
        y2 = y1 + 30
        unit = "%" if self.kind in ("pct", "trailing") else "prix"
        widgets.draw_text(surf, f"SEUIL ({unit}) :", (rect.x + pad, y2 + 4),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        self._price_box = pygame.Rect(rect.x + pad + 100, y2, 80, 24)
        pygame.draw.rect(surf, config.COL_BG, self._price_box, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER if self.text_focus == "price" else config.COL_BORDER,
                         self._price_box, 1, border_radius=4)
        pcursor = "_" if (self.text_focus == "price" and int(self._t * 2) % 2 == 0) else ""
        widgets.draw_text(surf, (self.price_text or "0") + pcursor,
                          (self._price_box.x + 8, self._price_box.y + 4),
                          fonts.small(), config.COL_TEXT)
        self._post_btn = pygame.Rect(self._price_box.right + 10, y2, 150, 24)
        can = self._can_alert()
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._post_btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_AMBER if can else config.COL_BORDER,
                         self._post_btn, 1, border_radius=4)
        widgets.draw_text(surf, "POSER L'ALERTE", self._post_btn.center, fonts.tiny(bold=True),
                          config.COL_AMBER if can else config.COL_TEXT_DIM, align="center")
        info = self.msg
        if not can and not info:
            g = unlocks.effective_required_grade(p, "analyst")
            info = f"⊘ Alertes débloquées au grade {config.GRADES[g]}."
        if info:
            widgets.draw_text(surf, widgets.fit_text(info, fonts.tiny(),
                                                     rect.right - pad - self._post_btn.right - 16),
                              (self._post_btn.right + 10, y2 + 5), fonts.tiny(), config.COL_TEXT_DIM)

        # panneaux : actifs (gauche) / alertes actives (droite)
        top = y2 + 32
        panes = pygame.Rect(rect.x + pad, top, rect.w - 2 * pad, rect.bottom - top - pad)
        list_w = max(280, int(panes.w * 0.56))
        list_area = pygame.Rect(panes.x, panes.y, list_w, panes.h)
        alerts_area = pygame.Rect(list_area.right + 8, panes.y,
                                  panes.right - list_area.right - 8, panes.h)
        pygame.draw.rect(surf, config.COL_BG, list_area)
        pygame.draw.rect(surf, config.COL_BORDER, list_area, 1)
        self._list_rect = list_area
        rows = self._filtered()
        self._name_rects = {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        ry = list_area.y + 2 - self.scroll
        for r in rows:
            if (list_area.top - ROW_H) < ry < list_area.bottom:
                self._draw_asset_row(surf, r, ry, list_area, mp)
            ry += ROW_H
        surf.set_clip(prev_clip)
        content_h = len(rows) * ROW_H + 4
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, list_area, list_area, self.scroll,
                                             self._max_scroll, content_h)

        pygame.draw.rect(surf, config.COL_BG, alerts_area)
        pygame.draw.rect(surf, config.COL_BORDER, alerts_area, 1)
        alerts = getattr(p, "alerts", None) or []
        widgets.draw_text(surf, f"ACTIVES ({len(alerts)})", (alerts_area.x + 8, alerts_area.y + 4),
                          fonts.tiny(bold=True), config.COL_AMBER)
        self._delete_rects = {}
        inner = pygame.Rect(alerts_area.x, alerts_area.y + 22, alerts_area.w,
                            alerts_area.h - 24)
        self._alerts_list_rect = inner
        if not alerts:
            widgets.draw_text(surf, "Aucune alerte active.", (inner.x + 8, inner.y + 4),
                              fonts.tiny(), config.COL_TEXT_DIM)
            self._alerts_max_scroll = 0
        else:
            prev_clip = surf.get_clip()
            surf.set_clip(inner)
            ay = inner.y + 2 - self._alerts_scroll
            for a in alerts:
                if (inner.top - ROW_H) < ay < inner.bottom:
                    self._draw_alert_row(surf, a, ay, inner, mp)
                ay += ROW_H
            surf.set_clip(prev_clip)
            acontent_h = len(alerts) * ROW_H + 4
            self._alerts_max_scroll = max(0, acontent_h - inner.h)
            self._alerts_scroll = min(self._alerts_scroll, self._alerts_max_scroll)
            self._alerts_scroll = widgets.draw_scrollbar(surf, inner, inner, self._alerts_scroll,
                                                         self._alerts_max_scroll, acontent_h)

    def _draw_asset_row(self, surf, r, y, area, mp):
        tk = r["ticker"]
        row = pygame.Rect(area.x + 2, y, area.w - 4, ROW_H - 2)
        self._name_rects[tk] = row
        if row.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
        if tk == self.sel_ticker:
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row)
            pygame.draw.rect(surf, config.COL_AMBER, (row.x, row.y, 3, row.h))
        widgets.draw_text(surf, tk, (row.x + 6, y + 3), fonts.small(bold=True), config.COL_AMBER)
        name_w = max(40, row.w - 210)
        widgets.draw_text(surf, widgets.fit_text(r["name"], fonts.small(), name_w),
                          (row.x + 64, y + 3), fonts.small(), config.COL_TEXT)
        widgets.draw_text(surf, f"{r['price']:,.2f}", (row.right - 76, y + 3),
                          fonts.small(), config.COL_WHITE, align="right")
        if r["change_pct"] is not None:
            vcol = config.COL_UP if r["change_pct"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{r['change_pct']:+.1f}%", (row.right - 8, y + 3),
                              fonts.small(bold=True), vcol, align="right")

    def _draw_alert_row(self, surf, a, y, area, mp):
        row = pygame.Rect(area.x + 2, y, area.w - 4, ROW_H - 2)
        if row.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
        widgets.draw_text(surf, a["ticker"], (row.x + 6, y + 3), fonts.small(bold=True),
                          config.COL_AMBER)
        kind = a.get("kind", "level")
        if kind == "level":
            sens = "↑" if a["above"] else "↓"
            desc = f"{sens} {a['value']:.2f}"
        elif kind == "pct":
            desc = f"{'+' if a['above'] else '-'}{a['value']:.1f}%"
        else:
            desc = f"trail {a['value']:.1f}%"
        widgets.draw_text(surf, desc, (row.x + 64, y + 3), fonts.small(), config.COL_TEXT)
        cur = self.market.price_of(a["ticker"])
        if cur is not None and kind == "level" and a["value"]:
            dist_pct = abs(cur - a["value"]) / a["value"] * 100
            if dist_pct <= 2:
                pcol, ptxt = config.COL_DOWN, "imminent"
            elif dist_pct <= 8:
                pcol, ptxt = config.COL_WARN, "proche"
            else:
                pcol, ptxt = config.COL_TEXT_DIM, "loin"
            widgets.draw_text(surf, ptxt, (row.right - 34, y + 4), fonts.tiny(bold=True),
                              pcol, align="right")
        dr = pygame.Rect(row.right - 24, y + 2, 18, 18)
        self._delete_rects[a["id"]] = dr
        hov = dr.collidepoint(mp)
        pygame.draw.line(surf, config.COL_DOWN if hov else config.COL_TEXT_DIM,
                         (dr.x + 4, dr.y + 4), (dr.right - 4, dr.bottom - 4), 2)
        pygame.draw.line(surf, config.COL_DOWN if hov else config.COL_TEXT_DIM,
                         (dr.x + 4, dr.bottom - 4), (dr.right - 4, dr.y + 4), 2)
