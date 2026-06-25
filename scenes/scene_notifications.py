"""
scene_notifications.py — Centre de notifications unifié : fusionne la
messagerie (player.inbox — manager, client, conformité, desk, RH, pays,
veille, dont les alertes de prix franchies) et le fil d'actualités
(player.news_history) en un seul flux chronologique filtrable par source.
Cliquer une ligne navigue vers l'écran dédié (INBOX ou NEWS) correspondant,
en pré-sélectionnant l'élément cliqué pour les interactions complètes.
"""
import pygame

from core import config
from core import news as N
from core.scene_manager import Scene
from ui import fonts, widgets

_INBOX_KIND = {
    "manager": ("MANAGER", config.COL_AMBER), "client": ("CLIENT", config.COL_CYAN),
    "compliance": ("CONFORMITÉ", config.COL_DOWN), "desk": ("DESK", config.COL_TEXT),
    "hr": ("RH", config.COL_UP), "country": ("PAYS", config.COL_PRESTIGE),
    "research": ("VEILLE", config.COL_CYAN),
}
_NEWS_KIND_COL = {"good": config.COL_UP, "bad": config.COL_DOWN, "info": config.COL_CYAN}
ROW_H = 24
_SOURCE_CHIPS = [(None, "TOUTES"), ("inbox", "MESSAGES"), ("news", "ACTUALITÉS")]


class NotificationsScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.source_filter = None
        self.search = ""
        self.scroll = 0
        self._max_scroll = 0
        self._list_rect = None
        self._chip_rects = {}
        self._search_clear_rect = None
        self.row_rects = []      # [(rect, ("inbox", idx) | ("news", entry))]
        self._t = 0.0
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def _rows(self):
        p = self.app.gs.player
        out = []
        if self.source_filter in (None, "inbox"):
            for idx, m in enumerate(p.inbox):
                tag, col = _INBOX_KIND.get(m["kind"], ("•", config.COL_TEXT))
                out.append({"src": "inbox", "ref": idx, "day": m["day"], "tag": tag,
                            "col": col, "text": f"{m['subject']} — {m['body']}",
                            "read": m.get("read", False)})
        if self.source_filter in (None, "news"):
            for e in N.query(p):
                col = _NEWS_KIND_COL.get(e["kind"], config.COL_TEXT)
                out.append({"src": "news", "ref": e, "day": e["day"],
                            "tag": N.category_label(e["cat"]), "col": col,
                            "text": e["text"], "read": True})
        q = self.search.strip().lower()
        if q:
            out = [r for r in out if q in r["text"].lower()]
        out.sort(key=lambda r: r["day"], reverse=True)
        return out

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
            for val, rect in self._chip_rects.items():
                if rect.collidepoint(event.pos):
                    self.source_filter = val
                    self.scroll = 0
                    return
            for rect, (src, ref) in self.row_rects:
                if rect.collidepoint(event.pos):
                    if src == "inbox":
                        self.app.gs.player.inbox[ref]["read"] = True
                        self.app.scenes.go("inbox", return_to="notifications", select_idx=ref)
                    else:
                        self.app.scenes.go("news", return_to="notifications", search=ref["text"][:60])
                    return

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        p = self.app.gs.player
        unread = sum(1 for m in p.inbox if not m.get("read"))
        widgets.draw_text(surf, "CENTRE DE NOTIFICATIONS", (40, 22),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"Messagerie + actualités en un seul flux · {unread} message(s) non lu(s).",
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        x0 = 40
        top = config.content_top()
        search_rect = pygame.Rect(x0, top, 300, 24)
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

        chip_y = search_rect.bottom + 8
        self._chip_rects = {}
        cx = x0
        for val, label in _SOURCE_CHIPS:
            w = fonts.tiny(bold=True).size(label)[0] + 16
            rect = pygame.Rect(cx, chip_y, w, 20)
            self._chip_rects[val] = rect
            sel = (val == self.source_filter)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, label, rect.center, fonts.tiny(bold=sel),
                              config.COL_CYAN if sel else config.COL_TEXT_DIM, align="center")
            cx += w + 6

        legend_y = chip_y + 26
        widgets.draw_text(surf, "✉ message :", (x0, legend_y), fonts.tiny(), config.COL_TEXT_DIM)
        lx = x0 + 76
        for kind, (tag, col) in _INBOX_KIND.items():
            w = fonts.tiny(bold=True).size(tag)[0]
            widgets.draw_text(surf, tag, (lx, legend_y), fonts.tiny(bold=True), col)
            lx += w + 10
        widgets.draw_text(surf, "📰 actu :", (lx + 14, legend_y), fonts.tiny(), config.COL_TEXT_DIM)
        lx2 = lx + 14 + 60
        for kind_lbl, col in (("bonne", config.COL_UP), ("mauvaise", config.COL_DOWN),
                              ("neutre", config.COL_CYAN)):
            w = fonts.tiny(bold=True).size(kind_lbl)[0]
            widgets.draw_text(surf, kind_lbl, (lx2, legend_y), fonts.tiny(bold=True), col)
            lx2 += w + 10

        rows = self._rows()
        list_top = legend_y + 22
        panel = pygame.Rect(x0, list_top, config.SCREEN_WIDTH - 80, config.footer_y() - 8 - list_top)
        inner = widgets.draw_panel(surf, panel, f"Flux ({len(rows)})", config.COL_CYAN)
        list_area = pygame.Rect(inner.x - 4, inner.y, inner.w + 8, inner.h)
        self._list_rect = list_area
        self.row_rects = []
        if not rows:
            widgets.draw_text(surf, "Aucune notification pour ce filtre.",
                              (inner.x, inner.y), fonts.body(), config.COL_TEXT_DIM)
            self.back_btn.draw(surf)
            return

        mp = pygame.mouse.get_pos()
        prev_clip = surf.get_clip()
        surf.set_clip(list_area)
        y = inner.y - self.scroll
        last_day = None
        for r in rows:
            if r["day"] != last_day:
                last_day = r["day"]
                if (list_area.top - ROW_H) < y < list_area.bottom:
                    widgets.draw_text(surf, f"— Jour {r['day']}", (inner.x, y),
                                      fonts.tiny(bold=True), config.COL_AMBER)
                y += ROW_H
            if (list_area.top - ROW_H) < y < list_area.bottom:
                row = pygame.Rect(inner.x - 4, y - 2, inner.w + 8, ROW_H - 2)
                self.row_rects.append((row, (r["src"], r["ref"])))
                if row.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
                src_tag = "✉" if r["src"] == "inbox" else "📰"
                widgets.draw_text(surf, src_tag, (inner.x, y), fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, widgets.fit_text(r["tag"], fonts.tiny(bold=True), 100),
                                  (inner.x + 20, y), fonts.tiny(bold=True), r["col"])
                bold = not r["read"]
                txt = ("● " if bold else "") + r["text"]
                widgets.draw_text(surf, widgets.fit_text(txt, fonts.small(bold=bold), inner.w - 130),
                                  (inner.x + 130, y), fonts.small(bold=bold),
                                  config.COL_WHITE if bold else config.COL_TEXT)
            y += ROW_H
        surf.set_clip(prev_clip)

        content_h = (y + self.scroll) - inner.y
        self._max_scroll = max(0, content_h - list_area.h)
        self.scroll = min(self.scroll, self._max_scroll)
        self.scroll = widgets.draw_scrollbar(surf, panel, list_area, self.scroll, self._max_scroll, content_h)

        self.back_btn.draw(surf)
