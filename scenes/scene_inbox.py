"""
scene_inbox.py — Boîte de réception (monde vivant).
Liste des messages à gauche (non-lus en gras), volet de lecture à droite.
Cliquer un message le marque comme lu. Ouvert via INBOX / MAIL.
"""
import pygame

from core import config
from core.scene_manager import Scene
from ui import fonts, widgets

_KIND = {
    "manager": ("MANAGER", config.COL_AMBER),
    "client": ("CLIENT", config.COL_CYAN),
    "compliance": ("CONFORMITÉ", config.COL_DOWN),
    "desk": ("DESK", config.COL_TEXT),
    "hr": ("RH", config.COL_UP),
    "country": ("PAYS", config.COL_PRESTIGE),
}
FILTER_CHIPS = [(None, "TOUS")] + [(k, v[0]) for k, v in _KIND.items()]


class InboxScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        msgs = self.app.gs.player.inbox
        # plus récents en haut ; sélectionne le 1er par défaut
        self.order = list(reversed(range(len(msgs))))
        self.sel = self.order[0] if self.order else None
        if self.sel is not None:
            msgs[self.sel]["read"] = True
        self.row_rects = {}
        self.search = ""
        self._search_clear_rect = None
        self.kind_filter = None
        self._kind_rects = {}
        self._t = 0.0
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

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
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._search_clear_rect and self._search_clear_rect.collidepoint(event.pos):
                self.search = ""
                return
            for kind, rect in self._kind_rects.items():
                if rect.collidepoint(event.pos):
                    self.kind_filter = kind
                    return
            for idx, rect in self.row_rects.items():
                if rect.collidepoint(event.pos):
                    self.sel = idx
                    self.app.gs.player.inbox[idx]["read"] = True

    def update(self, dt):
        self._t += dt
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        msgs = self.app.gs.player.inbox
        unread = sum(1 for m in msgs if not m.get("read"))
        widgets.draw_text(surf, "MESSAGERIE", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"{len(msgs)} messages · {unread} non lus",
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        # ---- recherche ----
        search_rect = pygame.Rect(40, 100, 300, 24)
        pygame.draw.rect(surf, config.COL_PANEL, search_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN if self.search else config.COL_BORDER, search_rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.search + cursor) if self.search else "Tapez pour rechercher…"
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
        for kind, label in FILTER_CHIPS:
            w = fonts.tiny(bold=True).size(label)[0] + 14
            rect = pygame.Rect(cx, chip_y, w, 20)
            self._kind_rects[kind] = rect
            sel = (kind == self.kind_filter)
            _, kcol = _KIND.get(kind, ("", config.COL_AMBER)) if kind else ("", config.COL_AMBER)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_PANEL, rect, border_radius=3)
            pygame.draw.rect(surf, kcol if sel else config.COL_BORDER, rect, 1, border_radius=3)
            widgets.draw_text(surf, label, rect.center, fonts.tiny(bold=sel),
                              kcol if sel else config.COL_TEXT_DIM, align="center")
            cx += w + 6

        # liste à gauche
        list_top = chip_y + 28
        ph = config.footer_y() - 8 - list_top
        listp = pygame.Rect(40, list_top, 480, ph)
        q = self.search.strip().lower()
        order = self.order
        if self.kind_filter:
            order = [idx for idx in order if msgs[idx]["kind"] == self.kind_filter]
        if q:
            order = [idx for idx in order
                     if q in f"{_KIND.get(msgs[idx]['kind'], ('', None))[0]} {msgs[idx].get('sender', '')} "
                              f"{msgs[idx].get('subject', '')} {msgs[idx].get('body', '')}".lower()]
        linner = widgets.draw_panel(surf, listp, f"Reçus ({len(order)})", config.COL_CYAN)
        self.row_rects = {}
        if not msgs:
            widgets.draw_text(surf, "Aucun message pour l'instant.", (linner.x, linner.y),
                              fonts.body(), config.COL_TEXT_DIM)
        elif not order:
            widgets.draw_text(surf, "Aucun message ne correspond au filtre.", (linner.x, linner.y),
                              fonts.body(), config.COL_TEXT_DIM)
        else:
            y = linner.y
            for idx in order:
                m = msgs[idx]
                row = pygame.Rect(linner.x - 4, y - 2, linner.w + 8, 46)
                self.row_rects[idx] = row
                sel = (idx == self.sel)
                if sel:
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, row)
                tag, tcol = _KIND.get(m["kind"], ("•", config.COL_TEXT))
                bold = not m.get("read")
                widgets.draw_text(surf, tag, (linner.x, y), fonts.tiny(bold=True), tcol)
                widgets.draw_text(surf, f"J{m['day']}", (linner.right - 40, y),
                                  fonts.tiny(), config.COL_TEXT_DIM)
                subj = ("● " if bold else "") + m["subject"]
                widgets.draw_text(surf, subj[:42], (linner.x, y + 16),
                                  fonts.small(bold=bold),
                                  config.COL_WHITE if bold else config.COL_TEXT)
                y += 46
                if y > linner.bottom - 30:
                    break

        # volet de lecture à droite
        readp = pygame.Rect(540, list_top, config.SCREEN_WIDTH - 580, ph)
        rinner = widgets.draw_panel(surf, readp, "Lecture", config.COL_AMBER)
        if self.sel is not None and 0 <= self.sel < len(msgs):
            m = msgs[self.sel]
            tag, tcol = _KIND.get(m["kind"], ("•", config.COL_TEXT))
            widgets.draw_badge(surf, tag, (rinner.x, rinner.y), tcol)
            widgets.draw_text(surf, f"Jour {m['day']}", (rinner.right, rinner.y),
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
            widgets.draw_text(surf, "Sélectionnez un message.", (rinner.x, rinner.y),
                              fonts.body(), config.COL_TEXT_DIM)

        self.back_btn.draw(surf)
