"""
app_notifications.py — Application « Notifications » du bureau : historique
des toasts (`ui/notifications.py::NotificationCenter.history`), jusqu'ici
poussé en mémoire mais sans aucun panneau pour le consulter après coup — un
toast disparaît après quelques secondes, sans trace. Liste les derniers
évènements (jour, texte, couleur par nature) du plus récent au plus ancien ;
cliquer une ligne dont l'évènement a un contexte connu (`action`, ex. offre de
mandat, appel de marge, dilemme…) ouvre l'écran correspondant en fenêtre —
retrouver de quoi il s'agissait sans avoir eu le temps de lire le toast.
"""
import pygame

from apps.base import DesktopApp
from core import config
from ui import fonts, widgets

ROW_H = 40

_KIND_COLOR = {
    "good": config.COL_EVENT_GOOD,
    "bad": config.COL_EVENT_BAD,
    "warn": config.COL_WARN,
    "info": config.COL_CYAN,
    "prestige": config.COL_PRESTIGE,
}


class NotificationCenterApp(DesktopApp):
    title = "Notifications"
    icon_kind = "bell"
    default_size = (420, 460)
    min_size = (300, 260)

    def on_open(self):
        self.scroll = 0
        self._row_rects = {}   # index -> (Rect, entry)
        self._list_rect = None
        self._max_scroll = 0

    def handle_event(self, event, rect):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if self._list_rect and self._list_rect.collidepoint(event.pos):
                self.scroll = max(0, min(self._max_scroll,
                                         self.scroll + (-32 if event.button == 4 else 32)))
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for r, entry in self._row_rects.values():
                if r.collidepoint(event.pos):
                    action = entry.get("action")
                    if action and self.desktop is not None:
                        self.desktop._open_scene_window(action, **entry.get("action_kwargs", {}))
                    return True
        return False

    def draw(self, surf, rect):
        surf.fill(config.COL_PANEL, rect)
        pad = 10
        hist = list(reversed(self.app.notes.history))
        widgets.draw_text(surf, f"NOTIFICATIONS ({len(hist)})", (rect.x + pad, rect.y + pad),
                          fonts.small(bold=True), config.COL_AMBER)
        area = pygame.Rect(rect.x + pad, rect.y + pad + 22, rect.w - 2 * pad,
                           rect.bottom - rect.y - pad * 2 - 22)
        pygame.draw.rect(surf, config.COL_BG, area)
        pygame.draw.rect(surf, config.COL_BORDER, area, 1)
        self._list_rect = area
        self._row_rects = {}
        if not hist:
            widgets.draw_text(surf, "Aucune notification pour l'instant.",
                              (area.x + 10, area.y + 12), fonts.small(), config.COL_TEXT_DIM)
            return
        self._max_scroll = max(0, len(hist) * ROW_H - area.h)
        self.scroll = max(0, min(self._max_scroll, self.scroll))
        mp = pygame.mouse.get_pos()
        prev_clip = surf.get_clip()
        surf.set_clip(area)
        y = area.y - self.scroll
        for idx, entry in enumerate(hist):
            r = pygame.Rect(area.x + 2, y, area.w - 4, ROW_H - 4)
            if r.bottom >= area.y and r.top <= area.bottom:
                col = _KIND_COLOR.get(entry["kind"], config.COL_CYAN)
                clickable = bool(entry.get("action"))
                if clickable and r.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, r)
                pygame.draw.rect(surf, col, (r.x, r.y, 3, r.h))
                day = entry.get("day")
                day_txt = f"J{day}" if day is not None else ""
                widgets.draw_text(surf, day_txt, (r.x + 10, r.y + 3), fonts.tiny(), config.COL_TEXT_DIM)
                widgets.draw_text(surf, widgets.fit_text(entry["text"], fonts.small(), r.w - 20),
                                  (r.x + 10, r.y + 16), fonts.small(), config.COL_TEXT)
                if clickable:
                    widgets.draw_text(surf, "→", (r.right - 16, r.y + 10), fonts.small(bold=True), col)
                self._row_rects[idx] = (r, entry)
            y += ROW_H
        surf.set_clip(prev_clip)
