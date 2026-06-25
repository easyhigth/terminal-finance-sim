"""
scene_structured.py — Desk produits structurés.

Le joueur souscrit des produits à payoff non linéaire (capital garanti, reverse
convertible, autocallable) sur l'indice de sa région. Le payoff est évalué à
l'échéance (cf. core/structured). Ouvert via STRUCT.
"""
import pygame

from core import config, unlocks
from core import structured as S
from core.scene_manager import Scene
from ui import fonts, keynav, widgets

LOT = S.LOT     # notionnel souscrit par clic
FAMILY_CHIPS = [(None, "TOUTES"), ("Classique", "CLASSIQUE"),
                ("Exotique", "EXOTIQUE"), ("Volatilité", "VOLATILITÉ")]
_CHART_W, _CHART_H = 110, 38


def _draw_payoff_chart(surf, rect, tpl_id):
    """Mini-diagramme indicatif du payoff (ratio capital final / notionnel)
    en fonction de la performance finale du sous-jacent (ou de la volatilité
    réalisée pour les produits Volatilité)."""
    pts = S.payoff_curve(tpl_id, n=21)
    if not pts:
        return
    pygame.draw.rect(surf, config.COL_PANEL, rect, border_radius=3)
    pygame.draw.rect(surf, config.COL_BORDER, rect, 1, border_radius=3)
    ratios = [r for _, r in pts]
    lo, hi = min(0.0, min(ratios)), max(1.0, max(ratios))
    span = max(1e-6, hi - lo)
    zero_y = rect.bottom - int(((1.0 - lo) / span) * rect.h)
    pygame.draw.line(surf, config.COL_TEXT_DIM, (rect.x, zero_y), (rect.right, zero_y), 1)
    n = len(pts)
    pixels = []
    for i, (_, ratio) in enumerate(pts):
        x = rect.x + int(i / (n - 1) * (rect.w - 1))
        y = rect.bottom - int(((ratio - lo) / span) * rect.h)
        pixels.append((x, max(rect.y, min(rect.bottom, y))))
    col = config.COL_UP if ratios[-1] >= 1.0 else config.COL_AMBER
    if len(pixels) > 1:
        pygame.draw.lines(surf, col, False, pixels, 2)


class StructuredScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.search = ""
        self._search_clear_rect = None
        self._t = 0.0
        self.invest_rects = {}
        self.sell_rects = {}
        self._family_rects = {}
        self.family_filter = None
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self.row_cursor = 0
        self._row_list = []
        self._row_rects = {}
        self._row_offsets = {}
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button((config.back_button_rect(160)[0] + 170,
                                        config.back_button_rect(160)[1], 150, 42),
                                       "📘 TUTO", config.COL_CYAN)

    def _can_trade(self):
        return unlocks.unlocked(self.app.gs.player, "structured")

    def _search_rect(self):
        return pygame.Rect(40, 100, 280, 24)

    def _scroll_to_cursor(self):
        if not self._list_rect or not self._row_list:
            return
        tid = self._row_list[self.row_cursor]
        row_top = self._row_offsets.get(tid)
        if row_top is None:
            return
        row_bottom = row_top + 90
        if row_top < self.scroll:
            self.scroll = row_top
        elif row_bottom > self.scroll + self._list_rect.h:
            self.scroll = row_bottom - self._list_rect.h
        self.scroll = max(0, min(self._max_scroll, self.scroll))

    def _activate_cursor(self):
        if not self._row_list or not self._can_trade():
            return
        tid = self._row_list[self.row_cursor]
        r = S.invest(self.app.gs.player, self.app.market, tid, LOT)
        self.msg = ("Souscrit pour " + widgets.format_money(LOT, self._cur())
                    if r["ok"] else f"Refusé ({r['reason']}).")
        if r["ok"] and not self.app.gs.player.hardcore:
            self.app.gs.save(config.AUTOSAVE_SLOT)

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
                self.scroll = 0
                return
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.row_cursor, activate = widgets.list_key_nav(
                    event, self.row_cursor, len(self._row_list))
                if self._row_list:
                    self._scroll_to_cursor()
                if activate:
                    self._activate_cursor()
                return
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search += event.unicode
                self.scroll = 0
                return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="structured", return_to="structured")
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                self.scroll = 0
                return
            for fam, rect in self._family_rects.items():
                if rect.collidepoint(event.pos):
                    self.family_filter = fam
                    self.scroll = 0
                    return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self._can_trade():
            for tid, rect in self.sell_rects.items():
                if rect.collidepoint(event.pos):
                    r = S.sell_by_type(self.app.gs.player, self.app.market, tid,
                                       min(LOT, S.held_notional(self.app.gs.player, tid)))
                    self.msg = (f"Vendu (P&L {r['realized']:+.0f})." if r["ok"]
                                else f"Vente refusée ({r['reason']}).")
                    if r["ok"] and not self.app.gs.player.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)
                    return
            for tid, rect in self.invest_rects.items():
                if rect.collidepoint(event.pos):
                    r = S.invest(self.app.gs.player, self.app.market, tid, LOT)
                    self.msg = ("Souscrit pour " + widgets.format_money(LOT, self._cur())
                                if r["ok"] else f"Refusé ({r['reason']}).")
                    if r["ok"] and not self.app.gs.player.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)

    def _cur(self):
        return config.CONTINENTS[self.app.gs.player.continent]["currency"]

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)
        self.tuto_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        m, p = self.app.market, self.app.gs.player
        cur = self._cur()
        widgets.draw_text(surf, "PRODUITS STRUCTURÉS", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Payoff non linéaire sur l'indice régional, évalué à l'échéance. "
                                f"Risque émetteur. Régime : {m.regime_label()} (★ = recommandé par le desk). "
                                + self.msg,
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        search_rect = self._search_rect()
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        slabel = (self.search + cursor) if self.search else (cursor + "Rechercher un produit…")
        scol = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(slabel, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 4), fonts.small(), scol)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 22, search_rect.y,
                                                   22, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        # ---- chips FAMILLE ----
        fy = search_rect.bottom + 8
        self._family_rects = {}
        fx = 40
        for fam, label in FAMILY_CHIPS:
            w = fonts.tiny(bold=True).size(label)[0] + 14
            rect = pygame.Rect(fx, fy, w, 20)
            self._family_rects[fam] = rect
            sel = (fam == self.family_filter)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, label, rect.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM, align="center")
            fx += w + 6

        top = fy + 28
        ph = config.footer_y() - 8 - top
        # catalogue (gauche)
        cat = pygame.Rect(40, top, 700, ph)
        inner = widgets.draw_panel(surf, cat, "Catalogue", config.COL_CYAN)
        list_area = pygame.Rect(inner.x - 6, inner.y, inner.w + 12, inner.h)
        self._list_rect = list_area
        self.invest_rects = {}
        self.sell_rects = {}
        q_filter = self.search.strip().lower()
        templates = [tpl for tpl in S.all_templates(m)
                     if (not self.family_filter or tpl["family"] == self.family_filter)
                     and (not q_filter or q_filter in tpl["name"].lower() or q_filter in tpl["desc"].lower())]
        templates.sort(key=lambda tpl: not tpl["featured"])
        self._row_list = [tpl["id"] for tpl in templates]
        self._row_offsets = {}
        self._row_rects = {}
        self.row_cursor = min(self.row_cursor, len(self._row_list) - 1) if self._row_list else 0
        cursor_id = self._row_list[self.row_cursor] if self._row_list else None
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = inner.y - self.scroll
        for tpl in templates:
            row_y0 = y
            visible = (list_area.top - 100) < y < list_area.bottom
            self._row_offsets[tpl["id"]] = row_y0 - inner.y + self.scroll
            name = ("★ " + tpl["name"]) if tpl["featured"] else tpl["name"]
            widgets.draw_text(surf, name, (inner.x, y), fonts.small(bold=True),
                              config.COL_UP if tpl["featured"] else config.COL_AMBER)
            widgets.draw_text(surf, f"{tpl['family']} · {tpl['years']} ans", (inner.right - 160, y),
                              fonts.tiny(), config.COL_TEXT_DIM)
            y += 20
            desc_h = widgets.draw_text_wrapped(surf, tpl["desc"], (inner.x, y),
                                               fonts.small(), config.COL_TEXT, inner.w - 150, line_gap=3)
            if visible:
                chart_rect = pygame.Rect(inner.right - _CHART_W, y, _CHART_W, _CHART_H)
                _draw_payoff_chart(surf, chart_rect, tpl["id"])
                widgets.draw_text(surf, S.payoff_curve_xlabel(tpl["id"]),
                                  (chart_rect.x, chart_rect.bottom + 1), fonts.tiny(), config.COL_TEXT_DIM)
            y += max(desc_h, _CHART_H + 14) + 4
            if self._can_trade():
                rect = pygame.Rect(inner.right - 150, y, 140, 26)
                if visible:
                    self.invest_rects[tpl["id"]] = rect
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect, border_radius=4)
                pygame.draw.rect(surf, config.COL_UP, rect, 1, border_radius=4)
                widgets.draw_text(surf, f"SOUSCRIRE {LOT/1000:.0f}k", (rect.x + 12, y + 4),
                                  fonts.tiny(bold=True), config.COL_UP)
                if S.held_notional(p, tpl["id"]) > 0:
                    srect = pygame.Rect(rect.left - 96, y, 88, 26)
                    if visible:
                        self.sell_rects[tpl["id"]] = srect
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, srect, border_radius=4)
                    pygame.draw.rect(surf, config.COL_DOWN, srect, 1, border_radius=4)
                    widgets.draw_text(surf, "VENDRE", srect.center, fonts.tiny(bold=True),
                                      config.COL_DOWN, align="center")
            y += 40
            if visible:
                row_rect = pygame.Rect(inner.x - 4, row_y0 - 2, inner.w + 8, y - row_y0 - 8)
                self._row_rects[tpl["id"]] = row_rect
                keynav.draw_focus_ring(surf, row_rect, tpl["id"] == cursor_id)
        surf.set_clip(prev_clip)

        content_h = (y + self.scroll) - inner.y
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, cat, list_area, self.scroll, self._max_scroll, content_h)

        # positions en cours (droite)
        posp = pygame.Rect(760, top, config.SCREEN_WIDTH - 800, ph)
        pinner = widgets.draw_panel(surf, posp, "Vos produits", config.COL_AMBER)
        hold = S.holdings(p, m)
        if not hold:
            if self._can_trade():
                lock_msg = "Aucun produit en cours."
            else:
                g = unlocks.effective_required_grade(p, "structured")
                lock_msg = f"⊘ trading débloqué au grade {config.GRADES[g]}."
            widgets.draw_text(surf, lock_msg, (pinner.x, pinner.y), fonts.small(), config.COL_TEXT_DIM)
        else:
            y = pinner.y
            for h in hold:
                widgets.draw_text(surf, h["name"], (pinner.x, y), fonts.small(bold=True), config.COL_TEXT)
                pcol = config.COL_UP if h["perf"] >= 0 else config.COL_DOWN
                widgets.draw_text(surf, f"{widgets.format_money(h['notional'], cur)} · "
                                        f"sous-jacent {h['perf']:+.1f}% · échéance {h['years_left']:.1f} an",
                                  (pinner.x, y + 18), fonts.tiny(), pcol)
                y += 44
        widgets.draw_hint_bar(surf, (config.SCREEN_WIDTH - 40, config.footer_y() + 14),
                              [("↑↓", "naviguer"), ("ENTRÉE", "investir/vendre")])
        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
