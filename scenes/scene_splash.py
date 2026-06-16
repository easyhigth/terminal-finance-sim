"""
scene_splash.py — Écran de démarrage Terminal Alpha.
Logo animé avec fondu entrant/sortant. Clic ou touche = passer au menu.
"""
import pygame
from core import config
from core.scene_manager import Scene
from ui import fonts
from ui.logo import draw_ta_logo

_DURATION = 3.2   # durée totale (secondes)
_FADE_IN  = 0.75
_FADE_OUT = 0.60


class SplashScene(Scene):
    def on_enter(self, **kwargs):
        self.t     = 0.0
        self._gone = False

    def handle_event(self, event):
        if self._gone:
            return
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self._gone = True
            self.app.scenes.go("menu")

    def update(self, dt):
        self.t += dt
        if not self._gone and self.t >= _DURATION:
            self._gone = True
            self.app.scenes.go("menu")

    def draw(self, surf):
        surf.fill(config.COL_BG)

        cx = config.SCREEN_WIDTH  // 2
        cy = config.SCREEN_HEIGHT // 2 - 40   # légèrement au-dessus du centre

        # Couche intermédiaire pour le fade global (surface opaque + set_alpha)
        layer = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        layer.fill(config.COL_BG)

        # --- Monogramme TA ---
        draw_ta_logo(layer, cx, cy, size=200)

        # --- Titre "TERMINAL ALPHA" ---
        f_huge  = fonts.huge(bold=True)
        f_small = fonts.small()

        w1 = f_huge.size("TERMINAL")[0]
        w2 = f_huge.size("ALPHA")[0]
        gap   = 18
        total = w1 + gap + w2
        tx    = cx - total // 2
        ty    = cy + 128

        t1 = f_huge.render("TERMINAL", True, config.COL_AMBER)
        t2 = f_huge.render("ALPHA",    True, config.COL_CYAN)
        layer.blit(t1, (tx,           ty))
        layer.blit(t2, (tx + w1 + gap, ty))

        # --- Tagline ---
        tag_text = "Finance Career Simulator"
        tw = f_small.size(tag_text)[0]
        tag = f_small.render(tag_text, True, config.COL_TEXT_DIM)
        layer.blit(tag, (cx - tw // 2, ty + 78))

        # --- Calcul de l'alpha (fondu entrée / sortie) ---
        if self.t < _FADE_IN:
            alpha = int(255 * self.t / _FADE_IN)
        elif self.t > _DURATION - _FADE_OUT:
            alpha = int(255 * (1.0 - (self.t - (_DURATION - _FADE_OUT)) / _FADE_OUT))
        else:
            alpha = 255

        layer.set_alpha(max(0, min(255, alpha)))
        surf.blit(layer, (0, 0))
