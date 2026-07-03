"""
glossary_hint.py — Lexique contextuel en un clic.

Un libellé financier technique affiché à l'écran (Bêta, EV/EBITDA, VaR…)
devient cliquable : un clic ouvre une courte définition tirée du glossaire
existant (data/glossary_data.py — même source que l'écran GLOSSAIRE et les
suggestions de la palette Ctrl+K), dans une bulle flottante, SANS quitter
l'écran courant. Complète le glossaire dédié (consultation volontaire) par
une aide "juste à temps", au point d'usage.

Une scène possède UNE instance (`self._gloss = GlossaryHint()`), appelée à
trois endroits :
  - `begin_frame()` en tout début de `draw()` (réinitialise les zones
    cliquables, recalculées à chaque frame comme le reste du layout) ;
  - `label(surf, pos, text, font, color, term=None)` À LA PLACE de
    `widgets.draw_text` pour un libellé jargon — si `term` (ou `text` à
    défaut) existe dans le glossaire, le libellé est souligné en pointillés
    et devient cliquable ; sinon, comportement strictement identique à
    `widgets.draw_text` (aucun risque à l'appeler partout) ;
  - `handle_event(event)` tôt dans `handle_event` de la scène (retourne True
    si l'évènement est consommé) et `draw_popup(surf)` en toute fin de
    `draw()` (par-dessus le reste, comme un tooltip).
"""
import pygame

from core import config
from ui import fonts, widgets


class GlossaryHint:
    def __init__(self):
        self._rects = []          # [(Rect, term)] recalculé à chaque frame
        self.active_term = None
        self.active_pos = None

    def begin_frame(self):
        self._rects = []

    def label(self, surf, pos, text, font=None, color=None, term=None):
        font = font or fonts.small()
        color = color or config.COL_TEXT
        rect = widgets.draw_text(surf, text, pos, font, color)
        key = term or text
        from data import glossary_data
        if key in glossary_data.GLOSSARY:
            self._rects.append((pygame.Rect(rect), key))
            y = rect.bottom
            x = rect.x
            while x < rect.right:
                pygame.draw.line(surf, color, (x, y), (min(x + 2, rect.right), y))
                x += 5
        return rect

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, term in self._rects:
                if rect.collidepoint(event.pos):
                    self.active_term = term
                    self.active_pos = event.pos
                    return True
            if self.active_term is not None:
                self.active_term = None
                return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.active_term:
            self.active_term = None
            return True
        return False

    def draw_popup(self, surf, lang="fr"):
        if not self.active_term:
            return
        from data import glossary_data
        entry = glossary_data.entry(self.active_term, lang)
        if not entry:
            self.active_term = None
            return
        cat, definition = entry
        font = fonts.tiny()
        W = 320
        lines = widgets.wrap_text_lines(definition, font, W - 24)
        H = 44 + 16 * len(lines)
        x, y = self.active_pos
        box = pygame.Rect(x + 12, y + 12, W, H)
        box.right = min(box.right, config.SCREEN_WIDTH - 8)
        box.bottom = min(box.bottom, config.SCREEN_HEIGHT - 8)
        panel = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
        panel.fill((*config.COL_PANEL, 245))
        surf.blit(panel, box.topleft)
        pygame.draw.rect(surf, config.COL_CYAN, box, 1, border_radius=5)
        widgets.draw_text(surf, f"{self.active_term} — {cat}", (box.x + 10, box.y + 8),
                          fonts.tiny(bold=True), config.COL_CYAN)
        ly = box.y + 28
        for ln in lines:
            widgets.draw_text(surf, ln, (box.x + 10, ly), font, config.COL_TEXT)
            ly += 16
