"""
chart_widgets.py — Widgets de graphes et séries temporelles (extraits de widgets.py).

Fonctions de tracé de courbes, chandeliers, axes, curseurs, légendes, etc.
Tout est dessiné à la main avec pygame.draw pour garder l'esthétique Bloomberg.
"""
import pygame

from core import config
from core.i18n import get_lang
from ui import fonts


# ---------------------------------------------------------------------------
# SPARKLINE — mini graphique de série temporelle
# ---------------------------------------------------------------------------
class Sparkline:
    """
    Mini-courbe d'historique. On pousse des valeurs au fil du temps via push()
    et on dessine une polyligne lissée dans un rectangle donné.
    La couleur s'adapte à la tendance (hausse/baisse) si aucune n'est imposée.
    """

    def __init__(self, maxlen=64):
        self.maxlen = maxlen
        self.values = []

    def push(self, v):
        self.values.append(float(v))
        if len(self.values) > self.maxlen:
            self.values.pop(0)

    def draw(self, surf, rect, color=None, baseline=True, mouse_pos=None, y_fmt=None,
             show_pct=False, show_extrema=True):
        draw_series(surf, rect, self.values, color, baseline, mouse_pos=mouse_pos, y_fmt=y_fmt,
                   show_pct=show_pct, show_extrema=show_extrema)


# ---------------------------------------------------------------------------
# STYLE « APPLI DE TRADING » (remplissage en dégradé + ligne de cours actuel)
# ---------------------------------------------------------------------------
_GRADIENT_MASK_CACHE = {}   # hauteur (px) -> Surface 1×h SRCALPHA (dégradé vertical)



def _L(fr, en):
    return en if get_lang() == "en" else fr

def _gradient_mask(height):
    """Masque de dégradé vertical 1px de large (plein en haut, nul en bas),
    mis en cache par hauteur — appelé à CHAQUE frame pour chaque graphe visible
    (sparklines comprises), le recalculer pixel par pixel à chaque appel serait
    sensiblement plus lent ; le nombre de hauteurs distinctes utilisées dans le
    jeu est petit et borné (tailles de rects fixes par écran), donc pas de
    risque de croissance illimitée du cache."""
    mask = _GRADIENT_MASK_CACHE.get(height)
    if mask is None:
        mask = pygame.Surface((1, height), pygame.SRCALPHA)
        for y in range(height):
            a = max(0, 255 - int(255 * y / max(1, height - 1)))
            mask.set_at((0, y), (255, 255, 255, a))
        _GRADIENT_MASK_CACHE[height] = mask
    return mask


def fill_gradient_area(surf, rect, pts, color, top_alpha=55):
    """Remplissage en dégradé vertical sous une polyligne de prix, façon
    appli de trading (eToro/Trading212) : plein près de la courbe,
    transparent vers le bas du graphe — remplace l'ancien style « ligne nue »
    pour donner un rendu de marché vivant plutôt qu'un tracé technique plat.
    `top_alpha` réglable (défaut 55) pour garder le tracé principal lisible
    plutôt qu'noie sous un bloc de couleur opaque.
    `pts` : liste de (x, y) DÉJÀ projetés en pixels, mêmes coordonnées que la
    ligne dessinée par-dessus (donc appelé AVANT `pygame.draw.aalines`)."""
    rect = pygame.Rect(rect)
    if len(pts) < 2 or rect.w <= 0 or rect.h <= 0:
        return
    poly = list(pts) + [(pts[-1][0], rect.bottom), (pts[0][0], rect.bottom)]
    local_poly = [(x - rect.x, y - rect.y) for x, y in poly]
    fill_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.polygon(fill_surf, (*color[:3], top_alpha), local_poly)
    grad = pygame.transform.smoothscale(_gradient_mask(rect.h), (rect.w, rect.h))
    fill_surf.blit(grad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surf.blit(fill_surf, rect.topleft)


def draw_current_price_line(surf, rect, y, label, color, font=None):
    """Ligne horizontale de cours actuel traversant tout le graphe + pastille
    de valeur sur le bord droit — façon appli de trading (ligne fine qui
    « accroche » le dernier prix, immédiatement lisible sans survoler)."""
    y = max(rect.y, min(rect.bottom, int(y)))
    pygame.draw.line(surf, color, (rect.x, y), (rect.right, y), 1)
    font = font or fonts.tiny(bold=True)
    tw, th = font.size(label)
    pad = 4
    box = pygame.Rect(0, 0, tw + 2 * pad, th + 4)
    box.right = rect.right
    box.centery = y
    pygame.draw.rect(surf, color, box, border_radius=3)
    from ui.widgets import draw_text
    draw_text(surf, label, box.center, font, config.COL_BG, align="center")


def draw_series(surf, rect, vals, color=None, baseline=True, mouse_pos=None, y_fmt=None,
                show_pct=False, show_extrema=True, extrema_label=True, band_frac=None,
                area_fill=True, show_current_line=False, line_width=1, area_alpha=None,
                lo=None, hi=None):
    """Trace une polyligne à partir d'une liste de valeurs, dans `rect`.

    Si `mouse_pos` est fourni et survole `rect`, affiche un curseur (ligne
    pointillée verticale + point + étiquette de la valeur Y, et si `show_pct`
    la variation en % depuis le début) à l'abscisse la plus proche du curseur
    — cf. `draw_chart_crosshair`. Marque aussi les extrêmes de la série
    (cf. `draw_chart_extrema`), sauf si `show_extrema=False` (l'appelant
    annote déjà ses propres extrêmes, p. ex. record/plus bas d'une carrière).
    `extrema_label=False` garde les petits triangles d'extrêmes mais omet
    leur étiquette de valeur (l'appelant l'affiche ailleurs, hors du tracé,
    pour éviter tout chevauchement sur les graphes compacts).
    `band_frac` (fraction, p. ex. 0.0008 = 0.08%) dessine une bande
    translucide bid/ask "respirant" autour du dernier prix — purement
    visuelle (profondeur de marché simulée), sans rapport avec le prix
    d'exécution réel des ordres.
    `area_fill` (défaut True) : remplissage en dégradé sous la courbe, façon
    appli de trading (cf. `fill_gradient_area`) — désactivable pour les
    contextes très compacts où le dégradé n'apporterait rien de lisible.
    `show_current_line` : ligne + pastille de cours actuel sur le bord droit
    (cf. `draw_current_price_line`) — hors par défaut (surchargerait les
    petites vignettes type watchlist), à activer pour un graphe dédié.
    `line_width` (défaut 1) : épaisseur du trait ; pour les graphes principaux
    on passe 2–3 px afin d'obtenir une courbe bien visible façon appli mobile.
    `area_alpha` (None) : alpha au sommet du remplissage ; si None, utilise le
    nouveau défaut de `fill_gradient_area` (55), plus discret que l'ancien 90.
    `lo`/`hi` optionnels : bornes Y explicites pour aligner la courbe sur des
    axes déjà tracés avec un padding (cf. `_plot_axes` de l'atelier de graphes)."""
    rect = pygame.Rect(rect)
    if not vals or len(vals) < 2:
        return
    if lo is None or hi is None:
        lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    col = color
    if col is None:
        col = config.COL_UP if vals[-1] >= vals[0] else config.COL_DOWN
    if baseline:
        by = rect.bottom - int((vals[0] - lo) / span * rect.h)
        pygame.draw.line(surf, config.COL_GRID, (rect.x, by), (rect.right, by), 1)
    if band_frac:
        last = vals[-1]
        ask_y = rect.bottom - int((last * (1 + band_frac) - lo) / span * rect.h)
        bid_y = rect.bottom - int((last * (1 - band_frac) - lo) / span * rect.h)
        band = pygame.Surface((rect.w, max(1, bid_y - ask_y)), pygame.SRCALPHA)
        band.fill((*col[:3], 40))
        surf.blit(band, (rect.x, ask_y))
    pts = []
    n = len(vals)
    for i, v in enumerate(vals):
        x = rect.x + int(i / (n - 1) * rect.w)
        y = rect.bottom - int((v - lo) / span * rect.h)
        pts.append((x, y))
    if len(pts) >= 2:
        if area_fill:
            fill_gradient_area(surf, rect, pts, col, top_alpha=area_alpha if area_alpha is not None else 55)
        if line_width <= 1:
            pygame.draw.aalines(surf, col, False, pts)
        else:
            glow = tuple(max(0, int(c * 0.35)) for c in col[:3])
            pygame.draw.lines(surf, glow, False, pts, line_width + 2)
            pygame.draw.lines(surf, col, False, pts, line_width)
        if show_current_line:
            draw_current_price_line(surf, rect, pts[-1][1],
                                    y_fmt(vals[-1]) if y_fmt else f"{vals[-1]:,.2f}", col)
    if pts:
        pygame.draw.circle(surf, col, pts[-1], max(2, line_width))
    if show_extrema:
        draw_chart_extrema(surf, rect, vals, lo, span, y_fmt=y_fmt, color=config.COL_TEXT_DIM,
                           label=extrema_label)
    if mouse_pos is not None:
        draw_chart_crosshair(surf, rect, vals, lo, span, mouse_pos, y_fmt=y_fmt, color=col,
                             show_pct=show_pct)


def _aggregate_ohlc(closes, n_candles):
    """Agrège une série de clôtures en `n_candles` bougies OHLC."""
    n = len(closes)
    n_candles = max(1, min(n_candles, n))
    bucket = max(1, n // n_candles)
    candles = []
    i = 0
    while i < n:
        grp = closes[i:i + bucket]
        if grp:
            candles.append((grp[0], max(grp), min(grp), grp[-1]))  # O, H, L, C
        i += bucket
    return candles


def _sma(vals, window):
    """Moyenne mobile simple (renvoie une liste de même longueur, None au début)."""
    out = []
    s = 0.0
    for i, v in enumerate(vals):
        s += v
        if i >= window:
            s -= vals[i - window]
        out.append(s / window if i >= window - 1 else None)
    return out


def draw_candles(surf, rect, closes, n_candles=32, sma_windows=(10, 30),
                 body_frac=0.55):
    """Dessine un graphe en chandeliers à partir d'une série de clôtures, avec
    des moyennes mobiles optionnelles (en nombre de pas). Les bougies sont
    agrégées depuis les clôtures (open/high/low/close par groupe de pas).
    `body_frac` (0..1) contrôle l'espace entre bougies : 0.55 laisse des
    interstices visibles, évitant l'aspect « mur de couleur »."""
    rect = pygame.Rect(rect)
    if not closes or len(closes) < 2:
        return
    candles = _aggregate_ohlc(closes, n_candles)
    lo = min(min(c[2] for c in candles), min(closes))
    hi = max(max(c[1] for c in candles), max(closes))
    span = (hi - lo) or 1.0

    def yof(v):
        return rect.bottom - int((v - lo) / span * rect.h)

    n = len(candles)
    slot = rect.w / n
    bw = max(2, int(slot * body_frac))
    for k, (o, h, l, c) in enumerate(candles):
        cx = int(rect.x + (k + 0.5) * slot)
        up = c >= o
        col = config.COL_UP if up else config.COL_DOWN
        # mèche
        pygame.draw.line(surf, col, (cx, yof(h)), (cx, yof(l)), 1)
        # corps
        y_top, y_bot = yof(max(o, c)), yof(min(o, c))
        body = pygame.Rect(cx - bw // 2, y_top, bw, max(1, y_bot - y_top))
        pygame.draw.rect(surf, col, body)

    # moyennes mobiles (sur la série de clôtures brute, ré-échantillonnée par bougie)
    ma_cols = [config.COL_AMBER, config.COL_TEXT_DIM]
    bucket = max(1, len(closes) // max(1, n))
    for wi, w in enumerate(sma_windows or ()):
        if len(closes) <= w:
            continue
        ma = _sma(closes, w)
        pts = []
        for k in range(n):
            idx = min(len(closes) - 1, k * bucket + bucket - 1)
            if ma[idx] is None:
                continue
            cx = int(rect.x + (k + 0.5) * slot)
            pts.append((cx, yof(ma[idx])))
        if len(pts) >= 2:
            pygame.draw.aalines(surf, ma_cols[wi % len(ma_cols)], False, pts)


# ---------------------------------------------------------------------------
# AXES DE GRAPHE
# ---------------------------------------------------------------------------
def draw_chart_axes(surf, rect, lo, hi, y_fmt=lambda v: f"{v:.0f}", rows=5,
                     right_labels=False):
    """Dessine la grille horizontale + libellés d'axe Y d'un graphe en lignes
    (style atelier de graphes / option / quant). Commun à plusieurs écrans à
    panneaux de graphe (scene_graph, scene_quant...). Retourne (lo, hi, span)
    pour que l'appelant convertisse ensuite ses valeurs en pixels via
    `rect.bottom - (v - lo) / span * rect.h`.

    `rect`  : zone de tracé (hors marges d'axe, déjà réservées par l'appelant).
    `lo/hi` : bornes de l'axe Y.
    `y_fmt` : formatte la valeur affichée à côté de chaque ligne de grille.
    `rows`  : nombre d'intervalles de la grille (rows+1 lignes, haut compris).
    `right_labels` : place les libellés d'axe Y à droite (style Trading212)
                     au lieu de la gauche.
    """
    from ui.widgets import draw_text
    rect = pygame.Rect(rect)
    span = (hi - lo) or 1.0
    for r in range(rows + 1):
        v = hi - span * r / rows
        yy = rect.y + int(rect.h * r / rows)
        pygame.draw.line(surf, config.COL_GRID, (rect.x, yy), (rect.right, yy), 1)
        if right_labels:
            draw_text(surf, y_fmt(v), (rect.right + 6, yy - 7), fonts.tiny(),
                      config.COL_TEXT_DIM, align="left")
        else:
            draw_text(surf, y_fmt(v), (rect.x - 6, yy - 7), fonts.tiny(),
                      config.COL_TEXT_DIM, align="right")
    return lo, hi, span


def draw_chart_x_labels(surf, rect, labels):
    """Libellés d'axe X sous une zone de tracé (`rect`), pour indiquer la
    période/l'étendue représentée (cf. items « axe des X manquant »).
    `labels` : liste de `(frac, texte)` où `frac` ∈ [0, 1] est la position
    relative le long de `rect.w` (0 = bord gauche, 1 = bord droit) ; l'appelant
    doit avoir réservé une marge sous `rect` pour ce texte."""
    from ui.widgets import draw_text
    rect = pygame.Rect(rect)
    y = rect.bottom + 4
    for frac, text in labels:
        px = rect.x + int(frac * rect.w)
        align = "left" if frac <= 0.05 else ("right" if frac >= 0.95 else "center")
        draw_text(surf, text, (px, y), fonts.tiny(), config.COL_TEXT_DIM, align=align)


def draw_chart_zero_line(surf, rect, lo, span, color=None):
    """Trace une ligne horizontale au niveau y=0 si elle tombe dans [lo, lo+span]
    (utile pour les graphes de variation % / spread centrés sur zéro)."""
    if lo <= 0 <= lo + span:
        rect = pygame.Rect(rect)
        zy = rect.bottom - int((0 - lo) / span * rect.h)
        pygame.draw.line(surf, color or config.COL_TEXT_DIM, (rect.x, zy), (rect.right, zy), 1)


def draw_chart_crosshair(surf, rect, series, lo, span, mouse_pos, x_fmt=None, y_fmt=None,
                          color=config.COL_AMBER, show_pct=False):
    """Curseur de lecture pour un graphe en ligne : si `mouse_pos` survole
    `rect`, trace une ligne pointillée verticale jusqu'au point de `series`
    (valeurs Y, indexées 0..n-1 et réparties uniformément sur `rect.w` — même
    mapping que `draw_series`/`_polyline`) le plus proche du curseur, avec un
    point sur la courbe et une étiquette affichant la valeur Y (et, si
    `x_fmt` est fourni, le libellé d'abscisse correspondant à cet index).
    Si `show_pct` est vrai, ajoute la variation en % depuis le début de la
    série affichée (utile pour situer un point intermédiaire, pas seulement
    les deux extrémités). `lo`/`span` sont les bornes Y déjà utilisées pour
    convertir `series` en pixels (cf. retour de `draw_chart_axes`), pour
    rester exactement aligné sur la courbe tracée par l'appelant."""
    from ui.widgets import draw_text
    rect = pygame.Rect(rect)
    n = len(series)
    if n < 2 or not rect.collidepoint(mouse_pos):
        return
    mx, _ = mouse_pos
    i = round((mx - rect.x) / rect.w * (n - 1))
    i = max(0, min(n - 1, i))
    v = series[i]
    if v is None:
        return
    px = rect.x + int(i / (n - 1) * rect.w)
    py = rect.bottom - int((v - lo) / span * rect.h)
    yy = rect.top
    while yy < rect.bottom:
        pygame.draw.line(surf, config.COL_TEXT_DIM, (px, yy), (px, min(yy + 4, rect.bottom)), 1)
        yy += 8
    pygame.draw.circle(surf, config.COL_WHITE, (px, py), 4)
    pygame.draw.circle(surf, color, (px, py), 4, 1)
    label = y_fmt(v) if y_fmt else f"{v:,.2f}"
    if show_pct:
        v0 = next((x for x in series if x is not None), None)
        if v0:
            pct = (v - v0) / v0 * 100
            label = _L(f"{label}  ({'+' if pct >= 0 else ''}{pct:.1f}% depuis le début)", f"{label}  ({'+' if pct >= 0 else ''}{pct:.1f}% since start)")
    if x_fmt:
        label = f"{x_fmt(i)}   {label}"
    font = fonts.tiny(bold=True)
    w, h = font.size(label)
    bx = px + 10
    if bx + w + 10 > rect.right:
        bx = px - w - 18
    by = py - h - 14
    if by < rect.top:
        by = py + 12
    box = pygame.Rect(bx, by, w + 10, h + 8)
    pygame.draw.rect(surf, config.COL_PANEL_HEAD, box, border_radius=4)
    pygame.draw.rect(surf, color, box, 1, border_radius=4)
    draw_text(surf, label, (box.x + 5, box.y + 4), font, config.COL_TEXT)


def draw_chart_extrema(surf, rect, series, lo, span, y_fmt=None, color=config.COL_TEXT_DIM,
                       label=True):
    """Repère le plus haut et le plus bas d'une série affichée dans `rect`
    (même mapping que `draw_series`/`_polyline`) par un petit triangle et,
    si `label=True`, une étiquette de valeur, pour situer les extrêmes d'un
    coup d'œil sans avoir à survoler toute la courbe. N'affiche rien sur les
    graphes trop étroits (sparklines) où l'étiquette surchargerait le tracé.
    `label=False` ne garde que les triangles (l'appelant affiche les valeurs
    haut/bas ailleurs, hors du tracé, sur les graphes compacts où le texte
    chevaucherait sinon les libellés d'axe)."""
    from ui.widgets import draw_text
    rect = pygame.Rect(rect)
    n = len(series)
    if n < 3 or rect.w < 130:
        return
    idx_vals = [(i, v) for i, v in enumerate(series) if v is not None]
    if len(idx_vals) < 3:
        return
    i_max, v_max = max(idx_vals, key=lambda t: t[1])
    i_min, v_min = min(idx_vals, key=lambda t: t[1])
    if i_max == i_min:
        return
    for i, v, up in ((i_max, v_max, True), (i_min, v_min, False)):
        px = rect.x + int(i / (n - 1) * rect.w)
        py = rect.bottom - int((v - lo) / span * rect.h)
        tip = (px, py - 7) if up else (px, py + 7)
        base = [(px - 4, py - 1 if up else py + 1), (px + 4, py - 1 if up else py + 1)]
        pygame.draw.polygon(surf, color, [tip] + base)
        if not label:
            continue
        txt = y_fmt(v) if y_fmt else f"{v:,.2f}"
        font = fonts.tiny()
        lw, lh = font.size(txt)
        lx = max(rect.x, min(px - lw // 2, rect.right - lw))
        ly = py - lh - 10 if up else py + 10
        ly = max(rect.y, min(ly, rect.bottom - lh))
        draw_text(surf, txt, (lx, ly), font, color)


_hover_sync = {"frac": None, "source": None}


def sync_chart_hover(windows, mouse_pos):
    """Repère, parmi une liste de fenêtres-graphes (`DataWindow` en mode
    `chart`), celle survolée par la souris, et mémorise sa position relative
    sur l'axe X (0..1) afin que les AUTRES fenêtres ouvertes affichent un
    curseur fantôme au même instant — pratique pour comparer plusieurs actifs
    d'un coup d'œil sans déplacer la souris d'une fenêtre à l'autre. À appeler
    une fois par frame, avant de dessiner les fenêtres (cf. `PopupMixin.popups_draw`)."""
    _hover_sync["frac"] = None
    _hover_sync["source"] = None
    for w in windows:
        area = getattr(w, "_chart_area", None)
        chart = getattr(w, "chart", None)
        if area is None or not chart or len(chart) < 2 or getattr(w, "minimized", False):
            continue
        if area.collidepoint(mouse_pos):
            n = len(chart)
            i = max(0, min(n - 1, round((mouse_pos[0] - area.x) / area.w * (n - 1))))
            _hover_sync["frac"] = i / (n - 1)
            _hover_sync["source"] = id(w)
            return


def draw_chart_ghost(surf, rect, series, lo, span, frac, y_fmt=None, color=config.COL_TEXT_DIM):
    """Curseur fantôme (sans interaction directe) à la position relative
    `frac` (0..1) de l'axe X — utilisé pour répercuter le survol d'une autre
    fenêtre-graphe ouverte, cf. `sync_chart_hover`."""
    from ui.widgets import draw_text
    rect = pygame.Rect(rect)
    n = len(series)
    if frac is None or n < 2:
        return
    i = max(0, min(n - 1, round(frac * (n - 1))))
    v = series[i]
    if v is None:
        return
    px = rect.x + int(i / (n - 1) * rect.w)
    py = rect.bottom - int((v - lo) / span * rect.h)
    pygame.draw.line(surf, color, (px, rect.top), (px, rect.bottom), 1)
    pygame.draw.circle(surf, color, (px, py), 3, 1)
    label = y_fmt(v) if y_fmt else f"{v:,.2f}"
    font = fonts.tiny()
    w, h = font.size(label)
    bx = max(rect.x, min(px + 6, rect.right - w - 4))
    by = max(rect.top + 2, min(py - h - 6, rect.bottom - h - 2))
    draw_text(surf, label, (bx, by), font, color)


class ChartCursor:
    """État interactif persistant pour UN graphe en ligne — à instancier une
    fois par graphe (sur la scène, pas par frame) et réutiliser à chaque appel
    de `draw()`. Ajoute, par-dessus le curseur de lecture (`draw_chart_crosshair`)
    et les marqueurs d'extrêmes (`draw_chart_extrema`) :

      - clic droit sur la courbe : épingle/désépingle une ligne de référence
        horizontale au niveau cliqué, avec l'écart en % par rapport à la
        dernière valeur affiché en continu ;
      - clic gauche + glisser : sélectionne une plage de l'axe X et affiche
        la variation en % et la durée (en pas) entre les deux bornes.

    Usage :
        self._cursor = widgets.ChartCursor()              # dans on_enter
        if self._cursor.handle_event(event): return        # dans handle_event
        self._cursor.draw(surf, rect, series, lo, span,     # dans draw, après
                          mouse_pos=pygame.mouse.get_pos()) # avoir tracé la ligne

    La géométrie (rect/lo/span/series) utilisée par `handle_event` est celle
    mémorisée lors du DERNIER appel à `draw` (mise en page stable d'une frame
    à l'autre, comme `DataWindow._row_rects`) : pas besoin de dupliquer le
    calcul de mise en page de l'appelant pour traiter les clics.
    """

    def __init__(self):
        self.pin = None
        self._drag_from = None
        self._drag_to = None
        self._rect = None
        self._series = None

    def _index_at(self, mx):
        n = len(self._series)
        i = round((mx - self._rect.x) / self._rect.w * (n - 1))
        return max(0, min(n - 1, i))

    def handle_event(self, event):
        if self._rect is None or not self._series or len(self._series) < 2:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and self._rect.collidepoint(event.pos):
            if event.button == 3:
                if self.pin is None:
                    self.pin = self._series[self._index_at(event.pos[0])]
                else:
                    self.pin = None
                return True
            if event.button == 1:
                self._drag_from = self._index_at(event.pos[0])
                self._drag_to = self._drag_from
                return True
        elif event.type == pygame.MOUSEMOTION and self._drag_from is not None:
            if self._rect.collidepoint(event.pos):
                self._drag_to = self._index_at(event.pos[0])
            return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._drag_from is not None and self._drag_from == self._drag_to:
                self._drag_from = self._drag_to = None
            return False
        return False

    def draw(self, surf, rect, series, lo, span, mouse_pos=None, x_fmt=None, y_fmt=None,
             color=config.COL_AMBER, show_pct=False):
        self._rect = pygame.Rect(rect)
        self._series = series
        if mouse_pos is not None:
            draw_chart_crosshair(surf, rect, series, lo, span, mouse_pos,
                                 x_fmt=x_fmt, y_fmt=y_fmt, color=color, show_pct=show_pct)
        draw_chart_extrema(surf, rect, series, lo, span, y_fmt=y_fmt)
        if self.pin is not None:
            self._draw_pin(surf, rect, lo, span, y_fmt, series)
        if (self._drag_from is not None and self._drag_to is not None
                and self._drag_from != self._drag_to):
            self._draw_range(surf, rect, series)

    def _draw_pin(self, surf, rect, lo, span, y_fmt, series):
        from ui.widgets import draw_text
        rect = pygame.Rect(rect)
        py = max(rect.top, min(rect.bottom, rect.bottom - int((self.pin - lo) / span * rect.h)))
        pygame.draw.line(surf, config.COL_WARN, (rect.x, py), (rect.right, py), 1)
        last = next((v for v in reversed(series) if v is not None), None)
        diff = (last - self.pin) / self.pin * 100 if (last is not None and self.pin) else 0.0
        pin_label = y_fmt(self.pin) if y_fmt else f"{self.pin:,.2f}"
        label = _L(f"Réf. {pin_label}  ({'+' if diff >= 0 else ''}{diff:.1f}% vs actuel)", f"Ref. {pin_label}  ({'+' if diff >= 0 else ''}{diff:.1f}% vs current)")
        font = fonts.tiny(bold=True)
        ly = py - font.get_height() - 4 if py - font.get_height() - 4 > rect.top else py + 4
        draw_text(surf, label, (rect.x + 4, ly), font, config.COL_WARN)

    def _draw_range(self, surf, rect, series):
        from ui.widgets import draw_text
        rect = pygame.Rect(rect)
        n = len(series)
        i0, i1 = sorted((self._drag_from, self._drag_to))
        x0 = rect.x + int(i0 / (n - 1) * rect.w)
        x1 = rect.x + int(i1 / (n - 1) * rect.w)
        shade = pygame.Surface((max(1, x1 - x0), rect.h), pygame.SRCALPHA)
        shade.fill((*config.COL_CYAN[:3], 40))
        surf.blit(shade, (x0, rect.top))
        v0, v1 = series[i0], series[i1]
        if v0 is None or v1 is None or not v0:
            return
        pct = (v1 - v0) / v0 * 100
        label = f"{'+' if pct >= 0 else ''}{pct:.1f}%  sur {i1 - i0} pas"
        font = fonts.tiny(bold=True)
        w, h = font.size(label)
        bx = max(rect.x, min(x0, rect.right - w - 10))
        box = pygame.Rect(bx, rect.top + 4, w + 10, h + 8)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, box, border_radius=4)
        pygame.draw.rect(surf, config.COL_CYAN, box, 1, border_radius=4)
        draw_text(surf, label, (box.x + 5, box.y + 4), font, config.COL_TEXT)


def draw_chart_legend(surf, rect, items):
    """Dessine une légende compacte (carré coloré + libellé) en haut à gauche
    d'un panneau de graphe, avec retour à la ligne automatique. `items` est une
    liste de tuples (texte, couleur)."""
    from ui.widgets import draw_text
    rect = pygame.Rect(rect)
    x = rect.x + 6
    y = rect.y + 4
    for text, col in items:
        r = draw_text(surf, "■ ", (x, y), fonts.tiny(bold=True), col)
        r2 = draw_text(surf, text, (r.right, y), fonts.tiny(), config.COL_TEXT)
        x = r2.right + 16
        if x > rect.right - 120:
            x = rect.x + 6
            y += 16
