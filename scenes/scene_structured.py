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

LOT = 50_000.0     # notionnel souscrit par clic


class StructuredScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        self.search = ""
        self._search_clear_rect = None
        self._t = 0.0
        self.invest_rects = {}
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
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self._can_trade():
            for ti, rect in self.invest_rects.items():
                if rect.collidepoint(event.pos):
                    r = S.invest(self.app.gs.player, self.app.market, ti, LOT)
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

        top = search_rect.bottom + 8
        ph = config.footer_y() - 8 - top
        # catalogue (gauche)
        cat = pygame.Rect(40, top, 700, ph)
        inner = widgets.draw_panel(surf, cat, "Catalogue", config.COL_CYAN)
        self.invest_rects = {}
        y = inner.y
        q_filter = self.search.strip().lower()
        templates = [(ti, tpl) for ti, tpl in enumerate(S.TEMPLATES)
                     if not q_filter or q_filter in tpl["name"].lower() or q_filter in tpl["desc"].lower()]
        for ti, tpl in templates:
            widgets.draw_text(surf, tpl["name"], (inner.x, y), fonts.small(bold=True), config.COL_AMBER)
            widgets.draw_text(surf, f"maturité {tpl['years']} ans", (inner.right - 120, y),
                              fonts.tiny(), config.COL_TEXT_DIM)
            y += 20
            y += widgets.draw_text_wrapped(surf, tpl["desc"], (inner.x, y),
                                           fonts.small(), config.COL_TEXT, inner.w - 130, line_gap=3) + 4
            if self._can_trade():
                rect = pygame.Rect(inner.right - 150, y, 140, 26)
                self.invest_rects[ti] = rect
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect, border_radius=4)
                pygame.draw.rect(surf, config.COL_UP, rect, 1, border_radius=4)
                widgets.draw_text(surf, f"SOUSCRIRE {LOT/1000:.0f}k", (rect.x + 12, y + 4),
                                  fonts.tiny(bold=True), config.COL_UP)
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
