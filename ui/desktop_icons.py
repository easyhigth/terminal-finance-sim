"""
desktop_icons.py — Icônes vectorielles du bureau et de l'interface.

Les emoji Unicode ne s'affichent pas de façon fiable selon les polices système.
On dessine donc chaque icône en VECTORIEL avec pygame.draw.

Style V3++ « tuiles OS haut contraste » :
- Fonds colorés vifs et saturés, pour trancher sur le bureau sombre.
- Pictogrammes blancs purs, traits épais (3–4 px).
- Ombre portée noire légère sous chaque tuile pour un effet de relief.
- Halo blanc subtil autour du pictogramme pour le faire "sauter".
- Taille de tuile 30×30 px ; pictogrammes simplifiés et bien centrés.
"""
import math

import pygame

from ui import style


# ---------------------------------------------------------------------------
# Palette de fond (couleurs vives, plus saturées)
# ---------------------------------------------------------------------------
C_RESEARCH  = (66, 153, 255)    # bleu vif
C_TRADING   = (52, 211, 153)    # vert vif
C_SHEET     = (34, 197, 94)     # vert
C_TERMINAL  = (75, 85, 99)     # gris
C_MA        = (168, 85, 247)    # violet vif
C_RISK      = (251, 146, 60)    # orange vif
C_QUANT     = (59, 130, 246)    # bleu royal
C_PORTFOLIO = (37, 99, 235)     # bleu marine
C_ADVISORY  = (250, 204, 21)    # jaune vif
C_APPS      = (100, 116, 139)   # gris clair
C_MENU      = (100, 116, 139)   # gris clair
C_MARKET    = (45, 212, 191)    # émeraude vif
C_BOOK      = (245, 158, 11)    # ambre/orange foncé
C_ALERT     = (248, 113, 113)    # rouge vif
C_INBOX     = (96, 165, 250)    # bleu clair
C_NEWS      = (148, 163, 184)   # gris clair
C_MISSION   = (251, 146, 60)    # orange vif
C_DEALS     = (192, 132, 252)   # violet clair
C_DECIDE    = (148, 163, 184)   # gris clair
C_EXAMCERT  = (250, 204, 21)    # jaune vif
C_WALL      = (148, 163, 184)   # gris clair
C_SHOP      = (251, 146, 60)    # orange vif
C_EXPLORER  = (59, 130, 246)    # bleu
C_GRAPH     = (45, 212, 191)    # émeraude vif
C_SAVE      = (148, 163, 184)   # gris clair
C_HELP      = (250, 204, 21)    # jaune vif
C_CALC      = (100, 116, 139)   # gris clair
C_STAR      = (250, 204, 21)    # jaune vif
C_BELL      = (250, 204, 21)    # jaune vif
C_GENERIC   = (148, 163, 184)   # gris clair

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


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


def _shadow(surf, cx, cy, size=30, radius=7):
    """Ombre portée noire semi-transparente sous la tuile."""
    r = pygame.Rect(cx - size // 2 + 2, cy - size // 2 + 3, size, size)
    shadow_surf = pygame.Surface((size + 4, size + 4), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surf, (0, 0, 0, 70), shadow_surf.get_rect(), border_radius=radius)
    surf.blit(shadow_surf, (r.x - 2, r.y - 2))


def _tile(surf, cx, cy, col, size=30, radius=7):
    """Fond carré arrondi coloré + ombre + contour subtil."""
    _shadow(surf, cx, cy, size, radius)
    r = pygame.Rect(cx - size // 2, cy - size // 2, size, size)
    _rect(surf, r, col, 0, radius=radius)
    # contour plus foncé pour sceller la tuile
    edge = tuple(max(0, int(c * 0.6)) for c in col)
    _rect(surf, r, edge, 1, radius=radius)
    return r


# ---------------------------------------------------------------------------
# APPS NATIVES DU BUREAU
# ---------------------------------------------------------------------------
def _research(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_RESEARCH)
    _circle(surf, (cx - 2, cy - 2), 8, col, 3)
    _line(surf, (cx + 5, cy + 5), (cx + 12, cy + 12), col, 4)


def _trading(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_TRADING)
    pts = [(cx - 10, cy + 6), (cx - 2, cy - 1), (cx + 6, cy - 6)]
    pygame.draw.lines(surf, col, False, pts, 4)
    _poly(surf, [(cx + 6, cy - 10), (cx + 12, cy - 4), (cx + 5, cy - 4)], col, 0)


def _sheet(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_SHEET)
    _rect(surf, pygame.Rect(cx - 8, cy - 9, 16, 18), col, 2, radius=2)
    _rect(surf, pygame.Rect(cx - 6, cy - 6, 12, 3), col, 0, radius=1)
    _line(surf, (cx - 1, cy - 2), (cx - 1, cy + 9), col, 2)
    _line(surf, (cx - 6, cy + 3), (cx + 6, cy + 3), col, 2)
    _line(surf, (cx - 6, cy + 7), (cx + 6, cy + 7), col, 2)


def _terminal(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_TERMINAL)
    _line(surf, (cx - 7, cy - 3), (cx - 2, cy + 2), col, 3)
    _line(surf, (cx - 7, cy + 2), (cx - 1, cy + 2), col, 3)
    _rect(surf, pygame.Rect(cx + 2, cy - 1, 5, 3), col, 0, radius=1)


def _ma(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_MA)
    _rect(surf, pygame.Rect(cx - 11, cy - 6, 7, 13), col, 2, radius=2)
    _rect(surf, pygame.Rect(cx + 4, cy - 9, 8, 16), col, 2, radius=2)
    _line(surf, (cx - 2, cy - 2), (cx + 5, cy - 2), col, 3)
    _poly(surf, [(cx + 5, cy - 5), (cx + 10, cy - 2), (cx + 5, cy + 1)], col, 0)


def _risk(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_RISK)
    pts = [(cx, cy - 10), (cx + 10, cy - 5), (cx + 10, cy + 3),
           (cx, cy + 11), (cx - 10, cy + 3), (cx - 10, cy - 5)]
    _poly(surf, pts, col, 3)
    pts2 = [(cx - 4, cy + 2), (cx - 1, cy - 2), (cx + 1, cy + 1), (cx + 4, cy - 3)]
    pygame.draw.lines(surf, col, False, pts2, 3)


def _quant(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_QUANT)
    _line(surf, (cx - 7, cy - 5), (cx + 7, cy - 5), col, 3)
    _line(surf, (cx - 7, cy - 5), (cx, cy), col, 3)
    _line(surf, (cx, cy), (cx - 7, cy + 5), col, 3)
    _line(surf, (cx - 7, cy + 5), (cx + 7, cy + 5), col, 3)


def _portfolio(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_PORTFOLIO)
    _circle(surf, (cx, cy), 10, col, 3)
    _line(surf, (cx, cy), (cx, cy - 10), col, 3)
    _line(surf, (cx, cy), (cx + 8, cy + 5), col, 3)
    _disk(surf, (cx, cy), 2, col)


def _advisory(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_ADVISORY)
    _rect(surf, pygame.Rect(cx - 6, cy - 9, 11, 18), col, 2, radius=2)
    _line(surf, (cx - 4, cy - 4), (cx + 3, cy - 4), col, 2)
    _line(surf, (cx - 4, cy + 1), (cx + 3, cy + 1), col, 2)
    _circle(surf, (cx + 6, cy - 4), 5, col, 2)


# ---------------------------------------------------------------------------
# CONTRÔLES / GÉNÉRIQUES
# ---------------------------------------------------------------------------
def _apps_grid(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_APPS)
    step = 5
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            _disk(surf, (cx + dx * step, cy + dy * step), 2, col)


def _menu(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_MENU)
    for dy in (-5, 0, 5):
        _line(surf, (cx - 8, cy + dy), (cx + 8, cy + dy), col, 3)


def _generic(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_GENERIC)
    _circle(surf, (cx, cy), 9, col, 3)
    _disk(surf, (cx, cy), 3, col)


# ---------------------------------------------------------------------------
# ACCÈS RAPIDES / QUICK APPS
# ---------------------------------------------------------------------------
def _market(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_MARKET)
    pts = [(cx - 10, cy + 5), (cx - 3, cy + 1), (cx + 3, cy + 4), (cx + 8, cy - 5)]
    pygame.draw.lines(surf, col, False, pts, 3)
    _poly(surf, [(cx + 8, cy - 9), (cx + 12, cy - 2), (cx + 5, cy - 2)], col, 0)


def _book(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_BOOK)
    _rect(surf, pygame.Rect(cx - 8, cy - 9, 16, 18), col, 2, radius=2)
    _rect(surf, pygame.Rect(cx - 5, cy - 7, 4, 14), col, 2, radius=1)
    _line(surf, (cx + 1, cy - 3), (cx + 6, cy - 3), col, 2)
    _line(surf, (cx + 1, cy + 2), (cx + 6, cy + 2), col, 2)


def _alert(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_ALERT)
    pts = [(cx, cy - 9), (cx + 10, cy + 8), (cx - 10, cy + 8)]
    _poly(surf, pts, col, 3)
    _rect(surf, pygame.Rect(cx - 1, cy - 2, 2, 5), col, 0, radius=1)
    _disk(surf, (cx, cy + 5), 2, col)


def _inbox(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_INBOX)
    r = pygame.Rect(cx - 9, cy - 5, 18, 11)
    _rect(surf, r, col, 2, radius=2)
    pygame.draw.lines(surf, col, False,
                      [(r.x, r.y), (r.centerx, r.centery + 1), (r.right, r.y)], 2)


def _news(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_NEWS)
    _rect(surf, pygame.Rect(cx - 7, cy - 9, 14, 18), col, 2, radius=2)
    _line(surf, (cx - 5, cy - 5), (cx + 5, cy - 5), col, 2)
    _rect(surf, pygame.Rect(cx - 5, cy - 1, 5, 5), col, 2, radius=1)
    _line(surf, (cx + 1, cy - 1), (cx + 4, cy - 1), col, 2)
    _line(surf, (cx + 1, cy + 3), (cx + 4, cy + 3), col, 2)


def _mission(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_MISSION)
    for r in (9, 5, 2):
        _circle(surf, (cx, cy), r, col, 2)
    _line(surf, (cx - 10, cy), (cx - 4, cy), col, 2)
    _line(surf, (cx + 4, cy), (cx + 10, cy), col, 2)
    _line(surf, (cx, cy - 10), (cx, cy - 4), col, 2)
    _line(surf, (cx, cy + 4), (cx, cy + 10), col, 2)


def _deals(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_DEALS)
    _rect(surf, pygame.Rect(cx - 7, cy - 9, 14, 18), col, 2, radius=2)
    _line(surf, (cx - 4, cy - 4), (cx + 4, cy - 4), col, 2)
    _line(surf, (cx - 4, cy + 1), (cx + 4, cy + 1), col, 2)
    _disk(surf, (cx + 4, cy + 5), 3, col)


def _decide(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_DECIDE)
    _line(surf, (cx, cy - 9), (cx, cy + 8), col, 3)
    _line(surf, (cx - 8, cy + 8), (cx + 8, cy + 8), col, 3)
    _line(surf, (cx - 9, cy - 3), (cx + 9, cy - 3), col, 3)
    pygame.draw.lines(surf, col, False,
                      [(cx - 9, cy - 3), (cx - 6, cy + 2), (cx - 12, cy + 2)], 2)
    pygame.draw.lines(surf, col, False,
                      [(cx + 9, cy - 3), (cx + 6, cy + 2), (cx + 12, cy + 2)], 2)


def _examcert(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_EXAMCERT)
    _rect(surf, pygame.Rect(cx - 7, cy - 9, 14, 18), col, 2, radius=2)
    _line(surf, (cx - 4, cy - 4), (cx + 4, cy - 4), col, 2)
    _line(surf, (cx - 4, cy + 1), (cx + 4, cy + 1), col, 2)
    _disk(surf, (cx + 4, cy + 5), 3, col)


def _wall(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_WALL)
    r = pygame.Rect(cx - 9, cy - 8, 18, 16)
    _rect(surf, r, col, 2, radius=2)
    _line(surf, (r.x, r.y + r.h // 2), (r.right, r.y + r.h // 2), col, 2)
    _line(surf, (r.x + r.w // 2, r.y), (r.x + r.w // 2, r.y + r.h // 2), col, 2)


def _shop(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_SHOP)
    _rect(surf, pygame.Rect(cx - 8, cy - 1, 16, 10), col, 2, radius=2)
    _line(surf, (cx - 5, cy - 1), (cx - 5, cy + 9), col, 2)
    _line(surf, (cx, cy - 1), (cx, cy + 9), col, 2)
    _line(surf, (cx + 5, cy - 1), (cx + 5, cy + 9), col, 2)
    pygame.draw.arc(surf, col, pygame.Rect(cx - 5, cy - 11, 10, 10), 0, 3.14, 3)


def _explorer(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_EXPLORER)
    _circle(surf, (cx - 2, cy - 1), 8, col, 2)
    _line(surf, (cx - 2, cy - 9), (cx - 2, cy + 7), col, 2)
    _circle(surf, (cx + 6, cy + 5), 4, col, 2)
    _line(surf, (cx + 8, cy + 7), (cx + 11, cy + 10), col, 3)


def _graph(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_GRAPH)
    for dx, h in ((-6, 7), (-2, 11), (2, 8), (6, 13)):
        _rect(surf, pygame.Rect(cx + dx, cy + 6 - h, 3, h), col, 0, radius=1)


def _save(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_SAVE)
    _rect(surf, pygame.Rect(cx - 7, cy - 9, 14, 18), col, 2, radius=2)
    _rect(surf, pygame.Rect(cx - 4, cy - 6, 10, 5), col, 2, radius=1)
    _rect(surf, pygame.Rect(cx - 2, cy + 1, 4, 3), col, 2, radius=1)


def _help(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_HELP)
    _circle(surf, (cx, cy), 9, col, 2)
    pygame.draw.arc(surf, col, pygame.Rect(cx - 3, cy - 6, 6, 6), 3.3, 6.2, 2)
    _disk(surf, (cx, cy + 4), 2, col)


def _calc(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_CALC)
    _rect(surf, pygame.Rect(cx - 6, cy - 9, 12, 18), col, 2, radius=2)
    _rect(surf, pygame.Rect(cx - 4, cy - 6, 8, 3), col, 0, radius=1)
    _rect(surf, pygame.Rect(cx - 4, cy - 1, 3, 3), col, 0, radius=1)
    _rect(surf, pygame.Rect(cx + 1, cy - 1, 3, 3), col, 0, radius=1)
    _rect(surf, pygame.Rect(cx - 4, cy + 4, 3, 3), col, 0, radius=1)
    _rect(surf, pygame.Rect(cx + 1, cy + 4, 3, 3), col, 0, radius=1)


def _star(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_STAR)
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rad = 9 if k % 2 == 0 else 4
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    _poly(surf, pts, col, 0)


def _bell(surf, cx, cy, col=WHITE):
    _tile(surf, cx, cy, C_BELL)
    pygame.draw.arc(surf, col, pygame.Rect(cx - 7, cy - 9, 14, 16), 3.14, 0, 3)
    _line(surf, (cx - 8, cy + 4), (cx + 8, cy + 4), col, 3)
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


def draw(surf, center, kind, color=WHITE):
    """Dessine l'icône `kind` centrée sur `center`.

    Le fond est une tuile colorée vive, avec ombre portée.
    `color` teinte le pictogramme (blanc pur par défaut).
    Si `kind` est inconnu, dessine une tuile générique sans planter.
    """
    _ICONS.get(kind, _generic)(surf, center[0], center[1], color)
