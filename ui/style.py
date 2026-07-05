"""
style.py — Helpers de style visuel unifiés pour l'interface "Jeu PC".

Centralise les ombres, les arrondis, les gradients et les effets de survol.
Version optimisée : tout ce qui est coûteux est mis en cache pour ne pas être
recalculé à chaque frame (fonds, ombres, gradients). Compatible headless.
"""
import math
import random

import pygame

from core import config


# ---------------------------------------------------------------------------
# CONSTANTES DE RAYON DE COIN
# ---------------------------------------------------------------------------
RADIUS_SM = 3
RADIUS_MD = 5
RADIUS_LG = 8

# ---------------------------------------------------------------------------
# OMBRES
# ---------------------------------------------------------------------------
SHADOW_ALPHA = 90
SHADOW_OFFSET = (3, 5)
SHADOW_RADIUS = 10

# Cache des ombres : clé -> surface. Les fenêtres ont peu de tailles distinctes
# (resolutions fixes, layouts), donc le cache reste petit.
_SHADOW_CACHE = {}


def _lerp(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))


def _lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _mix_alpha(color, alpha):
    return (*color[:3], max(0, min(255, int(alpha))))


# ---------------------------------------------------------------------------
# DÉGRADÉS (avec cache)
# ---------------------------------------------------------------------------
_GRADIENT_CACHE = {}


def surface_gradient(width, height, color_top, color_bottom, direction="vertical"):
    """Dégradé linéaire vertical/horizontal — mis en cache par dimensions."""
    if width <= 0 or height <= 0:
        return pygame.Surface((1, 1), pygame.SRCALPHA)
    key = (width, height, color_top, color_bottom, direction)
    if key in _GRADIENT_CACHE:
        return _GRADIENT_CACHE[key]
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    if direction == "horizontal":
        for x in range(width):
            t = x / max(1, width - 1)
            col = _lerp_color(color_top, color_bottom, t)
            pygame.draw.line(surf, col, (x, 0), (x, height - 1))
    else:
        for y in range(height):
            t = y / max(1, height - 1)
            col = _lerp_color(color_top, color_bottom, t)
            pygame.draw.line(surf, col, (0, y), (width - 1, y))
    _GRADIENT_CACHE[key] = surf
    return surf


def surface_radial_gradient(width, height, center_color, edge_color, center=None):
    """Dégradé radial circulaire — mis en cache."""
    if width <= 0 or height <= 0:
        return pygame.Surface((1, 1), pygame.SRCALPHA)
    cx, cy = center if center else (width // 2, height // 2)
    key = (width, height, center_color, edge_color, cx, cy)
    if key in _GRADIENT_CACHE:
        return _GRADIENT_CACHE[key]
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    max_r = math.hypot(max(cx, width - cx), max(cy, height - cy))
    if max_r <= 0:
        surf.fill(center_color)
        _GRADIENT_CACHE[key] = surf
        return surf
    steps = int(max_r) + 1
    for i in range(steps, -1, -1):
        t = i / max_r
        col = _lerp_color(center_color, edge_color, t)
        pygame.draw.circle(surf, col, (int(cx), int(cy)), i)
    _GRADIENT_CACHE[key] = surf
    return surf


# ---------------------------------------------------------------------------
# TEXTURE DE BRUIT (cache)
# ---------------------------------------------------------------------------
_NOISE_CACHE = {}


def noise_texture(width, height, intensity=12, seed=0):
    """Texture de bruit tileable très petite, étirée via smoothscale."""
    if width <= 0 or height <= 0:
        return pygame.Surface((1, 1), pygame.SRCALPHA)
    key = (intensity, seed)
    tile = _NOISE_CACHE.get(key)
    if tile is None:
        rng = random.Random(seed)
        tile = pygame.Surface((128, 128), pygame.SRCALPHA)
        for y in range(128):
            for x in range(128):
                a = rng.randint(0, intensity)
                if a:
                    tile.set_at((x, y), (255, 255, 255, a))
        _NOISE_CACHE[key] = tile
    if width == 128 and height == 128:
        return tile
    return pygame.transform.smoothscale(tile, (width, height))


# ---------------------------------------------------------------------------
# OMBRES PORTÉES (cache)
# ---------------------------------------------------------------------------
def _make_shadow(width, height, alpha):
    """Ombre rectangulaire arrondie via un seul rectangle alpha + étirement.

    Version légère : au lieu de 6 couches de rectangles, on dessine un
    rectangle flouté via smoothscale d'une tiny surface. C'est 5-10× plus
    rapide et visuellement très proche.
    """
    if width <= 0 or height <= 0:
        return pygame.Surface((1, 1), pygame.SRCALPHA)
    # on génère une ombre à taille réduite (1/3) puis on l'étire pour le flou
    blur = 12
    pad = blur
    tiny_w = max(1, (width + 2 * pad) // 3)
    tiny_h = max(1, (height + 2 * pad) // 3)
    tiny = pygame.Surface((tiny_w, tiny_h), pygame.SRCALPHA)
    tiny.fill((0, 0, 0, alpha))
    big = pygame.transform.smoothscale(tiny, (width + 2 * pad, height + 2 * pad))
    return big


def draw_shadow(surf, rect, alpha=SHADOW_ALPHA, radius=SHADOW_RADIUS,
                offset=SHADOW_OFFSET):
    """Dessine une ombre portée douce sous `rect` (cache par taille/alpha)."""
    rect = pygame.Rect(rect)
    key = (rect.w, rect.h, alpha)
    shadow = _SHADOW_CACHE.get(key)
    if shadow is None:
        shadow = _make_shadow(rect.w, rect.h, alpha)
        _SHADOW_CACHE[key] = shadow
    dx = rect.w // 2 + offset[0]
    dy = rect.h // 2 + offset[1]
    surf.blit(shadow, (rect.x - shadow.get_width() // 2 + dx,
                       rect.y - shadow.get_height() // 2 + dy))


def draw_window_shadow(surf, rect, focused=True):
    """Ombre adaptée à une fenêtre : plus marquée si active."""
    alpha = 110 if focused else 55
    draw_shadow(surf, rect, alpha=alpha, offset=(4, 6) if focused else (3, 5))


# ---------------------------------------------------------------------------
# FORMES ANTI-ALIASÉES
# ---------------------------------------------------------------------------
try:
    import pygame.gfxdraw as _gfxdraw
except Exception:
    _gfxdraw = None

_HAS_GFX = _gfxdraw is not None


def draw_aa_circle(surf, center, radius, color, width=1):
    """Cercle anti-aliasé. Retombe sur pygame.draw.circle si gfxdraw absent."""
    if radius <= 0:
        return
    if _HAS_GFX and width <= 1:
        x, y = int(center[0]), int(center[1])
        r = int(radius)
        if width <= 0:
            _gfxdraw.filled_circle(surf, x, y, r, color)
            _gfxdraw.aacircle(surf, x, y, r, color)
        else:
            _gfxdraw.aacircle(surf, x, y, r, color)
    else:
        pygame.draw.circle(surf, color, (int(center[0]), int(center[1])),
                          int(radius), max(1, width))


def draw_aa_filled_circle(surf, center, radius, color):
    draw_aa_circle(surf, center, radius, color, width=0)


def draw_aa_round_rect(surf, rect, color, radius=RADIUS_MD, width=0):
    """Rectangle arrondi anti-aliasé."""
    rect = pygame.Rect(rect)
    if _HAS_GFX and width <= 1:
        r = max(0, min(radius, rect.w // 2, rect.h // 2))
        if width == 0:
            _gfxdraw.box(surf, rect, color)
            if r > 0:
                for cx, cy in ((rect.x + r, rect.y + r),
                               (rect.right - r - 1, rect.y + r),
                               (rect.x + r, rect.bottom - r - 1),
                               (rect.right - r - 1, rect.bottom - r - 1)):
                    _gfxdraw.filled_circle(surf, cx, cy, r, color)
                    _gfxdraw.aacircle(surf, cx, cy, r, color)
        else:
            _gfxdraw.rectangle(surf, rect, color)
    else:
        pygame.draw.rect(surf, color, rect, border_radius=radius)
        if width > 0:
            pygame.draw.rect(surf, color, rect, width, border_radius=radius)


# ---------------------------------------------------------------------------
# PANNEAUX / CARTES / CHAMPS
# ---------------------------------------------------------------------------
def draw_card(surf, rect, bg=None, border=None, radius=RADIUS_MD,
              shadow=False, title_color=None, title=None, font=None,
              padding=None):
    rect = pygame.Rect(rect)
    bg = bg or config.COL_PANEL
    border = border or config.COL_BORDER
    if shadow:
        draw_window_shadow(surf, rect, focused=True)
    pygame.draw.rect(surf, bg, rect, border_radius=radius)
    pygame.draw.rect(surf, border, rect, 1, border_radius=radius)
    inner = rect.inflate(-(padding or 0) * 2, -(padding or 0) * 2)
    if title and font:
        pygame.draw.rect(surf, config.COL_PANEL_HEAD,
                         (rect.x, rect.y, rect.w, 26), border_radius=radius)
        from ui import widgets
        widgets.draw_text(surf, title.upper(), (rect.x + 10, rect.y + 5),
                          font, title_color or border)
        inner = pygame.Rect(rect.x + (padding or 0), rect.y + 30,
                            rect.w - 2 * (padding or 0), rect.h - 30 - (padding or 0))
    return inner


def draw_inset(surf, rect, bg=None, border=None, radius=RADIUS_SM):
    rect = pygame.Rect(rect)
    bg = bg or config.COL_BG
    border = border or config.COL_BORDER
    pygame.draw.rect(surf, bg, rect, border_radius=radius)
    pygame.draw.rect(surf, border, rect, 1, border_radius=radius)
    top = pygame.Rect(rect.x + radius, rect.y + 1, rect.w - 2 * radius, 1)
    pygame.draw.rect(surf, _lerp_color(border, config.COL_WHITE, 0.15), top)
    return rect


def draw_glass_panel(surf, rect, alpha=200, border_color=None, radius=RADIUS_MD):
    rect = pygame.Rect(rect)
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    panel.fill(_mix_alpha(config.COL_PANEL, alpha))
    surf.blit(panel, rect.topleft)
    border_color = border_color or _lerp_color(config.COL_BORDER, config.COL_WHITE, 0.25)
    pygame.draw.rect(surf, border_color, rect, 1, border_radius=radius)


def draw_hover_row(surf, rect, hover, selected=False, accent=None,
                   animation_t=0.0, radius=RADIUS_SM):
    rect = pygame.Rect(rect)
    accent = accent or config.COL_CYAN
    if selected:
        bg = config.COL_PANEL_HEAD
        border = accent
        bw = 1
    elif animation_t > 0.001:
        bg = _lerp_color(config.COL_PANEL, config.COL_PANEL_HEAD, animation_t)
        border = _lerp_color(config.COL_BORDER, accent, animation_t * 0.5)
        bw = 1
    else:
        return
    pygame.draw.rect(surf, bg, rect, border_radius=radius)
    if selected or animation_t > 0.001:
        pygame.draw.rect(surf, border, rect, bw, border_radius=radius)
