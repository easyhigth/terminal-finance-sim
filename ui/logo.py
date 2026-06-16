"""
ui/logo.py — Logo Terminal Alpha dessiné procéduralement avec pygame.
Monogramme TA : barre T, tige, jambes A, barres cyan, triangle or.
"""
import pygame


def draw_ta_logo(surf, cx, cy, size=200):
    """
    Dessine le monogramme TA (Terminal Alpha).
    cx, cy : centre du logo.  size : hauteur totale approximative (px).
    """
    s = size / 200.0

    cream      = (242, 234, 212)
    cyan_edge  = (16,  130, 165)
    cyan_mid   = (55,  205, 235)
    gold_dark  = (175, 125,  15)
    gold_light = (228, 165,  45)

    # --- Barres cyan verticales (fond, derrière la forme blanche) ---
    offsets = [-52, -34, -16, 16, 34, 52]
    bw     = max(1, int(9 * s))
    b_bot  = cy + int(88 * s)
    b_top0 = cy - int(52 * s)

    for off in offsets:
        x    = int(cx + off * s)
        frac = 1.0 - abs(off) / 58.0
        c    = tuple(int(cyan_edge[k] + (cyan_mid[k] - cyan_edge[k]) * frac)
                     for k in range(3))
        h_factor = 0.60 + 0.40 * frac
        b_top = int(b_bot - (b_bot - b_top0) * h_factor)
        pygame.draw.rect(surf, c, (x - bw // 2, b_top, bw, b_bot - b_top))

    # --- Jambes de l'A (polygones diagonaux) ---
    stem_bot_y = cy - int(28 * s)
    stem_x1    = cx - int(13 * s)
    stem_x2    = cx + int(13 * s)
    leg_bot_y  = cy + int(88 * s)
    leg_spread = int(78 * s)
    leg_w      = int(22 * s)

    pygame.draw.polygon(surf, cream, [
        (stem_x1,                   stem_bot_y),
        (stem_x2,                   stem_bot_y),
        (cx - leg_spread + leg_w,   leg_bot_y),
        (cx - leg_spread,           leg_bot_y),
    ])
    pygame.draw.polygon(surf, cream, [
        (stem_x1,                   stem_bot_y),
        (stem_x2,                   stem_bot_y),
        (cx + leg_spread,           leg_bot_y),
        (cx + leg_spread - leg_w,   leg_bot_y),
    ])

    # --- Tige verticale du T ---
    t_stem_top = cy - int(82 * s)
    pygame.draw.rect(surf, cream,
                     (stem_x1, t_stem_top,
                      stem_x2 - stem_x1, stem_bot_y - t_stem_top))

    # --- Barre horizontale du T ---
    bar_w = int(170 * s)
    bar_h = max(2, int(24 * s))
    bar_y = cy - int(96 * s)
    pygame.draw.rect(surf, cream, (cx - bar_w // 2, bar_y, bar_w, bar_h))

    # --- Triangle or (centre du A) ---
    tri_top_y  = stem_bot_y + int(6 * s)
    tri_bot_y  = leg_bot_y - int(4 * s)
    tri_half_w = int(30 * s)

    pygame.draw.polygon(surf, gold_dark, [
        (cx,               tri_top_y),
        (cx - tri_half_w,  tri_bot_y),
        (cx + tri_half_w,  tri_bot_y),
    ])
    # reflet doré (partie haute plus claire)
    hi_frac  = 0.45
    hi_bot_y = int(tri_top_y + (tri_bot_y - tri_top_y) * hi_frac)
    hi_hw    = int(tri_half_w * hi_frac)
    pygame.draw.polygon(surf, gold_light, [
        (cx,        tri_top_y),
        (cx - hi_hw, hi_bot_y),
        (cx + hi_hw, hi_bot_y),
    ])


def make_icon_surface(size=64):
    """Crée une surface pygame pour l'icône de la barre des tâches (taskbar)."""
    icon = pygame.Surface((size, size))
    icon.fill((10, 15, 25))
    draw_ta_logo(icon, size // 2, size // 2 + int(size * 0.04), size=int(size * 0.86))
    return icon
