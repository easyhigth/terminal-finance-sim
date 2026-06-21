"""
keynav.py — Gestionnaire central de navigation clavier (focus spatial).

Fournit les primitives réutilisées par les scènes pour qu'un joueur puisse
jouer 100% au clavier :
  - `nearest_in_direction` : trouve, parmi un ensemble de rects positionnés à
    l'écran, celui le plus pertinent dans une direction (HAUT/BAS/GAUCHE/
    DROITE) par rapport à un rect courant — navigation *spatiale*, pas juste
    linéaire.
  - `grid_nav` : variante de `widgets.list_key_nav` pour une grille de rects
    réels (pas un simple index), en s'appuyant sur `nearest_in_direction`.
  - `FocusRing` : dessine l'indicateur de focus clavier, visuellement distinct
    du survol souris (cyan) et de l'ambre par défaut — un double-liseré blanc
    avec coins accentués.
  - `ZoneStack` : pile de niveaux de focus pour la navigation hiérarchique
    scène → bloc → contenu interne (Entrée = descendre d'un niveau, Échap =
    remonter d'un niveau), cf. scene_terminal.py pour l'exemple de référence.
"""
import pygame

from core import config

DIRECTIONS = {
    pygame.K_UP: "up",
    pygame.K_DOWN: "down",
    pygame.K_LEFT: "left",
    pygame.K_RIGHT: "right",
}


def nearest_in_direction(rects, current, direction):
    """Parmi `rects` (dict id -> pygame.Rect), renvoie l'id le plus proche de
    `current` dans `direction` ('up'/'down'/'left'/'right'), selon la position
    visuelle réelle (centre des rects). Pénalise le désalignement sur l'axe
    perpendiculaire pour rester intuitif. Renvoie `current` si rien ne convient."""
    if current not in rects:
        return current
    cx, cy = rects[current].center
    best, best_score = None, None
    for key, r in rects.items():
        if key == current:
            continue
        x, y = r.center
        dx, dy = x - cx, y - cy
        if direction == "up" and dy >= -1:
            continue
        if direction == "down" and dy <= 1:
            continue
        if direction == "left" and dx >= -1:
            continue
        if direction == "right" and dx <= 1:
            continue
        if direction in ("up", "down"):
            primary, perp = abs(dy), abs(dx)
        else:
            primary, perp = abs(dx), abs(dy)
        score = primary + perp * 2.0
        if best_score is None or score < best_score:
            best_score, best = score, key
    return best if best is not None else current


def grid_nav(event, rects, current):
    """Navigation spatiale 4-directions + Entrée sur une grille de rects réels
    (dict id -> Rect, ou liste — un index sert alors d'id). Renvoie
    (nouvel_id, activer)."""
    if event.type != pygame.KEYDOWN:
        return current, False
    items = rects if isinstance(rects, dict) else {i: r for i, r in enumerate(rects)}
    if not items:
        return current, False
    if current not in items:
        current = next(iter(items))
    if event.key in DIRECTIONS:
        nxt = nearest_in_direction(items, current, DIRECTIONS[event.key])
        return nxt, False
    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        return current, True
    return current, False


def draw_focus_ring(surf, rect, focused, color=config.COL_FOCUS):
    """Dessine l'indicateur de focus CLAVIER (distinct du survol souris cyan
    et de la sélection ambre) : double liseré + coins accentués, pour rester
    visible même sur un panneau déjà coloré."""
    if not focused:
        return
    r = pygame.Rect(rect).inflate(4, 4)
    pygame.draw.rect(surf, color, r, 2, border_radius=5)
    cl = 10
    for cx, cy, dx, dy in (
        (r.left, r.top, 1, 1), (r.right, r.top, -1, 1),
        (r.left, r.bottom, 1, -1), (r.right, r.bottom, -1, -1),
    ):
        pygame.draw.line(surf, color, (cx, cy), (cx + dx * cl, cy), 3)
        pygame.draw.line(surf, color, (cx, cy), (cx, cy + dy * cl), 3)


class ZoneStack:
    """Pile de niveaux de focus pour la navigation hiérarchique
    bloc → contenu interne. Niveau 0 = blocs de la scène (Tab/flèches en
    déplacent le focus) ; Entrée pousse un niveau « interne » (les items du
    bloc, naviguables aux flèches) ; Échap dépile (`pop`) pour remonter."""

    def __init__(self, zone_order):
        self.zone_order = list(zone_order)
        self.zone = self.zone_order[0] if self.zone_order else None
        self.inside = False          # True = focus descendu dans le bloc courant
        self.item = None             # id de l'item interne sélectionné

    def cycle_zone(self, step=1):
        if not self.zone_order:
            return
        self.inside = False
        self.item = None
        i = self.zone_order.index(self.zone)
        self.zone = self.zone_order[(i + step) % len(self.zone_order)]

    def move_zone(self, zone_rects, direction):
        """Déplace le focus de bloc selon la position visuelle réelle des blocs."""
        self.inside = False
        self.item = None
        self.zone = nearest_in_direction(zone_rects, self.zone, direction)

    def enter(self):
        self.inside = True
        self.item = None

    def escape(self):
        """Remonte d'un niveau. Renvoie True si on était « dans » un bloc
        (consommé localement), False si on était déjà au niveau des blocs
        (laisse l'appelant gérer l'échap de scène)."""
        if self.inside:
            self.inside = False
            self.item = None
            return True
        return False
