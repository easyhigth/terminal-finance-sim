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
        self.back_btn = widgets.Button(
            config.back_button_rect(200), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.scenes.go(self.return_to)
        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for idx, rect in self.row_rects.items():
                if rect.collidepoint(event.pos):
                    self.sel = idx
                    self.app.gs.player.inbox[idx]["read"] = True

    def update(self, dt):
        self.back_btn.update(pygame.mouse.get_pos(), dt)

    def draw(self, surf):
        surf.fill(config.COL_BG)
        msgs = self.app.gs.player.inbox
        unread = sum(1 for m in msgs if not m.get("read"))
        widgets.draw_text(surf, "MESSAGERIE", (40, 22), fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, f"{len(msgs)} messages · {unread} non lus",
                          (42, 72), fonts.small(), config.COL_TEXT_DIM)

        # liste à gauche
        ph = config.footer_y() - 8 - 100
        listp = pygame.Rect(40, 100, 480, ph)
        linner = widgets.draw_panel(surf, listp, "Reçus", config.COL_CYAN)
        self.row_rects = {}
        if not msgs:
            widgets.draw_text(surf, "Aucun message pour l'instant.", (linner.x, linner.y),
                              fonts.body(), config.COL_TEXT_DIM)
        else:
            y = linner.y
            mp = pygame.mouse.get_pos()
            for idx in self.order:
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
        readp = pygame.Rect(540, 100, config.SCREEN_WIDTH - 580, ph)
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
