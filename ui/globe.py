"""
globe.py — Globe terrestre 3D filaire en rotation, projeté à la main.
Pas de dépendance 3D externe : on projette des points (lat, lon) sur un
disque via une projection orthographique simple, avec rotation continue.
Les continents sont des hotspots cliquables.
"""
import math
import pygame
from core import config
from ui import fonts, widgets
from ui.worldmap import CONTINENTS as _LAND_POLYS   # formes (x:lon, y:lat) normalisées


def _in_poly(x, y, poly):
    """Ray casting : (x, y) dans le polygone (coordonnées normalisées 0..1)."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi):
            inside = not inside
        j = i
    return inside


def _is_land(lat_deg, lon_deg):
    x = (lon_deg + 180) / 360.0
    y = (90 - lat_deg) / 180.0
    return any(_in_poly(x, y, p) for p in _LAND_POLYS)


# Grille océan (méridiens/parallèles) + masque de terre (points « continents »)
def _sphere_grid(step=15):
    return [(math.radians(lat), math.radians(lon))
            for lat in range(-75, 76, step) for lon in range(-180, 180, step)]


def _land_grid(step=5):
    return [(math.radians(lat), math.radians(lon))
            for lat in range(-78, 79, step) for lon in range(-180, 180, step)
            if _is_land(lat, lon)]


# Centres approximatifs des régions cliquables (lat, lon) en degrés
REGION_ANCHORS = {
    "Europe":  (50, 10),
    "USA":     (39, -98),
    "Asia":    (34, 108),
    "Am.Nord": (58, -106),
    "Am.Sud":  (-15, -58),
    "Afrique": (2, 22),
    "Océanie": (-27, 134),
}


class Globe:
    def __init__(self, center, radius):
        self.cx, self.cy = center
        self.r = radius
        self.rot = 0.0                 # rotation longitude (rad)
        self.tilt = math.radians(18)   # inclinaison de l'axe
        self.grid = _sphere_grid(15)
        self.land = _land_grid(3)        # points « terre » (continents) — fine pour le détail
        self.hover_region = None

    # --- Projection orthographique d'un point (lat, lon) en rad ----------
    def _project(self, lat, lon):
        lon = lon + self.rot
        x = math.cos(lat) * math.sin(lon)
        y = math.sin(lat) * math.cos(self.tilt) - \
            math.cos(lat) * math.cos(lon) * math.sin(self.tilt)
        z = math.sin(lat) * math.sin(self.tilt) + \
            math.cos(lat) * math.cos(lon) * math.cos(self.tilt)
        sx = self.cx + x * self.r
        sy = self.cy - y * self.r
        return sx, sy, z   # z>0 => face visible

    def update(self, dt, mouse_pos):
        self.rot += dt * 0.25          # rotation lente
        # détection de survol des ancres régionales
        self.hover_region = None
        for name, (lat, lon) in REGION_ANCHORS.items():
            sx, sy, z = self._project(math.radians(lat), math.radians(lon))
            if z > 0 and math.hypot(mouse_pos[0]-sx, mouse_pos[1]-sy) < 26:
                self.hover_region = name
                break

    def region_at(self, pos):
        """Retourne le nom de région cliquée, ou None."""
        for name, (lat, lon) in REGION_ANCHORS.items():
            sx, sy, z = self._project(math.radians(lat), math.radians(lon))
            if z > 0 and math.hypot(pos[0]-sx, pos[1]-sy) < 26:
                return name
        return None

    def draw(self, surf):
        # halo
        for i, a in enumerate((28, 18, 10)):
            s = pygame.Surface((self.r*2+40, self.r*2+40), pygame.SRCALPHA)
            pygame.draw.circle(s, (*config.COL_CYAN, a),
                               (self.r+20, self.r+20), self.r+10-i*4)
            surf.blit(s, (self.cx-self.r-20, self.cy-self.r-20))

        # disque océan
        pygame.draw.circle(surf, (10, 16, 26), (self.cx, self.cy), self.r)
        pygame.draw.circle(surf, config.COL_BORDER, (self.cx, self.cy), self.r, 1)

        # grille océan (points discrets, faibles)
        for lat, lon in self.grid:
            sx, sy, z = self._project(lat, lon)
            if z > 0:
                shade = int(40 + 50 * z)
                surf.set_at((int(sx), int(sy)), (shade // 3, shade // 2, shade))

        # masse continentale (points « terre » plus clairs/verts)
        for lat, lon in self.land:
            sx, sy, z = self._project(lat, lon)
            if z > 0:
                g = int(70 + 120 * z)
                col = (int(g * 0.45), g, int(g * 0.6))
                r = 2 if z > 0.45 else 1
                pygame.draw.circle(surf, col, (int(sx), int(sy)), r)

        # ancres régionales
        for name, (lat, lon) in REGION_ANCHORS.items():
            sx, sy, z = self._project(math.radians(lat), math.radians(lon))
            if z <= 0:
                continue
            color = config.CONTINENTS[name]["color"]
            hovered = (self.hover_region == name)
            rad = 9 if hovered else 6
            pygame.draw.circle(surf, color, (int(sx), int(sy)), rad)
            pygame.draw.circle(surf, config.COL_WHITE, (int(sx), int(sy)), rad, 1)
            if hovered:
                widgets.draw_text(surf, name, (int(sx)+14, int(sy)-8),
                                  fonts.small(bold=True), color)
