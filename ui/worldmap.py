"""
worldmap.py — Carte du monde interactive (style terminal) au centre du jeu.

Vue MONDE : continents bas-poly, océan quadrillé, hubs régionaux (USA/Europe/
Asia) affichant les indices de la région et la 1ʳᵉ société ; les actualités
« poppent » par région.

Vue RÉGION (au clic sur un hub) : zoom sur la région avec la liste des plus
grosses sociétés, cliquables vers leur fiche, et tous les indices régionaux.

Interaction : handle_click(pos, rect, market) renvoie une action :
  ("zoom", region) | ("company", ticker) | ("unzoom", None) | None
"""
import math
import pygame
from core import config
from ui import fonts, widgets
from data.worldmap_geo import WORLD as CONTINENTS   # côtes détaillées (normalisées)

REGION_HUBS = {
    "USA":     {"pos": (0.16, 0.31), "color": config.COL_USA},
    "Am.Nord": {"pos": (0.21, 0.15), "color": config.COL_NORTHAM},
    "Europe":  {"pos": (0.50, 0.20), "color": config.COL_EUROPE},
    "Afrique": {"pos": (0.53, 0.55), "color": config.COL_AFRICA},
    "Am.Sud":  {"pos": (0.29, 0.66), "color": config.COL_SOUTHAM},
    "Asia":    {"pos": (0.77, 0.27), "color": config.COL_ASIA},
    "Océanie": {"pos": (0.87, 0.74), "color": config.COL_OCEANIA},
}

OCEAN = (10, 16, 26)
LAND = (24, 32, 46)
LAND_EDGE = (58, 74, 100)
LAND_DOT = (46, 64, 86)


def _pt_in_poly(x, y, poly):
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


# Texture de points sur les terres (précalculée une fois, en coords normalisées)
def _build_land_dots(nx=120, ny=64):
    dots = []
    for ix in range(nx):
        x = (ix + 0.5) / nx
        for iy in range(ny):
            y = (iy + 0.5) / ny
            if any(_pt_in_poly(x, y, p) for p in CONTINENTS):
                dots.append((x, y))
    return dots


LAND_DOTS = _build_land_dots()


class WorldMap:
    def __init__(self):
        self.t = 0.0
        self.pings = []
        self.hub_pulse = {r: 0.0 for r in REGION_HUBS}
        self.zoom = None             # None = vue monde ; sinon nom de région
        self._hub_rects = {}         # region -> (cx, cy) en pixels (dernier rendu)
        self._company_rects = {}     # ticker -> Rect (vue région)
        self._unzoom_rect = None

    def _to_screen(self, rect, nx, ny):
        return (rect.x + int(nx * rect.w), rect.y + int(ny * rect.h))

    def push_news(self, news_list):
        for n in news_list:
            region = n.get("region")
            kind = n.get("kind", "info")
            color = (config.COL_EVENT_GOOD if kind == "good"
                     else config.COL_EVENT_BAD if kind == "bad"
                     else config.COL_EVENT_INFO)
            if region and region in REGION_HUBS:
                nx, ny = REGION_HUBS[region]["pos"]
                self.hub_pulse[region] = 1.0
            else:
                nx, ny = 0.5, 0.5
                for r in self.hub_pulse:
                    self.hub_pulse[r] = max(self.hub_pulse[r], 0.7)
            self.pings.append({"nx": nx, "ny": ny, "color": color,
                               "life": 3.0, "max_life": 3.0, "text": n.get("text", "")})
        self.pings = self.pings[-8:]

    def update(self, dt):
        self.t += dt
        for p in self.pings:
            p["life"] -= dt
        self.pings = [p for p in self.pings if p["life"] > 0]
        for r in self.hub_pulse:
            self.hub_pulse[r] = max(0.0, self.hub_pulse[r] - dt * 0.5)

    # --------------------------------------------------------------- click
    def handle_click(self, pos, rect, market):
        rect = pygame.Rect(rect)
        if not rect.collidepoint(pos):
            return None
        if self.zoom is None:
            best = None
            for region, (cx, cy) in self._hub_rects.items():
                d2 = (pos[0] - cx) ** 2 + (pos[1] - cy) ** 2
                if d2 <= 22 ** 2 and (best is None or d2 < best[1]):
                    best = (region, d2)
            if best:
                self.zoom = best[0]
                return ("zoom", best[0])
            return None
        # vue région
        if self._unzoom_rect and self._unzoom_rect.collidepoint(pos):
            self.zoom = None
            return ("unzoom", None)
        for ticker, r in self._company_rects.items():
            if r.collidepoint(pos):
                return ("company", ticker)
        return None

    # ----------------------------------------------------------------- draw
    def draw(self, surf, rect, market):
        rect = pygame.Rect(rect)
        if self.zoom is None:
            self._draw_world(surf, rect, market)
        else:
            self._draw_region(surf, rect, market)

    def _region_indices(self, market, region):
        return [n for n, r, *_ in market.index_defs if r == region]

    def _draw_world(self, surf, rect, market):
        pygame.draw.rect(surf, OCEAN, rect)
        pygame.draw.rect(surf, config.COL_BORDER, rect, 1)
        for gx in range(1, 10):
            x = rect.x + rect.w * gx / 10
            pygame.draw.line(surf, config.COL_GRID, (x, rect.y), (x, rect.bottom), 1)
        for gy in range(1, 6):
            y = rect.y + rect.h * gy / 6
            pygame.draw.line(surf, config.COL_GRID, (rect.x, y), (rect.right, y), 1)
        for poly in CONTINENTS:
            pts = [self._to_screen(rect, nx, ny) for nx, ny in poly]
            pygame.draw.polygon(surf, LAND, pts)
            pygame.draw.polygon(surf, LAND_EDGE, pts, 1)
        # texture de points sur les terres (rendu « carte détaillée »)
        for nx, ny in LAND_DOTS:
            surf.set_at(self._to_screen(rect, nx, ny), LAND_DOT)

        from core.i18n import t as _t
        widgets.draw_text(surf, _t("term.world_hint"),
                          (rect.x + 10, rect.y + 8), fonts.tiny(), config.COL_TEXT_DIM)

        for p in self.pings:
            cx, cy = self._to_screen(rect, p["nx"], p["ny"])
            frac = 1.0 - p["life"] / p["max_life"]
            pygame.draw.circle(surf, p["color"], (cx, cy), int(6 + frac * 26), 1)
            pygame.draw.circle(surf, p["color"], (cx, cy), 3)

        # 7 hubs : point + label court toujours ; la fiche détaillée de l'indice
        # ne s'affiche qu'au SURVOL (sinon trop chargé). Clic = zoom région.
        self._hub_rects = {}
        mp = pygame.mouse.get_pos()
        hovered = None
        for region, hub in REGION_HUBS.items():
            cx, cy = self._to_screen(rect, *hub["pos"])
            self._hub_rects[region] = (cx, cy)
            color = hub["color"]
            pulse = self.hub_pulse[region]
            r = int(4 + 3 * (0.5 + 0.5 * math.sin(self.t * 2)) + pulse * 6)
            is_hover = (mp[0] - cx) ** 2 + (mp[1] - cy) ** 2 <= 16 ** 2
            if is_hover:
                hovered = region
            pygame.draw.circle(surf, color, (cx, cy), r + 2, 1)
            pygame.draw.circle(surf, color, (cx, cy), 3)
            widgets.draw_text(surf, region, (cx + 8, cy - 7), fonts.tiny(bold=is_hover),
                              color if is_hover else config.COL_TEXT)
        # fiche au survol (au-dessus de tout)
        if hovered:
            self._draw_hub_box(surf, rect, hovered, market)

        if self.pings:
            last = self.pings[-1]
            widgets.draw_text(surf, "● " + last["text"], (rect.x + 10, rect.bottom - 20),
                              fonts.small(), last["color"])

    def _draw_hub_box(self, surf, rect, region, market):
        """Petite fiche de l'indice phare d'une région (affichée au survol)."""
        cx, cy = self._hub_rects[region]
        color = REGION_HUBS[region]["color"]
        idxs = self._region_indices(market, region)
        main = idxs[0] if idxs else None
        bw, bh = 138, 38
        bx = max(rect.x + 2, min(rect.right - bw - 2, cx + 10))
        by = max(rect.y + 2, min(rect.bottom - bh - 2, cy - bh - 6))
        box = pygame.Rect(bx, by, bw, bh)
        pygame.draw.rect(surf, (10, 14, 22), box, border_radius=4)
        pygame.draw.rect(surf, color, box, 1, border_radius=4)
        widgets.draw_text(surf, region, (box.x + 6, box.y + 4), fonts.tiny(bold=True), color)
        widgets.draw_text(surf, "clic = zoom", (box.right - 6, box.y + 4),
                          fonts.tiny(), config.COL_TEXT_DIM, align="right")
        if main:
            chg = market.index_change_pct(main)
            ccol = config.COL_UP if chg >= 0 else config.COL_DOWN
            widgets.draw_text(surf, f"{main} {market.index_value(main):,.0f}",
                              (box.x + 6, box.y + 20), fonts.tiny(), config.COL_WHITE)
            widgets.draw_text(surf, f"{'+' if chg>=0 else ''}{chg:.1f}%",
                              (box.right - 6, box.y + 20), fonts.tiny(bold=True),
                              ccol, align="right")

    def _draw_region(self, surf, rect, market):
        region = self.zoom
        accent = REGION_HUBS.get(region, {}).get("color", config.COL_AMBER)
        pygame.draw.rect(surf, OCEAN, rect)
        pygame.draw.rect(surf, accent, rect, 1)
        # en-tête + bouton retour monde
        widgets.draw_text(surf, f"RÉGION — {region}", (rect.x + 12, rect.y + 8),
                          fonts.head(bold=True), accent)
        self._unzoom_rect = pygame.Rect(rect.right - 120, rect.y + 8, 108, 22)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, self._unzoom_rect, border_radius=3)
        pygame.draw.rect(surf, accent, self._unzoom_rect, 1, border_radius=3)
        widgets.draw_text(surf, "‹ MONDE", (self._unzoom_rect.x + 10, self._unzoom_rect.y + 4),
                          fonts.tiny(bold=True), accent)
        # indices régionaux
        y = rect.y + 40
        for nm in self._region_indices(market, region):
            chg = market.index_change_pct(nm)
            ccol = config.COL_UP if chg >= 0 else config.COL_DOWN
            widgets.draw_text(surf, nm, (rect.x + 14, y), fonts.small(bold=True), config.COL_TEXT)
            widgets.draw_text(surf, f"{market.index_value(nm):,.0f}", (rect.x + 150, y),
                              fonts.small(), config.COL_WHITE)
            widgets.draw_text(surf, f"{'+' if chg>=0 else ''}{chg:.2f}%", (rect.x + 250, y),
                              fonts.small(bold=True), ccol)
            y += 20
        pygame.draw.line(surf, config.COL_BORDER, (rect.x + 12, y + 2),
                         (rect.right - 12, y + 2), 1)
        y += 10
        widgets.draw_text(surf, "Sociétés (clic → fiche)", (rect.x + 14, y),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        y += 18
        # liste des sociétés en 3 colonnes — on ne dessine QUE ce qui tient
        # (aucune société à moitié cachée), avec un compteur du reste.
        self._company_rects = {}
        cols = 3
        gap = 10
        col_w = (rect.w - 28 - gap * (cols - 1)) // cols
        x0 = rect.x + 14
        start_y = y
        rowh = 20
        per_col = max(1, (rect.bottom - 12 - start_y) // rowh)
        capacity = cols * per_col
        all_comps = market.top_companies(region=region, n=80)
        comps = all_comps[:capacity]
        mp = pygame.mouse.get_pos()
        for i, c in enumerate(comps):
            col = i // per_col
            row = i % per_col
            x = x0 + col * (col_w + gap)
            ry = start_y + row * rowh
            rr = pygame.Rect(x - 4, ry - 1, col_w, rowh - 1)
            self._company_rects[c["ticker"]] = rr
            hover = rr.collidepoint(mp)
            if hover:
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rr, border_radius=3)
            widgets.draw_text(surf, c["ticker"], (x, ry), fonts.small(bold=True), accent)
            widgets.draw_text(surf, c["name"][:13], (x + 56, ry), fonts.tiny(),
                              config.COL_TEXT if not hover else config.COL_WHITE)
        rest = len(all_comps) - len(comps)
        if rest > 0:
            widgets.draw_text(surf, f"+{rest} autres sociétés dans la région",
                              (rect.x + 14, rect.bottom - 16), fonts.tiny(), config.COL_TEXT_DIM)
