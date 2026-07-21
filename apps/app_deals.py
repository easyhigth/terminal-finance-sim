"""
app_deals.py — Application « Deals » du bureau (NATIVE).

Migration de `scenes/scene_deals.py` (rendu hébergé 1280×720 réduit par
smoothscale → flou, cf. apps/scene_host.py) vers une app dessinée à la
résolution de sa fenêtre — même principe que Mission/Évaluation avant elle.
Toutes les positions sont relatives au `rect` de la fenêtre. Cliquer une
ligne ouvre le mini-jeu (scène "deal") EN FENÊTRE via
`DesktopScene._open_scene_window` (et non `app.scenes.go`, qui basculerait
tout l'écran hors du bureau) — la scène plein écran "deal" elle-même reste
hébergée (hors scope de cette migration). La scène "deals" plein écran reste
enregistrée (fallback/tests) ; l'ouverture EN FENÊTRE est redirigée ici
(cf. DesktopScene._open_scene_window).
"""
import pygame

from apps.base import DesktopApp
from core import config, i18n, unlocks
from core import deals as D
from ui import fonts, keynav, widgets


def _L(fr, en):
    return en if i18n.get_lang() == "en" else fr


ROW_H = 92
KINDS = ["M&A", "Portfolio", "Risk", "Quant", "Advisory", "General"]


class DealsApp(DesktopApp):
    title = "Deals"
    icon_kind = "deals"
    default_size = (1040, 660)
    min_size = (680, 440)

    def on_open(self):
        self.search = ""
        self._search_clear_rect = None
        self.kind_filter = None
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self._kind_rects = {}
        self._row_rects = {}
        self._t = 0.0
        self.row_cursor = 0
        self._row_list = []
        self._tooltip = None
        self.view_mode = "active"
        self._mode_rects = {}
        self.scroll_hist = 0
        self._max_scroll_hist = 0
        self._hist_list_rect = None

    def _can(self):
        return unlocks.unlocked(self.app.gs.player, "deals")

    def _filtered_sorted_deals(self):
        p = self.app.gs.player
        deals = list(p.deals)
        q = self.search.strip().lower()
        if q:
            deals = [d for d in deals if q in f"{d['title']} {d['kind']} {d.get('desc','')}".lower()]
        if self.kind_filter:
            deals = [d for d in deals if d["kind"] == self.kind_filter]
        deals.sort(key=lambda d: d["days_left"])
        return deals

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

    def _open_deal(self, deal_id):
        if self.desktop is not None:
            self.desktop._open_scene_window("deal", deal_id=deal_id, return_to="deals")

    # ------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for mode, r in self._mode_rects.items():
                if r.collidepoint(event.pos):
                    self.view_mode = mode
                    return True
        if self.view_mode == "history":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
                if self._hist_list_rect and self._hist_list_rect.collidepoint(event.pos):
                    self.scroll_hist = max(0, min(self._max_scroll_hist,
                                             self.scroll_hist + (-48 if event.button == 4 else 48)))
                    return True
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search:
                    self.search = ""
                    return True
                return False
            if event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                return True
            if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                deals = self._filtered_sorted_deals()
                self.row_cursor, activate = widgets.list_key_nav(event, self.row_cursor, len(deals))
                if deals:
                    self._scroll_to_cursor()
                if activate and deals:
                    self._open_deal(deals[self.row_cursor]["id"])
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
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return True
            for kind, r in self._kind_rects.items():
                if r.collidepoint(event.pos):
                    self.kind_filter = None if self.kind_filter == kind else kind
                    self.scroll = 0
                    return True
            for did, r in self._row_rects.items():
                if r.collidepoint(event.pos):
                    self._open_deal(did)
                    return True
            return False
        return False

    def update(self, dt):
        self._t += dt

    # ------------------------------------------------------------- draw
    def _draw_mode_toggle(self, surf, rect):
        btn_w, btn_h, gap = 110, 24, 6
        x = rect.right - 12 - 2 * btn_w - gap
        self._mode_rects = {}
        for mode, label in (("active", _L("EN COURS", "ACTIVE")), ("history", _L("HISTORIQUE", "HISTORY"))):
            r = pygame.Rect(x, rect.y + 10, btn_w, btn_h)
            active = self.view_mode == mode
            accent = config.COL_AMBER if active else config.COL_TEXT_DIM
            pygame.draw.rect(surf, config.COL_PANEL, r)
            pygame.draw.rect(surf, accent, r, 2 if active else 1)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=active), accent, align="center")
            self._mode_rects[mode] = r
            x += btn_w + gap

    def draw(self, surf, rect):
        surf.fill(config.COL_BG, rect)
        widgets.draw_text(surf, _L("DEALS — OPPORTUNITÉS EN COURS", "DEALS — ACTIVE OPPORTUNITIES"), (rect.x + 16, rect.y + 10),
                          fonts.head(bold=True), config.COL_AMBER)
        p = self.app.gs.player
        if not self._can():
            g = unlocks.effective_required_grade(p, "deals")
            widgets.draw_text(surf, _L(f"⊘ Deals débloqués au grade {config.GRADES[g]}.", f"⊘ Deals unlocked at grade {config.GRADES[g]}."),
                              (rect.x + 16, rect.y + 40), fonts.small(), config.COL_TEXT_DIM)
            return
        self._draw_mode_toggle(surf, rect)
        if self.view_mode == "history":
            self._draw_history(surf, rect, p)
            return
        widgets.draw_text(surf, _L("Chaque deal expire au bout d'un nombre de jours ; cliquez une ligne pour le lancer.", "Each deal expires after a number of days; click a row to launch it."),
                          (rect.x + 16, rect.y + 34), fonts.tiny(), config.COL_TEXT_DIM)

        top = rect.y + 56
        search_rect = pygame.Rect(rect.x + 16, top, min(220, rect.w - 32), 22)
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else (cursor + _L("Rechercher…", "Search…"))
        col = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.tiny(), search_rect.w - 26),
                          (search_rect.x + 6, search_rect.y + 4), fonts.tiny(), col)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 20, search_rect.y, 20, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.tiny(bold=True),
                              config.COL_TEXT_DIM, align="center")

        self._kind_rects = {}
        cx = search_rect.right + 12
        cy = top
        counts = {}
        for d in p.deals:
            counts[d["kind"]] = counts.get(d["kind"], 0) + 1
        for kind in KINDS:
            klabel = f"{kind} ({counts.get(kind, 0)})"
            w = max(56, fonts.tiny(bold=True).size(klabel)[0] + 14)
            r = pygame.Rect(cx, cy, w, 22)
            if r.right > rect.right - 16:
                cx = rect.x + 16
                cy += 26
                r = pygame.Rect(cx, cy, w, 22)
            self._kind_rects[kind] = r
            sel = (self.kind_filter == kind)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, klabel, r.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM, align="center")
            cx += w + 6

        deals = self._filtered_sorted_deals()
        self._row_list = deals
        self.row_cursor = min(self.row_cursor, len(deals) - 1) if deals else 0

        panel_top = cy + 30
        panel = pygame.Rect(rect.x + 16, panel_top, rect.w - 32, rect.bottom - 12 - panel_top)
        inner = widgets.draw_panel(surf, panel, _L(f"Deals ({len(deals)} / {len(p.deals)})", f"Deals ({len(deals)} / {len(p.deals)})"), config.COL_CYAN)
        list_top = inner.y
        list_area = pygame.Rect(inner.x - 6, list_top, inner.w + 12, inner.bottom - list_top - 4)
        self._list_rect = list_area
        self._row_rects = {}
        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")

        if not p.deals:
            widgets.draw_text(surf, _L("Aucun deal en cours. Patientez, le temps avance en direct.", "No active deal. Wait, time advances live."),
                              (inner.x, list_top + 4), fonts.tiny(), config.COL_TEXT_DIM)
            return
        if not deals:
            widgets.draw_text(surf, _L("Aucun deal ne correspond à ce filtre.", "No deal matches this filter."),
                              (inner.x, list_top + 4), fonts.tiny(), config.COL_TEXT_DIM)

        wide = inner.w >= 620
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        mp = pygame.mouse.get_pos()
        self._tooltip = None
        y = list_top - self.scroll
        for i, d in enumerate(deals):
            visible = (list_area.top - ROW_H) < y < list_area.bottom
            if visible:
                self._draw_row(surf, d, inner, y, i, cur, mp, wide)
            y += ROW_H
        surf.set_clip(prev_clip)
        content_h = (y + self.scroll) - list_top
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, panel, list_area, self.scroll, self._max_scroll, content_h)
        if self._tooltip:
            widgets.draw_tooltip(surf, *self._tooltip)

    def _draw_row(self, surf, d, inner, y, i, cur, mp, wide):
        prob = D.success_probability(self.app.gs.player, d)
        row = pygame.Rect(inner.x, y, inner.w, ROW_H - 8)
        pygame.draw.rect(surf, config.COL_PANEL, row, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, row, 1, border_radius=4)
        keynav.draw_focus_ring(surf, row, i == self.row_cursor)
        self._row_rects[d["id"]] = row

        widgets.draw_text(surf, widgets.fit_text(f"#{d['id']} {d['title']}", fonts.small(bold=True), row.w - 24),
                          (row.x + 12, row.y + 6), fonts.small(bold=True), config.COL_AMBER)
        widgets.draw_badge(surf, d["kind"], (row.x + 12, row.y + 26), accent=config.COL_PRESTIGE)
        diff_lbl = "✶" * d["difficulty"]
        widgets.draw_text(surf, diff_lbl, (row.x + 110, row.y + 28), fonts.tiny(), config.COL_TEXT_DIM)

        if wide:
            widgets.draw_text(surf, widgets.fit_text(d.get("desc", ""), fonts.tiny(), 300),
                              (row.x + 12, row.y + 50), fonts.tiny(), config.COL_TEXT_DIM)
            px = row.x + 380
        else:
            px = row.x + 12

        py = row.y + 50 if not wide else row.y + 8
        pcol = config.COL_UP if prob >= 0.6 else config.COL_WARN if prob >= 0.35 else config.COL_DOWN
        calib = (_L("Facile", "Easy") if prob >= 0.6 else _L("Modéré", "Moderate") if prob >= 0.35
                 else _L("Difficile", "Hard") if prob >= 0.15 else _L("Très difficile", "Very hard"))
        widgets.draw_text(surf, _L(f"Probabilité {int(prob*100)}% — {calib}", f"Probability {int(prob*100)}% — {calib}"), (px, py), fonts.tiny(), pcol)
        widgets.draw_progress(surf, pygame.Rect(px, py + 16, 140, 10), prob, accent=pcol)

        gy = py + 30 if not wide else row.y + 46
        widgets.draw_text(surf, _L(f"Gain {widgets.format_money(d['reward_cash'], cur)} (+{d['reward_rep']} rép.)", f"Gain {widgets.format_money(d['reward_cash'], cur)} (+{d['reward_rep']} rep.)"),
                          (px, gy), fonts.tiny(), config.COL_UP)

        ux = row.right - 150 if wide else px
        uy = row.y + 8 if wide else gy + 16
        widgets.draw_text(surf, _L(f"{d['days_left']} j restants", f"{d['days_left']} days left"), (ux, uy), fonts.tiny(), config.COL_TEXT)
        urgent = d["days_left"] <= 7
        ucol = config.COL_DOWN if urgent else config.COL_WARN if d["days_left"] <= 14 else config.COL_UP
        widgets.draw_progress(surf, pygame.Rect(ux, uy + 16, 130, 8), min(1.0, d["days_left"] / 26), accent=ucol)
        hover_rect = pygame.Rect(ux, uy, 130, 30)
        if hover_rect.collidepoint(mp):
            self._tooltip = (_L("Passé ce délai, l'offre est retirée — un rival peut la "
                              "rafler avant vous.",
                              "After this deadline the offer is withdrawn — a rival can "
                              "grab it before you."), mp)
        if urgent:
            widgets.draw_badge(surf, _L("URGENT", "URGENT"), (ux, uy + 28), accent=config.COL_DOWN)

    # --------------------------------------------------------- historique
    def _draw_history(self, surf, rect, p):
        widgets.draw_text(surf, _L("Replay des derniers deals résolus (succès, échecs, expirations).", "Replay of the latest resolved deals (successes, failures, expirations)."),
                          (rect.x + 16, rect.y + 34), fonts.tiny(), config.COL_TEXT_DIM)
        top = rect.y + 56
        panel = pygame.Rect(rect.x + 16, top, rect.w - 32, rect.bottom - 12 - top)
        history = list(reversed(p.deals_history))
        inner = widgets.draw_panel(surf, panel, _L(f"Historique ({len(history)})", f"History ({len(history)})"), config.COL_CYAN)
        list_area = pygame.Rect(inner.x - 6, inner.y, inner.w + 12, inner.h)
        self._hist_list_rect = list_area
        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")
        if not history:
            widgets.draw_text(surf, _L("Aucun deal résolu pour l'instant.", "No deal resolved yet."),
                              (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
            self._max_scroll_hist = 0
            return

        wide = inner.w >= 700
        row_h = 30
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = inner.y - self.scroll_hist
        for h in history:
            visible = (list_area.top - row_h) < y < list_area.bottom
            if visible:
                col = {"success": config.COL_UP, "partial": config.COL_UP,
                       "fail": config.COL_DOWN, "expired": config.COL_WARN}.get(h["outcome"], config.COL_TEXT_DIM)
                label = {"success": _L("RÉUSSI", "SUCCESS"), "partial": _L("PARTIEL", "PARTIAL"),
                         "fail": _L("ÉCHEC", "FAIL"), "expired": _L("EXPIRÉ", "EXPIRED")}.get(h["outcome"], h["outcome"].upper())
                widgets.draw_text(surf, f"J{h['day']}", (inner.x, y + 6), fonts.tiny(), config.COL_TEXT_DIM)
                title_w = 260 if not wide else 360
                widgets.draw_text(surf, widgets.fit_text(h["title"], fonts.tiny(), title_w),
                                  (inner.x + 44, y + 4), fonts.tiny(), config.COL_TEXT)
                if wide:
                    widgets.draw_badge(surf, h["kind"], (inner.x + 420, y + 2), accent=config.COL_PRESTIGE)
                widgets.draw_badge(surf, label, (inner.x + (500 if wide else 320), y + 2), accent=col)
                sign = "+" if h["cash_delta"] >= 0 else ""
                widgets.draw_text(surf, f"{sign}{widgets.format_money(h['cash_delta'], cur)}",
                                  (inner.right - 180, y + 6), fonts.tiny(), col)
                rsign = "+" if h["rep_delta"] >= 0 else ""
                widgets.draw_text(surf, _L(f"{rsign}{h['rep_delta']} rép.", f"{rsign}{h['rep_delta']} rep."),
                                  (inner.right - 70, y + 6), fonts.tiny(), col)
            y += row_h
        surf.set_clip(prev_clip)
        content_h = (y + self.scroll_hist) - inner.y
        self._max_scroll_hist = max(0, content_h - list_area.h)
        self.scroll_hist = min(self.scroll_hist, self._max_scroll_hist)
        self.scroll_hist = widgets.draw_scrollbar(surf, panel, list_area, self.scroll_hist,
                                                   self._max_scroll_hist, content_h)
