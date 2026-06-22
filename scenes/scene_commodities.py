"""
scene_commodities.py — Matières premières : spot, courbe de futures, roll yield.

Affiche pour chaque commodity le spot, le contrat de premier mois, la structure
de courbe (contango/backwardation) et le roll yield. Achat/vente de contrats.
Le roulement (roll) coûte en contango et rapporte en backwardation, prélevé à
chaque tour. Liste groupée par catégorie, DÉFILABLE, filtrable par catégorie.
Ouvert via CMDTY.
"""
import pygame

from core import commodities as C
from core import config, unlocks
from core.scene_manager import Scene
from ui import fonts, widgets
from ui.popups import PopupMixin

LOT = 5
ROW_H = 26

CATEGORY_ORDER = [
    "Métaux précieux", "Énergie", "Métaux industriels", "Minéraux stratégiques",
    "Céréales & oléagineux", "Softs & tropicaux", "Bétail & laitier",
    "Matériaux & construction", "Exotiques & environnement",
]


class CommoditiesScene(Scene, PopupMixin):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.init_popups()
        self.msg = ""
        self.buy_rects, self.sell_rects = {}, {}
        self.name_rects = {}
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self.cat_filter = None     # None = toutes catégories
        self._cat_rects = {}
        self.search_box = widgets.SearchBox((40, 74, 260, 24), "Tapez pour rechercher…")
        self.back_btn = widgets.Button(config.back_button_rect(160),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def _can_trade(self):
        return unlocks.unlocked(self.app.gs.player, "trade")

    def handle_event(self, event):
        if self.popups_handle_event(event):
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.popups_close_top():
                    return
                if self.search_box.text:
                    self.search_box.text = ""
                    return
                self.app.scenes.go(self.return_to)
                return
            elif event.key == pygame.K_BACKSPACE:
                self.search_box.handle_typing(event)
                return
            elif event.key == pygame.K_PAGEUP:
                self.scroll = max(0, self.scroll - 200)
                return
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll = min(self._max_scroll, self.scroll + 200)
                return
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search_box.handle_typing(event)
                self.scroll = 0
                return
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            for cid, rect in self.name_rects.items():
                if rect.collidepoint(event.pos):
                    self.open_commodity(cid)
                    return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.search_box.handle_clear_click(event):
                return
            for cat, rect in self._cat_rects.items():
                if rect.collidepoint(event.pos):
                    if cat == "__ALL__":
                        self.cat_filter = None
                    else:
                        self.cat_filter = None if self.cat_filter == cat else cat
                    self.scroll = 0
                    return
            for cid, rect in self.name_rects.items():
                if rect.collidepoint(event.pos):
                    self.open_commodity(cid)
                    return
            p, m = self.app.gs.player, self.app.market
            if not self._can_trade():
                return
            for cid, rect in self.buy_rects.items():
                if rect.collidepoint(event.pos):
                    r = C.buy(p, m, cid, LOT)
                    self.msg = (f"Acheté {LOT} {cid}" if r["ok"]
                                else f"Achat refusé ({r['reason']}).")
                    if r["ok"] and not p.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)
            for cid, rect in self.sell_rects.items():
                if rect.collidepoint(event.pos):
                    r = C.sell(p, m, cid, LOT)
                    self.msg = (f"Vendu {cid} (P&L {r['realized']:+.0f})" if r["ok"]
                                else "Aucune position.")
                    if r["ok"] and not p.hardcore:
                        self.app.gs.save(config.AUTOSAVE_SLOT)

    def update(self, dt):
        self.search_box.update(dt)
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        m, p = self.app.market, self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        widgets.draw_text(surf, "MATIÈRES PREMIÈRES — FUTURES", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Contango = futures > spot (roll négatif) · "
                                "backwardation = futures < spot (roll positif). " + self.msg,
                          (42, 50), fonts.small(), config.COL_TEXT_DIM)

        # ---- recherche ----
        self.search_box.draw(surf)

        # chips de catégorie
        self._cat_rects = {}
        cx = 42 + self.search_box.rect.w + 16
        cy = 74
        all_rect = pygame.Rect(cx, cy, 70, 20)
        self._cat_rects["__ALL__"] = all_rect
        sel = self.cat_filter is None
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, all_rect, border_radius=3)
        pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER, all_rect, 1, border_radius=3)
        widgets.draw_text(surf, "TOUTES", all_rect.center, fonts.tiny(bold=sel),
                          config.COL_CYAN if sel else config.COL_TEXT_DIM, align="center")
        cx += 78
        for cat in CATEGORY_ORDER:
            w = max(70, fonts.tiny(bold=True).size(cat)[0] + 16)
            rect = pygame.Rect(cx, cy, w, 20)
            if rect.right > config.SCREEN_WIDTH - 40:
                cx = 42
                cy += 24
                rect = pygame.Rect(cx, cy, w, 20)
            self._cat_rects[cat] = rect
            sel = (self.cat_filter == cat)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if sel else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, cat, rect.center, fonts.tiny(bold=sel),
                              config.COL_AMBER if sel else config.COL_TEXT_DIM, align="center")
            cx += w + 8

        panel_top = cy + 30
        ph = config.footer_y() - 8 - panel_top
        panel = pygame.Rect(40, panel_top, config.SCREEN_WIDTH - 80, ph)
        inner = widgets.draw_panel(surf, panel, "Contrats", config.COL_CYAN)
        cols = [("COMMODITY", inner.x), ("SPOT", inner.x + 280), ("FUTURE 1M", inner.x + 380),
                ("STRUCTURE", inner.x + 500), ("ROLL/AN", inner.x + 660),
                ("VOL", inner.x + 740), ("VOUS", inner.x + 800)]
        for label, x in cols:
            widgets.draw_text(surf, label, (x, inner.y), fonts.tiny(bold=True), config.COL_TEXT_DIM)

        list_top = inner.y + 22
        list_area = pygame.Rect(inner.x - 6, list_top, inner.w + 12, inner.bottom - list_top - 26)
        self._list_rect = list_area
        self.buy_rects, self.sell_rects, self.name_rects = {}, {}, {}
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)

        all_q = C.all_quotes(m)
        q = self.search_box.query
        if q:
            all_q = [r for r in all_q if q in f"{r['name']} {r['id']} {r['category']}".lower()]
        cats = [self.cat_filter] if self.cat_filter else CATEGORY_ORDER
        y = list_top - self.scroll
        for cat in cats:
            q_cat = [q for q in all_q if q["category"] == cat]
            if not q_cat:
                continue
            y = self._draw_group(surf, cat, q_cat, y, p, list_area, cols, cur)
        surf.set_clip(prev_clip)

        content_h = (y + self.scroll) - list_top
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        if self._max_scroll > 0:
            track = pygame.Rect(panel.right - 8, list_area.y, 6, list_area.h)
            pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=3)
            frac = list_area.h / (content_h or 1)
            bar_h = max(24, int(list_area.h * frac))
            bar_y = list_area.y + int((list_area.h - bar_h) * (self.scroll / self._max_scroll))
            pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 6, bar_h), border_radius=3)

        hv = C.holdings_value(p, m)
        widgets.draw_text(surf, f"Valeur commodities détenue : {widgets.format_money(hv, cur)}"
                          + ("" if self._can_trade() else "   ⊘ trading débloqué au grade Associate"),
                          (inner.x, inner.bottom - 22), fonts.small(bold=True),
                          config.COL_UP if hv else config.COL_TEXT_DIM)
        self.back_btn.draw(surf)
        self.popups_draw(surf)

    def _draw_group(self, surf, title, quotes, y, p, list_area, cols, cur):
        widgets.draw_text(surf, f"— {title} ({len(quotes)})", (cols[0][1], y),
                          fonts.tiny(bold=True), config.COL_AMBER)
        y += 20
        for q in quotes:
            visible = (list_area.top - ROW_H) < y < list_area.bottom
            if visible:
                pos = p.commodities.get(q["id"])
                held = pos["qty"] if pos else 0
                name_w = min(260, fonts.small(bold=True).size(q["name"])[0])
                self.name_rects[q["id"]] = pygame.Rect(cols[0][1] - 2, y - 2, name_w + 4, ROW_H - 4)
                widgets.draw_text(surf, widgets.fit_text(q["name"], fonts.small(bold=True), 260),
                                  (cols[0][1], y), fonts.small(bold=True), config.COL_TEXT)
                widgets.draw_text(surf, f"{q['spot']:,.2f}".replace(",", " "), (cols[1][1], y), fonts.small(), config.COL_WHITE)
                widgets.draw_text(surf, f"{q['front']:,.2f}".replace(",", " "), (cols[2][1], y), fonts.small(bold=True), config.COL_WHITE)
                scol = (config.COL_DOWN if q["structure"] == "Contango" else
                        config.COL_UP if q["structure"] == "Backwardation" else config.COL_TEXT_DIM)
                widgets.draw_text(surf, q["structure"], (cols[3][1], y), fonts.small(bold=True), scol)
                rcol = config.COL_UP if q["roll_yield"] >= 0 else config.COL_DOWN
                widgets.draw_text(surf, f"{q['roll_yield']*100:+.1f}%", (cols[4][1], y), fonts.small(), rcol)
                widgets.draw_text(surf, f"{q['vol']*100:.0f}%", (cols[5][1], y), fonts.small(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, f"{held:.0f}", (cols[6][1], y), fonts.small(),
                                  config.COL_UP if held else config.COL_TEXT_DIM)
                if self._can_trade():
                    br = pygame.Rect(cols[6][1] + 56, y - 2, 42, 20)
                    sr = pygame.Rect(cols[6][1] + 104, y - 2, 42, 20)
                    self.buy_rects[q["id"]] = br
                    self.sell_rects[q["id"]] = sr
                    for rect, sym, c2 in ((br, f"+{LOT}", config.COL_UP), (sr, f"-{LOT}", config.COL_DOWN)):
                        pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect, border_radius=3)
                        widgets.draw_text(surf, sym, (rect.x + 6, y), fonts.tiny(bold=True), c2)
            y += ROW_H
        return y + 6
