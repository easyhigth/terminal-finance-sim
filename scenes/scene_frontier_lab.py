"""
scene_frontier_lab.py — Laboratoire de frontière efficiente.
Vue interactive ouverte depuis l'analyse de portefeuille (en popup-page) :
permet de cocher/décocher des actions (détenues + candidates suggérées) pour
voir en direct comment la frontière efficiente bouge, et d'identifier quels
actifs peu corrélés au portefeuille actuel amélioreraient la diversification.
Le joueur manipule lui-même l'univers d'actifs — aucune position n'est
réellement achetée/vendue ici, c'est une simulation.
"""
import pygame

from core import analytics, config, portfolio as pf
from core.scene_manager import Scene
from ui import fonts, widgets

ROW_H = 22


class FrontierLabScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "analytics")
        self.market = self.app.ensure_market()
        p = self.app.gs.player
        held = [h["ticker"] for h in pf.holdings(p, self.market) if not h["short"]]
        self._held = list(held)
        candidates = analytics.diversification_candidates(p, self.market, n=10)
        self.universe = list(dict.fromkeys(held + candidates))
        self._candidates_sorted = list(candidates)
        self.selected = set(held)
        self.scroll = 0
        self._max_scroll = 0
        self._row_rects = {}
        self.back_btn = widgets.Button(
            config.back_button_rect(180), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.reset_btn = widgets.Button(
            (240, config.SCREEN_HEIGHT - 50, 220, 42), "↺ RÉINITIALISER", config.COL_TEXT_DIM)

    def refresh_data(self):
        p = self.app.gs.player
        held = [h["ticker"] for h in pf.holdings(p, self.market) if not h["short"]]
        self._held = list(held)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if self.reset_btn.handle(event):
            self.selected = set(self._held)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            delta = -ROW_H * 2 if event.button == 4 else ROW_H * 2
            self.scroll = max(0, min(self._max_scroll, self.scroll + delta))
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for tk, rect in self._row_rects.items():
                if rect.collidepoint(event.pos):
                    if tk in self.selected:
                        if len(self.selected) > 2:
                            self.selected.discard(tk)
                    else:
                        self.selected.add(tk)
                    return

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp, dt)
        self.reset_btn.update(mp, dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "LABORATOIRE — FRONTIÈRE EFFICIENTE", (40, 20),
                          fonts.title(bold=True), config.COL_UP)
        widgets.draw_text(surf, "Cochez/décochez des actions pour simuler leur ajout ou "
                          "retrait du portefeuille et observer l'effet sur la diversification.",
                          (42, 68), fonts.small(), config.COL_TEXT_DIM)

        top = 100
        bottom = config.footer_y() - 8
        h = bottom - top
        M = config.MARGIN
        lw = 300
        rw = config.SCREEN_WIDTH - 2 * M - lw - M
        self._draw_universe(surf, pygame.Rect(M, top, lw, h))
        self._draw_lab(surf, pygame.Rect(M + lw + M, top, rw, h))
        self.back_btn.draw(surf)
        self.reset_btn.draw(surf)

    def _draw_universe(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, f"Univers d'actifs ({len(self.selected)} sél.)",
                                   config.COL_CYAN)
        self._row_rects = {}
        prev_clip = surf.get_clip()
        surf.set_clip(inner)
        y = inner.y - self.scroll
        for tk in self.universe:
            row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, ROW_H - 2)
            self._row_rects[tk] = row
            checked = tk in self.selected
            held = tk in self._held
            box_col = config.COL_UP if checked else config.COL_TEXT_DIM
            box = f"[x]" if checked else "[ ]"
            widgets.draw_text(surf, box, (inner.x, y), fonts.small(bold=True), box_col)
            label = tk + (" ★" if held else "")
            col = config.COL_WHITE if checked else config.COL_TEXT_DIM
            widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), inner.w - 40),
                              (inner.x + 28, y), fonts.small(), col)
            y += ROW_H
        surf.set_clip(prev_clip)
        content_h = (y + self.scroll) - inner.y
        self._max_scroll = max(0, content_h - inner.h)
        self.scroll = max(0, min(self._max_scroll, self.scroll))
        widgets.draw_scrollbar(surf, rect, inner, self.scroll, self._max_scroll, content_h)
        widgets.draw_text(surf, "★ = détenue actuellement · clic = inclure/exclure",
                          (inner.x, inner.bottom - 12), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_lab(self, surf, rect):
        half = (rect.h - config.MARGIN) // 2
        frontier_rect = pygame.Rect(rect.x, rect.y, rect.w, half)
        corr_rect = pygame.Rect(rect.x, rect.y + half + config.MARGIN, rect.w, half)
        self._draw_frontier(surf, frontier_rect)
        self._draw_recommendations(surf, corr_rect)

    def _draw_frontier(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Frontière efficiente — simulation", config.COL_UP)
        sel = [tk for tk in self.universe if tk in self.selected]
        fr = analytics.frontier_for_universe(self.market, sel)
        if not fr:
            widgets.draw_text(surf, "Cochez ≥ 2 actions avec historique suffisant.",
                              (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
            return
        held_fr = analytics.equity_frontier(self.app.gs.player, self.market)
        vols, rets = fr["vols"], fr["rets"]
        svol, sret = fr["sim"]
        xs, ys = list(vols) + [svol], list(rets) + [sret]
        if held_fr:
            xs.append(held_fr["cur"][0]); ys.append(held_fr["cur"][1])
        lo_x, hi_x = min(xs), max(xs)
        lo_y, hi_y = min(ys), max(ys)
        sx = (hi_x - lo_x) or 1.0
        sy = (hi_y - lo_y) or 1.0
        plot = inner.inflate(-30, -28)
        plot.move_ip(10, 6)

        def px(v, r):
            return (plot.x + int((v - lo_x) / sx * plot.w),
                    plot.bottom - int((r - lo_y) / sy * plot.h))
        pts = [px(v, r) for v, r in zip(vols, rets)]
        if len(pts) >= 2:
            pygame.draw.aalines(surf, config.COL_CYAN, False, pts)
        if held_fr:
            hp = px(*held_fr["cur"])
            pygame.draw.circle(surf, config.COL_TEXT_DIM, hp, 4, 1)
            widgets.draw_text(surf, "ACTUEL", (hp[0] + 6, hp[1] + 4), fonts.tiny(), config.COL_TEXT_DIM)
        sp = px(svol, sret)
        pygame.draw.circle(surf, config.COL_AMBER, sp, 5)
        widgets.draw_text(surf, "SIMULATION", (sp[0] + 6, sp[1] - 10), fonts.tiny(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"vol {svol:.0f}%  ·  rdt att. {sret:.0f}%  ·  {len(sel)} actifs (équipondéré)",
                          (inner.x, inner.bottom - 14), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_recommendations(self, surf, rect):
        inner = widgets.draw_panel(surf, rect, "Suggestions de diversification", config.COL_AMBER)
        cands = [tk for tk in self._candidates_sorted if tk not in self.selected][:6]
        if not cands:
            widgets.draw_text(surf, "Toutes les candidates suggérées sont déjà incluses.",
                              (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
            return
        widgets.draw_text(surf, "Actions peu corrélées à vos positions actuelles — "
                          "cochez-les à gauche pour voir l'effet sur la frontière.",
                          (inner.x, inner.y), fonts.tiny(), config.COL_TEXT_DIM)
        y = inner.y + 18
        for tk in cands:
            widgets.draw_text(surf, tk, (inner.x, y), fonts.small(bold=True), config.COL_CYAN)
            y += 18
