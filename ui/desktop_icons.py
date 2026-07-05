"""
desktop_icons.py — Icônes vectorielles du bureau et de l'interface.

Les emoji Unicode ne s'affichent pas de façon fiable selon les polices système.
On dessine donc chaque icône en VECTORIEL avec pygame.draw / pygame.gfxdraw :
rendu identique partout, de 16×16 (barre de titre) à 40×40 (bureau).

Style : icônes de 24×24 px logiques, trait de 2px, formes reconnaissables,
anti-aliasées. Chaque icône est pensée comme un pictogramme autonome :
la métaphore doit être lisible au premier coup d'œil.
"""
import math

import pygame

from ui import style


# ---------------------------------------------------------------------------
# Helpers de dessin
# ---------------------------------------------------------------------------
def _line(surf, a, b, col, width=2):
    """Ligne avec épaisseur, centrée sur les points."""
    pygame.draw.line(surf, col, a, b, width)


def _rect(surf, rect, col, width=0, radius=2):
    """Rectangle arrondi, plein ou contour."""
    pygame.draw.rect(surf, col, rect, width, border_radius=radius)


def _circle(surf, c, r, col, width=2):
    """Cercle anti-aliasé."""
    style.draw_aa_circle(surf, c, r, col, width)


def _disk(surf, c, r, col):
    """Disque plein anti-aliasé."""
    style.draw_aa_filled_circle(surf, c, r, col)


def _poly(surf, pts, col, width=0):
    """Polygone plein ou contour."""
    pygame.draw.polygon(surf, col, pts, width)


def _rounded_bottom(surf, cx, cy, w, h, r, col, width=0):
    """Rectangle avec les deux coins du bas arrondis (style carte/app)."""
    rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
    pygame.draw.rect(surf, col, rect, width, border_radius=r)


# ---------------------------------------------------------------------------
# APPS NATIVES DU BUREAU
# ---------------------------------------------------------------------------
def _research(surf, cx, cy, col):
    """Loupe classique : cercle + poignée oblique."""
    _circle(surf, (cx - 3, cy - 3), 9, col, 2)
    _line(surf, (cx + 4, cy + 4), (cx + 12, cy + 12), col, 3)


def _trading(surf, cx, cy, col):
    """Graphique à bougies avec une flèche de tendance haussière."""
    # cadre
    _rect(surf, pygame.Rect(cx - 13, cy - 12, 26, 24), col, 2, radius=2)
    # bougies
    for dx, h, top in ((-6, 10, -2), (0, 14, -5), (6, 9, 0)):
        bw = 3
        x = cx + dx - bw // 2
        y1 = cy + top
        y2 = cy + top + h
        _rect(surf, pygame.Rect(x, y1, bw, h), col, 0, radius=1)
        _line(surf, (cx + dx, y1 - 3), (cx + dx, y2 + 3), col, 1)
    # flèche tendance
    _line(surf, (cx - 10, cy + 7), (cx + 4, cy - 3), col, 2)
    _poly(surf, [(cx + 4, cy - 6), (cx + 9, cy - 3), (cx + 4, cy)], col, 0)


def _sheet(surf, cx, cy, col):
    """Feuille de calcul type Excel : grille + onglet + barre de formule."""
    r = pygame.Rect(cx - 12, cy - 13, 24, 26)
    _rect(surf, r, col, 2, radius=2)
    # barre de formule
    _line(surf, (r.x + 3, r.y + 5), (r.right - 3, r.y + 5), col, 1)
    # colonnes
    for gx in (r.x + 7, r.x + 13, r.x + 19):
        _line(surf, (gx, r.y + 8), (gx, r.bottom - 3), col, 1)
    # lignes
    for gy in (r.y + 12, r.y + 17, r.y + 22):
        _line(surf, (r.x + 3, gy), (r.right - 3, gy), col, 1)
    # onglet en bas
    _rect(surf, pygame.Rect(r.x + 4, r.bottom - 5, 10, 5), col, 0, radius=1)


def _terminal(surf, cx, cy, col):
    """Terminal : écran avec invite `>` et curseur."""
    r = pygame.Rect(cx - 14, cy - 11, 28, 22)
    _rect(surf, r, col, 2, radius=3)
    # prompt >
    _line(surf, (r.x + 5, r.y + 8), (r.x + 9, r.y + 12), col, 2)
    _line(surf, (r.x + 5, r.y + 16), (r.x + 9, r.y + 12), col, 2)
    # ligne de commande
    _line(surf, (r.x + 12, r.y + 15), (r.right - 6, r.y + 15), col, 2)
    # curseur
    _rect(surf, pygame.Rect(r.right - 5, r.y + 12, 3, 6), col, 0, radius=1)


def _ma(surf, cx, cy, col):
    """M&A : deux bâtiments reliés par une flèche de fusion."""
    # bâtiment gauche (plus petit)
    _rect(surf, pygame.Rect(cx - 12, cy - 4, 8, 12), col, 2, radius=1)
    # bâtiment droit (plus grand)
    _rect(surf, pygame.Rect(cx + 4, cy - 9, 9, 17), col, 2, radius=1)
    # flèche de fusion horizontale
    _line(surf, (cx - 2, cy - 2), (cx + 2, cy - 2), col, 2)
    _poly(surf, [(cx + 2, cy - 5), (cx + 7, cy - 2), (cx + 2, cy + 1)], col, 0)


def _risk(surf, cx, cy, col):
    """Risk : bouclier avec une courbe de volatilité dedans."""
    # bouclier
    pts = [(cx, cy - 12), (cx + 11, cy - 6), (cx + 11, cy + 3),
           (cx, cy + 12), (cx - 11, cy + 3), (cx - 11, cy - 6)]
    _poly(surf, pts, col, 2)
    # courbe électrocardiogramme / volatilité
    pts2 = [(cx - 6, cy + 2), (cx - 3, cy - 1), (cx, cy + 2),
            (cx + 3, cy - 4), (cx + 6, cy + 1)]
    pygame.draw.lines(surf, col, False, pts2, 2)


def _quant(surf, cx, cy, col):
    """Quant : sigma Σ + courbe de fonction mathématique."""
    # sigma grec stylisé
    _line(surf, (cx - 8, cy - 9), (cx + 6, cy - 9), col, 2)
    _line(surf, (cx - 8, cy - 9), (cx - 1, cy), col, 2)
    _line(surf, (cx - 1, cy), (cx - 8, cy + 9), col, 2)
    _line(surf, (cx - 8, cy + 9), (cx + 6, cy + 9), col, 2)
    # petite courbe sinusoïdale
    pts = [(cx + 4, cy - 7), (cx + 7, cy - 2), (cx + 10, cy - 5), (cx + 13, cy + 2)]
    pygame.draw.lines(surf, col, False, pts, 2)


def _portfolio(surf, cx, cy, col):
    """Portfolio : camembert 3 portions + bourse/sac."""
    _circle(surf, (cx - 2, cy - 2), 11, col, 2)
    # deux lignes de séparation du camembert
    _line(surf, (cx - 2, cy - 2), (cx - 2, cy - 13), col, 2)
    _line(surf, (cx - 2, cy - 2), (cx + 8, cy + 6), col, 2)
    # petit sac / bourse à droite
    _rect(surf, pygame.Rect(cx + 8, cy + 2, 6, 8), col, 2, radius=2)
    _line(surf, (cx + 9, cy + 2), (cx + 13, cy + 2), col, 2)


def _advisory(surf, cx, cy, col):
    """Advisory : contrat avec signature + bulle de conseil."""
    # feuille de contrat
    r = pygame.Rect(cx - 10, cy - 11, 16, 22)
    _rect(surf, r, col, 2, radius=1)
    # lignes de texte
    for dy in (r.y + 5, r.y + 10, r.y + 15):
        _line(surf, (r.x + 3, dy), (r.right - 3, dy), col, 1)
    # signature
    _line(surf, (r.x + 3, r.bottom - 5), (r.right - 3, r.bottom - 5), col, 2)
    # bulle
    _circle(surf, (cx + 7, cy - 6), 6, col, 2)
    _line(surf, (cx + 4, cy - 4), (cx + 2, cy + 2), col, 2)


# ---------------------------------------------------------------------------
# CONTRÔLES / GÉNÉRIQUES
# ---------------------------------------------------------------------------
def _apps_grid(surf, cx, cy, col):
    """Grille d'applications : 3×3 points."""
    step = 6
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            _disk(surf, (cx + dx * step, cy + dy * step), 2, col)


def _menu(surf, cx, cy, col):
    """Menu hamburger avec 3 lignes arrondies."""
    for i, dy in enumerate((-5, 0, 5)):
        y = cy + dy
        _line(surf, (cx - 10, y), (cx + 10, y), col, 2 + (i == 1))


def _generic(surf, cx, cy, col):
    """Icône générique : rectangle arrondi avec un point."""
    _rect(surf, pygame.Rect(cx - 10, cy - 10, 20, 20), col, 2, radius=3)
    _disk(surf, (cx, cy), 3, col)


# ---------------------------------------------------------------------------
# ACCÈS RAPIDES / QUICK APPS (anciennement rail latéral)
# ---------------------------------------------------------------------------
def _market(surf, cx, cy, col):
    """Marché : graphique linéaire avec axes et flèche haussière."""
    # axes
    _line(surf, (cx - 12, cy + 10), (cx - 12, cy - 12), col, 2)
    _line(surf, (cx - 12, cy + 10), (cx + 12, cy + 10), col, 2)
    # courbe
    pts = [(cx - 10, cy + 6), (cx - 5, cy + 2), (cx, cy + 5),
           (cx + 5, cy - 3), (cx + 10, cy - 7)]
    pygame.draw.lines(surf, col, False, pts, 2)
    # flèche
    _poly(surf, [(cx + 10, cy - 10), (cx + 13, cy - 5), (cx + 7, cy - 5)], col, 0)


def _book(surf, cx, cy, col):
    """Portefeuille : porte-documents / classeur."""
    r = pygame.Rect(cx - 11, cy - 12, 22, 24)
    _rect(surf, r, col, 2, radius=2)
    # reliure / fermoir
    _rect(surf, pygame.Rect(r.x + 4, r.y + 4, 5, r.h - 8), col, 2, radius=1)
    # ligne de texte visible
    _line(surf, (r.x + 12, r.y + 7), (r.right - 4, r.y + 7), col, 1)
    _line(surf, (r.x + 12, r.y + 12), (r.right - 4, r.y + 12), col, 1)


def _alert(surf, cx, cy, col):
    """Alerte : triangle avec point d'exclamation."""
    pts = [(cx, cy - 12), (cx + 12, cy + 10), (cx - 12, cy + 10)]
    _poly(surf, pts, col, 2)
    # point d'exclamation
    _rect(surf, pygame.Rect(cx - 1, cy - 5, 2, 7), col, 0, radius=1)
    _disk(surf, (cx, cy + 6), 2, col)


def _inbox(surf, cx, cy, col):
    """Inbox : enveloppe avec rabat."""
    r = pygame.Rect(cx - 13, cy - 8, 26, 17)
    _rect(surf, r, col, 2, radius=2)
    # rabat en V
    pygame.draw.lines(surf, col, False,
                      [(r.x, r.y), (r.centerx, r.centery + 3), (r.right, r.y)], 2)
    # petite lettre qui dépasse
    _rect(surf, pygame.Rect(cx - 6, cy - 11, 12, 8), col, 2, radius=1)


def _news(surf, cx, cy, col):
    """Journal : page pliée avec titre + image + colonnes."""
    r = pygame.Rect(cx - 11, cy - 12, 22, 24)
    _rect(surf, r, col, 2, radius=1)
    # titre
    _line(surf, (r.x + 4, r.y + 5), (r.right - 4, r.y + 5), col, 2)
    # image
    _rect(surf, pygame.Rect(r.x + 4, r.y + 9, 7, 6), col, 2, radius=1)
    # colonnes de texte
    _line(surf, (r.x + 13, r.y + 9), (r.right - 4, r.y + 9), col, 1)
    _line(surf, (r.x + 13, r.y + 13), (r.right - 4, r.y + 13), col, 1)
    _line(surf, (r.x + 13, r.y + 17), (r.right - 4, r.y + 17), col, 1)


def _mission(surf, cx, cy, col):
    """Mission : cible avec drapeau/check au centre."""
    # cible concentrique
    for r in (11, 7, 3):
        _circle(surf, (cx, cy), r, col, 2)
    # croix de visée
    _line(surf, (cx - 13, cy), (cx - 4, cy), col, 1)
    _line(surf, (cx + 4, cy), (cx + 13, cy), col, 1)
    _line(surf, (cx, cy - 13), (cx, cy - 4), col, 1)
    _line(surf, (cx, cy + 4), (cx, cy + 13), col, 1)


def _deals(surf, cx, cy, col):
    """Deals : contrat avec tampon et ruban."""
    # contrat
    r = pygame.Rect(cx - 10, cy - 12, 20, 24)
    _rect(surf, r, col, 2, radius=1)
    _line(surf, (r.x + 4, r.y + 5), (r.right - 4, r.y + 5), col, 1)
    _line(surf, (r.x + 4, r.y + 9), (r.right - 4, r.y + 9), col, 1)
    _line(surf, (r.x + 4, r.y + 13), (r.right - 4, r.y + 13), col, 1)
    # tampon rond
    _circle(surf, (cx + 5, cy + 6), 5, col, 2)


def _decide(surf, cx, cy, col):
    """Décide : balance de justice (dilemme à choix)."""
    # piliers
    _line(surf, (cx, cy - 12), (cx, cy + 10), col, 2)
    _line(surf, (cx - 8, cy + 10), (cx + 8, cy + 10), col, 2)
    # barre horizontale
    _line(surf, (cx - 12, cy - 6), (cx + 12, cy - 6), col, 2)
    # deux plateaux en V inversé
    pygame.draw.lines(surf, col, False,
                      [(cx - 12, cy - 6), (cx - 10, cy), (cx - 14, cy)], 2)
    pygame.draw.lines(surf, col, False,
                      [(cx + 12, cy - 6), (cx + 10, cy), (cx + 14, cy)], 2)


def _examcert(surf, cx, cy, col):
    """Exam/Certification : diplôme roulé avec ruban."""
    # diplôme
    r = pygame.Rect(cx - 10, cy - 12, 20, 24)
    _rect(surf, r, col, 2, radius=1)
    # bordures enroulées
    _circle(surf, (r.x, cy), 3, col, 2)
    _circle(surf, (r.right - 1, cy), 3, col, 2)
    # texte + sceau
    _line(surf, (r.x + 5, r.y + 6), (r.right - 5, r.y + 6), col, 1)
    _line(surf, (r.x + 5, r.y + 10), (r.right - 5, r.y + 10), col, 1)
    _circle(surf, (cx + 4, cy + 6), 4, col, 2)


def _wall(surf, cx, cy, col):
    """Wall : mur de briques en 3 rangées."""
    r = pygame.Rect(cx - 12, cy - 11, 24, 22)
    _rect(surf, r, col, 2, radius=2)
    # joints horizontaux
    for dy in (r.h // 3, 2 * r.h // 3):
        _line(surf, (r.x, r.y + dy), (r.right, r.y + dy), col, 1)
    # joints verticaux décalés
    for dy, dxs in ((0, [r.w // 3]), (r.h // 3, [r.w // 2]),
                    (2 * r.h // 3, [r.w // 3, 2 * r.w // 3])):
        for dx in dxs:
            y1 = r.y + dy
            y2 = r.y + dy + r.h // 3
            _line(surf, (r.x + dx, y1), (r.x + dx, y2), col, 1)


def _shop(surf, cx, cy, col):
    """Shop : panier d'achat."""
    # panier
    _rect(surf, pygame.Rect(cx - 9, cy - 3, 18, 12), col, 2, radius=2)
    # mailles
    for gx in (cx - 5, cx, cx + 5):
        _line(surf, (gx, cy - 3), (gx, cy + 9), col, 1)
    for gy in (cy + 1, cy + 6):
        _line(surf, (cx - 9, gy), (cx + 9, gy), col, 1)
    # poignée
    pygame.draw.arc(surf, col, pygame.Rect(cx - 6, cy - 12, 12, 10), 0, 3.14, 2)


def _explorer(surf, cx, cy, col):
    """Explorateur : globe terrestre avec loupe."""
    # globe
    _circle(surf, (cx - 2, cy - 2), 10, col, 2)
    # méridiens / parallèles
    _line(surf, (cx - 2, cy - 12), (cx - 2, cy + 8), col, 1)
    pygame.draw.arc(surf, col, pygame.Rect(cx - 11, cy - 7, 18, 10), 0, 3.14, 1)
    pygame.draw.arc(surf, col, pygame.Rect(cx - 11, cy - 2, 18, 10), 3.14, 0, 1)
    # loupe
    _circle(surf, (cx + 7, cy + 7), 5, col, 2)
    _line(surf, (cx + 10, cy + 10), (cx + 14, cy + 14), col, 3)


def _graph(surf, cx, cy, col):
    """Graphes : graphique à barres avec axes."""
    _line(surf, (cx - 12, cy + 10), (cx - 12, cy - 12), col, 2)
    _line(surf, (cx - 12, cy + 10), (cx + 12, cy + 10), col, 2)
    # barres de hauteurs variées
    for dx, h in ((-7, 8), (-2, 14), (3, 10), (8, 17)):
        _rect(surf, pygame.Rect(cx + dx, cy + 10 - h, 4, h), col, 0, radius=1)


def _save(surf, cx, cy, col):
    """Sauvegarde : disquette classique."""
    r = pygame.Rect(cx - 11, cy - 12, 22, 24)
    _rect(surf, r, col, 2, radius=2)
    # fenêtre métallique haut
    _rect(surf, pygame.Rect(r.x + 3, r.y + 2, 16, 7), col, 2, radius=1)
    # fente
    _rect(surf, pygame.Rect(r.x + 6, r.y + 12, 10, 4), col, 2, radius=1)
    # étiquette
    _rect(surf, pygame.Rect(r.x + 4, r.y + 19, 14, 4), col, 0, radius=1)


def _help(surf, cx, cy, col):
    """Aide : point d'interrogation dans un cercle épais."""
    _circle(surf, (cx, cy), 12, col, 2)
    # point d'interrogation stylisé
    pygame.draw.arc(surf, col, pygame.Rect(cx - 4, cy - 9, 8, 8), 3.3, 6.2, 2)
    _line(surf, (cx, cy - 1), (cx, cy + 2), col, 2)
    _disk(surf, (cx, cy + 6), 2, col)


def _calc(surf, cx, cy, col):
    """Calculatrice : écran + touches."""
    r = pygame.Rect(cx - 10, cy - 13, 20, 26)
    _rect(surf, r, col, 2, radius=2)
    # écran
    _rect(surf, pygame.Rect(r.x + 3, r.y + 3, r.w - 6, 6), col, 2, radius=1)
    # touches
    for gy in (r.y + 12, r.y + 17, r.y + 22):
        for gx in (r.x + 5, r.x + 11):
            _rect(surf, pygame.Rect(gx - 3, gy - 3, 5, 5), col, 0, radius=1)


def _star(surf, cx, cy, col):
    """Favori : étoile 5 branches pleine et régulière."""
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rad = 11 if k % 2 == 0 else 5
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    _poly(surf, pts, col, 0)


def _bell(surf, cx, cy, col):
    """Notifications : cloche classique."""
    # corps de cloche
    pygame.draw.arc(surf, col, pygame.Rect(cx - 10, cy - 12, 20, 22),
                    3.14, 0, 2)
    # base
    _line(surf, (cx - 10, cy + 4), (cx + 10, cy + 4), col, 2)
    # battant
    _disk(surf, (cx, cy + 8), 3, col)
    # anse
    pygame.draw.arc(surf, col, pygame.Rect(cx - 5, cy - 16, 10, 10),
                    3.14, 0, 2)


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


def draw(surf, center, kind, color):
    """Dessine l'icône `kind` centrée sur `center` (repère absolu de `surf`).

    Si `kind` est inconnu, dessine une icône générique sans planter.
    """
    _ICONS.get(kind, _generic)(surf, center[0], center[1], color)
