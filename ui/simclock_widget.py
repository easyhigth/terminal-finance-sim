"""
simclock_widget.py — Contrôles d'horloge de jeu (pause / x1 / x2 / x3) + icône
⚙ RÉGLAGES, dessinés dans la BANDE D'ONGLETS (en haut de la fenêtre, sur leur
propre ligne), par `core/pages.py::PageManager`. Ils ne chevauchent donc plus
jamais le bandeau d'info des scènes (devise, badges…) ni le ticker.

Les icônes sont dessinées en VECTORIEL (barres pour la pause, triangles pour
les vitesses) plutôt qu'avec des glyphes Unicode, qui ne sont pas garantis dans
la police monospace embarquée (le « ▮▮ » de pause ne s'affichait pas).

Coordonnées en repère FENÊTRE (la bande d'onglets vit au-dessus du canvas de
jeu), donc les clics sont gérés par PageManager avant la translation souris.
"""
import pygame

from core import config
from core.sim_clock import SPEEDS
from ui import widgets

BTN_W, BTN_H = 30, 20
GAP = 4
GEAR_W = 28
PAD_RIGHT = 8


def cluster_width():
    """Largeur totale réservée à droite de la bande d'onglets (boutons + gear)."""
    n = 1 + len(SPEEDS)
    return n * BTN_W + n * GAP + GEAR_W + PAD_RIGHT + 8


def _rects():
    """Rects (repère fenêtre) : pause, x1, x2, x3 (gauche→droite) puis gear, le
    tout aligné à droite, centré verticalement dans la bande d'onglets."""
    y = (config.TAB_BAR_H - BTN_H) // 2
    gear = pygame.Rect(config.SCREEN_WIDTH - PAD_RIGHT - GEAR_W, y, GEAR_W, BTN_H)
    rects = {"gear": gear}
    x = gear.x - 8 - BTN_W
    for sp in reversed(SPEEDS):
        rects[sp] = pygame.Rect(x, y, BTN_W, BTN_H)
        x -= BTN_W + GAP
    rects["pause"] = pygame.Rect(x, y, BTN_W, BTN_H)
    return rects


def gear_rect():
    return _rects()["gear"]


# ----------------------------------------------------------------- icônes vectorielles
def _draw_pause(surf, rect, col):
    bw, gap = 3, 3
    h = rect.h - 8
    y = rect.centery - h // 2
    pygame.draw.rect(surf, col, (rect.centerx - gap // 2 - bw, y, bw, h))
    pygame.draw.rect(surf, col, (rect.centerx + gap // 2, y, bw, h))


def _draw_speed(surf, rect, count, col):
    """`count` petits triangles « play » côte à côte (1 = x1, 2 = x2, 3 = x3)."""
    h = rect.h - 9
    tw = h - 1
    total = count * tw + (count - 1) * 2
    x = rect.centerx - total // 2
    cy = rect.centery
    for _ in range(count):
        pygame.draw.polygon(surf, col, [(x, cy - h // 2), (x, cy + h // 2), (x + tw, cy)])
        x += tw + 2


def _draw_gear(surf, rect, col):
    # roue simplifiée : disque + couronne de dents, lisible à petite taille
    cx, cy = rect.center
    r = rect.h // 2 - 2
    pygame.draw.circle(surf, col, (cx, cy), r, 1)
    pygame.draw.circle(surf, col, (cx, cy), max(1, r // 3))
    import math
    for k in range(8):
        a = k * math.pi / 4
        x1 = cx + int(r * math.cos(a)); y1 = cy + int(r * math.sin(a))
        x2 = cx + int((r + 3) * math.cos(a)); y2 = cy + int((r + 3) * math.sin(a))
        pygame.draw.line(surf, col, (x1, y1), (x2, y2), 1)


def _btn_bg(surf, rect, active, hover, accent):
    bg = config.COL_PANEL_HEAD if (hover or active) else config.COL_PANEL
    pygame.draw.rect(surf, bg, rect, border_radius=4)
    pygame.draw.rect(surf, accent if active else config.COL_BORDER, rect, 1, border_radius=4)


# ----------------------------------------------------------------- API
def handle_click(app, win_pos):
    """Clic en repère FENÊTRE (bande d'onglets). Retourne True si consommé."""
    clock = getattr(app, "sim_clock", None)
    if clock is None:
        return False
    rects = _rects()
    if rects["gear"].collidepoint(win_pos):
        cur = app.scenes.current_name or "terminal"
        if cur != "settings":
            app.scenes.go("settings", return_to=cur)
        return True
    if rects["pause"].collidepoint(win_pos):
        clock.toggle_pause()
        return True
    for sp in SPEEDS:
        if rects[sp].collidepoint(win_pos):
            clock.set_speed(sp)
            return True
    return False


def draw(surf, app):
    """Dessine les contrôles dans la bande d'onglets (surf = fenêtre complète)."""
    clock = getattr(app, "sim_clock", None)
    if clock is None:
        return
    rects = _rects()
    # PageManager a remplacé pygame.mouse.get_pos par une version translatée en
    # repère canvas ; pour la bande d'onglets on veut le repère fenêtre.
    mx, my = _window_mouse()
    # pause
    pr = rects["pause"]
    paused = clock.paused or clock.auto_paused
    _btn_bg(surf, pr, paused, pr.collidepoint((mx, my)), config.COL_AMBER)
    _draw_pause(surf, pr, config.COL_AMBER if paused else config.COL_TEXT_DIM)
    # vitesses
    for sp in SPEEDS:
        r = rects[sp]
        active = (clock.speed == sp) and not clock.paused and not clock.auto_paused
        _btn_bg(surf, r, active, r.collidepoint((mx, my)), config.COL_CYAN)
        _draw_speed(surf, r, sp, config.COL_CYAN if active else config.COL_TEXT_DIM)
    # gear
    g = rects["gear"]
    ghover = g.collidepoint((mx, my))
    _btn_bg(surf, g, False, ghover, config.COL_AMBER)
    _draw_gear(surf, g, config.COL_AMBER if ghover else config.COL_TEXT_DIM)
    # état de pause auto : petit liseré ambre déjà via le fond ; tooltip au survol
    if ghover:
        widgets.draw_tooltip(surf, "Réglages (affichage, son, langue, raccourcis)",
                             (g.left - 6, g.bottom + 2))
    elif pr.collidepoint((mx, my)):
        label = "Reprendre (Espace)" if paused else "Pause (Espace)"
        widgets.draw_tooltip(surf, label, (pr.left, pr.bottom + 2))


def _window_mouse():
    """Position souris en repère FENÊTRE (annule la translation canvas que
    core/pages.py applique globalement à pygame.mouse.get_pos)."""
    x, y = pygame.mouse.get_pos()
    return x, y + config.TAB_BAR_H
