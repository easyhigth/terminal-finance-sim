"""
scene_inbox.py — Boîte de réception (monde vivant).
Liste des messages à gauche (non-lus en gras), volet de lecture à droite.
Cliquer un message le marque comme lu. Ouvert via INBOX / MAIL.
"""
import pygame

from core import config
from core.i18n import get_lang
from core.scene_manager import Scene
from ui import fonts, keynav, widgets


def _L(fr, en):
    return en if get_lang() == "en" else fr


_KIND = {
    "manager": (("MANAGER", "MANAGER"), config.COL_AMBER),
    "client": (("CLIENT", "CLIENT"), config.COL_CYAN),
    "compliance": (("CONFORMITÉ", "COMPLIANCE"), config.COL_DOWN),
    "desk": (("DESK", "DESK"), config.COL_TEXT),
    "hr": (("RH", "HR"), config.COL_UP),
    "country": (("PAYS", "COUNTRY"), config.COL_PRESTIGE),
    "research": (("VEILLE", "RESEARCH"), config.COL_CYAN),
}


def _kind_label(kind):
    pair = _KIND.get(kind)
    return _L(*pair[0]) if pair else kind


FILTER_CHIPS = [(None, ("TOUS", "ALL"))] + [(k, v[0]) for k, v in _KIND.items()]
ROW_H = 46


class InboxScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        self.app.gs.player.flags["onboarding_seen_inbox"] = True
        msgs = self.app.gs.player.inbox
        # plus récents en haut ; sélectionne le 1er par défaut, sauf si on
        # arrive depuis le centre de notifications avec un message précis visé
        self.order = list(reversed(range(len(msgs))))
        select_idx = kwargs.get("select_idx")
        if select_idx is not None and 0 <= select_idx < len(msgs):
            self.sel = select_idx
        else:
            self.sel = self.order[0] if self.order else None
        if self.sel is not None:
            msgs[self.sel]["read"] = True
        self.row_rects = {}
        self.search = ""
        self._search_clear_rect = None
        self.kind_filter = None
        self._kind_rects = {}
        self._t = 0.0
        self.cursor = self.order.index(self.sel) if self.sel in self.order else 0
        self.scroll = 0
        self._pending_scroll = select_idx is not None
        self._max_scroll = 0
        self._list_rect = None
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def _visible_order(self):
        msgs = self.app.gs.player.inbox
        q = self.search.strip().lower()
        order = self.order
        if self.kind_filter:
            order = [idx for idx in order if msgs[idx]["kind"] == self.kind_filter]
        if q:
            order = [idx for idx in order
                     if q in f"{_kind_label(msgs[idx]['kind'])} {msgs[idx].get('sender', '')} "
                              f"{msgs[idx].get('subject', '')} {msgs[idx].get('body', '')}".lower()]
        return order

    def _scroll_to_cursor(self):
        """Ajuste le scroll pour garder la ligne sélectionnée au clavier visible."""
        if not self._list_rect:
            return
        row_top = self.cursor * ROW_H
        row_bottom = row_top + ROW_H
        if row_top < self.scroll:
            self.scroll = row_top
        elif row_bottom > self.scroll + self._list_rect.h:
            self.scroll = row_bottom - self._list_rect.h
        self.scroll = max(0, min(self._max_scroll, self.scroll))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search:
                    self.search = ""
                    return
                self.app.scenes.back(self.return_to)
                return
            elif event.key == pygame.K_BACKSPACE:
                self.search = self.search[:-1]
                return
            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN, pygame.K_KP_ENTER):
                visible = self._visible_order()
                self.cursor, activate = widgets.list_key_nav(event, self.cursor, len(visible))
                if visible:
                    self._scroll_to_cursor()
                if activate:
                    idx = visible[self.cursor]
                    self.sel = idx
                    self.app.gs.player.inbox[idx]["read"] = True
                return
            elif event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
                self.search += event.unicode
                self.scroll = 0
                return
        if self.back_btn.handle(event):
            self.app.scenes.back(self.return_to)
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
            for kind, rect in self._kind_rects.items():
                if rect.collidepoint(event.pos):
                    self.kind_filter = kind
                    self.scroll = 0
                    return
            for idx, rect in self.row_rects.items():
                if rect.collidepoint(event.pos):
                    self.sel = idx
                    self.app.gs.player.inbox[idx]["read"] = True
                    visible = self._visible_order()
                    if idx in visible:
                        self.cursor = visible.index(idx)

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        msgs = self.app.gs.player.inbox
        unread = sum(1 for m in msgs if not m.get("read"))
        widgets.draw_text(surf, _L("MESSAGERIE", "MAILBOX"), (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, _L(f"{len(msgs)} messages · {unread} non lus", f"{len(msgs)} messages · {unread} unread"),
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        # ---- recherche ----
        search_rect = pygame.Rect(40, 100, 300, 24)
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else (cursor + _L("Tapez pour rechercher…", "Type to search…"))
        col = config.COL_TEXT if self.search else config.COL_TEXT_DIM
        widgets.draw_text(surf, widgets.fit_text(label, fonts.small(), search_rect.w - 30),
                          (search_rect.x + 8, search_rect.y + 4), fonts.small(), col)
        self._search_clear_rect = None
        if self.search:
            self._search_clear_rect = pygame.Rect(search_rect.right - 22, search_rect.y, 22, search_rect.h)
            widgets.draw_text(surf, "✕", self._search_clear_rect.center, fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")

        # ---- chips de filtre par type ----
        chip_y = search_rect.bottom + 8
        self._kind_rects = {}
        cx = 40
        for kind, label_pair in FILTER_CHIPS:
            label = _L(*label_pair)
            w = fonts.tiny(bold=True).size(label)[0] + 14
            rect = pygame.Rect(cx, chip_y, w, 20)
            self._kind_rects[kind] = rect
            sel = (kind == self.kind_filter)
            _, kcol = _KIND.get(kind, (("", ""), config.COL_AMBER)) if kind else (("", ""), config.COL_AMBER)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, kcol if sel else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, label, rect.center, fonts.tiny(bold=sel),
                              kcol if sel else config.COL_TEXT_DIM, align="center")
            cx += w + 6

        if self.kind_filter:
            klabel = _kind_label(self.kind_filter)
            widgets.draw_text(surf, _L(f"Filtre actif : {klabel} — cliquez TOUS pour réinitialiser.", f"Active filter: {klabel} — click ALL to reset."),
                              (cx + 14, chip_y + 2), fonts.tiny(), config.COL_AMBER)

        # liste à gauche
        list_top = chip_y + 28
        ph = config.footer_y() - 8 - list_top
        listp = pygame.Rect(40, list_top, 480, ph)
        order = self._visible_order()
        self.cursor = min(self.cursor, len(order) - 1) if order else 0
        linner = widgets.draw_panel(surf, listp, _L(f"Reçus ({len(order)})", f"Inbox ({len(order)})"), config.COL_CYAN)
        list_area = pygame.Rect(linner.x - 4, linner.y, linner.w + 8, linner.h)
        self._list_rect = list_area
        if self._pending_scroll:
            self._pending_scroll = False
            self._scroll_to_cursor()
        self.row_rects = {}
        if not msgs:
            widgets.draw_text(surf, "Aucun message pour l'instant.", (linner.x, linner.y),
                              fonts.body(), config.COL_TEXT_DIM)
            self.scroll = self._max_scroll = 0
        elif not order:
            widgets.draw_text(surf, "Aucun message ne correspond au filtre.", (linner.x, linner.y),
                              fonts.body(), config.COL_TEXT_DIM)
            self.scroll = self._max_scroll = 0
        else:
            prev_clip = surf.get_clip()
            surf.set_clip(list_area)
            y = linner.y - self.scroll
            for pos, idx in enumerate(order):
                visible = (list_area.top - ROW_H) < y < list_area.bottom
                if visible:
                    m = msgs[idx]
                    row = pygame.Rect(linner.x - 4, y - 2, linner.w + 8, ROW_H)
                    self.row_rects[idx] = row
                    sel = (idx == self.sel)
                    if sel:
                        pygame.draw.rect(surf, config.COL_PANEL_HEAD, row)
                    keynav.draw_focus_ring(surf, row, pos == self.cursor)
                    _kp, tcol = _KIND.get(m["kind"], (("•", "•"), config.COL_TEXT))
                    tag = _L(*_kp)
                    bold = not m.get("read")
                    widgets.draw_text(surf, tag, (linner.x, y), fonts.tiny(bold=True), tcol)
                    widgets.draw_text(surf, f"J{m['day']}", (linner.right - 40, y),
                                      fonts.tiny(), config.COL_TEXT_DIM)
                    subj = ("● " if bold else "") + m["subject"]
                    widgets.draw_text(surf, subj[:42], (linner.x, y + 16),
                                      fonts.small(bold=bold),
                                      config.COL_WHITE if bold else config.COL_TEXT)
                y += ROW_H
            surf.set_clip(prev_clip)
            content_h = (y + self.scroll) - linner.y
            self._max_scroll = max(0, content_h - list_area.h)
            self.scroll = min(self.scroll, self._max_scroll)
            self.scroll = widgets.draw_scrollbar(surf, listp, list_area, self.scroll, self._max_scroll, content_h)

        # volet de lecture à droite
        readp = pygame.Rect(540, list_top, config.SCREEN_WIDTH - 580, ph)
        rinner = widgets.draw_panel(surf, readp, "Lecture", config.COL_AMBER)
        if self.sel is not None and 0 <= self.sel < len(msgs):
            m = msgs[self.sel]
            _kp, tcol = _KIND.get(m["kind"], (("•", "•"), config.COL_TEXT))
            tag = _L(*_kp)
            widgets.draw_badge(surf, tag, (rinner.x, rinner.y), tcol)
            widgets.draw_text(surf, _L(f"Jour {m['day']}", f"Day {m['day']}"), (rinner.right, rinner.y),
                              fonts.small(), config.COL_TEXT_DIM, align="right")
            widgets.draw_text(surf, m["subject"], (rinner.x, rinner.y + 30),
                              fonts.head(bold=True), config.COL_WHITE)
            widgets.draw_text(surf, "De : " + m["sender"], (rinner.x, rinner.y + 64),
                              fonts.small(), tcol)
            pygame.draw.line(surf, config.COL_BORDER, (rinner.x, rinner.y + 88),
                             (rinner.right, rinner.y + 88), 1)
            widgets.draw_text_wrapped(surf, m["body"], (rinner.x, rinner.y + 100),
                                      fonts.body(), config.COL_TEXT, rinner.w, line_gap=6)
        else:
            widgets.draw_text(surf, _L("Sélectionnez un message.", "Select a message."), (rinner.x, rinner.y),
                              fonts.body(), config.COL_TEXT_DIM)

        self.back_btn.draw(surf)
