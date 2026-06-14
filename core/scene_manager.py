"""
scene_manager.py — Machine à états des écrans (scènes).
Chaque scène gère ses événements, sa logique et son rendu.
Un fondu (fade-in) est joué automatiquement à chaque changement de scène.
"""
import pygame
from core import config


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

    def register(self, name, scene):
        self.scenes[name] = scene

    def go(self, name, **kwargs):
        if name not in self.scenes:
            raise KeyError(f"Scène inconnue : {name}")
        self.current = self.scenes[name]
        self.current_name = name
        self.current.on_enter(**kwargs)
        self._fade = 1.0          # déclenche le fondu d'entrée

    def handle_event(self, event):
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
        if self._fade > 0.0:
            if self._overlay is None or self._overlay.get_size() != surf.get_size():
                self._overlay = pygame.Surface(surf.get_size())
                self._overlay.fill(config.COL_BG)
            self._overlay.set_alpha(int(255 * self._fade))
            surf.blit(self._overlay, (0, 0))
