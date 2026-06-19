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
from ui import fonts, widgets

LOT = S.LOT     # notionnel souscrit par clic
FAMILY_CHIPS = [(None, "TOUTES"), ("Classique", "CLASSIQUE"),
                ("Exotique", "EXOTIQUE"), ("Volatilité", "VOLATILITÉ")]


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
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button((config.back_button_rect(160)[0] + 170,
                                        config.back_button_rect(160)[1], 150, 42),
                                       "📘 TUTO", config.COL_CYAN)

    def _can_trade(self):
        return unlocks.unlocked(self.app.gs.player, "trade")

    def _search_rect(self):
        return pygame.Rect(40, 100, 280, 24)

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
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search += event.unicode
                return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="structured", return_to="structured")
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return
            for fam, rect in self._family_rects.items():
                if rect.collidepoint(event.pos):
                    self.family_filter = fam
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
                                "Risque émetteur. " + self.msg,
                          (42, 74), fonts.small(), config.COL_TEXT_DIM)

        search_rect = self._search_rect()
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN if self.search else config.COL_BORDER,
                          search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        slabel = (self.search + cursor) if self.search else "Rechercher un produit…"
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
        self.invest_rects = {}
        self.sell_rects = {}
        y = inner.y
        q_filter = self.search.strip().lower()
        templates = [tpl for tpl in S.all_templates()
                     if (not self.family_filter or tpl["family"] == self.family_filter)
                     and (not q_filter or q_filter in tpl["name"].lower() or q_filter in tpl["desc"].lower())]
        for tpl in templates:
            widgets.draw_text(surf, tpl["name"], (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
            widgets.draw_text(surf, f"{tpl['family']} · {tpl['years']} ans", (inner.right - 160, y),
                              fonts.tiny(), config.COL_TEXT_DIM)
            y += 20
            y += widgets.draw_text_wrapped(surf, tpl["desc"], (inner.x, y),
                                           fonts.small(), config.COL_TEXT, inner.w - 130, line_gap=3) + 4
            if self._can_trade():
                rect = pygame.Rect(inner.right - 150, y, 140, 26)
                self.invest_rects[tpl["id"]] = rect
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect, border_radius=4)
                pygame.draw.rect(surf, config.COL_UP, rect, 1, border_radius=4)
                widgets.draw_text(surf, f"SOUSCRIRE {LOT/1000:.0f}k", (rect.x + 12, y + 4),
                                  fonts.tiny(bold=True), config.COL_UP)
                if S.held_notional(p, tpl["id"]) > 0:
                    srect = pygame.Rect(rect.left - 96, y, 88, 26)
                    self.sell_rects[tpl["id"]] = srect
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, srect, border_radius=4)
                    pygame.draw.rect(surf, config.COL_DOWN, srect, 1, border_radius=4)
                    widgets.draw_text(surf, "VENDRE", srect.center, fonts.tiny(bold=True),
                                      config.COL_DOWN, align="center")
            y += 40

        # positions en cours (droite)
        posp = pygame.Rect(760, top, config.SCREEN_WIDTH - 800, ph)
        pinner = widgets.draw_panel(surf, posp, "Vos produits", config.COL_AMBER)
        hold = S.holdings(p, m)
        if not hold:
            widgets.draw_text(surf, "Aucun produit en cours." if self._can_trade()
                              else "⊘ trading débloqué au grade Associate.",
                              (pinner.x, pinner.y), fonts.small(), config.COL_TEXT_DIM)
        else:
            y = pinner.y
            for h in hold:
                widgets.draw_text(surf, h["name"], (pinner.x, y), fonts.small(bold=True), config.COL_TEXT)
                pcol = config.COL_UP if h["perf"] >= 0 else config.COL_DOWN
                widgets.draw_text(surf, f"{widgets.format_money(h['notional'], cur)} · "
                                        f"sous-jacent {h['perf']:+.1f}% · échéance {h['years_left']:.1f} an",
                                  (pinner.x, y + 18), fonts.tiny(), pcol)
                y += 44
        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)
