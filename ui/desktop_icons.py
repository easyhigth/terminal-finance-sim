"""
desktop_icons.py — Icônes vectorielles du bureau (refonte UI « Jeu PC »).

Les emoji (🔍💹▦🖥🤝⚠∑…) ne s'affichent pas de façon fiable : la police
embarquée (JetBrains Mono, cf. `ui/fonts.py`) ne couvre pas les glyphes emoji,
qui apparaissent en blanc/« tofu » selon les plateformes — même défaut déjà
rencontré et corrigé pour le bouton pause (`ui/simclock_widget.py`). On dessine
donc chaque icône en VECTORIEL (primitives `pygame.draw`) : rendu identique
partout, quelle que soit la police système.
"""
import pygame


def _research(surf, cx, cy, col):
    pygame.draw.circle(surf, col, (cx - 4, cy - 4), 10, 2)
    pygame.draw.line(surf, col, (cx + 3, cy + 3), (cx + 11, cy + 11), 3)


def _trading(surf, cx, cy, col):
    pygame.draw.rect(surf, col, (cx - 13, cy + 3, 7, 11))
    pygame.draw.rect(surf, col, (cx - 3, cy - 5, 7, 19))
    pygame.draw.rect(surf, col, (cx + 7, cy - 12, 7, 26))


def _sheet(surf, cx, cy, col):
    r = pygame.Rect(cx - 13, cy - 13, 26, 26)
    pygame.draw.rect(surf, col, r, 2)
    pygame.draw.line(surf, col, (r.x, r.centery), (r.right, r.centery), 1)
    pygame.draw.line(surf, col, (r.centerx, r.y), (r.centerx, r.bottom), 1)
    pygame.draw.line(surf, col, (r.x, r.y + r.h // 4), (r.right, r.y + r.h // 4), 1)
    pygame.draw.line(surf, col, (r.x + 3 * r.w // 4, r.y), (r.x + 3 * r.w // 4, r.bottom), 1)


def _terminal(surf, cx, cy, col):
    r = pygame.Rect(cx - 15, cy - 12, 30, 24)
    pygame.draw.rect(surf, col, r, 2, border_radius=3)
    pygame.draw.lines(surf, col, False,
                      [(r.x + 6, r.y + 7), (r.x + 12, r.y + 12), (r.x + 6, r.y + 17)], 2)
    pygame.draw.line(surf, col, (r.x + 15, r.y + 17), (r.x + 22, r.y + 17), 2)


def _ma(surf, cx, cy, col):
    for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        pygame.draw.line(surf, col, (cx + dx * 13, cy + dy * 9), (cx, cy), 3)
    pygame.draw.circle(surf, col, (cx, cy), 3)


def _risk(surf, cx, cy, col):
    pts = [(cx, cy - 13), (cx - 13, cy + 11), (cx + 13, cy + 11)]
    pygame.draw.polygon(surf, col, pts, 2)
    pygame.draw.line(surf, col, (cx, cy - 3), (cx, cy + 3), 2)
    pygame.draw.circle(surf, col, (cx, cy + 7), 1)


def _quant(surf, cx, cy, col):
    pts = [(cx + 9, cy - 11), (cx - 9, cy - 11), (cx + 3, cy), (cx - 9, cy + 11), (cx + 9, cy + 11)]
    pygame.draw.lines(surf, col, False, pts, 2)


def _portfolio(surf, cx, cy, col):
    pygame.draw.circle(surf, col, (cx, cy), 12, 2)
    pygame.draw.line(surf, col, (cx, cy), (cx, cy - 12), 2)
    pygame.draw.line(surf, col, (cx, cy), (cx + 10, cy + 7), 2)


def _advisory(surf, cx, cy, col):
    r = pygame.Rect(cx - 13, cy - 10, 26, 17)
    pygame.draw.rect(surf, col, r, 2, border_radius=4)
    pygame.draw.polygon(surf, col, [(cx - 5, cy + 7), (cx + 2, cy + 7), (cx - 2, cy + 14)])


def _apps_grid(surf, cx, cy, col):
    s, g = 6, 4
    for dx in (-1, 1):
        for dy in (-1, 1):
            pygame.draw.rect(surf, col, (cx + dx * (s + g) // 2 - s // 2,
                                         cy + dy * (s + g) // 2 - s // 2, s, s))


def _menu(surf, cx, cy, col):
    for i in range(-1, 2):
        pygame.draw.line(surf, col, (cx - 10, cy + i * 6), (cx + 10, cy + i * 6), 2)


def _generic(surf, cx, cy, col):
    pygame.draw.rect(surf, col, (cx - 11, cy - 11, 22, 22), 2, border_radius=3)


# ------------------------------------------------ icônes des accès rapides
# (anciennement le rail latéral du terminal, désormais des icônes du bureau)
def _market(surf, cx, cy, col):
    pts = [(cx - 12, cy + 8), (cx - 4, cy - 2), (cx + 4, cy + 4), (cx + 12, cy - 10)]
    pygame.draw.lines(surf, col, False, pts, 2)
    pygame.draw.circle(surf, col, pts[-1], 2)


def _book(surf, cx, cy, col):
    r = pygame.Rect(cx - 11, cy - 13, 22, 26)
    pygame.draw.rect(surf, col, r, 2, border_radius=2)
    for i in range(3):
        y = r.y + 7 + i * 6
        pygame.draw.line(surf, col, (r.x + 4, y), (r.right - 4, y), 1)


def _alert(surf, cx, cy, col):
    pygame.draw.arc(surf, col, (cx - 9, cy - 12, 18, 18), 0.3, 2.85, 2)
    pygame.draw.line(surf, col, (cx - 9, cy + 2), (cx + 9, cy + 2), 2)
    pygame.draw.circle(surf, col, (cx, cy + 8), 2)


def _inbox(surf, cx, cy, col):
    r = pygame.Rect(cx - 13, cy - 9, 26, 18)
    pygame.draw.rect(surf, col, r, 2, border_radius=2)
    pygame.draw.lines(surf, col, False, [(r.x, r.y), (r.centerx, r.centery + 4), (r.right, r.y)], 2)


def _news(surf, cx, cy, col):
    r = pygame.Rect(cx - 12, cy - 12, 24, 24)
    pygame.draw.rect(surf, col, r, 2)
    for i, w in enumerate((16, 12, 16)):
        y = r.y + 6 + i * 6
        pygame.draw.line(surf, col, (r.x + 4, y), (r.x + 4 + w, y), 1)


def _mission(surf, cx, cy, col):
    pygame.draw.line(surf, col, (cx - 9, cy - 13), (cx - 9, cy + 13), 2)
    pygame.draw.polygon(surf, col, [(cx - 9, cy - 12), (cx + 11, cy - 7), (cx - 9, cy - 2)], 0)


def _deals(surf, cx, cy, col):
    r = pygame.Rect(cx - 13, cy - 6, 26, 18)
    pygame.draw.rect(surf, col, r, 2, border_radius=2)
    pygame.draw.rect(surf, col, (cx - 6, r.y - 6, 12, 8), 2, border_radius=2)
    pygame.draw.line(surf, col, (r.x, r.centery), (r.right, r.centery), 1)


def _decide(surf, cx, cy, col):
    pygame.draw.line(surf, col, (cx, cy - 12), (cx, cy - 2), 2)
    pygame.draw.line(surf, col, (cx, cy - 2), (cx - 9, cy + 10), 2)
    pygame.draw.line(surf, col, (cx, cy - 2), (cx + 9, cy + 10), 2)
    pygame.draw.circle(surf, col, (cx - 9, cy + 12), 2)
    pygame.draw.circle(surf, col, (cx + 9, cy + 12), 2)


def _examcert(surf, cx, cy, col):
    pygame.draw.circle(surf, col, (cx, cy - 4), 9, 2)
    pygame.draw.circle(surf, col, (cx, cy - 4), 4)
    pygame.draw.polygon(surf, col, [(cx - 6, cy + 3), (cx - 2, cy + 13), (cx - 6, cy + 10)])
    pygame.draw.polygon(surf, col, [(cx + 6, cy + 3), (cx + 2, cy + 13), (cx + 6, cy + 10)])


def _wall(surf, cx, cy, col):
    r = pygame.Rect(cx - 13, cy - 11, 26, 22)
    pygame.draw.rect(surf, col, r, 2)
    for i in (1, 2):
        pygame.draw.line(surf, col, (r.x + i * r.w // 3, r.y), (r.x + i * r.w // 3, r.bottom), 1)
        pygame.draw.line(surf, col, (r.x, r.y + i * r.h // 3), (r.right, r.y + i * r.h // 3), 1)


def _shop(surf, cx, cy, col):
    pygame.draw.polygon(surf, col, [(cx - 12, cy - 10), (cx + 4, cy - 10), (cx + 12, cy + 2),
                                    (cx - 4, cy + 12), (cx - 12, cy)], 2)
    pygame.draw.circle(surf, col, (cx + 4, cy - 4), 2)


def _explorer(surf, cx, cy, col):
    pygame.draw.circle(surf, col, (cx, cy), 12, 2)
    pygame.draw.polygon(surf, col, [(cx, cy - 7), (cx + 3, cy), (cx, cy + 7), (cx - 3, cy)], 1)


def _graph(surf, cx, cy, col):
    pygame.draw.line(surf, col, (cx - 12, cy + 12), (cx - 12, cy - 12), 2)
    pygame.draw.line(surf, col, (cx - 12, cy + 12), (cx + 12, cy + 12), 2)
    pts = [(cx - 9, cy + 6), (cx - 2, cy - 2), (cx + 5, cy + 2), (cx + 11, cy - 9)]
    pygame.draw.lines(surf, col, False, pts, 2)


def _save(surf, cx, cy, col):
    r = pygame.Rect(cx - 12, cy - 12, 24, 24)
    pygame.draw.rect(surf, col, r, 2, border_radius=2)
    pygame.draw.rect(surf, col, (r.x + 5, r.y, 12, 8), 1)
    pygame.draw.rect(surf, col, (r.x + 4, r.y + 13, 16, 8), 1)


def _help(surf, cx, cy, col):
    pygame.draw.circle(surf, col, (cx, cy), 12, 2)
    pygame.draw.arc(surf, col, (cx - 5, cy - 8, 10, 10), 3.4, 6.2, 2)
    pygame.draw.line(surf, col, (cx, cy + 1), (cx, cy + 3), 2)
    pygame.draw.circle(surf, col, (cx, cy + 7), 1)


def _star(surf, cx, cy, col):
    import math
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rad = 12 if k % 2 == 0 else 5
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    pygame.draw.polygon(surf, col, pts, 2)


def _calc(surf, cx, cy, col):
    r = pygame.Rect(cx - 11, cy - 13, 22, 26)
    pygame.draw.rect(surf, col, r, 2, border_radius=2)
    pygame.draw.line(surf, col, (r.x + 3, r.y + 5), (r.right - 3, r.y + 5), 1)
    for gy in range(r.y + 11, r.bottom - 3, 6):
        for gx in range(r.x + 4, r.right - 3, 6):
            pygame.draw.rect(surf, col, (gx, gy, 3, 3))


_ICONS = {
    "research": _research, "trading": _trading, "sheet": _sheet,
    "terminal": _terminal, "ma": _ma, "risk": _risk, "quant": _quant,
    "portfolio": _portfolio, "advisory": _advisory, "apps": _apps_grid,
    "menu": _menu, "market": _market, "book": _book, "alert": _alert,
    "inbox": _inbox, "news": _news, "mission": _mission, "deals": _deals,
    "decide": _decide, "examcert": _examcert, "wall": _wall, "shop": _shop,
    "explorer": _explorer, "graph": _graph, "save": _save, "help": _help,
    "calc": _calc, "star": _star,
}


def draw(surf, center, kind, color):
    """Dessine l'icône `kind` centrée sur `center` (repère absolu de `surf`)."""
    _ICONS.get(kind, _generic)(surf, center[0], center[1], color)
