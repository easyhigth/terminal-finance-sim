"""
desktop_icons.py — Icônes vectorielles du bureau et de l'interface.

Les emoji Unicode ne s'affichent pas de façon fiable selon les polices système.
On dessine donc chaque icône en VECTORIEL avec pygame.draw.

Style V4 « complémentaires haut contraste » :
- Fond très foncé/saturé.
- Pictogramme dans la couleur complémentaire/opposée la plus vive possible.
- Pas de blanc : l'icône ENTIÈRE est en couleur néon sur fond noir.
- Contour épais de la couleur du pictogramme pour amplifier le glow.
"""
import math

import pygame

from ui import style


# ---------------------------------------------------------------------------
# Palettes complémentaires : (fond sombre, pictogramme néon vif)
# ---------------------------------------------------------------------------
PALETTES = {
    "research":  ((15, 23, 42),    (56, 189, 248)),    # fond bleu nuit / cyan néon
    "trading":   ((20, 83, 45),    (74, 222, 128)),    # fond vert très foncé / vert néon
    "sheet":     ((6, 78, 59),     (110, 231, 183)),  # fond émeraude noir / menthe
    "terminal":  ((17, 24, 39),    (148, 163, 184)),  # fond nuit / gris clair
    "ma":        ((40, 15, 60),    (232, 121, 249)),  # fond violet noir / magenta clair
    "risk":      ((60, 20, 10),    (251, 146, 60)),   # fond brun/orange noir / orange néon
    "quant":     ((15, 23, 60),    (96, 165, 250)),   # fond bleu nuit profond / bleu clair
    "portfolio": ((10, 25, 70),    (99, 102, 241)),   # fond indigo noir / indigo clair
    "advisory":  ((50, 40, 5),     (250, 204, 21)),   # fond jaune très sale / jaune vif
    "apps":      ((30, 41, 59),    (203, 213, 225)),  # fond ardoise / blanc cassé
    "menu":      ((30, 41, 59),    (203, 213, 225)),
    "market":    ((6, 78, 59),     (45, 212, 191)),   # fond émeraude noir / émeraude néon
    "book":      ((69, 26, 3),     (251, 191, 36)),   # fond brun foncé / ambre vif
    "alert":     ((69, 10, 10),    (248, 113, 113)),  # fond rouge noir / rouge néon
    "inbox":     ((15, 23, 60),    (96, 165, 250)),   # fond bleu profond / bleu clair
    "news":      ((30, 41, 59),    (148, 163, 184)),  # fond ardoise / gris clair
    "mission":   ((60, 20, 10),    (251, 146, 60)),   # fond orange noir / orange néon
    "deals":     ((40, 15, 60),    (216, 180, 254)),  # fond violet noir / violet clair
    "decide":    ((30, 41, 59),    (148, 163, 184)),
    "examcert":  ((50, 40, 5),     (250, 204, 21)),
    "wall":      ((30, 41, 59),    (148, 163, 184)),
    "shop":      ((60, 20, 10),    (251, 146, 60)),
    "explorer":  ((15, 23, 60),    (96, 165, 250)),
    "graph":     ((6, 78, 59),     (45, 212, 191)),
    "save":      ((30, 41, 59),    (148, 163, 184)),
    "help":      ((50, 40, 5),     (250, 204, 21)),
    "calc":      ((30, 41, 59),    (203, 213, 225)),
    "star":      ((50, 40, 5),     (250, 204, 21)),
    "bell":      ((50, 40, 5),     (250, 204, 21)),
}
C_GENERIC = ((17, 24, 39), (148, 163, 184))


# ---------------------------------------------------------------------------
# Helpers de dessin
# ---------------------------------------------------------------------------
def _line(surf, a, b, col, width=2):
    pygame.draw.line(surf, col, a, b, width)


def _rect(surf, rect, col, width=0, radius=2):
    pygame.draw.rect(surf, col, rect, width, border_radius=radius)


def _circle(surf, c, r, col, width=2):
    style.draw_aa_circle(surf, c, r, col, width)


def _disk(surf, c, r, col):
    style.draw_aa_filled_circle(surf, c, r, col)


def _poly(surf, pts, col, width=0):
    pygame.draw.polygon(surf, col, pts, width)


def _tile(surf, cx, cy, bg, neon, size=30, radius=7):
    """Tuile très foncée avec contour néon épais."""
    r = pygame.Rect(cx - size // 2, cy - size // 2, size, size)
    _rect(surf, r, bg, 0, radius=radius)
    # contour néon épais
    _rect(surf, r, neon, 2, radius=radius)
    return r


# ---------------------------------------------------------------------------
# APPS NATIVES DU BUREAU
# ---------------------------------------------------------------------------
def _research(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["research"]
    _tile(surf, cx, cy, bg, neon)
    _circle(surf, (cx - 2, cy - 2), 8, neon, 3)
    _line(surf, (cx + 5, cy + 5), (cx + 12, cy + 12), neon, 4)


def _trading(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["trading"]
    _tile(surf, cx, cy, bg, neon)
    pts = [(cx - 10, cy + 6), (cx - 2, cy - 1), (cx + 6, cy - 6)]
    pygame.draw.lines(surf, neon, False, pts, 4)
    _poly(surf, [(cx + 6, cy - 10), (cx + 12, cy - 4), (cx + 5, cy - 4)], neon, 0)


def _sheet(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["sheet"]
    _tile(surf, cx, cy, bg, neon)
    _rect(surf, pygame.Rect(cx - 8, cy - 9, 16, 18), neon, 2, radius=2)
    _rect(surf, pygame.Rect(cx - 6, cy - 6, 12, 3), neon, 0, radius=1)
    _line(surf, (cx - 1, cy - 2), (cx - 1, cy + 9), neon, 2)
    _line(surf, (cx - 6, cy + 3), (cx + 6, cy + 3), neon, 2)
    _line(surf, (cx - 6, cy + 7), (cx + 6, cy + 7), neon, 2)


def _terminal(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["terminal"]
    _tile(surf, cx, cy, bg, neon)
    _line(surf, (cx - 7, cy - 3), (cx - 2, cy + 2), neon, 3)
    _line(surf, (cx - 7, cy + 2), (cx - 1, cy + 2), neon, 3)
    _rect(surf, pygame.Rect(cx + 2, cy - 1, 5, 3), neon, 0, radius=1)


def _ma(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["ma"]
    _tile(surf, cx, cy, bg, neon)
    _rect(surf, pygame.Rect(cx - 11, cy - 6, 7, 13), neon, 2, radius=2)
    _rect(surf, pygame.Rect(cx + 4, cy - 9, 8, 16), neon, 2, radius=2)
    _line(surf, (cx - 2, cy - 2), (cx + 5, cy - 2), neon, 3)
    _poly(surf, [(cx + 5, cy - 5), (cx + 10, cy - 2), (cx + 5, cy + 1)], neon, 0)


def _risk(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["risk"]
    _tile(surf, cx, cy, bg, neon)
    pts = [(cx, cy - 10), (cx + 10, cy - 5), (cx + 10, cy + 3),
           (cx, cy + 11), (cx - 10, cy + 3), (cx - 10, cy - 5)]
    _poly(surf, pts, neon, 3)
    pts2 = [(cx - 4, cy + 2), (cx - 1, cy - 2), (cx + 1, cy + 1), (cx + 4, cy - 3)]
    pygame.draw.lines(surf, neon, False, pts2, 3)


def _quant(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["quant"]
    _tile(surf, cx, cy, bg, neon)
    _line(surf, (cx - 7, cy - 5), (cx + 7, cy - 5), neon, 3)
    _line(surf, (cx - 7, cy - 5), (cx, cy), neon, 3)
    _line(surf, (cx, cy), (cx - 7, cy + 5), neon, 3)
    _line(surf, (cx - 7, cy + 5), (cx + 7, cy + 5), neon, 3)


def _portfolio(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["portfolio"]
    _tile(surf, cx, cy, bg, neon)
    _circle(surf, (cx, cy), 10, neon, 3)
    _line(surf, (cx, cy), (cx, cy - 10), neon, 3)
    _line(surf, (cx, cy), (cx + 8, cy + 5), neon, 3)
    _disk(surf, (cx, cy), 2, neon)


def _advisory(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["advisory"]
    _tile(surf, cx, cy, bg, neon)
    _rect(surf, pygame.Rect(cx - 6, cy - 9, 11, 18), neon, 2, radius=2)
    _line(surf, (cx - 4, cy - 4), (cx + 3, cy - 4), neon, 2)
    _line(surf, (cx - 4, cy + 1), (cx + 3, cy + 1), neon, 2)
    _circle(surf, (cx + 6, cy - 4), 5, neon, 2)


# ---------------------------------------------------------------------------
# CONTRÔLES / GÉNÉRIQUES
# ---------------------------------------------------------------------------
def _apps_grid(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["apps"]
    _tile(surf, cx, cy, bg, neon)
    step = 5
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            _disk(surf, (cx + dx * step, cy + dy * step), 2, neon)


def _menu(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["menu"]
    _tile(surf, cx, cy, bg, neon)
    for dy in (-5, 0, 5):
        _line(surf, (cx - 8, cy + dy), (cx + 8, cy + dy), neon, 3)


def _generic(surf, cx, cy, _unused=None):
    bg, neon = C_GENERIC
    _tile(surf, cx, cy, bg, neon)
    _circle(surf, (cx, cy), 9, neon, 3)
    _disk(surf, (cx, cy), 3, neon)


# ---------------------------------------------------------------------------
# ACCÈS RAPIDES / QUICK APPS
# ---------------------------------------------------------------------------
def _market(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["market"]
    _tile(surf, cx, cy, bg, neon)
    pts = [(cx - 10, cy + 6), (cx - 3, cy + 1), (cx + 3, cy + 4), (cx + 8, cy - 5)]
    pygame.draw.lines(surf, neon, False, pts, 3)
    _poly(surf, [(cx + 8, cy - 9), (cx + 12, cy - 2), (cx + 5, cy - 2)], neon, 0)


def _book(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["book"]
    _tile(surf, cx, cy, bg, neon)
    _rect(surf, pygame.Rect(cx - 8, cy - 9, 16, 18), neon, 2, radius=2)
    _rect(surf, pygame.Rect(cx - 5, cy - 7, 4, 14), neon, 2, radius=1)
    _line(surf, (cx + 1, cy - 3), (cx + 6, cy - 3), neon, 2)
    _line(surf, (cx + 1, cy + 2), (cx + 6, cy + 2), neon, 2)


def _alert(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["alert"]
    _tile(surf, cx, cy, bg, neon)
    pts = [(cx, cy - 9), (cx + 10, cy + 8), (cx - 10, cy + 8)]
    _poly(surf, pts, neon, 3)
    _rect(surf, pygame.Rect(cx - 1, cy - 2, 2, 5), neon, 0, radius=1)
    _disk(surf, (cx, cy + 5), 2, neon)


def _inbox(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["inbox"]
    _tile(surf, cx, cy, bg, neon)
    r = pygame.Rect(cx - 9, cy - 5, 18, 11)
    _rect(surf, r, neon, 2, radius=2)
    pygame.draw.lines(surf, neon, False,
                      [(r.x, r.y), (r.centerx, r.centery + 1), (r.right, r.y)], 2)


def _news(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["news"]
    _tile(surf, cx, cy, bg, neon)
    _rect(surf, pygame.Rect(cx - 7, cy - 9, 14, 18), neon, 2, radius=2)
    _line(surf, (cx - 5, cy - 5), (cx + 5, cy - 5), neon, 2)
    _rect(surf, pygame.Rect(cx - 5, cy - 1, 5, 5), neon, 2, radius=1)
    _line(surf, (cx + 1, cy - 1), (cx + 4, cy - 1), neon, 2)
    _line(surf, (cx + 1, cy + 3), (cx + 4, cy + 3), neon, 2)


def _mission(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["mission"]
    _tile(surf, cx, cy, bg, neon)
    for r in (9, 5, 2):
        _circle(surf, (cx, cy), r, neon, 2)
    _line(surf, (cx - 10, cy), (cx - 4, cy), neon, 2)
    _line(surf, (cx + 4, cy), (cx + 10, cy), neon, 2)
    _line(surf, (cx, cy - 10), (cx, cy - 4), neon, 2)
    _line(surf, (cx, cy + 4), (cx, cy + 10), neon, 2)


def _deals(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["deals"]
    _tile(surf, cx, cy, bg, neon)
    _rect(surf, pygame.Rect(cx - 7, cy - 9, 14, 18), neon, 2, radius=2)
    _line(surf, (cx - 4, cy - 4), (cx + 4, cy - 4), neon, 2)
    _line(surf, (cx - 4, cy + 1), (cx + 4, cy + 1), neon, 2)
    _disk(surf, (cx + 4, cy + 5), 3, neon)


def _decide(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["decide"]
    _tile(surf, cx, cy, bg, neon)
    _line(surf, (cx, cy - 9), (cx, cy + 8), neon, 3)
    _line(surf, (cx - 8, cy + 8), (cx + 8, cy + 8), neon, 3)
    _line(surf, (cx - 9, cy - 3), (cx + 9, cy - 3), neon, 3)
    pygame.draw.lines(surf, neon, False,
                      [(cx - 9, cy - 3), (cx - 6, cy + 2), (cx - 12, cy + 2)], 2)
    pygame.draw.lines(surf, neon, False,
                      [(cx + 9, cy - 3), (cx + 6, cy + 2), (cx + 12, cy + 2)], 2)


def _examcert(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["examcert"]
    _tile(surf, cx, cy, bg, neon)
    _rect(surf, pygame.Rect(cx - 7, cy - 9, 14, 18), neon, 2, radius=2)
    _line(surf, (cx - 4, cy - 4), (cx + 4, cy - 4), neon, 2)
    _line(surf, (cx - 4, cy + 1), (cx + 4, cy + 1), neon, 2)
    _disk(surf, (cx + 4, cy + 5), 3, neon)


def _wall(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["wall"]
    _tile(surf, cx, cy, bg, neon)
    r = pygame.Rect(cx - 9, cy - 8, 18, 16)
    _rect(surf, r, neon, 2, radius=2)
    _line(surf, (r.x, r.y + r.h // 2), (r.right, r.y + r.h // 2), neon, 2)
    _line(surf, (r.x + r.w // 2, r.y), (r.x + r.w // 2, r.y + r.h // 2), neon, 2)


def _shop(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["shop"]
    _tile(surf, cx, cy, bg, neon)
    _rect(surf, pygame.Rect(cx - 8, cy - 1, 16, 10), neon, 2, radius=2)
    _line(surf, (cx - 5, cy - 1), (cx - 5, cy + 9), neon, 2)
    _line(surf, (cx, cy - 1), (cx, cy + 9), neon, 2)
    _line(surf, (cx + 5, cy - 1), (cx + 5, cy + 9), neon, 2)
    pygame.draw.arc(surf, neon, pygame.Rect(cx - 5, cy - 11, 10, 10), 0, 3.14, 3)


def _explorer(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["explorer"]
    _tile(surf, cx, cy, bg, neon)
    _circle(surf, (cx - 2, cy - 1), 8, neon, 2)
    _line(surf, (cx - 2, cy - 9), (cx - 2, cy + 7), neon, 2)
    _circle(surf, (cx + 6, cy + 5), 4, neon, 2)
    _line(surf, (cx + 8, cy + 7), (cx + 11, cy + 10), neon, 3)


def _graph(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["graph"]
    _tile(surf, cx, cy, bg, neon)
    for dx, h in ((-6, 7), (-2, 11), (2, 8), (6, 13)):
        _rect(surf, pygame.Rect(cx + dx, cy + 6 - h, 3, h), neon, 0, radius=1)


def _save(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["save"]
    _tile(surf, cx, cy, bg, neon)
    _rect(surf, pygame.Rect(cx - 7, cy - 9, 14, 18), neon, 2, radius=2)
    _rect(surf, pygame.Rect(cx - 4, cy - 6, 10, 5), neon, 2, radius=1)
    _rect(surf, pygame.Rect(cx - 2, cy + 1, 4, 3), neon, 2, radius=1)


def _help(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["help"]
    _tile(surf, cx, cy, bg, neon)
    _circle(surf, (cx, cy), 9, neon, 2)
    pygame.draw.arc(surf, neon, pygame.Rect(cx - 3, cy - 6, 6, 6), 3.3, 6.2, 2)
    _disk(surf, (cx, cy + 4), 2, neon)


def _calc(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["calc"]
    _tile(surf, cx, cy, bg, neon)
    _rect(surf, pygame.Rect(cx - 6, cy - 9, 12, 18), neon, 2, radius=2)
    _rect(surf, pygame.Rect(cx - 4, cy - 6, 8, 3), neon, 0, radius=1)
    _rect(surf, pygame.Rect(cx - 4, cy - 1, 3, 3), neon, 0, radius=1)
    _rect(surf, pygame.Rect(cx + 1, cy - 1, 3, 3), neon, 0, radius=1)
    _rect(surf, pygame.Rect(cx - 4, cy + 4, 3, 3), neon, 0, radius=1)
    _rect(surf, pygame.Rect(cx + 1, cy + 4, 3, 3), neon, 0, radius=1)


def _star(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["star"]
    _tile(surf, cx, cy, bg, neon)
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rad = 9 if k % 2 == 0 else 4
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    _poly(surf, pts, neon, 0)


def _bell(surf, cx, cy, _unused=None):
    bg, neon = PALETTES["bell"]
    _tile(surf, cx, cy, bg, neon)
    pygame.draw.arc(surf, neon, pygame.Rect(cx - 7, cy - 9, 14, 16), 3.14, 0, 3)
    _line(surf, (cx - 8, cy + 4), (cx + 8, cy + 4), neon, 3)
    _disk(surf, (cx, cy + 7), 2, neon)
    pygame.draw.arc(surf, neon, pygame.Rect(cx - 4, cy - 13, 8, 6), 3.14, 0, 2)


# ---------------------------------------------------------------------------
# REGISTRE ET API
# ---------------------------------------------------------------------------
_ICONS = {
    "research": _research, "trading": _trading, "sheet": _sheet,
    "terminal": _terminal, "ma": _ma, "risk": _risk, "quant": _quant,
    "portfolio": _portfolio, "advisory": _advisory, "apps": _apps_grid,
    "menu": _menu, "market": _market, "book": _book, "alert": _alert,
    "inbox": _inbox, "news": _news, "mission": _mission, "deals": _deals,
    "decide": _decide, "examcert": _examcert, "wall": _wall, "shop": _shop,
    "explorer": _explorer, "graph": _graph, "save": _save, "help": _help,
    "calc": _calc, "star": _star, "bell": _bell,
}


def draw(surf, center, kind, color=None):
    """Dessine l'icône `kind` centrée sur `center`.

    Style haut contraste : fond très foncé + pictogramme néon en couleur
    complémentaire/opposée. L'argument `color` est ignoré (compatibilité).
    """
    _ICONS.get(kind, _generic)(surf, center[0], center[1])
