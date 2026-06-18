"""
scene_swaps.py — Desk swaps de devises (cross-currency swap).

Le joueur choisit une devise étrangère, un sens (reçoit le taux étranger ou
le taux domestique), une maturité et un notionnel, puis conclut un swap qui
échange en cash le différentiel de taux entre les deux devises à chaque tour
jusqu'à l'échéance (cf. core/swaps.py). Ouvert via SWAP/SWAPS.
"""
import pygame

from core import config, unlocks
from core import swaps as SW
from core.scene_manager import Scene
from ui import fonts, widgets

NOTIONAL_STEP = 100_000.0
NOTIONAL_MIN = 100_000.0
NOTIONAL_MAX = 5_000_000.0


class SwapsScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.msg = ""
        p = self.app.gs.player
        regions = SW.foreign_regions(p)
        self.region = regions[0] if regions else None
        self.direction = "receive_foreign"
        self.years = SW.TENORS[0]
        self.notional = 500_000.0
        self._region_rects = {}
        self._dir_rects = {}
        self._tenor_rects = {}
        self._notional_rects = {}
        self._enter_rect = None
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.tuto_btn = widgets.Button((config.back_button_rect(160)[0] + 170,
                                        config.back_button_rect(160)[1], 150, 42),
                                       "📘 TUTO", config.COL_CYAN)

    def _can_trade(self):
        return unlocks.unlocked(self.app.gs.player, "trade")

    def _cur(self, region=None):
        region = region or self.app.gs.player.continent
        return config.CONTINENTS.get(region, {}).get("currency", "$")

    # ------------------------------------------------------------- events
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
            return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
            return
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="swaps", return_to="swaps")
            return
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if not self._can_trade():
            return
        for region, rect in self._region_rects.items():
            if rect.collidepoint(event.pos):
                self.region = region
                return
        for direction, rect in self._dir_rects.items():
            if rect.collidepoint(event.pos):
                self.direction = direction
                return
        for years, rect in self._tenor_rects.items():
            if rect.collidepoint(event.pos):
                self.years = years
                return
        for key, rect in self._notional_rects.items():
            if rect.collidepoint(event.pos):
                delta = NOTIONAL_STEP if key == "plus" else -NOTIONAL_STEP
                self.notional = max(NOTIONAL_MIN, min(NOTIONAL_MAX, self.notional + delta))
                return
        if self._enter_rect and self._enter_rect.collidepoint(event.pos) and self.region:
            p = self.app.gs.player
            r = SW.enter_swap(p, self.app.market, self.region, self.direction, self.notional, self.years)
            if r["ok"]:
                self.msg = f"Swap conclu : {self.region} / {self.years} ans / " \
                          f"{widgets.format_money(self.notional, self._cur())}."
                if not p.hardcore:
                    self.app.gs.save(config.AUTOSAVE_SLOT)
            else:
                self.msg = f"Refusé ({r['reason']})."

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)
        self.tuto_btn.update(pygame.mouse.get_pos(), dt)

    # ------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "SWAPS DE DEVISES (CROSS-CURRENCY)", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        if not self._can_trade():
            g = unlocks.required_grade("trade")
            widgets.draw_text(surf, f"⊘ Swaps débloqués au grade {config.GRADES[g]}.",
                              (42, 56), fonts.small(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            self.tuto_btn.draw(surf)
            return
        widgets.draw_text(surf, "Échange le différentiel de taux entre votre devise et une devise "
                                f"étrangère, sans échange de principal. {self.msg}",
                          (42, 56), fonts.small(), config.COL_TEXT_DIM)

        p, m = self.app.gs.player, self.app.market
        ph = config.footer_y() - 8 - 96
        cat = pygame.Rect(40, 96, 660, ph)
        inner = widgets.draw_panel(surf, cat, "Nouveau swap", config.COL_CYAN)
        self._draw_builder(surf, inner, p, m)

        posp = pygame.Rect(720, 96, config.SCREEN_WIDTH - 760, ph)
        pinner = widgets.draw_panel(surf, posp, "Vos swaps", config.COL_PRESTIGE)
        self._draw_holdings(surf, pinner, p, m)

        self.back_btn.draw(surf)
        self.tuto_btn.draw(surf)

    def _draw_builder(self, surf, inner, p, m):
        cur_home = self._cur()
        x, y = inner.x, inner.y
        widgets.draw_text(surf, f"Devise domestique : {p.continent} ({cur_home})",
                          (x, y), fonts.small(), config.COL_TEXT_DIM)
        y += 26

        # ---- choix de la devise étrangère ----
        widgets.draw_text(surf, "Devise étrangère :", (x, y), fonts.small(bold=True), config.COL_AMBER)
        y += 22
        self._region_rects = {}
        for region in SW.foreign_regions(p):
            q = SW.quote(m, p, region)
            row = pygame.Rect(x, y, inner.w, 24)
            sel = (region == self.region)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, row, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER, row, 1, border_radius=3)
            self._region_rects[region] = row
            widgets.draw_text(surf, f"{region} ({self._cur(region)})", (row.x + 8, row.y + 4),
                              fonts.tiny(bold=sel), config.COL_TEXT)
            dcol = config.COL_UP if q["diff"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"taux {q['foreign_rate']*100:.2f}%  écart {q['diff']*100:+.2f}%",
                              (row.right - 12, row.y + 4), fonts.tiny(), dcol, align="right")
            y += 27
        y += 10

        # ---- sens du swap ----
        widgets.draw_text(surf, "Sens :", (x, y), fonts.small(bold=True), config.COL_AMBER)
        y += 22
        self._dir_rects = {}
        for direction in SW.DIRECTIONS:
            w = inner.w
            row = pygame.Rect(x, y, w, 26)
            sel = (direction == self.direction)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, row, border_radius=3)
            pygame.draw.rect(surf, config.COL_UP if sel else config.COL_BORDER, row, 1, border_radius=3)
            self._dir_rects[direction] = row
            widgets.draw_text(surf, SW.DIRECTION_LABEL[direction], row.center, fonts.tiny(bold=sel),
                              config.COL_TEXT, align="center")
            y += 30
        y += 6

        # ---- maturité ----
        widgets.draw_text(surf, "Maturité :", (x, y), fonts.small(bold=True), config.COL_AMBER)
        ty = y
        self._tenor_rects = {}
        tx = x + 110
        for years in SW.TENORS:
            label = f"{years} ans"
            w = fonts.small(bold=True).size(label)[0] + 24
            rect = pygame.Rect(tx, ty - 3, w, 24)
            sel = (years == self.years)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER, rect, 1, border_radius=3)
            self._tenor_rects[years] = rect
            widgets.draw_text(surf, label, rect.center, fonts.small(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM, align="center")
            tx += w + 8
        y += 36

        # ---- notionnel ----
        widgets.draw_text(surf, "Notionnel :", (x, y), fonts.small(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, widgets.format_money(self.notional, cur_home), (x + 110, y),
                          fonts.small(bold=True), config.COL_WHITE)
        minus = pygame.Rect(x + 260, y - 3, 26, 24)
        plus = pygame.Rect(x + 290, y - 3, 26, 24)
        self._notional_rects = {"minus": minus, "plus": plus}
        for rect, sym in ((minus, "-"), (plus, "+")):
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
            pygame.draw.rect(surf, config.COL_BORDER, rect, 1)
            widgets.draw_text(surf, sym, rect.center, fonts.body(bold=True), config.COL_AMBER, align="center")
        y += 38

        # ---- estimation du carry ----
        if self.region:
            q = SW.quote(m, p, self.region)
            net = q["diff"] if self.direction == "receive_foreign" else -q["diff"]
            carry = self.notional * net
            ccol = config.COL_UP if carry >= 0 else config.COL_DOWN
            box = pygame.Rect(x, y, inner.w, 56)
            pygame.draw.rect(surf, config.COL_PANEL, box, border_radius=4)
            pygame.draw.rect(surf, ccol, box, 1, border_radius=4)
            widgets.draw_text(surf, f"Écart de taux net : {net*100:+.2f}%/an", (box.x + 12, box.y + 8),
                              fonts.small(), config.COL_TEXT)
            widgets.draw_text(surf, f"Carry annuel estimé : {widgets.format_money(carry, cur_home)}",
                              (box.x + 12, box.y + 28), fonts.small(bold=True), ccol)
            y += 64

        self._enter_rect = pygame.Rect(x, y, 200, 32)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._enter_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_UP, self._enter_rect, 1, border_radius=4)
        widgets.draw_text(surf, "CONCLURE LE SWAP", self._enter_rect.center, fonts.small(bold=True),
                          config.COL_UP, align="center")

    def _draw_holdings(self, surf, pinner, p, m):
        hold = SW.holdings(p, m)
        if not hold:
            widgets.draw_text(surf, "Aucun swap en cours.", (pinner.x, pinner.y),
                              fonts.small(), config.COL_TEXT_DIM)
            return
        cur_home = self._cur()
        y = pinner.y
        for h in hold:
            dir_lbl = "REÇOIT ÉTR." if h["direction"] == "receive_foreign" else "REÇOIT DOM."
            widgets.draw_text(surf, f"#{h['id']} {h['home_region']} ↔ {h['foreign_region']}",
                              (pinner.x, y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_badge(surf, dir_lbl, (pinner.right, y), accent=config.COL_CYAN, align="right")
            ccol = config.COL_UP if h["annual_carry"] >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"Notionnel {widgets.format_money(h['notional'], cur_home)} · "
                                    f"écart {h['net_rate']*100:+.2f}%/an",
                              (pinner.x, y + 20), fonts.tiny(), config.COL_TEXT_DIM)
            widgets.draw_text(surf, f"Carry annuel {widgets.format_money(h['annual_carry'], cur_home)} · "
                                    f"{h['years_left']:.1f} an(s) restant(es)",
                              (pinner.x, y + 36), fonts.tiny(), ccol)
            y += 56
