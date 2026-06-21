"""
scene_manager.py — Machine à états des écrans (scènes).
Chaque scène gère ses événements, sa logique et son rendu.
Un fondu (fade-in) est joué automatiquement à chaque changement de scène.
Ctrl+K ouvre par-dessus la scène courante une palette de navigation globale
(recherche + accès direct à n'importe quelle page du jeu).
"""
import pygame

from core import config, fuzzy
from ui import fonts, widgets

PALETTE_W, PALETTE_H = 560, 360
PALETTE_ROW_H = 30


class Scene:
    """Classe de base. À hériter pour chaque écran."""

    def __init__(self, app):
        self.app = app          # référence à l'application (accès global)

    def on_enter(self, **kwargs):
        """Appelé quand la scène devient active."""
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass


class SceneManager:
    """Gère la pile de scènes et les transitions (fondu au changement)."""

    FADE_TIME = 0.28   # durée du fondu d'entrée (secondes)

    def __init__(self, app):
        self.app = app
        self.scenes = {}
        self.current = None
        self.current_name = None
        self._fade = 0.0          # 1.0 = écran noir, 0.0 = pleinement visible
        self._overlay = None      # surface noire réutilisée pour le fondu
        self.palette_open = False
        self.palette_query = ""
        self.palette_sel = 0

    def register(self, name, scene):
        self.scenes[name] = scene

    def go(self, name, **kwargs):
        if name not in self.scenes:
            raise KeyError(f"Scène inconnue : {name}")
        self.current = self.scenes[name]
        self.current_name = name
        self.current.on_enter(**kwargs)
        self._fade = 1.0          # déclenche le fondu d'entrée
        self.palette_open = False

    # --- palette de navigation globale (Ctrl+K) ---------------------------
    def _palette_entries(self):
        from scenes.scene_more import SECTIONS
        return [(label, scene, kw) for _, items in SECTIONS for (label, scene, kw) in items]

    def _palette_filtered(self):
        entries = self._palette_entries()
        if not self.palette_query.strip():
            return entries
        return fuzzy.filter_sorted(self.palette_query, entries, key=lambda e: e[0])

    def open_palette(self):
        self.palette_open = True
        self.palette_query = ""
        self.palette_sel = 0

    def close_palette(self):
        self.palette_open = False

    def _handle_palette_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            filtered = self._palette_filtered()
            box = pygame.Rect((config.SCREEN_WIDTH-PALETTE_W)//2,
                              (config.SCREEN_HEIGHT-PALETTE_H)//2, PALETTE_W, PALETTE_H)
            if not box.collidepoint(event.pos):
                self.close_palette()
                return
            list_y = box.y + 64
            for i, (label, scene, kw) in enumerate(filtered):
                row = pygame.Rect(box.x+10, list_y + i*PALETTE_ROW_H, box.w-20, PALETTE_ROW_H)
                if row.collidepoint(event.pos):
                    self.close_palette()
                    self.go(scene, return_to=self.current_name or "terminal", **kw)
                    return
            return
        if event.type != pygame.KEYDOWN:
            return
        filtered = self._palette_filtered()
        if event.key == pygame.K_ESCAPE:
            self.close_palette()
        elif event.key == pygame.K_BACKSPACE:
            self.palette_query = self.palette_query[:-1]
            self.palette_sel = 0
        elif event.key == pygame.K_DOWN:
            if filtered:
                self.palette_sel = (self.palette_sel + 1) % len(filtered)
        elif event.key == pygame.K_UP:
            if filtered:
                self.palette_sel = (self.palette_sel - 1) % len(filtered)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if filtered:
                _, scene, kw = filtered[self.palette_sel % len(filtered)]
                self.close_palette()
                self.go(scene, return_to=self.current_name or "terminal", **kw)
        elif event.unicode and event.unicode.isprintable():
            self.palette_query += event.unicode
            self.palette_sel = 0

    def _draw_palette(self, surf):
        filtered = self._palette_filtered()
        self.palette_sel = min(self.palette_sel, max(0, len(filtered)-1))
        box = pygame.Rect((config.SCREEN_WIDTH-PALETTE_W)//2,
                          (config.SCREEN_HEIGHT-PALETTE_H)//2, PALETTE_W, PALETTE_H)
        shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 160))
        surf.blit(shade, (0, 0))
        pygame.draw.rect(surf, config.COL_PANEL, box)
        pygame.draw.rect(surf, config.COL_CYAN, box, 2)
        widgets.draw_text(surf, "NAVIGATION (Ctrl+K)", (box.x+14, box.y+12),
                          fonts.small(bold=True), config.COL_CYAN)
        search_box = pygame.Rect(box.x+14, box.y+38, box.w-28, 26)
        pygame.draw.rect(surf, (6, 8, 12), search_box)
        pygame.draw.rect(surf, config.COL_BORDER, search_box, 1)
        widgets.draw_text(surf, self.palette_query or "tapez pour filtrer…", (search_box.x+8, search_box.y+5),
                          fonts.small(), config.COL_WHITE if self.palette_query else config.COL_TEXT_DIM)
        list_y = box.y + 64
        max_rows = (box.bottom - 10 - list_y) // PALETTE_ROW_H
        if not filtered:
            widgets.draw_text(surf, "Aucun résultat.", (box.x+14, list_y+6),
                              fonts.small(), config.COL_TEXT_DIM)
        for i, (label, scene, kw) in enumerate(filtered[:max_rows]):
            row = pygame.Rect(box.x+10, list_y + i*PALETTE_ROW_H, box.w-20, PALETTE_ROW_H)
            if i == self.palette_sel:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row)
                pygame.draw.rect(surf, config.COL_CYAN, row, 1)
            widgets.draw_text(surf, label, (row.x+8, row.y+6), fonts.small(), config.COL_TEXT)
        if len(filtered) > max_rows:
            widgets.draw_text(surf, f"… et {len(filtered)-max_rows} autre(s)",
                              (box.x+14, box.bottom-22), fonts.tiny(), config.COL_TEXT_DIM)

    def handle_event(self, event):
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_k
                and (event.mod & pygame.KMOD_CTRL)):
            if self.palette_open:
                self.close_palette()
            else:
                self.open_palette()
            return
        if self.palette_open:
            self._handle_palette_event(event)
            return
        # on ignore les entrées pendant le tout début du fondu pour éviter
        # les clics fantômes hérités de la scène précédente
        if self.current and self._fade < 0.6:
            self.current.handle_event(event)

    def update(self, dt):
        if self._fade > 0.0:
            self._fade = max(0.0, self._fade - dt / self.FADE_TIME)
        if self.current:
            self.current.update(dt)
        notes = getattr(self.app, "notes", None)
        if notes:
            notes.update(dt)

    def draw(self, surf):
        if not self.current:
            return
        self.current.draw(surf)
        # overlay : notifications (toasts) au-dessus de la scène, sous le fondu
        notes = getattr(self.app, "notes", None)
        if notes:
            notes.draw(surf)
        if self.palette_open:
            self._draw_palette(surf)
        if self._fade > 0.0:
            if self._overlay is None or self._overlay.get_size() != surf.get_size():
                self._overlay = pygame.Surface(surf.get_size())
                self._overlay.fill(config.COL_BG)
            self._overlay.set_alpha(int(255 * self._fade))
            surf.blit(self._overlay, (0, 0))
