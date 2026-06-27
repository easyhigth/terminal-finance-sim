"""
simclock_widget.py — Barre ▮▮ ▶ ▶▶ ▶▶▶ de l'horloge de jeu (SimClock).

Affichée par `core/scene_manager.py::SceneManager.draw()` au-dessus de
*toutes* les scènes (sauf l'écran-titre / création de partie), pour que la
vitesse et la pause restent visibles et accessibles depuis n'importe où.
"""
import pygame

from core import config
from core.sim_clock import SPEEDS
from ui import fonts, widgets

BTN_W, BTN_H = 30, 22
GAP = 4
Y = 4

_LABELS = {1: "▶", 2: "▶▶", 3: "▶▶▶"}


# Largeur réservée à droite des boutons d'horloge pour le bouton ⚙ RÉGLAGES
# (icône compacte du terminal, cf. scene_terminal_render). Sur les autres
# scènes ce coin reste simplement vide — alignement cohérent partout.
GEAR_RESERVE = 38


def _btn_rects():
    """Rects des boutons (pause, x1, x2, x3), de gauche à droite, ancrés en
    haut à droite, juste à gauche de l'icône ⚙ RÉGLAGES."""
    n = 1 + len(SPEEDS)
    right = config.SCREEN_WIDTH - 10 - GEAR_RESERVE
    rects = {}
    x = right - n * (BTN_W + GAP)
    rects["pause"] = pygame.Rect(x, Y, BTN_W, BTN_H)
    x += BTN_W + GAP
    for sp in SPEEDS:
        rects[sp] = pygame.Rect(x, Y, BTN_W, BTN_H)
        x += BTN_W + GAP
    return rects


def gear_rect():
    """Rect de l'icône ⚙ RÉGLAGES dans le coin haut-droit (réservé par
    GEAR_RESERVE). Dessinée et gérée par le terminal, mais la géométrie vit
    ici pour rester alignée avec les boutons d'horloge."""
    w = 30
    return pygame.Rect(config.SCREEN_WIDTH - 10 - w, Y, w, BTN_H)


def handle_click(app, pos):
    """Retourne True si le clic a été consommé par la barre d'horloge."""
    clock = getattr(app, "sim_clock", None)
    if clock is None:
        return False
    rects = _btn_rects()
    if rects["pause"].collidepoint(pos):
        clock.toggle_pause()
        return True
    for sp in SPEEDS:
        if rects[sp].collidepoint(pos):
            clock.set_speed(sp)
            return True
    return False


def draw(surf, app):
    clock = getattr(app, "sim_clock", None)
    if clock is None:
        return
    rects = _btn_rects()
    mp = pygame.mouse.get_pos()
    btn = rects["pause"]
    hover = btn.collidepoint(mp)
    active = clock.paused
    bg = config.COL_PANEL_HEAD if (hover or active) else config.COL_PANEL
    pygame.draw.rect(surf, bg, btn, border_radius=4)
    pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, btn, 1, border_radius=4)
    widgets.draw_text(surf, "▮▮", btn.center, fonts.small(bold=True),
                      config.COL_AMBER if active else config.COL_TEXT_DIM, align="center")
    for sp in SPEEDS:
        btn = rects[sp]
        hover = btn.collidepoint(mp)
        active = (clock.speed == sp) and not clock.paused
        bg = config.COL_PANEL_HEAD if (hover or active) else config.COL_PANEL
        pygame.draw.rect(surf, bg, btn, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN if active else config.COL_BORDER, btn, 1, border_radius=4)
        widgets.draw_text(surf, _LABELS[sp], btn.center, fonts.small(bold=True),
                          config.COL_CYAN if active else config.COL_TEXT_DIM, align="center")
    if clock.auto_paused:
        tag_rect = rects["pause"]
        widgets.draw_text(surf, "▮▮ EN PAUSE (action en cours)",
                          (tag_rect.x, tag_rect.bottom + 3), fonts.tiny(), config.COL_AMBER)
