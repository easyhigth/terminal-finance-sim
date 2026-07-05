"""
style.py — Helpers de style visuel unifiés pour l'interface "Jeu PC".

Centralise les ombres, les arrondis, les gradients et les effets de survol
utilisés par le bureau, les fenêtres, les panneaux et les widgets. Tout est
en pygame pur (pas de dépendance externe), compatible headless
(SDL_VIDEODRIVER=dummy).
"""
import math
import random

import pygame

from core import config


# ---------------------------------------------------------------------------
# CONSTANTES DE RAYON DE COIN
# ---------------------------------------------------------------------------
RADIUS_SM = 3   # petits éléments (champs, pastilles, items de liste)
RADIUS_MD = 5   # boutons, cartes, panneaux
RADIUS_LG = 8   # fenêtres, grandes cartes modales

# ---------------------------------------------------------------------------
# OMBRES
# ---------------------------------------------------------------------------
SHADOW_ALPHA = 90          # alpha de base de l'ombre
SHADOW_BLUR_STEPS = 6      # nombre d'étapes pour le flou de l'ombre
SHADOW_OFFSET = (3, 5)     # décalage (x, y) de l'ombre par défaut
SHADOW_RADIUS = 12         # rayon de diffusion de l'ombre


def _lerp(a, b, t):
    """Interpolation linéaire entre deux scalaires."""
    return a + (b - a) * max(0.0, min(1.0, t))


def _lerp_color(a, b, t):
    """Interpolation linéaire entre deux couleurs RGB."""
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _mix_alpha(color, alpha):
    """Retourne une couleur RGBA à partir d'une couleur RGB et d'un alpha."""
    return (*color[:3], max(0, min(255, int(alpha))))


# ---------------------------------------------------------------------------
# DÉGRADÉS
# ---------------------------------------------------------------------------
def surface_gradient(width, height, color_top, color_bottom, direction="vertical"):
    """Crée une surface SRCALPHA avec un dégradé linéaire.

    `direction` : "vertical" (haut→bas), "horizontal" (gauche→droite).
    Les couleurs sont des tuples RGB.
    """
    if width <= 0 or height <= 0:
        return pygame.Surface((1, 1), pygame.SRCALPHA)
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
    return surf


def surface_radial_gradient(width, height, center_color, edge_color, center=None):
    """Dégradé radial circulaire inscrit dans un rectangle.

    Utile pour les fonds de bureau ou les halos. Le centre par défaut est le
    centre du rectangle.
    """
    if width <= 0 or height <= 0:
        return pygame.Surface((1, 1), pygame.SRCALPHA)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    cx, cy = center if center else (width // 2, height // 2)
    max_r = math.hypot(max(cx, width - cx), max(cy, height - cy))
    if max_r <= 0:
        surf.fill(center_color)
        return surf
    # on dessine par cercles concentriques pour un effet radial doux
    steps = int(max_r) + 1
    for i in range(steps, -1, -1):
        t = i / max_r
        col = _lerp_color(center_color, edge_color, t)
        pygame.draw.circle(surf, col, (int(cx), int(cy)), i)
    return surf


def noise_texture(width, height, intensity=12, seed=0):
    """Crée une petite texture de bruit tileable (SRCALPHA).

    `intensity` : alpha maximal d'un grain (0-255). Le bruit est très subtil
    pour ne pas gêner la lisibilité.
    Le résultat est mis en cache dans une surface 128x128 et étiré si besoin.
    """
    rng = random.Random(seed)
    tile = 128
    surf = pygame.Surface((tile, tile), pygame.SRCALPHA)
    for y in range(tile):
        for x in range(tile):
            a = rng.randint(0, intensity)
            if a:
                surf.set_at((x, y), (255, 255, 255, a))
    if width == tile and height == tile:
        return surf
    return pygame.transform.smoothscale(surf, (width, height))


# ---------------------------------------------------------------------------
# OMBRES PORTÉES
# ---------------------------------------------------------------------------
def _shadow_surface(width, height, radius, alpha):
    """Surface d'ombre rectangulaire arrondie avec diffusion alpha."""
    pad = radius + 4
    big = pygame.Surface((width + 2 * pad, height + 2 * pad), pygame.SRCALPHA)
    base = pygame.Rect(pad, pad, width, height)
    # plusieur couches de rectangles arrondis de plus en plus grands et transparents
    for i in range(SHADOW_BLUR_STEPS, -1, -1):
        factor = i / SHADOW_BLUR_STEPS
        offset = int(radius * factor)
        a = int(alpha * (1.0 - factor))
        if a <= 0:
            continue
        r = base.inflate(offset * 2, offset * 2)
        pygame.draw.rect(big, (0, 0, 0, a), r, border_radius=RADIUS_LG + offset // 2)
    return big


def draw_shadow(surf, rect, alpha=SHADOW_ALPHA, radius=SHADOW_RADIUS,
                offset=SHADOW_OFFSET):
    """Dessine une ombre portée douce sous `rect`.

    L'ombre est pré-calculée et blittée. Le coût est faible car les fenêtres
    sont peu nombreuses.
    """
    rect = pygame.Rect(rect)
    key = (rect.w, rect.h, alpha, radius, offset)
    shadow = _shadow_surface(rect.w, rect.h, radius, alpha)
    surf.blit(shadow, (rect.x - shadow.get_width() // 2 + rect.w // 2 + offset[0],
                       rect.y - shadow.get_height() // 2 + rect.h // 2 + offset[1]))


def draw_window_shadow(surf, rect, focused=True):
    """Ombre adaptée à une fenêtre : plus marquée si active."""
    alpha = 110 if focused else 55
    radius = 14 if focused else 9
    offset = (4, 6) if focused else (3, 5)
    draw_shadow(surf, rect, alpha=alpha, radius=radius, offset=offset)


# ---------------------------------------------------------------------------
# FORMES ANTI-ALIASÉES
# ---------------------------------------------------------------------------
def _has_gfxdraw():
    try:
        import pygame.gfxdraw
        return True
    except Exception:
        return False


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
        pygame.draw.circle(surf, color, (int(center[0]), int(center[1])), int(radius), max(1, width))


def draw_aa_filled_circle(surf, center, radius, color):
    """Disque plein anti-aliasé."""
    draw_aa_circle(surf, center, radius, color, width=0)


def draw_aa_round_rect(surf, rect, color, radius=RADIUS_MD, width=0):
    """Rectangle arrondi anti-aliasé (plein si width=0, sinon contour)."""
    rect = pygame.Rect(rect)
    if _HAS_GFX and width <= 1:
        r = max(0, min(radius, rect.w // 2, rect.h // 2))
        if width == 0:
            _gfxdraw.box(surf, rect, color)
            # arrondir les coins en redessinant des disques aux coins
            if r > 0:
                for cx, cy in ((rect.x + r, rect.y + r),
                               (rect.right - r - 1, rect.y + r),
                               (rect.x + r, rect.bottom - r - 1),
                               (rect.right - r - 1, rect.bottom - r - 1)):
                    _gfxdraw.filled_circle(surf, cx, cy, r, color)
                    _gfxdraw.aacircle(surf, cx, cy, r, color)
        else:
            _gfxdraw.rectangle(surf, rect, color)
            # arcs de coin approximés par petits segments
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
    """Dessine une carte/panneau arrondi avec bordure et ombre optionnelles.

    Retourne le Rect intérieur utilisable pour le contenu.
    """
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
        # ligne de séparation colorée
        from ui import widgets
        widgets.draw_text(surf, title.upper(), (rect.x + 10, rect.y + 5),
                          font, title_color or border)
        inner = pygame.Rect(rect.x + (padding or 0), rect.y + 30,
                            rect.w - 2 * (padding or 0), rect.h - 30 - (padding or 0))
    return inner


def draw_inset(surf, rect, bg=None, border=None, radius=RADIUS_SM):
    """Dessine un champ/panneau "enfoncé" (fond sombre + bordure plus claire
    en haut et sombre en bas pour un effet de profondeur)."""
    rect = pygame.Rect(rect)
    bg = bg or config.COL_BG
    border = border or config.COL_BORDER
    pygame.draw.rect(surf, bg, rect, border_radius=radius)
    pygame.draw.rect(surf, border, rect, 1, border_radius=radius)
    # liseré haut très subtil pour l'effet "encastré"
    top = pygame.Rect(rect.x + radius, rect.y + 1, rect.w - 2 * radius, 1)
    pygame.draw.rect(surf, _lerp_color(border, config.COL_WHITE, 0.15), top)
    return rect


def draw_glass_panel(surf, rect, alpha=200, border_color=None, radius=RADIUS_MD):
    """Panneau semi-transparent avec une bordure fine — effet "glass" léger
    pour les overlays (recherche, menus, cartes modales) sans le coût d'un vrai
    flou.
    """
    rect = pygame.Rect(rect)
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    panel.fill(_mix_alpha(config.COL_PANEL, alpha))
    surf.blit(panel, rect.topleft)
    border_color = border_color or _lerp_color(config.COL_BORDER, config.COL_WHITE, 0.25)
    pygame.draw.rect(surf, border_color, rect, 1, border_radius=radius)


def draw_hover_row(surf, rect, hover, selected=False, accent=None,
                   animation_t=0.0, radius=RADIUS_SM):
    """Dessine le fond d'une ligne de liste avec un survol progressif.

    `animation_t` : progression du survol [0,1] (gérée par l'appelant via dt).
    """
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


def draw_badge(surf, rect, color, radius=RADIUS_SM):
    """Petit badge arrondi coloré, avec un léger dégradé vertical."""
    rect = pygame.Rect(rect)
    grad = surface_gradient(rect.w, rect.h, _lerp_color(color, config.COL_WHITE, 0.12), color)
    surf.blit(grad, rect.topleft)
    pygame.draw.rect(surf, color, rect, 1, border_radius=radius)
    return rect
