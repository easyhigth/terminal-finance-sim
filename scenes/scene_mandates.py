"""
scene_mandates.py — Hub MANDATS CLIENTS : offres en attente + mandats actifs,
avec graphes (net worth) et jauges de faisabilité (croissance vs objectif,
bêta vs limite de risque) pour faciliter la décision ACCEPTER/REFUSER.
Ouvert via MANDATS/MANDATE, le rail ou PLUS.
"""
import pygame
from core import config
from core import mandates as MD
from core import portfolio
from core import unlocks
from core.scene_manager import Scene
from ui import fonts, widgets

ROW_H = 26


class MandatesScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self._accept_rects = {}
        self._decline_rects = {}
        self._t = 0.0
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def _can(self):
        return unlocks.unlocked(self.app.gs.player, "mandates")

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
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
            p = self.app.gs.player
            for oid, rect in self._accept_rects.items():
                if rect.collidepoint(event.pos):
                    res = MD.accept(p, oid, self.app.ensure_market())
                    if res == "full":
                        self.app.notify("Trop de mandats actifs en parallèle.", "warn")
                    elif res:
                        self.app.notify(f"Mandat de {res['client']} accepté.", "info")
                    return
            for oid, rect in self._decline_rects.items():
                if rect.collidepoint(event.pos):
                    MD.decline(p, oid)
                    return

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    # ------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "MANDATS CLIENTS", (40, 22), fonts.title(bold=True), config.COL_PRESTIGE)
        p = self.app.gs.player
        if not self._can():
            g = unlocks.required_grade("mandates")
            widgets.draw_text(surf, f"⊘ Mandats débloqués au grade {config.GRADES[g]}.",
                              (42, 56), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            return
        widgets.draw_text(surf, "Gérez l'argent de clients sous objectif de rendement et limite de risque (bêta).",
                          (42, 56), fonts.small(), config.COL_TEXT_DIM)

        market = self.app.ensure_market()
        cur = config.CONTINENTS.get(p.continent, {}).get("currency", "$")
        top = 86
        self._accept_rects = {}
        self._decline_rects = {}

        # ---- offres en attente ----
        offers = list(p.mandate_offers)
        off_h = 50 + len(offers) * 64 if offers else 50
        off_h = min(off_h, 230)
        off_panel = pygame.Rect(40, top, config.SCREEN_WIDTH - 80, off_h)
        inner = widgets.draw_panel(surf, off_panel, f"Offres en attente ({len(offers)})", config.COL_CYAN)
        if not offers:
            widgets.draw_text(surf, "Aucune offre en attente. Avancez le temps (ADV) pour en recevoir.",
                              (inner.x, inner.y + 4), fonts.small(), config.COL_TEXT_DIM)
        else:
            y = inner.y
            for o in offers:
                row = pygame.Rect(inner.x, y, inner.w, 58)
                pygame.draw.rect(surf, config.COL_PANEL, row, border_radius=4)
                pygame.draw.rect(surf, config.COL_CYAN, row, 1, border_radius=4)
                widgets.draw_text(surf, f"#{o['id']} {o['client']}", (row.x + 12, row.y + 6),
                                  fonts.small(bold=True), config.COL_AMBER)
                widgets.draw_text(surf, f"Capital : {widgets.format_money(o['capital'], cur)}  ·  "
                                        f"Horizon : {o['horizon']}T  ·  Objectif : {o['target_pct']:.1f}%  ·  "
                                        f"β max {o['max_beta']:.2f}",
                                  (row.x + 12, row.y + 26), fonts.tiny(), config.COL_TEXT)
                widgets.draw_text(surf, f"Commission si réussite : {widgets.format_money(o['reward_cash'], cur)}  "
                                        f"(+{o['reward_rep']} rép.)  ·  échec : -{o['penalty_rep']} rép.",
                                  (row.x + 12, row.y + 42), fonts.tiny(), config.COL_TEXT_DIM)
                acc = pygame.Rect(row.right - 196, row.y + 14, 90, 30)
                dec = pygame.Rect(row.right - 100, row.y + 14, 90, 30)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, acc, border_radius=4)
                pygame.draw.rect(surf, config.COL_UP, acc, 1, border_radius=4)
                widgets.draw_text(surf, "ACCEPTER", acc.center, fonts.tiny(bold=True), config.COL_UP, align="center")
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, dec, border_radius=4)
                pygame.draw.rect(surf, config.COL_DOWN, dec, 1, border_radius=4)
                widgets.draw_text(surf, "REFUSER", dec.center, fonts.tiny(bold=True), config.COL_DOWN, align="center")
                self._accept_rects[o["id"]] = acc
                self._decline_rects[o["id"]] = dec
                y += 64

        # ---- mandats actifs ----
        act_top = off_panel.bottom + 10
        act_panel = pygame.Rect(40, act_top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - act_top)
        ainner = widgets.draw_panel(surf, act_panel, f"Mandats actifs ({len(p.mandates)})", config.COL_PRESTIGE)
        list_top = ainner.y
        list_area = pygame.Rect(ainner.x - 6, list_top, ainner.w + 12, ainner.bottom - list_top - 4)
        self._list_rect = list_area
        if not p.mandates:
            widgets.draw_text(surf, "Aucun mandat actif. Acceptez une offre ci-dessus.",
                              (ainner.x, list_top + 4), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            return

        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = list_top - self.scroll
        ROW = 120
        for m in p.mandates:
            visible = (list_area.top - ROW) < y < list_area.bottom
            if visible:
                growth, beta = MD.progress(p, market, m)
                row = pygame.Rect(ainner.x, y, ainner.w, ROW - 8)
                pygame.draw.rect(surf, config.COL_PANEL, row, border_radius=4)
                pygame.draw.rect(surf, config.COL_BORDER, row, 1, border_radius=4)
                widgets.draw_text(surf, f"#{m['id']} {m['client']}  ·  capital {widgets.format_money(m['capital'], cur)}",
                                  (row.x + 12, row.y + 8), fonts.small(bold=True), config.COL_AMBER)
                qleft = max(0, m["deadline_q"] - p.quarter)
                widgets.draw_text(surf, f"Échéance T{m['deadline_q']} ({qleft} trim. restants)",
                                  (row.right - 12, row.y + 8), fonts.tiny(), config.COL_TEXT_DIM, align="right")

                # jauge croissance vs objectif
                gy = row.y + 34
                widgets.draw_text(surf, f"Croissance {growth:+.1f}% / objectif {m['target_pct']:.1f}%",
                                  (row.x + 12, gy), fonts.tiny(), config.COL_TEXT)
                gauge = pygame.Rect(row.x + 320, gy, 220, 14)
                gcol = config.COL_UP if growth >= m["target_pct"] else config.COL_WARN
                ratio = growth / m["target_pct"] if m["target_pct"] else 1.0
                widgets.draw_progress(surf, gauge, ratio, accent=gcol)

                # jauge bêta vs limite
                by = row.y + 56
                widgets.draw_text(surf, f"Bêta {beta:.2f} / limite {m['max_beta']:.2f}",
                                  (row.x + 12, by), fonts.tiny(), config.COL_TEXT)
                bgauge = pygame.Rect(row.x + 320, by, 220, 14)
                bcol = config.COL_DOWN if beta > m["max_beta"] else config.COL_UP
                bratio = beta / m["max_beta"] if m["max_beta"] else 1.0
                widgets.draw_progress(surf, bgauge, bratio, accent=bcol)

                # mini-graphe net worth (feasibility trend)
                spark = pygame.Rect(row.right - 200, row.y + 30, 180, 46)
                pygame.draw.rect(surf, config.COL_BG, spark)
                pygame.draw.rect(surf, config.COL_BORDER, spark, 1)
                hist = (p.cash_history or [])[-24:]
                widgets.draw_series(surf, spark.inflate(-4, -4), hist)
                widgets.draw_text(surf, "Net worth (tendance)", (spark.x, spark.y - 14),
                                  fonts.tiny(), config.COL_TEXT_DIM)

                feas = growth >= m["target_pct"] and beta <= m["max_beta"]
                widgets.draw_badge(surf, "EN BONNE VOIE" if feas else "EN RISQUE",
                                   (row.x + 12, row.bottom - 22),
                                   accent=config.COL_UP if feas else config.COL_WARN)
            y += ROW
        surf.set_clip(prev_clip)
        content_h = (y + self.scroll) - list_top
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        if self._max_scroll > 0:
            track = pygame.Rect(act_panel.right - 8, list_area.y, 6, list_area.h)
            pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=3)
            frac = list_area.h / (content_h or 1)
            bar_h = max(24, int(list_area.h * frac))
            bar_y = list_area.y + int((list_area.h - bar_h) * (self.scroll / self._max_scroll))
            pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 6, bar_h), border_radius=3)

        self.back_btn.draw(surf)
