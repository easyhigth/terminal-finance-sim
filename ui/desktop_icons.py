"""
desktop_icons.py — Icônes vectorielles du bureau et de l'interface.

Les emoji Unicode ne s'affichent pas de façon fiable selon les polices système.
On dessine donc chaque icône en VECTORIEL avec pygame.draw.

Style V5 « tuiles néon lissées » :
- Rendu SURÉCHANTILLONNÉ (dessin en 4x puis `smoothscale`) : tous les traits,
  cercles et polygones sont anti-aliasés — fini les pictos en escalier.
- Tuile avec ombre portée douce, fond en dégradé vertical (plus clair en haut),
  halo lumineux derrière le pictogramme et liseré néon.
- Pictogramme en DEUX TONS : trait principal presque blanc (`ink`) + aplat
  secondaire dans une teinte intermédiaire (`soft`) pour la profondeur.
- Chaque icône a un dessin DISTINCT et évocateur de ce qu'elle ouvre
  (bougies pour Trading, balance pour Décide, médaille pour Certif...).
- Rendu mis en CACHE par (type, taille) : le coût du suréchantillonnage n'est
  payé qu'une fois, ensuite c'est un simple blit.
"""
import math

import pygame

from ui import style

# facteur de suréchantillonnage : on dessine en grand, on réduit en lissant
_SS = 4
# espace « design » : la tuile fait 30 unités de côté, centrée sur (0, 0)
_TILE = 30.0

_WHITE = (255, 255, 255)


# ---------------------------------------------------------------------------
# Palettes : (fond sombre, couleur néon du pictogramme)
# ---------------------------------------------------------------------------
PALETTES = {
    "research":  ((15, 23, 42),    (56, 189, 248)),   # bleu nuit / cyan
    "trading":   ((20, 83, 45),    (74, 222, 128)),   # vert foncé / vert néon
    "sheet":     ((6, 78, 59),     (110, 231, 183)),  # émeraude noir / menthe
    "terminal":  ((17, 24, 39),    (148, 163, 184)),  # nuit / gris clair
    "ma":        ((40, 15, 60),    (232, 121, 249)),  # violet noir / magenta
    "risk":      ((60, 20, 10),    (251, 146, 60)),   # brun noir / orange
    "quant":     ((15, 23, 60),    (96, 165, 250)),   # bleu nuit / bleu clair
    "portfolio": ((10, 25, 70),    (99, 102, 241)),   # indigo noir / indigo
    "advisory":  ((50, 40, 5),     (250, 204, 21)),   # jaune sale / jaune vif
    "apps":      ((30, 41, 59),    (203, 213, 225)),  # ardoise / blanc cassé
    "menu":      ((30, 41, 59),    (203, 213, 225)),
    "market":    ((6, 78, 59),     (45, 212, 191)),   # émeraude noir / teal
    "book":      ((69, 26, 3),     (251, 191, 36)),   # brun foncé / ambre
    "alert":     ((69, 10, 10),    (248, 113, 113)),  # rouge noir / rouge néon
    "inbox":     ((15, 23, 60),    (96, 165, 250)),   # bleu profond / bleu
    "news":      ((30, 41, 59),    (148, 163, 184)),  # ardoise / gris clair
    "mission":   ((60, 20, 10),    (251, 146, 60)),   # orange noir / orange
    "deals":     ((40, 15, 60),    (216, 180, 254)),  # violet noir / violet
    "decide":    ((22, 22, 64),    (165, 180, 252)),  # indigo nuit / pervenche
    "examcert":  ((50, 40, 5),     (250, 204, 21)),
    "wall":      ((15, 35, 60),    (125, 211, 252)),  # bleu nuit / ciel
    "shop":      ((45, 10, 35),    (244, 114, 182)),  # prune noir / rose
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
# Stylo en espace « design » (tuile 30×30 centrée sur l'origine)
# ---------------------------------------------------------------------------
class _Pen:
    """Convertit des coordonnées design (unités de tuile, origine au centre)
    vers la surface haute résolution, avec les couleurs du thème de l'icône."""

    def __init__(self, surf, cx, cy, u, bg, neon):
        self.s = surf
        self.cx, self.cy, self.u = cx, cy, u
        self.bg = bg
        self.neon = neon
        # trait principal : néon tiré vers le blanc (lisible sur le glow)
        self.ink = style._lerp_color(neon, _WHITE, 0.22)
        # aplat secondaire : teinte intermédiaire fond/néon (profondeur)
        self.soft = style._lerp_color(neon, bg, 0.58)

    # conversions ----------------------------------------------------------
    def P(self, x, y):
        return (round(self.cx + x * self.u), round(self.cy + y * self.u))

    def W(self, w):
        return max(1, round(w * self.u))

    # primitives ------------------------------------------------------------
    def line(self, a, b, col=None, w=2.0):
        pygame.draw.line(self.s, col or self.ink, self.P(*a), self.P(*b), self.W(w))

    def lines(self, pts, col=None, w=2.0, closed=False):
        pygame.draw.lines(self.s, col or self.ink, closed,
                          [self.P(*p) for p in pts], self.W(w))

    def poly(self, pts, col=None, w=0):
        pygame.draw.polygon(self.s, col or self.ink, [self.P(*p) for p in pts],
                            0 if w == 0 else self.W(w))

    def rect(self, x, y, wid, hei, col=None, w=0, radius=1.5):
        r = pygame.Rect(*self.P(x, y), max(1, round(wid * self.u)),
                        max(1, round(hei * self.u)))
        pygame.draw.rect(self.s, col or self.ink, r,
                         0 if w == 0 else self.W(w),
                         border_radius=max(0, round(radius * self.u)))

    def circle(self, c, r, col=None, w=2.0):
        pygame.draw.circle(self.s, col or self.ink, self.P(*c),
                           max(1, round(r * self.u)),
                           0 if w == 0 else self.W(w))

    def disk(self, c, r, col=None):
        self.circle(c, r, col, w=0)

    def arc(self, c, r, a0, a1, col=None, w=2.0, rx=None, ry=None):
        """Arc de cercle/ellipse en POLYLIGNE échantillonnée (le arc() natif de
        pygame laisse des trous radiaux dès que width > 1). Angles en radians,
        0 = à droite, sens trigonométrique (y écran inversé)."""
        rx = r if rx is None else rx
        ry = r if ry is None else ry
        n = max(8, int(abs(a1 - a0) * 10))
        pts = []
        for i in range(n + 1):
            t = a0 + (a1 - a0) * i / n
            pts.append((c[0] + rx * math.cos(t), c[1] - ry * math.sin(t)))
        self.lines(pts, col, w)

    def arc_points(self, c, r, a0, a1, n=16):
        """Points d'un arc, en coordonnées design (pour composer des polygones)."""
        return [(c[0] + r * math.cos(a0 + (a1 - a0) * i / n),
                 c[1] - r * math.sin(a0 + (a1 - a0) * i / n))
                for i in range(n + 1)]


# ---------------------------------------------------------------------------
# Tuile de fond : ombre, dégradé, glow, liseré
# ---------------------------------------------------------------------------
def _rounded_mask(w, h, radius):
    m = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(m, (255, 255, 255, 255), m.get_rect(), 0, border_radius=radius)
    return m


def _draw_tile(surf, rect, u, bg, neon):
    rad = max(2, round(7 * u))
    # ombre portée douce (le smoothscale final la floute)
    shadow = rect.move(0, round(1.2 * u)).inflate(round(1.2 * u), round(1.2 * u))
    pygame.draw.rect(surf, (0, 0, 0, 90), shadow, 0, border_radius=rad + round(u))
    # fond : dégradé vertical (astuce 1×2 pixels étirés en lissant)
    top = style._lerp_color(bg, _WHITE, 0.20)
    bot = style._lerp_color(bg, (0, 0, 0), 0.32)
    g = pygame.Surface((1, 2))
    g.set_at((0, 0), top)
    g.set_at((0, 1), bot)
    grad = pygame.transform.smoothscale(g, rect.size).convert_alpha()
    # halo lumineux derrière le pictogramme (légèrement au-dessus du centre)
    gcx, gcy = rect.w // 2, rect.h // 2 - round(1.5 * u)
    for r, a in ((round(12 * u), 26), (round(9 * u), 36), (round(6 * u), 46)):
        glow = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.circle(glow, (*neon, a), (gcx, gcy), r)
        grad.blit(glow, (0, 0))
    # découpe aux coins arrondis
    grad.blit(_rounded_mask(rect.w, rect.h, rad), (0, 0),
              special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(grad, rect.topleft)
    # reflet en haut de tuile (fine ligne claire sous le bord)
    hl = pygame.Rect(rect.x + rad, rect.y + max(1, round(0.8 * u)),
                     rect.w - 2 * rad, max(1, round(0.7 * u)))
    pygame.draw.rect(surf, (*_WHITE, 46), hl, border_radius=hl.h)
    # liseré néon
    pygame.draw.rect(surf, neon, rect, max(1, round(1.5 * u)), border_radius=rad)


# ---------------------------------------------------------------------------
# Pictogrammes (espace design : tuile de -15 à +15, zone utile ~±11)
# ---------------------------------------------------------------------------
def _research(p):
    """Loupe (rechercher une société)."""
    p.disk((-2, -2), 7, p.soft)
    p.circle((-2, -2), 7, w=2.2)
    p.arc((-2, -2), 4.4, math.radians(100), math.radians(170),
          col=style._lerp_color(p.ink, _WHITE, 0.5), w=1.4)
    p.line((3.1, 3.1), (9.5, 9.5), w=3.2)


def _trading(p):
    """Trois chandeliers ascendants (acheter/vendre)."""
    for x, top, h in ((-7.5, 1, 7), (0, -3, 8), (7.5, -8, 8)):
        p.line((x, top - 2.5), (x, top + h + 2.5), w=1.4)
        p.rect(x - 2, top, 4, h, radius=1)


def _sheet(p):
    """Feuille de calcul : en-tête + grille."""
    p.rect(-8.5, -10, 17, 20, p.soft, radius=2)
    p.rect(-8.5, -10, 17, 5, radius=2)
    p.line((-8.5, 0), (8.5, 0), p.bg, 1.2)
    p.line((-8.5, 5), (8.5, 5), p.bg, 1.2)
    p.line((-1.5, -5), (-1.5, 10), p.bg, 1.2)
    p.rect(-8.5, -10, 17, 20, w=1.8, radius=2)


def _terminal(p):
    """Invite de commande : chevron + curseur."""
    p.lines([(-8, -4.5), (-2.5, 0), (-8, 4.5)], w=2.6)
    p.rect(1, 3, 7, 2.4, radius=1)


def _ma(p):
    """Deux immeubles + flèche d'absorption (fusions-acquisitions)."""
    p.rect(-11, -3, 7, 13, p.soft, radius=1)
    p.rect(-11, -3, 7, 13, w=1.6, radius=1)
    p.rect(4, -8, 8, 18, p.soft, radius=1)
    p.rect(4, -8, 8, 18, w=1.6, radius=1)
    for wx, wy in ((-9.3, -0.5), (-6.6, -0.5), (-9.3, 3), (-6.6, 3)):
        p.disk((wx, wy), 0.9)
    for wx in (6.2, 9.2):
        for wy in (-5.5, -1.5, 2.5):
            p.disk((wx, wy), 0.9)
    p.line((-3.5, -6), (1, -6), w=2)
    p.poly([(0.6, -8.4), (4.2, -6), (0.6, -3.6)])


def _risk(p):
    """Bouclier + électrocardiogramme (gestion des risques)."""
    shield = [(0, -10.5), (9, -7), (9, -1), (0, 10.5), (-9, -1), (-9, -7)]
    p.poly(shield, p.soft)
    p.poly(shield, w=2)
    p.lines([(-5.5, -1), (-2, -1), (-0.5, -4.5), (1.5, 2), (3, -1), (5.5, -1)],
            w=1.8)


def _quant(p):
    """Sigma (quant/statistiques)."""
    p.lines([(6, -8.5), (-6.5, -8.5), (0.5, 0), (-6.5, 8.5), (6, 8.5)], w=2.4)
    p.line((6, -8.5), (6, -6), w=2.2)
    p.line((6, 8.5), (6, 6), w=2.2)


def _portfolio(p):
    """Camembert à part détachée (allocation de portefeuille)."""
    p.disk((0, 0), 9.2, p.soft)
    p.circle((0, 0), 9.2, w=1.8)
    # part « sortie » vers le haut-droit (de -80° à -10°)
    off = (0.9, -1.1)
    wedge = [off] + [(x + off[0], y + off[1])
                     for (x, y) in p.arc_points(( 0, 0), 9.2,
                                                math.radians(10),
                                                math.radians(80))]
    p.poly(wedge)


def _advisory(p):
    """Mallette (conseil/advisory)."""
    p.rect(-3.5, -9.5, 7, 4.5, w=1.8, radius=2)
    p.rect(-10, -5, 20, 14, p.soft, radius=2.5)
    p.rect(-10, -5, 20, 14, w=1.8, radius=2.5)
    p.line((-10, 1), (10, 1), w=1.2)
    p.rect(-1.8, -0.8, 3.6, 3.6, radius=1)


def _apps_grid(p):
    """Grille 3×3 (toutes les applications)."""
    for dx in (-6, 0, 6):
        for dy in (-6, 0, 6):
            p.rect(dx - 2, dy - 2, 4, 4, radius=1.2)


def _menu(p):
    """Menu « hamburger »."""
    for y in (-6.5, -1.3, 3.9):
        p.rect(-8, y, 16, 2.6, radius=1.3)


def _generic(p):
    p.circle((0, 0), 8, w=2)
    p.disk((0, 0), 2.4)


def _market(p):
    """Axes + courbe montante avec aire (hub marché)."""
    p.line((-9.5, -8.5), (-9.5, 8), p.soft, 1.6)
    p.line((-9.5, 8), (9.5, 8), p.soft, 1.6)
    curve = [(-8, 5), (-3, 1), (1, 3), (8, -5)]
    p.poly([(-8, 8)] + curve + [(8, 8)], p.soft)
    p.lines(curve, w=2.2)
    p.poly([(9.5, -6.9), (8.8, -3.2), (6.0, -5.8)])


def _book(p):
    """Portefeuille (l'objet !) avec poche à cartes."""
    p.rect(-9.5, -6.5, 19, 13.5, p.soft, radius=3)
    p.rect(-9.5, -6.5, 19, 13.5, w=1.8, radius=3)
    p.rect(2.5, -1.5, 7, 5.5, radius=1.5)
    p.disk((6, 1.2), 1.0, p.bg)


def _alert(p):
    """Triangle d'avertissement + point d'exclamation."""
    tri = [(0, -9.5), (10, 8), (-10, 8)]
    p.poly(tri, p.soft)
    p.poly(tri, w=2)
    p.rect(-1.2, -4, 2.4, 6.5, radius=1.2)
    p.disk((0, 5.4), 1.6)


def _inbox(p):
    """Enveloppe (boîte de réception)."""
    p.rect(-9.5, -6.5, 19, 13, p.soft, radius=2)
    p.rect(-9.5, -6.5, 19, 13, w=1.8, radius=2)
    p.lines([(-9.5, -6.5), (0, 1.5), (9.5, -6.5)], w=1.8)


def _news(p):
    """Une du journal : manchette, photo, colonnes."""
    p.rect(-8, -10, 16, 20, w=1.8, radius=2)
    p.rect(-6, -8, 12, 3, radius=1)
    p.rect(-6, -3, 5.5, 5.5, p.soft, radius=1)
    for y in (-2, 0.5, 3):
        p.line((1.5, y), (6, y), w=1.2)
    p.line((-6, 5.8), (6, 5.8), w=1.2)
    p.line((-6, 7.8), (3, 7.8), w=1.2)


def _mission(p):
    """Cible (objectifs de mission)."""
    p.disk((0, 0), 8.8, p.soft)
    p.circle((0, 0), 8.8, w=2)
    p.circle((0, 0), 5.2, w=1.7)
    p.disk((0, 0), 2.2)


def _deals(p):
    """Deux flèches qui s'échangent (négocier un deal)."""
    p.line((-8, -4), (5.6, -4), w=2.4)
    p.poly([(5.2, -7), (10, -4), (5.2, -1)])
    p.line((8, 4), (-5.6, 4), w=2.4)
    p.poly([(-5.2, 1), (-10, 4), (-5.2, 7)])


def _decide(p):
    """Balance à plateaux (dilemmes/décisions)."""
    p.line((0, -9), (0, 6.5), w=2)
    p.disk((0, -9.3), 1.5)
    p.line((-8, -6.8), (8, -6.8), w=2)
    for sx in (-1, 1):
        top = (8 * sx, -6.8)
        p.line(top, (5.4 * sx, -1.6), w=1.2)
        p.line(top, (10.6 * sx, -1.6), w=1.2)
        p.arc((8 * sx, -1.8), 2.8, math.pi, 2 * math.pi, w=1.7)
    p.poly([(-4.5, 9), (4.5, 9), (2.4, 6.5), (-2.4, 6.5)])


def _examcert(p):
    """Médaille à rubans + coche (examens/certifications)."""
    p.poly([(-3.6, 0.5), (-0.8, 1.5), (-3.2, 9.5), (-6.2, 9.5)], p.soft)
    p.poly([(3.6, 0.5), (0.8, 1.5), (3.2, 9.5), (6.2, 9.5)], p.soft)
    p.disk((0, -3.2), 5.6, p.soft)
    p.circle((0, -3.2), 5.6, w=2)
    p.lines([(-2.4, -3.2), (-0.7, -1.3), (2.6, -5.4)], w=1.7)


def _wall(p):
    """Fil de posts avec avatars (le Mur)."""
    p.rect(-9, -9.5, 18, 19, w=1.8, radius=2)
    for base in (-5.5, 2.5):
        p.disk((-5.5, base), 2, p.soft)
        p.line((-2, base - 1.2), (6.5, base - 1.2), w=1.2)
        p.line((-2, base + 1.4), (3.5, base + 1.4), w=1.2)
    p.line((-9, -1.4), (9, -1.4), w=1)


def _shop(p):
    """Caddie (boutique)."""
    p.lines([(-11, -8), (-7.6, -8), (-6, -3.2)], w=1.8)
    cart = [(-6.5, -3.2), (9.5, -3.2), (7.3, 4.5), (-4.7, 4.5)]
    p.poly(cart, p.soft)
    p.poly(cart, w=1.8)
    p.disk((-2.8, 8.2), 1.9)
    p.disk((5, 8.2), 1.9)


def _explorer(p):
    """Boussole (explorer les sociétés)."""
    p.disk((0, 0), 9, p.soft)
    p.circle((0, 0), 9, w=2)
    for ang in range(0, 360, 90):
        a = math.radians(ang)
        p.line((7 * math.cos(a), 7 * math.sin(a)),
               (8.6 * math.cos(a), 8.6 * math.sin(a)), w=1.2)
    p.poly([(2.1, 2.6), (-4.9, 4.9), (-2.6, -2.1)],
           style._lerp_color(p.ink, p.bg, 0.45))
    p.poly([(-2.6, -2.1), (4.9, -4.9), (2.1, 2.6)])
    p.disk((0, 0), 1.1, p.bg)


def _graph(p):
    """Histogramme (atelier de graphes)."""
    p.line((-10, 8.2), (10, 8.2), p.soft, 1.4)
    for x, h in ((-7.5, 6), (-2.5, 10), (2.5, 7.5), (7.5, 13)):
        p.rect(x - 1.8, 7 - h, 3.6, h, radius=1.2)


def _save(p):
    """Disquette : volet métallique en haut, étiquette en bas."""
    body = [(-9, -9), (5.5, -9), (9, -5.5), (9, 9), (-9, 9)]
    p.poly(body, p.soft)
    p.poly(body, w=1.8)
    p.rect(-4, -9, 8, 6, radius=1)
    p.rect(-2.6, -8, 2, 3.6, p.soft, radius=0.8)
    label = style._lerp_color(p.neon, _WHITE, 0.5)
    p.rect(-6, 0.5, 12, 8.5, label, radius=1)
    p.line((-4, 3.4), (4, 3.4), p.bg, 1.1)
    p.line((-4, 5.8), (2, 5.8), p.bg, 1.1)


def _help(p):
    """Point d'interrogation."""
    p.arc((0, -4.4), 4.6, math.radians(-60), math.radians(210), w=2.3)
    p.lines([(2.3, -0.4), (0.2, 1.7), (0.2, 3.8)], w=2.3)
    p.disk((0.2, 8), 1.9)


def _calc(p):
    """Calculatrice : écran + clavier."""
    p.rect(-7, -10, 14, 20, p.soft, radius=2.5)
    p.rect(-7, -10, 14, 20, w=1.8, radius=2.5)
    p.rect(-5, -8, 10, 4.5, p.bg, radius=1)
    p.line((0.8, -5.6), (3.6, -5.6), w=1.3)
    for row, y in enumerate((-1, 3, 7)):
        for x in (-3.6, 0, 3.6):
            p.rect(x - 1.3, y - 1.3, 2.6, 2.6, radius=0.9)


def _star(p):
    """Étoile (watchlist/favoris)."""
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rad = 9.5 if k % 2 == 0 else 4
        pts.append((rad * math.cos(ang), rad * math.sin(ang)))
    p.poly(pts, p.soft)
    p.poly(pts, w=1.6)


def _bell(p):
    """Cloche (alertes/notifications)."""
    dome = p.arc_points((0, -1.8), 5.8, 0, math.pi)
    body = [(6.9, 3.6), (8.2, 5.4), (-8.2, 5.4), (-6.9, 3.6)]
    shape = list(reversed(dome)) + body
    p.poly(shape, p.soft)
    p.lines(shape, w=1.8, closed=True)
    p.circle((0, -8.4), 1.5, w=1.5)
    p.disk((0, 8), 1.8)


# ---------------------------------------------------------------------------
# Registre, cache et API
# ---------------------------------------------------------------------------
_PICTOS = {
    "research": _research, "trading": _trading, "sheet": _sheet,
    "terminal": _terminal, "ma": _ma, "risk": _risk, "quant": _quant,
    "portfolio": _portfolio, "advisory": _advisory, "apps": _apps_grid,
    "menu": _menu, "market": _market, "book": _book, "alert": _alert,
    "inbox": _inbox, "news": _news, "mission": _mission, "deals": _deals,
    "decide": _decide, "examcert": _examcert, "wall": _wall, "shop": _shop,
    "explorer": _explorer, "graph": _graph, "save": _save, "help": _help,
    "calc": _calc, "star": _star, "bell": _bell,
}
# alias de compat (l'ancien registre s'appelait _ICONS)
_ICONS = _PICTOS

_CACHE = {}


def _render(kind, size):
    """Rend l'icône en HAUTE RÉSOLUTION (×_SS) puis réduit en lissant.
    La surface rendue est un peu plus grande que la tuile (marge `pad`)
    pour laisser respirer l'ombre portée."""
    pad = max(2, round(size * 0.14))
    full = (size + 2 * pad) * _SS
    big = pygame.Surface((full, full), pygame.SRCALPHA)
    u = size * _SS / _TILE
    cx = cy = full / 2.0
    bg, neon = PALETTES.get(kind, C_GENERIC)
    side = round(_TILE * u)
    tile = pygame.Rect(0, 0, side, side)
    tile.center = (round(cx), round(cy))
    _draw_tile(big, tile, u, bg, neon)
    _PICTOS.get(kind, _generic)(_Pen(big, cx, cy, u, bg, neon))
    return pygame.transform.smoothscale(big, (size + 2 * pad, size + 2 * pad))


def draw(surf, center, kind, color=None, size=30, alpha=255):
    """Dessine l'icône `kind` centrée sur `center`.

    `size` : côté de la tuile en px (le rendu est mis en cache par taille).
    `alpha` : opacité globale (ex. icône « fantôme » pendant un glisser).
    L'argument `color` est ignoré (compatibilité avec l'ancienne API).
    """
    key = (kind, int(size))
    ic = _CACHE.get(key)
    if ic is None:
        ic = _render(kind, int(size))
        _CACHE[key] = ic
    if alpha < 255:
        ic = ic.copy()
        ic.set_alpha(alpha)
    surf.blit(ic, ic.get_rect(center=(round(center[0]), round(center[1]))))
