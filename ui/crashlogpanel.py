"""
crashlogpanel.py — Panneau déplaçable affichant le journal de plantage
(core/crashlog.py) : un joueur qui rencontre un comportement inattendu (filet
de sécurité de main.py::App._safe_call) peut consulter et copier les
tracebacks journalisés SANS accès au système de fichiers, pour les
transmettre en rapport de bug. Même pattern que ui/shortcutspanel.py (overlay
déplaçable/défilable ouvert depuis scenes/scene_settings.py).
"""
import pygame

from core import clipboard, config, crashlog
from core.i18n import get_lang
from ui import fonts, widgets

TITLE_H = 28
PADX = 14
ROW_H = 15


def _L(fr, en):
    return en if get_lang() == "en" else fr


class CrashLogPanel:
    def __init__(self, pos=(180, 60), size=(880, 580)):
        self.closed = False
        self.dragging = False
        self._drag_off = (0, 0)
        self.rect = pygame.Rect(pos[0], pos[1], size[0], size[1])
        self.scroll = 0
        self._max_scroll = 0
        self._copy_rect = None
        self._clear_rect = None
        self._msg = ""

    def _title_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.w, TITLE_H)

    def _close_rect(self):
        return pygame.Rect(self.rect.right - TITLE_H, self.rect.y, TITLE_H, TITLE_H)

    def handle(self, event):
        """Retourne True si l'event est consommé (absorbe tout tant qu'ouvert)."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.closed = True
            elif event.key == pygame.K_PAGEUP:
                self.scroll = max(0, self.scroll - (self.rect.h - 80))
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll = min(self._max_scroll, self.scroll + (self.rect.h - 80))
            elif event.key == pygame.K_UP:
                self.scroll = max(0, self.scroll - 32)
            elif event.key == pygame.K_DOWN:
                self.scroll = min(self._max_scroll, self.scroll + 32)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._close_rect().collidepoint(event.pos):
                self.closed = True
                return True
            if self._copy_rect and self._copy_rect.collidepoint(event.pos):
                content = crashlog.read()
                if content:
                    clipboard.copy(content)
                    self._msg = _L("Journal copié dans le presse-papiers.",
                                   "Log copied to clipboard.")
                else:
                    self._msg = _L("Journal vide — aucun plantage enregistré.",
                                   "Log empty — no crash recorded.")
                return True
            if self._clear_rect and self._clear_rect.collidepoint(event.pos):
                crashlog.clear()
                self.scroll = 0
                self._msg = _L("Journal vidé.", "Log cleared.")
                return True
            if self._title_rect().collidepoint(event.pos):
                self.dragging = True
                self._drag_off = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
                return True
            if self.rect.collidepoint(event.pos):
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.rect.x = max(0, min(config.SCREEN_WIDTH - self.rect.w,
                                     event.pos[0] - self._drag_off[0]))
            self.rect.y = max(config.TOPBAR_H, min(config.SCREEN_HEIGHT - 40,
                                                    event.pos[1] - self._drag_off[1]))
            return True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self.rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-32 if event.button == 4 else 32)))
                return True
        return False

    def draw(self, surf):
        pygame.draw.rect(surf, (0, 0, 0), self.rect.move(0, 3), border_radius=6)
        pygame.draw.rect(surf, config.COL_PANEL, self.rect, border_radius=6)
        pygame.draw.rect(surf, config.COL_CYAN, self.rect, 1, border_radius=6)
        tr = self._title_rect()
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, tr,
                         border_top_left_radius=6, border_top_right_radius=6)
        widgets.draw_text(surf, _L("Journal de plantage", "Crash log"), (tr.x + 10, tr.y + 6),
                          fonts.small(bold=True), config.COL_CYAN)
        widgets.draw_text(surf, "✕", (self._close_rect().centerx, tr.y + 6),
                          fonts.small(bold=True), config.COL_TEXT_DIM, align="center")

        btn_y = tr.bottom + 6
        self._copy_rect = pygame.Rect(self.rect.x + PADX, btn_y, 160, 26)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._copy_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, self._copy_rect, 1, border_radius=4)
        widgets.draw_text(surf, _L("Copier tout", "Copy all"), self._copy_rect.center,
                          fonts.tiny(bold=True), config.COL_CYAN, align="center")
        self._clear_rect = pygame.Rect(self._copy_rect.right + 8, btn_y, 100, 26)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._clear_rect, border_radius=4)
        pygame.draw.rect(surf, config.COL_DOWN, self._clear_rect, 1, border_radius=4)
        widgets.draw_text(surf, _L("Vider", "Clear"), self._clear_rect.center,
                          fonts.tiny(bold=True), config.COL_DOWN, align="center")
        if self._msg:
            widgets.draw_text(surf, self._msg, (self._clear_rect.right + 14, btn_y + 6),
                              fonts.tiny(), config.COL_TEXT_DIM)

        content = pygame.Rect(self.rect.x + 4, btn_y + 32, self.rect.w - 8,
                              self.rect.bottom - (btn_y + 32) - 8)
        prev_clip = surf.get_clip()
        surf.set_clip(content)
        text = crashlog.read()
        if not text:
            widgets.draw_text(surf, _L("Aucun plantage enregistré. Tout va bien !",
                                       "No crash recorded. All clear!"),
                              (content.x + PADX, content.y), fonts.small(), config.COL_TEXT_DIM)
            self._max_scroll = 0
        else:
            lines = text.splitlines()
            y = content.y - self.scroll
            for line in lines:
                if content.top - ROW_H < y < content.bottom:
                    widgets.draw_text(surf, widgets.fit_text(line, fonts.tiny(), content.w - 2 * PADX),
                                      (content.x + PADX, y), fonts.tiny(), config.COL_TEXT)
                y += ROW_H
            content_h = (y + self.scroll) - content.y
            self._max_scroll = max(0, content_h - content.h)
            self.scroll = min(self.scroll, self._max_scroll)
            self.scroll = widgets.draw_scrollbar(surf, self.rect, content, self.scroll,
                                                  self._max_scroll, content_h)
        surf.set_clip(prev_clip)
