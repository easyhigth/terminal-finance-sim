"""
app_inbox.py — Application « Inbox » du bureau (messagerie NATIVE).

Jusqu'ici la messagerie s'ouvrait en fenêtre via l'hébergement de la scène
plein écran (`scenes/scene_inbox.py`, rendue hors-champ en 1280×720 puis
réduite par smoothscale — donc floue, cf. apps/scene_host.py). Cette app
dessine directement à la résolution de la fenêtre, comme Recherche/Trading/
Tableur : texte net à toute taille. La scène plein écran reste enregistrée
(compat navigation hors bureau), mais toute ouverture EN FENÊTRE sur le
bureau est redirigée ici (cf. DesktopScene._open_scene_window).
"""
import pygame

from apps.base import DesktopApp
from core import config
from scenes.scene_inbox import _KIND, FILTER_CHIPS
from ui import fonts, keynav, widgets

ROW_H = 40


class InboxApp(DesktopApp):
    title = "Inbox"
    icon_kind = "inbox"
    default_size = (880, 540)
    min_size = (540, 320)

    def on_open(self):
        p = self.app.gs.player
        p.flags["onboarding_seen_inbox"] = True
        msgs = p.inbox
        # plus récent sélectionné par défaut (l'ordre d'affichage est inversé)
        self.sel = len(msgs) - 1 if msgs else None
        if self.sel is not None:
            msgs[self.sel]["read"] = True
        self.search = ""
        self.kind_filter = None
        self.cursor = 0
        self.scroll = 0
        self._t = 0.0
        self._max_scroll = 0
        self._list_rect = None
        self._row_rects = {}
        self._kind_rects = {}
        self._search_clear_rect = None
        self._pending_scroll = False

    def select_message(self, idx):
        """Cible un message précis (lien depuis le centre de notifications /
        la recherche globale) : sélectionne, marque lu, scrolle dessus."""
        msgs = self.app.gs.player.inbox
        if idx is None or not (0 <= idx < len(msgs)):
            return
        self.sel = idx
        msgs[idx]["read"] = True
        visible = self._visible_order()
        if idx in visible:
            self.cursor = visible.index(idx)
            self._pending_scroll = True

    # --------------------------------------------------------------- données
    def _visible_order(self):
        msgs = self.app.gs.player.inbox
        order = list(reversed(range(len(msgs))))     # plus récents en haut
        q = self.search.strip().lower()
        if self.kind_filter:
            order = [i for i in order if msgs[i]["kind"] == self.kind_filter]
        if q:
            order = [i for i in order
                     if q in f"{_KIND.get(msgs[i]['kind'], ('', None))[0]} {msgs[i].get('sender', '')} "
                             f"{msgs[i].get('subject', '')} {msgs[i].get('body', '')}".lower()]
        return order

    def _scroll_to_cursor(self):
        if not self._list_rect:
            return
        row_top = self.cursor * ROW_H
        row_bottom = row_top + ROW_H
        if row_top < self.scroll:
            self.scroll = row_top
        elif row_bottom > self.scroll + self._list_rect.h:
            self.scroll = row_bottom - self._list_rect.h
        self.scroll = max(0, min(self._max_scroll, self.scroll))

    def update(self, dt):
        self._t += dt

    # --------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and self.search:
                self.search = ""
                return True
            if event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                return True
            if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                visible = self._visible_order()
                self.cursor, activate = widgets.list_key_nav(event, self.cursor, len(visible))
                if visible:
                    self._scroll_to_cursor()
                if activate and visible:
                    idx = visible[self.cursor]
                    self.sel = idx
                    self.app.gs.player.inbox[idx]["read"] = True
                return True
            if event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search += event.unicode
                self.scroll = 0
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-48 if event.button == 4 else 48)))
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return True
            for kind, r in self._kind_rects.items():
                if r.collidepoint(event.pos):
                    self.kind_filter = kind
                    self.scroll = 0
                    return True
            for idx, r in self._row_rects.items():
                if r.collidepoint(event.pos):
                    self.sel = idx
                    self.app.gs.player.inbox[idx]["read"] = True
                    visible = self._visible_order()
                    if idx in visible:
                        self.cursor = visible.index(idx)
                    return True
        return False

    # ----------------------------------------------------------------- draw
    def draw(self, surf, rect):
        surf.fill(config.COL_PANEL, rect)
        pad = 10
        msgs = self.app.gs.player.inbox
        unread = sum(1 for m in msgs if not m.get("read"))
        widgets.draw_text(surf, f"MESSAGERIE — {len(msgs)} message(s) · {unread} non lu(s)",
                          (rect.x + pad, rect.y + pad), fonts.small(bold=True), config.COL_AMBER)

        # recherche
        search_rect = pygame.Rect(rect.x + pad, rect.y + pad + 22,
                                  min(300, rect.w - 2 * pad), 24)
        pygame.draw.rect(surf, config.COL_BG, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else (cursor + "Tapez pour rechercher…")
        col = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 4), fonts.small(), col)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 22, search_rect.y,
                                                  22, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center,
                              fonts.small(bold=True), config.COL_TEXT_DIM, align="center")

        # chips de filtre par type (à droite de la recherche si la place le
        # permet, sinon sur la ligne suivante)
        self._kind_rects = {}
        cx = search_rect.right + 10
        chip_y = search_rect.y + 2
        chips_w = sum(fonts.tiny(bold=True).size(lbl)[0] + 20 for _k, lbl in FILTER_CHIPS)
        if cx + chips_w > rect.right - pad:
            cx = rect.x + pad
            chip_y = search_rect.bottom + 6
        for kind, label in FILTER_CHIPS:
            w = fonts.tiny(bold=True).size(label)[0] + 14
            r = pygame.Rect(cx, chip_y, w, 20)
            self._kind_rects[kind] = r
            sel = (kind == self.kind_filter)
            _, kcol = _KIND.get(kind, ("", config.COL_AMBER)) if kind else ("", config.COL_AMBER)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_BG, r, border_radius=3)
            pygame.draw.rect(surf, kcol if sel else config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=sel),
                              kcol if sel else config.COL_TEXT_DIM, align="center")
            cx += w + 6

        # panneaux liste / lecture
        top = max(search_rect.bottom, chip_y + 20) + 8
        panes = pygame.Rect(rect.x + pad, top, rect.w - 2 * pad,
                            rect.bottom - top - pad)
        list_w = max(230, int(panes.w * 0.42))
        list_area = pygame.Rect(panes.x, panes.y, list_w, panes.h)
        read_area = pygame.Rect(list_area.right + 8, panes.y,
                                panes.right - list_area.right - 8, panes.h)
        pygame.draw.rect(surf, config.COL_BG, list_area)
        pygame.draw.rect(surf, config.COL_BORDER, list_area, 1)
        self._list_rect = list_area
        order = self._visible_order()
        self.cursor = min(self.cursor, len(order) - 1) if order else 0
        if self._pending_scroll:
            self._pending_scroll = False
            self._scroll_to_cursor()
        self._row_rects = {}
        if not order:
            txt = ("Aucun message pour l'instant." if not msgs
                   else "Aucun message ne correspond au filtre.")
            widgets.draw_text(surf, txt, (list_area.x + 8, list_area.y + 8),
                              fonts.small(), config.COL_TEXT_DIM)
            self.scroll = self._max_scroll = 0
        else:
            prev_clip = surf.get_clip()
            surf.set_clip(list_area)
            y = list_area.y + 2 - self.scroll
            for pos, idx in enumerate(order):
                if (list_area.top - ROW_H) < y < list_area.bottom:
                    m = msgs[idx]
                    row = pygame.Rect(list_area.x + 2, y, list_area.w - 4, ROW_H - 2)
                    self._row_rects[idx] = row
                    if idx == self.sel:
                        pygame.draw.rect(surf, config.COL_PANEL_HEAD, row)
                        pygame.draw.rect(surf, config.COL_AMBER, (row.x, row.y, 3, row.h))
                    keynav.draw_focus_ring(surf, row, pos == self.cursor)
                    tag, tcol = _KIND.get(m["kind"], ("•", config.COL_TEXT))
                    bold = not m.get("read")
                    widgets.draw_text(surf, tag, (row.x + 6, y + 3), fonts.tiny(bold=True), tcol)
                    widgets.draw_text(surf, f"J{m['day']}", (row.right - 8, y + 3),
                                      fonts.tiny(), config.COL_TEXT_DIM, align="right")
                    subj = ("● " if bold else "") + m["subject"]
                    widgets.draw_text(surf, widgets.fit_text(subj, fonts.small(bold=bold), row.w - 16),
                                      (row.x + 6, y + 18), fonts.small(bold=bold),
                                      config.COL_WHITE if bold else config.COL_TEXT)
                y += ROW_H
            surf.set_clip(prev_clip)
            content_h = len(order) * ROW_H + 4
            self._max_scroll = max(0, content_h - list_area.h)
            self.scroll = min(self.scroll, self._max_scroll)
            self.scroll = widgets.draw_scrollbar(surf, list_area, list_area, self.scroll,
                                                 self._max_scroll, content_h)

        # volet de lecture
        pygame.draw.rect(surf, config.COL_BG, read_area)
        pygame.draw.rect(surf, config.COL_BORDER, read_area, 1)
        rx, ry = read_area.x + 12, read_area.y + 10
        if self.sel is not None and 0 <= self.sel < len(msgs):
            m = msgs[self.sel]
            tag, tcol = _KIND.get(m["kind"], ("•", config.COL_TEXT))
            widgets.draw_badge(surf, tag, (rx, ry), tcol)
            widgets.draw_text(surf, f"Jour {m['day']}", (read_area.right - 12, ry),
                              fonts.tiny(), config.COL_TEXT_DIM, align="right")
            widgets.draw_text(surf, widgets.fit_text(m["subject"], fonts.head(bold=True),
                                                     read_area.w - 100),
                              (rx, ry + 24), fonts.head(bold=True), config.COL_WHITE)
            widgets.draw_text(surf, "De : " + m["sender"], (rx, ry + 52),
                              fonts.tiny(), tcol)
            pygame.draw.line(surf, config.COL_BORDER, (rx, ry + 70),
                             (read_area.right - 12, ry + 70), 1)
            prev_clip = surf.get_clip()
            surf.set_clip(read_area)
            widgets.draw_text_wrapped(surf, m["body"], (rx, ry + 80),
                                      fonts.small(), config.COL_TEXT,
                                      read_area.w - 24, line_gap=5)
            surf.set_clip(prev_clip)
        else:
            widgets.draw_text(surf, "Sélectionnez un message.", (rx, ry),
                              fonts.small(), config.COL_TEXT_DIM)
