"""
shortcutspanel.py — Panneau déplaçable et défilable listant tous les
raccourcis clavier du jeu (catalogue dans data/shortcuts_data.py), pour
permettre de jouer entièrement au clavier, sans la souris. Ouvert depuis
le bouton « ⌨ RACCOURCIS » en haut à droite du terminal, ou la commande
SHORTCUTS/KEYS.
"""
import pygame

from core import config
from core.i18n import get_lang, t, toggle_lang
from data.shortcuts_data import localized
from ui import fonts, widgets

TITLE_H = 28
PADX = 14
KEY_COL_W = 240
ROW_H = 17
ROW_GAP = 4
SECTION_GAP = 8
LANG_BTN_W = 56


class ShortcutsPanel:
    def __init__(self, pos=(220, 60), size=(820, 580)):
        self.closed = False
        self.dragging = False
        self._drag_off = (0, 0)
        self.rect = pygame.Rect(pos[0], pos[1], size[0], size[1])
        self.scroll = 0
        self._max_scroll = 0
        self._content_rect = None

    def _title_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.w, TITLE_H)

    def _close_rect(self):
        return pygame.Rect(self.rect.right - TITLE_H, self.rect.y, TITLE_H, TITLE_H)

    def _lang_rect(self):
        return pygame.Rect(self.rect.right - TITLE_H - LANG_BTN_W - 4, self.rect.y, LANG_BTN_W, TITLE_H)

    def handle(self, event):
        """Retourne True si l'event est consommé (le panneau absorbe tout le
        clavier tant qu'il est ouvert, pour éviter qu'une touche fuite vers le
        terminal en dessous)."""
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
            if self._lang_rect().collidepoint(event.pos):
                toggle_lang()
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
        widgets.draw_text(surf, t("shortcuts.title"), (tr.x + 10, tr.y + 6),
                          fonts.small(bold=True), config.COL_CYAN)
        lang_rect = self._lang_rect()
        widgets.draw_text(surf, get_lang().upper(), (lang_rect.centerx, tr.y + 6),
                          fonts.tiny(bold=True), config.COL_AMBER, align="center")
        widgets.draw_text(surf, "✕", (self._close_rect().centerx, tr.y + 6),
                          fonts.small(bold=True), config.COL_TEXT_DIM, align="center")

        content = pygame.Rect(self.rect.x + 4, tr.bottom + 4, self.rect.w - 8,
                              self.rect.bottom - tr.bottom - 12)
        self._content_rect = content
        prev_clip = surf.get_clip()
        surf.set_clip(content)
        y = content.y - self.scroll
        for title, rows in localized(get_lang()):
            if content.top - 22 < y < content.bottom:
                widgets.draw_text(surf, f"— {title}", (content.x + PADX, y),
                                  fonts.small(bold=True), config.COL_AMBER)
            y += 24
            for keys, desc in rows:
                desc_w = content.w - PADX - 8 - KEY_COL_W - 14
                widgets.draw_text(surf, keys, (content.x + PADX + 8, y),
                                  fonts.tiny(bold=True), config.COL_WHITE)
                row_h = max(ROW_H, widgets.draw_text_wrapped(
                    surf, desc, (content.x + PADX + 8 + KEY_COL_W, y),
                    fonts.tiny(), config.COL_TEXT_DIM, desc_w, line_gap=2))
                y += row_h + ROW_GAP
            y += SECTION_GAP
        surf.set_clip(prev_clip)

        content_h = (y + self.scroll) - content.y
        self._max_scroll = max(0, content_h - content.h)
        self.scroll = min(self.scroll, self._max_scroll)
        widgets.draw_scrollbar(surf, self.rect, content, self.scroll, self._max_scroll, content_h)
