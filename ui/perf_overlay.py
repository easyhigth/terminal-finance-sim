"""
perf_overlay.py — Overlay de PERFORMANCE (FINSIM_DEBUG=1 uniquement).

Petit cadran en haut à droite : FPS lissés + décomposition de la frame en
millisecondes (événements / update / draw / flip), moyennée sur une fenêtre
glissante pour rester lisible. Sert à VÉRIFIER les optimisations de rendu
(cache de texte, smoothscale réutilisé…) au lieu de les supposer efficaces,
et à repérer le prochain goulot d'étranglement.

Coût nul en jeu normal : `PerfOverlay.enabled` est figé au lancement sur
`core.applog.DEBUG` — quand il est faux, `frame()`/`draw()` retournent
immédiatement.
"""
import time
from collections import deque

import pygame

from core import config
from core.applog import DEBUG

_WINDOW = 60   # frames de lissage (~1 s à 60 FPS)


class PerfOverlay:
    def __init__(self):
        self.enabled = DEBUG
        self._samples = {k: deque(maxlen=_WINDOW)
                         for k in ("events", "update", "draw", "flip")}
        self._frame_t = deque(maxlen=_WINDOW)
        self._last = time.perf_counter()

    class _Timer:
        __slots__ = ("overlay", "key", "t0")

        def __init__(self, overlay, key):
            self.overlay = overlay
            self.key = key

        def __enter__(self):
            self.t0 = time.perf_counter()
            return self

        def __exit__(self, *exc):
            self.overlay._samples[self.key].append(time.perf_counter() - self.t0)
            return False

    def phase(self, key):
        """Chronomètre une phase de la frame : `with perf.phase("draw"): …`.
        No-op (timer quand même, coût négligeable) si désactivé — le chemin
        rapide est déjà court, on privilégie la simplicité du call site."""
        return self._Timer(self, key)

    def frame(self):
        """À appeler une fois par frame (après flip) : échantillonne le temps
        total de frame pour le FPS lissé."""
        if not self.enabled:
            return
        now = time.perf_counter()
        self._frame_t.append(now - self._last)
        self._last = now

    def draw(self, surf):
        if not self.enabled or not self._frame_t:
            return
        from ui import fonts, widgets
        avg_frame = sum(self._frame_t) / len(self._frame_t)
        fps = (1.0 / avg_frame) if avg_frame > 0 else 0.0
        parts = []
        for key in ("events", "update", "draw", "flip"):
            s = self._samples[key]
            ms = (sum(s) / len(s) * 1000.0) if s else 0.0
            parts.append(f"{key[:2]} {ms:4.1f}")
        text = f"{fps:5.1f} FPS · " + " ".join(parts) + " ms"
        font = fonts.tiny()
        w, h = font.size(text)
        rect = pygame.Rect(config.SCREEN_WIDTH - w - 14, config.SCREEN_HEIGHT - h - 10,
                           w + 10, h + 6)
        overlay = pygame.Surface((rect.w, rect.h))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(190)
        surf.blit(overlay, rect.topleft)
        color = config.COL_UP if fps >= config.FPS * 0.9 else (
            config.COL_WARN if fps >= config.FPS * 0.6 else config.COL_DOWN)
        widgets.draw_text(surf, text, (rect.x + 5, rect.y + 3), font, color)
