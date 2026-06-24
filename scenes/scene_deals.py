"""
scene_deals.py — Hub DEALS : liste des opportunités actives, avec recherche,
filtre par voie (kind), jauge de probabilité de réussite et compte à rebours
d'échéance, pour faciliter le choix avant de lancer le mini-jeu (DEAL <id>).
Ouvert via DEALS, le rail ou PLUS.
"""
import pygame

from core import config, unlocks
from core import deals as D
from core.scene_manager import Scene
from ui import fonts, keynav, widgets

ROW_H = 92
KINDS = ["M&A", "Portfolio", "Risk", "Quant", "Advisory", "General"]


class DealsScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.search = ""
        self._search_clear_rect = None
        self.kind_filter = None
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self._kind_rects = {}
        self._row_rects = {}
        self._t = 0.0
        self.row_cursor = 0  # curseur clavier dans la liste filtrée/triée
        self._row_list = []
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

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

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search:
                    self.search = ""
                    return
                self.app.scenes.go(self.return_to)
                return
            elif event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                return
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                deals = self._filtered_sorted_deals()
                self.row_cursor, activate = widgets.list_key_nav(event, self.row_cursor, len(deals))
                if deals:
                    self._scroll_to_cursor()
                if activate and deals:
                    d = deals[self.row_cursor]
                    self.app.scenes.go("deal", deal_id=d["id"], return_to="deals")
                return
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
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
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return
            for kind, rect in self._kind_rects.items():
                if rect.collidepoint(event.pos):
                    self.kind_filter = None if self.kind_filter == kind else kind
                    self.scroll = 0
                    return
            for did, rect in self._row_rects.items():
                if rect.collidepoint(event.pos):
                    self.app.scenes.go("deal", deal_id=did, return_to="deals")
                    return

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    # ------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "DEALS — OPPORTUNITÉS EN COURS", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        p = self.app.gs.player
        if not self._can():
            g = unlocks.effective_required_grade(self.app.gs.player, "deals")
            widgets.draw_text(surf, f"⊘ Deals débloqués au grade {config.GRADES[g]}.",
                              (42, 56), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            return
        widgets.draw_text(surf, "Chaque deal expire au bout d'un nombre de jours ; cliquez une ligne pour le lancer.",
                          (42, 64), fonts.small(), config.COL_TEXT_DIM)

        top = 94
        search_rect = pygame.Rect(40, top, 260, 24)
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else (cursor + "Tapez pour rechercher…")
        col = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 4), fonts.small(), col)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 22, search_rect.y, 22, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        self._kind_rects = {}
        cx = 40 + search_rect.w + 16
        cy = top
        counts = {}
        for d in p.deals:
            counts[d["kind"]] = counts.get(d["kind"], 0) + 1
        for kind in KINDS:
            label = f"{kind} ({counts.get(kind, 0)})"
            w = max(60, fonts.tiny(bold=True).size(label)[0] + 16)
            rect = pygame.Rect(cx, cy, w, 24)
            if rect.right > config.SCREEN_WIDTH - 40:
                cx = 40
                cy += 28
                rect = pygame.Rect(cx, cy, w, 24)
            self._kind_rects[kind] = rect
            sel = (self.kind_filter == kind)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, label, rect.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM, align="center")
            cx += w + 6

        deals = self._filtered_sorted_deals()
        self._row_list = deals
        self.row_cursor = min(self.row_cursor, len(deals) - 1) if deals else 0

        panel_top = cy + 34
        panel = pygame.Rect(40, panel_top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - panel_top)
        inner = widgets.draw_panel(surf, panel, f"Deals ({len(deals)} / {len(p.deals)})", config.COL_CYAN)
        list_top = inner.y
        list_area = pygame.Rect(inner.x - 6, list_top, inner.w + 12, inner.bottom - list_top - 4)
        self._list_rect = list_area
        self._row_rects = {}
        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")

        if not p.deals:
            widgets.draw_text(surf, "Aucun deal en cours. Avancez le temps (ADV) pour en générer.",
                              (inner.x, list_top + 4), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            return
        if not deals:
            widgets.draw_text(surf, "Aucun deal ne correspond à ce filtre.",
                              (inner.x, list_top + 4), fonts.small(), config.COL_TEXT_DIM)

        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_top - self.scroll
        for i, d in enumerate(deals):
            visible = (list_area.top - ROW_H) < y < list_area.bottom
            if visible:
                prob = D.success_probability(p, d)
                row = pygame.Rect(inner.x, y, inner.w, ROW_H - 8)
                pygame.draw.rect(surf, config.COL_PANEL, row, border_radius=4)
                pygame.draw.rect(surf, config.COL_BORDER, row, 1, border_radius=4)
                keynav.draw_focus_ring(surf, row, i == self.row_cursor)
                self._row_rects[d["id"]] = row

                widgets.draw_text(surf, f"#{d['id']} {d['title']}", (row.x + 12, row.y + 6),
                                  fonts.small(bold=True), config.COL_AMBER)
                widgets.draw_badge(surf, d["kind"], (row.x + 12, row.y + 26), accent=config.COL_PRESTIGE)
                diff_lbl = "★" * d["difficulty"]
                widgets.draw_text(surf, diff_lbl, (row.x + 120, row.y + 28), fonts.tiny(), config.COL_TEXT_DIM)
                if d.get("gov"):
                    widgets.draw_badge(surf, f"SOUVERAIN · {d['gov']}", (row.x + 170, row.y + 26), accent=config.COL_CYAN)

                widgets.draw_text(surf, widgets.fit_text(d.get("desc", ""), fonts.tiny(), 360),
                                  (row.x + 12, row.y + 50), fonts.tiny(), config.COL_TEXT_DIM)

                # jauge de probabilité de réussite
                px = row.x + 400
                widgets.draw_text(surf, f"Probabilité {int(prob*100)}%", (px, row.y + 8), fonts.tiny(), config.COL_TEXT)
                pcol = config.COL_UP if prob >= 0.6 else config.COL_WARN if prob >= 0.35 else config.COL_DOWN
                widgets.draw_progress(surf, pygame.Rect(px, row.y + 24, 160, 14), prob, accent=pcol)

                widgets.draw_text(surf, f"Gain {widgets.format_money(d['reward_cash'], cur)} (+{d['reward_rep']} rép.)",
                                  (px, row.y + 46), fonts.tiny(), config.COL_UP)
                widgets.draw_text(surf, f"Échec -{widgets.format_money(d['penalty_cash'], cur)} (-{d['penalty_rep']} rép.)",
                                  (px, row.y + 62), fonts.tiny(), config.COL_DOWN)

                # compte à rebours d'échéance
                ux = row.right - 190
                widgets.draw_text(surf, f"{d['days_left']} j restants", (ux, row.y + 8), fonts.tiny(), config.COL_TEXT)
                urgent = d["days_left"] <= 7
                ucol = config.COL_DOWN if urgent else config.COL_WARN if d["days_left"] <= 14 else config.COL_UP
                widgets.draw_progress(surf, pygame.Rect(ux, row.y + 24, 150, 10),
                                      min(1.0, d["days_left"] / 26), accent=ucol)
                if urgent:
                    widgets.draw_badge(surf, "URGENT", (ux, row.y + 42), accent=config.COL_DOWN)
            y += ROW_H
        surf.set_clip(prev_clip)
        content_h = (y + self.scroll) - list_top
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, panel, list_area, self.scroll, self._max_scroll, content_h)

        self.back_btn.draw(surf)
