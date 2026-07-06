"""
desktop_icons.py — Icônes vectorielles du bureau et de l'interface.

Les emoji Unicode ne s'affichent pas de façon fiable selon les polices système.
On dessine donc chaque icône en VECTORIEL avec pygame.draw.

Style V3 « tuiles OS » :
- Fond carré arrondi coloré par fonction (style dock / lanceur d'apps).
- Pictogramme blanc, très simplifié, en gros traits (3–4 px).
- Pas de micro-détails : lisible immédiatement en 24×24 et en 40×40.
- Chaque icône reste centrée sur (cx, cy) et tient dans ~30×30 px.
"""
import math

import pygame

from ui import style


# ---------------------------------------------------------------------------
# Palette de fond par icône (style dock)
# ---------------------------------------------------------------------------
C_RESEARCH  = (59, 130, 246)    # bleu
C_TRADING   = (34, 197, 94)     # vert
C_SHEET     = (22, 163, 74)     # vert foncé
C_TERMINAL  = (55, 65, 81)      # gris foncé
C_MA        = (147, 51, 234)    # violet
C_RISK      = (249, 115, 22)    # orange
C_QUANT     = (37, 99, 235)      # bleu royal
C_PORTFOLIO = (29, 78, 216)     # bleu marine
C_ADVISORY  = (234, 179, 8)     # jaune
C_APPS      = (75, 85, 99)      # gris
C_MENU      = (75, 85, 99)      # gris
C_MARKET    = (16, 185, 129)    # émeraude
C_BOOK      = (180, 83, 9)      # marron
C_ALERT     = (239, 68, 68)     # rouge
C_INBOX     = (59, 130, 246)    # bleu
C_NEWS      = (107, 114, 128)   # gris
C_MISSION   = (249, 115, 22)    # orange
C_DEALS     = (147, 51, 234)    # violet
C_DECIDE    = (107, 114, 128)   # gris
C_EXAMCERT  = (234, 179, 8)     # jaune
C_WALL      = (107, 114, 128)   # gris
C_SHOP      = (249, 115, 22)    # orange
C_EXPLORER  = (37, 99, 235)     # bleu
C_GRAPH     = (16, 185, 129)    # émeraude
C_SAVE      = (107, 114, 128)   # gris
C_HELP      = (234, 179, 8)     # jaune
C_CALC      = (75, 85, 99)      # gris
C_STAR      = (234, 179, 8)     # jaune
C_BELL      = (234, 179, 8)     # jaune
C_GENERIC   = (107, 114, 128)   # gris


_ICON_BG = {
    "research": C_RESEARCH, "trading": C_TRADING, "sheet": C_SHEET,
    "terminal": C_TERMINAL, "ma": C_MA, "risk": C_RISK, "quant": C_QUANT,
    "portfolio": C_PORTFOLIO, "advisory": C_ADVISORY, "apps": C_APPS,
    "menu": C_MENU, "market": C_MARKET, "book": C_BOOK, "alert": C_ALERT,
    "inbox": C_INBOX, "news": C_NEWS, "mission": C_MISSION, "deals": C_DEALS,
    "decide": C_DECIDE, "examcert": C_EXAMCERT, "wall": C_WALL, "shop": C_SHOP,
    "explorer": C_EXPLORER, "graph": C_GRAPH, "save": C_SAVE, "help": C_HELP,
    "calc": C_CALC, "star": C_STAR, "bell": C_BELL,
}


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


def _thick_line(surf, a, b, col, width=3):
    pygame.draw.line(surf, col, a, b, width)


def _tile(surf, cx, cy, col, size=26, radius=6):
    """Fond carré arrondi de l'icône."""
    r = pygame.Rect(cx - size // 2, cy - size // 2, size, size)
    _rect(surf, r, col, 0, radius=radius)
    return r


# ---------------------------------------------------------------------------
# APPS NATIVES DU BUREAU
# ---------------------------------------------------------------------------
def _research(surf, cx, cy, col):
    """Loupe blanche sur fond bleu."""
    _tile(surf, cx, cy, C_RESEARCH, 28, 7)
    _circle(surf, (cx - 3, cy - 3), 7, col, 3)
    _thick_line(surf, (cx + 4, cy + 4), (cx + 12, cy + 12), col, 4)


def _trading(surf, cx, cy, col):
    """Flèche haussière sur fond vert."""
    _tile(surf, cx, cy, C_TRADING, 28, 7)
    _thick_line(surf, (cx - 8, cy + 5), (cx - 2, cy - 2), col, 4)
    _thick_line(surf, (cx - 2, cy - 2), (cx + 7, cy - 8), col, 4)
    _poly(surf, [(cx + 7, cy - 12), (cx + 12, cy - 5), (cx + 4, cy - 5)], col, 0)


def _sheet(surf, cx, cy, col):
    """Grille tableur sur fond vert foncé."""
    _tile(surf, cx, cy, C_SHEET, 28, 7)
    _rect(surf, pygame.Rect(cx - 8, cy - 9, 16, 18), col, 2, radius=2)
    _line(surf, (cx - 8, cy - 4), (cx + 8, cy - 4), col, 2)
    _line(surf, (cx, cy - 9), (cx, cy + 9), col, 2)
    _line(surf, (cx - 8, cy + 3), (cx + 8, cy + 3), col, 2)


def _terminal(surf, cx, cy, col):
    """Invite >_ sur fond gris foncé."""
    _tile(surf, cx, cy, C_TERMINAL, 28, 7)
    _thick_line(surf, (cx - 7, cy - 3), (cx - 2, cy + 2), col, 3)
    _thick_line(surf, (cx - 7, cy + 2), (cx - 2, cy + 2), col, 3)
    _rect(surf, pygame.Rect(cx + 2, cy - 1, 6, 3), col, 0, radius=1)


def _ma(surf, cx, cy, col):
    """Fusion de deux blocs sur fond violet."""
    _tile(surf, cx, cy, C_MA, 28, 7)
    _rect(surf, pygame.Rect(cx - 10, cy - 5, 7, 12), col, 2, radius=2)
    _rect(surf, pygame.Rect(cx + 3, cy - 8, 8, 15), col, 2, radius=2)
    _poly(surf, [(cx - 2, cy - 4), (cx + 5, cy), (cx - 2, cy + 4)], col, 0)


def _risk(surf, cx, cy, col):
    """Bouclier avec éclair sur fond orange."""
    _tile(surf, cx, cy, C_RISK, 28, 7)
    pts = [(cx, cy - 10), (cx + 9, cy - 5), (cx + 9, cy + 3),
           (cx, cy + 11), (cx - 9, cy + 3), (cx - 9, cy - 5)]
    _poly(surf, pts, col, 3)
    pts2 = [(cx - 3, cy + 3), (cx, cy - 3), (cx + 3, cy + 3)]
    pygame.draw.lines(surf, col, False, pts2, 3)


def _quant(surf, cx, cy, col):
    """Sigma stylisé sur fond bleu royal."""
    _tile(surf, cx, cy, C_QUANT, 28, 7)
    _thick_line(surf, (cx - 7, cy - 6), (cx + 7, cy - 6), col, 3)
    _thick_line(surf, (cx - 7, cy - 6), (cx, cy), col, 3)
    _thick_line(surf, (cx, cy), (cx - 7, cy + 6), col, 3)
    _thick_line(surf, (cx - 7, cy + 6), (cx + 7, cy + 6), col, 3)


def _portfolio(surf, cx, cy, col):
    """Camembert sur fond bleu marine."""
    _tile(surf, cx, cy, C_PORTFOLIO, 28, 7)
    _circle(surf, (cx, cy), 10, col, 3)
    _thick_line(surf, (cx, cy), (cx, cy - 10), col, 3)
    _thick_line(surf, (cx, cy), (cx + 8, cy + 5), col, 3)


def _advisory(surf, cx, cy, col):
    """Document + bulle sur fond jaune."""
    _tile(surf, cx, cy, C_ADVISORY, 28, 7)
    _rect(surf, pygame.Rect(cx - 7, cy - 9, 12, 18), col, 2, radius=2)
    _line(surf, (cx - 5, cy - 4), (cx + 3, cy - 4), col, 2)
    _line(surf, (cx - 5, cy + 1), (cx + 3, cy + 1), col, 2)
    _circle(surf, (cx + 5, cy - 4), 4, col, 2)


# ---------------------------------------------------------------------------
# CONTRÔLES / GÉNÉRIQUES
# ---------------------------------------------------------------------------
def _apps_grid(surf, cx, cy, col):
    """Grille 3×3 sur fond gris."""
    _tile(surf, cx, cy, C_APPS, 26, 6)
    step = 5
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            _disk(surf, (cx + dx * step, cy + dy * step), 2, col)


def _menu(surf, cx, cy, col):
    """Hamburger sur fond gris."""
    _tile(surf, cx, cy, C_MENU, 26, 6)
    for dy in (-5, 0, 5):
        _thick_line(surf, (cx - 8, cy + dy), (cx + 8, cy + dy), col, 3)


def _generic(surf, cx, cy, col):
    """Tuile grise avec disque blanc."""
    _tile(surf, cx, cy, C_GENERIC, 26, 6)
    _disk(surf, (cx, cy), 5, col)


# ---------------------------------------------------------------------------
# ACCÈS RAPIDES / QUICK APPS
# ---------------------------------------------------------------------------
def _market(surf, cx, cy, col):
    """Courbe haussière sur fond émeraude."""
    _tile(surf, cx, cy, C_MARKET, 26, 6)
    _thick_line(surf, (cx - 9, cy + 6), (cx - 4, cy + 2), col, 3)
    _thick_line(surf, (cx - 4, cy + 2), (cx + 3, cy + 5), col, 3)
    _thick_line(surf, (cx + 3, cy + 5), (cx + 9, cy - 5), col, 3)
    _poly(surf, [(cx + 9, cy - 9), (cx + 12, cy - 2), (cx + 5, cy - 2)], col, 0)


def _book(surf, cx, cy, col):
    """Classeur sur fond marron."""
    _tile(surf, cx, cy, C_BOOK, 26, 6)
    _rect(surf, pygame.Rect(cx - 8, cy - 9, 16, 18), col, 2, radius=2)
    _rect(surf, pygame.Rect(cx - 5, cy - 7, 4, 14), col, 2, radius=1)
    _line(surf, (cx + 1, cy - 3), (cx + 6, cy - 3), col, 2)
    _line(surf, (cx + 1, cy + 2), (cx + 6, cy + 2), col, 2)


def _alert(surf, cx, cy, col):
    """Triangle d'alerte sur fond rouge."""
    _tile(surf, cx, cy, C_ALERT, 26, 6)
    pts = [(cx, cy - 9), (cx + 10, cy + 8), (cx - 10, cy + 8)]
    _poly(surf, pts, col, 3)
    _rect(surf, pygame.Rect(cx - 1, cy - 2, 2, 5), col, 0, radius=1)
    _disk(surf, (cx, cy + 5), 2, col)


def _inbox(surf, cx, cy, col):
    """Enveloppe sur fond bleu."""
    _tile(surf, cx, cy, C_INBOX, 26, 6)
    r = pygame.Rect(cx - 9, cy - 6, 18, 12)
    _rect(surf, r, col, 2, radius=2)
    pygame.draw.lines(surf, col, False,
                      [(r.x, r.y), (r.centerx, r.centery + 2), (r.right, r.y)], 2)


def _news(surf, cx, cy, col):
    """Journal sur fond gris."""
    _tile(surf, cx, cy, C_NEWS, 26, 6)
    _rect(surf, pygame.Rect(cx - 7, cy - 9, 14, 18), col, 2, radius=2)
    _thick_line(surf, (cx - 5, cy - 5), (cx + 5, cy - 5), col, 2)
    _rect(surf, pygame.Rect(cx - 5, cy - 1, 5, 5), col, 2, radius=1)
    _line(surf, (cx + 1, cy - 1), (cx + 4, cy - 1), col, 2)
    _line(surf, (cx + 1, cy + 3), (cx + 4, cy + 3), col, 2)


def _mission(surf, cx, cy, col):
    """Cible sur fond orange."""
    _tile(surf, cx, cy, C_MISSION, 26, 6)
    for r in (9, 5, 2):
        _circle(surf, (cx, cy), r, col, 2)
    _thick_line(surf, (cx - 10, cy), (cx - 4, cy), col, 2)
    _thick_line(surf, (cx + 4, cy), (cx + 10, cy), col, 2)
    _thick_line(surf, (cx, cy - 10), (cx, cy - 4), col, 2)
    _thick_line(surf, (cx, cy + 4), (cx, cy + 10), col, 2)


def _deals(surf, cx, cy, col):
    """Contrat + sceau sur fond violet."""
    _tile(surf, cx, cy, C_DEALS, 26, 6)
    _rect(surf, pygame.Rect(cx - 7, cy - 9, 14, 18), col, 2, radius=2)
    _line(surf, (cx - 4, cy - 4), (cx + 4, cy - 4), col, 2)
    _line(surf, (cx - 4, cy + 1), (cx + 4, cy + 1), col, 2)
    _disk(surf, (cx + 4, cy + 5), 3, col)


def _decide(surf, cx, cy, col):
    """Balance sur fond gris."""
    _tile(surf, cx, cy, C_DECIDE, 26, 6)
    _thick_line(surf, (cx, cy - 9), (cx, cy + 8), col, 3)
    _thick_line(surf, (cx - 8, cy + 8), (cx + 8, cy + 8), col, 3)
    _thick_line(surf, (cx - 9, cy - 3), (cx + 9, cy - 3), col, 3)
    pygame.draw.lines(surf, col, False,
                      [(cx - 9, cy - 3), (cx - 6, cy + 2), (cx - 12, cy + 2)], 2)
    pygame.draw.lines(surf, col, False,
                      [(cx + 9, cy - 3), (cx + 6, cy + 2), (cx + 12, cy + 2)], 2)


def _examcert(surf, cx, cy, col):
    """Diplôme sur fond jaune."""
    _tile(surf, cx, cy, C_EXAMCERT, 26, 6)
    _rect(surf, pygame.Rect(cx - 7, cy - 9, 14, 18), col, 2, radius=2)
    _line(surf, (cx - 4, cy - 4), (cx + 4, cy - 4), col, 2)
    _line(surf, (cx - 4, cy + 1), (cx + 4, cy + 1), col, 2)
    _disk(surf, (cx + 4, cy + 5), 3, col)


def _wall(surf, cx, cy, col):
    """Mur de briques sur fond gris."""
    _tile(surf, cx, cy, C_WALL, 26, 6)
    r = pygame.Rect(cx - 9, cy - 8, 18, 16)
    _rect(surf, r, col, 2, radius=2)
    _line(surf, (r.x, r.y + r.h // 2), (r.right, r.y + r.h // 2), col, 2)
    _line(surf, (r.x + r.w // 2, r.y), (r.x + r.w // 2, r.y + r.h // 2), col, 2)


def _shop(surf, cx, cy, col):
    """Panier sur fond orange."""
    _tile(surf, cx, cy, C_SHOP, 26, 6)
    _rect(surf, pygame.Rect(cx - 8, cy - 1, 16, 10), col, 2, radius=2)
    _line(surf, (cx - 5, cy - 1), (cx - 5, cy + 9), col, 2)
    _line(surf, (cx, cy - 1), (cx, cy + 9), col, 2)
    _line(surf, (cx + 5, cy - 1), (cx + 5, cy + 9), col, 2)
    # poignée plus haute
    pygame.draw.arc(surf, col, pygame.Rect(cx - 5, cy - 11, 10, 10), 0, 3.14, 3)


def _explorer(surf, cx, cy, col):
    """Globe + loupe sur fond bleu."""
    _tile(surf, cx, cy, C_EXPLORER, 26, 6)
    _circle(surf, (cx - 2, cy - 1), 8, col, 2)
    _line(surf, (cx - 2, cy - 9), (cx - 2, cy + 7), col, 2)
    _circle(surf, (cx + 6, cy + 5), 4, col, 2)
    _thick_line(surf, (cx + 8, cy + 7), (cx + 11, cy + 10), col, 3)


def _graph(surf, cx, cy, col):
    """Barres sur fond émeraude."""
    _tile(surf, cx, cy, C_GRAPH, 26, 6)
    for dx, h in ((-6, 7), (-2, 11), (2, 8), (6, 13)):
        _rect(surf, pygame.Rect(cx + dx, cy + 6 - h, 3, h), col, 0, radius=1)


def _save(surf, cx, cy, col):
    """Disquette sur fond gris."""
    _tile(surf, cx, cy, C_SAVE, 26, 6)
    _rect(surf, pygame.Rect(cx - 7, cy - 9, 14, 18), col, 2, radius=2)
    _rect(surf, pygame.Rect(cx - 4, cy - 6, 10, 5), col, 2, radius=1)
    _rect(surf, pygame.Rect(cx - 2, cy + 1, 4, 3), col, 2, radius=1)


def _help(surf, cx, cy, col):
    """Point d'interrogation sur fond jaune."""
    _tile(surf, cx, cy, C_HELP, 26, 6)
    _circle(surf, (cx, cy), 9, col, 2)
    pygame.draw.arc(surf, col, pygame.Rect(cx - 3, cy - 6, 6, 6), 3.3, 6.2, 2)
    _disk(surf, (cx, cy + 4), 2, col)


def _calc(surf, cx, cy, col):
    """Calculatrice sur fond gris."""
    _tile(surf, cx, cy, C_CALC, 26, 6)
    _rect(surf, pygame.Rect(cx - 6, cy - 9, 12, 18), col, 2, radius=2)
    _rect(surf, pygame.Rect(cx - 4, cy - 6, 8, 3), col, 2, radius=1)
    # touches en grille 2×2 plus visibles
    _rect(surf, pygame.Rect(cx - 4, cy - 1, 3, 3), col, 0, radius=1)
    _rect(surf, pygame.Rect(cx + 1, cy - 1, 3, 3), col, 0, radius=1)
    _rect(surf, pygame.Rect(cx - 4, cy + 4, 3, 3), col, 0, radius=1)
    _rect(surf, pygame.Rect(cx + 1, cy + 4, 3, 3), col, 0, radius=1)


def _star(surf, cx, cy, col):
    """Étoile pleine sur fond jaune."""
    _tile(surf, cx, cy, C_STAR, 26, 6)
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rad = 9 if k % 2 == 0 else 4
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    _poly(surf, pts, col, 0)


def _bell(surf, cx, cy, col):
    """Cloche sur fond jaune."""
    _tile(surf, cx, cy, C_BELL, 26, 6)
    pygame.draw.arc(surf, col, pygame.Rect(cx - 7, cy - 9, 14, 16), 3.14, 0, 3)
    _thick_line(surf, (cx - 8, cy + 4), (cx + 8, cy + 4), col, 3)
    _disk(surf, (cx, cy + 7), 2, col)
    pygame.draw.arc(surf, col, pygame.Rect(cx - 4, cy - 13, 8, 6), 3.14, 0, 2)


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


def draw(surf, center, kind, color=(255, 255, 255)):
    """Dessine l'icône `kind` centrée sur `center`.

    Le fond est une tuile colorée fixe par type d'icône (style dock).
    `color` teinte le pictogramme (blanc par défaut).
    Si `kind` est inconnu, dessine une tuile générique sans planter.
    """
    _ICONS.get(kind, _generic)(surf, center[0], center[1], color)
