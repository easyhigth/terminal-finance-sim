"""
scene_news.py — NEWS & ÉVÉNEMENTS : fil d'actualités persistant et filtrable.

Centralise tout ce qui se passe dans la partie (marché, macro, entreprises,
politique, réglementaire, événements) en un fil unique, horodaté, consultable
jusqu'à 3 ans en arrière. Filtres par TYPE (catégorie) et par RÉGION ; les
items sont regroupés par jour, du plus récent au plus ancien. Les news du jour
sont aussi affichées en marqueurs persistants sur la carte du terminal.
Ouvert via NEWS.
"""
import pygame

from core import config
from core import news as N
from core.scene_manager import Scene
from ui import fonts, widgets

ROW_H = 22
_KIND_COL = {"good": config.COL_UP, "bad": config.COL_DOWN, "info": config.COL_CYAN}
_KIND_TAG = {"good": "▲", "bad": "▼", "info": "◆"}


class NewsScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.cat_filter = None
        self.region_filter = None
        self.search = ""
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self._cat_rects = {}
        self._region_rects = {}
        self._search_clear_rect = None
        self._t = 0.0
        self.back_btn = widgets.Button(config.back_button_rect(180),
                                       f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

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
            elif event.key == pygame.K_PAGEUP:
                self.scroll = max(0, self.scroll - 200)
                return
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll = min(self._max_scroll, self.scroll + 200)
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
            for val, rect in self._cat_rects.items():
                if rect.collidepoint(event.pos):
                    self.cat_filter = None if self.cat_filter == val else val
                    self.scroll = 0
                    return
            for val, rect in self._region_rects.items():
                if rect.collidepoint(event.pos):
                    self.region_filter = None if self.region_filter == val else val
                    self.scroll = 0
                    return

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        items = N.query(p, cat=self.cat_filter, region=self.region_filter)
        q = self.search.strip().lower()
        if q:
            items = [e for e in items if q in f"{e['text']} {e['region'] or ''}".lower()]
        widgets.draw_text(surf, "NEWS", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Tout ce qui agite la partie — filtrez par type ou région. "
                                "Historique conservé jusqu'à 3 ans.",
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        x0 = 40
        top = config.content_top()

        # ---- recherche ----
        search_rect = pygame.Rect(x0, top, 300, 24)
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else (cursor + "Tapez pour rechercher dans le texte…")
        col = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 4), fonts.small(), col)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 22, search_rect.y, 22, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        counts = N.counts_by_category(p)
        cat_chips = [(None, f"TOUTES ({len(getattr(p, 'news_history', []) or [])})")]
        cat_chips += [(k, f"{lbl} ({counts.get(k, 0)})") for k, lbl in N.CATEGORIES]
        self._cat_rects, ybot = self._chip_row(surf, x0, top + 30, config.SCREEN_WIDTH - 40,
                                               cat_chips, self.cat_filter, config.COL_AMBER)
        regions = sorted({e["region"] for e in (getattr(p, "news_history", []) or []) if e["region"]})
        region_chips = [(None, "TOUTES RÉGIONS")] + [(r, r) for r in regions]
        self._region_rects, ybot = self._chip_row(surf, x0, ybot + 2, config.SCREEN_WIDTH - 40,
                                                  region_chips, self.region_filter, config.COL_CYAN)
        y = ybot + 6

        panel = pygame.Rect(x0, y, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - y)
        inner = widgets.draw_panel(surf, panel, f"Fil d'actualités ({len(items)})", config.COL_CYAN)
        list_top = inner.y + 4
        list_area = pygame.Rect(inner.x - 6, list_top, inner.w + 12, inner.bottom - list_top - 6)
        self._list_rect = list_area
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        ry = list_top - self.scroll
        last_day = None
        if not items:
            widgets.draw_text(surf, "Aucune actualité pour ce filtre (avancez le temps avec ADV).",
                              (inner.x, list_top + 4), fonts.body(), config.COL_TEXT_DIM)
        for e in items:
            if e["day"] != last_day:
                last_day = e["day"]
                if (list_area.top - ROW_H) < ry < list_area.bottom:
                    q = (e["day"] - 1) // config.DAYS_PER_QUARTER + 1
                    widgets.draw_text(surf, f"— Jour {e['day']}  (T{q})",
                                      (inner.x, ry + 2), fonts.tiny(bold=True), config.COL_AMBER)
                ry += ROW_H
            if (list_area.top - ROW_H) < ry < list_area.bottom:
                col = _KIND_COL.get(e["kind"], config.COL_TEXT)
                tag = _KIND_TAG.get(e["kind"], "•")
                cat = N.CATEGORY_LABEL.get(e["cat"], e["cat"])
                widgets.draw_text(surf, tag, (inner.x + 12, ry), fonts.small(bold=True), col)
                widgets.draw_text(surf, widgets.fit_text(cat, fonts.tiny(), 90),
                                  (inner.x + 32, ry + 1), fonts.tiny(), config.COL_PRESTIGE)
                widgets.draw_text(surf, e["region"] or "Monde", (inner.x + 128, ry + 1),
                                  fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, widgets.fit_text(e["text"], fonts.small(), inner.w - 230),
                                  (inner.x + 210, ry), fonts.small(), config.COL_TEXT)
            ry += ROW_H
        surf.set_clip(prev_clip)

        content_h = (ry + self.scroll) - list_top
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        widgets.draw_scrollbar(surf, panel, list_area, self.scroll, self._max_scroll, content_h)

        self.back_btn.draw(surf)

    def _chip_row(self, surf, x0, y0, x_max, chips, current, accent):
        rects = {}
        x, y = x0, y0
        for value, label in chips:
            w = fonts.tiny(bold=True).size(label)[0] + 16
            if x + w > x_max and x > x0:
                x = x0
                y += 24
            rect = pygame.Rect(x, y, w, 20)
            rects[value] = rect
            sel = (value == current)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, accent if sel else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, label, rect.center, fonts.tiny(bold=sel),
                              accent if sel else config.COL_TEXT_DIM, align="center")
            x += w + 6
        return rects, y + 24
