"""
widgets.py — Helpers de dessin et widgets réutilisables (style terminal).
Tout est dessiné à la main avec pygame.draw pour garder l'esthétique
Bloomberg : panneaux à bordure fine, en-têtes ambre, texte monospace.
"""
import pygame

from core import config
from ui import fonts


# ---------------------------------------------------------------------------
# NAVIGATION CLAVIER (listes sélectionnables)
# ---------------------------------------------------------------------------
def list_key_nav(event, selected, count):
    """Gère HAUT/BAS/ENTRÉE pour naviguer une liste de `count` items au clavier.
    Retourne (nouvel_index, activer) où `activer` est True si ENTRÉE a été
    pressée sur l'item sélectionné. `selected` peut être None (rien sélectionné
    encore) : HAUT/BAS sélectionnent alors le premier item."""
    if count <= 0 or event.type != pygame.KEYDOWN:
        return selected, False
    if event.key in (pygame.K_UP, pygame.K_DOWN):
        if selected is None:
            return 0, False
        step = -1 if event.key == pygame.K_UP else 1
        return (selected + step) % count, False
    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and selected is not None:
        return selected, True
    return selected, False


def draw_row_selection(surf, rect, selected, accent=config.COL_AMBER):
    """Surligne `rect` quand un item est navigué au clavier (sans le cliquer),
    pour donner un retour visuel cohérent avec la sélection à la souris."""
    if selected:
        pygame.draw.rect(surf, accent, rect, 1, border_radius=3)


# ---------------------------------------------------------------------------
# TEXTE
# ---------------------------------------------------------------------------
def draw_text(surf, text, pos, font, color=config.COL_TEXT, align="left"):
    """Dessine du texte. align: left | center | right. Retourne le Rect."""
    img = font.render(text, True, color)
    rect = img.get_rect()
    if align == "left":
        rect.topleft = pos
    elif align == "center":
        rect.center = pos
    elif align == "right":
        rect.topright = pos
    surf.blit(img, rect)
    return rect


def fit_text(text, font, max_width, ellipsis="…"):
    """Tronque `text` avec une ellipse pour qu'il tienne dans `max_width` pixels."""
    if max_width <= 0 or font.size(text)[0] <= max_width:
        return text
    while text and font.size(text + ellipsis)[0] > max_width:
        text = text[:-1]
    return (text.rstrip() + ellipsis) if text else ellipsis


def draw_text_fit(surf, text, pos, font, color=config.COL_TEXT, max_width=0, align="left"):
    """Comme draw_text mais tronque le texte (…) pour tenir dans `max_width`."""
    if max_width:
        text = fit_text(text, font, max_width)
    return draw_text(surf, text, pos, font, color, align)


def draw_text_scaled(surf, text, pos, font, color, max_width, align="left"):
    """Dessine du texte sur une seule ligne, réduit à l'échelle s'il dépasse
    `max_width` (utile pour les titres longs qui ne doivent pas sortir de l'écran)."""
    img = font.render(text, True, color)
    w = img.get_width()
    if max_width and w > max_width:
        h = max(1, int(img.get_height() * (max_width / w)))
        img = pygame.transform.smoothscale(img, (max_width, h))
    rect = img.get_rect()
    if align == "left":
        rect.topleft = pos
    elif align == "center":
        rect.center = pos
    elif align == "right":
        rect.topright = pos
    surf.blit(img, rect)
    return rect


def draw_text_wrapped(surf, text, pos, font, color, max_width, line_gap=4):
    """Dessine un paragraphe en gérant le retour à la ligne. Retourne la hauteur."""
    words = text.split(" ")
    x, y = pos
    line = ""
    line_h = font.get_height() + line_gap
    start_y = y
    for word in words:
        test = (line + " " + word).strip()
        if font.size(test)[0] <= max_width:
            line = test
        else:
            draw_text(surf, line, (x, y), font, color)
            y += line_h
            line = word
    if line:
        draw_text(surf, line, (x, y), font, color)
        y += line_h
    return y - start_y


# ---------------------------------------------------------------------------
# PANNEAU (cadre type terminal avec en-tête)
# ---------------------------------------------------------------------------
def draw_panel(surf, rect, title=None, accent=config.COL_AMBER, prio=None):
    """Dessine un panneau encadré avec en-tête optionnel. Retourne le rect interne.
    `prio` (couleur) ajoute une barre de priorité verticale à gauche."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, config.COL_PANEL, rect)
    pygame.draw.rect(surf, config.COL_BORDER, rect, 1)
    if prio:
        pygame.draw.rect(surf, prio, (rect.x, rect.y, 3, rect.h))

    inner = rect.inflate(-16, -16)
    if title:
        head_rect = pygame.Rect(rect.x, rect.y, rect.w, 26)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, head_rect)
        pygame.draw.line(surf, accent, (rect.x, rect.y + 26),
                         (rect.right, rect.y + 26), 1)
        draw_text(surf, title.upper(), (rect.x + 10, rect.y + 6),
                  fonts.small(bold=True), accent)
        inner = pygame.Rect(rect.x + 12, rect.y + 36, rect.w - 24, rect.h - 48)
    return inner


# ---------------------------------------------------------------------------
# BOUTON
# ---------------------------------------------------------------------------
def _lerp_col(a, b, t):
    """Interpolation linéaire entre deux couleurs RGB. t dans [0,1]."""
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Button:
    """Bouton cliquable avec état survol/désactivé et feedback d'appui."""

    PRESS_MS = 180   # durée du flash d'appui

    def __init__(self, rect, label, accent=config.COL_AMBER, enabled=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.accent = accent
        self.enabled = enabled
        self.hover = False
        self._press_ms = -10000     # instant du dernier clic (ms)
        self._hover_t = 0.0         # progression d'animation du survol [0,1]

    def update(self, mouse_pos, dt=0.0):
        self.hover = self.enabled and self.rect.collidepoint(mouse_pos)
        # animation douce du survol
        target = 1.0 if self.hover else 0.0
        speed = 10.0 * dt if dt else 1.0
        self._hover_t += (target - self._hover_t) * min(1.0, speed)

    def handle(self, event):
        """Retourne True si cliqué (et déclenche le feedback d'appui)."""
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._press_ms = pygame.time.get_ticks()
                return True
        return False

    def _press_factor(self):
        """Retourne l'intensité du flash d'appui [0,1] qui décroît avec le temps."""
        elapsed = pygame.time.get_ticks() - self._press_ms
        if elapsed < 0 or elapsed > self.PRESS_MS:
            return 0.0
        return 1.0 - elapsed / self.PRESS_MS

    def draw(self, surf):
        press = self._press_factor()
        if not self.enabled:
            bg, border, txt = config.COL_PANEL, config.COL_BORDER, config.COL_TEXT_DIM
        else:
            # interpolation fond/bordure/texte selon le survol animé
            bg = _lerp_col(config.COL_PANEL, config.COL_PANEL_HEAD, self._hover_t)
            border = self.accent
            txt = _lerp_col(config.COL_TEXT, self.accent, self._hover_t)
        # flash d'appui : éclaircit le fond brièvement
        if press > 0:
            bg = _lerp_col(bg, self.accent, 0.35 * press)
            txt = config.COL_BG
        # ombre portée subtile (profondeur), sauf si enfoncé
        if self.enabled and press <= 0:
            shadow = self.rect.move(0, 2)
            pygame.draw.rect(surf, (0, 0, 0), shadow, border_radius=6)
        pygame.draw.rect(surf, bg, self.rect, border_radius=6)
        # bordure plus épaisse au survol pour le feedback
        pygame.draw.rect(surf, border, self.rect, 2 if self.hover else 1, border_radius=6)
        # liseré clair en haut au survol (effet "relief")
        if self.hover and self.enabled and press <= 0:
            top = pygame.Rect(self.rect.x + 6, self.rect.y + 1, self.rect.w - 12, 1)
            pygame.draw.rect(surf, _lerp_col(bg, config.COL_WHITE, 0.25), top)
        # léger enfoncement du label quand on appuie
        dy = int(2 * press)
        img = fonts.body(bold=self.hover).render(self.label, True, txt)
        r = img.get_rect(center=(self.rect.centerx, self.rect.centery + dy))
        surf.blit(img, r)


# ---------------------------------------------------------------------------
# PIED DE CARTE — rangée de bouton(s) d'action alignée en bas d'une carte
# ---------------------------------------------------------------------------
def draw_card_footer(surf, card_rect, label, accent=config.COL_AMBER,
                      enabled=True, hover=False, height=36, pad=16):
    """Dessine un bouton d'action ancré en bas d'une carte, avec un padding et
    une hauteur constants : unifie le placement des CTA de carte entre les
    écrans (examcert / track / cert), qui variaient (bas-centré, bas-droite,
    en ligne). Retourne le Rect du bouton (pour la détection de clic/focus).

    `card_rect` : rect de la carte parente.
    `label`     : texte du bouton.
    `accent`    : couleur de bordure/texte du bouton.
    `enabled`   : si False, bouton grisé (non actionnable).
    `hover`     : si True, applique le fond "survolé".
    """
    card_rect = pygame.Rect(card_rect)
    rect = pygame.Rect(card_rect.x + pad, card_rect.bottom - pad - height,
                        card_rect.w - 2 * pad, height)
    col = accent if enabled else config.COL_TEXT_DIM
    bg = config.COL_PANEL_HEAD if (hover and enabled) else config.COL_PANEL
    pygame.draw.rect(surf, bg, rect, border_radius=5)
    pygame.draw.rect(surf, col, rect, 1, border_radius=5)
    img = fonts.small(bold=True).render(label, True, col)
    surf.blit(img, img.get_rect(center=rect.center))
    return rect


# ---------------------------------------------------------------------------
# DIVERS
# ---------------------------------------------------------------------------
def draw_ticker_value(surf, label, value, pos, change=None):
    """Affiche 'LABEL  value  (+x%)' avec couleur selon la variation."""
    x, y = pos
    r = draw_text(surf, label + "  ", (x, y), fonts.small(), config.COL_TEXT_DIM)
    r = draw_text(surf, value, (r.right, y), fonts.small(bold=True), config.COL_WHITE)
    if change is not None:
        col = config.COL_UP if change >= 0 else config.COL_DOWN
        sign = "+" if change >= 0 else ""
        draw_text(surf, f"  {sign}{change:.2f}%", (r.right, y), fonts.small(), col)


def format_money(amount, currency="$"):
    """Formate un montant en notation financière compacte."""
    a = abs(amount)
    sign = "-" if amount < 0 else ""
    if a >= 1e9:
        s = f"{a/1e9:.2f}B"
    elif a >= 1e6:
        s = f"{a/1e6:.2f}M"
    elif a >= 1e3:
        s = f"{a/1e3:.1f}K"
    else:
        s = f"{a:.0f}"
    return f"{sign}{currency}{s}"


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

    def draw(self, surf, rect, color=None, baseline=True):
        draw_series(surf, rect, self.values, color, baseline)


def draw_series(surf, rect, vals, color=None, baseline=True):
    """Trace une polyligne à partir d'une liste de valeurs, dans `rect`."""
    rect = pygame.Rect(rect)
    if not vals or len(vals) < 2:
        return
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    col = color
    if col is None:
        col = config.COL_UP if vals[-1] >= vals[0] else config.COL_DOWN
    if baseline:
        by = rect.bottom - int((vals[0] - lo) / span * rect.h)
        pygame.draw.line(surf, config.COL_GRID, (rect.x, by), (rect.right, by), 1)
    pts = []
    n = len(vals)
    for i, v in enumerate(vals):
        x = rect.x + int(i / (n - 1) * rect.w)
        y = rect.bottom - int((v - lo) / span * rect.h)
        pts.append((x, y))
    if len(pts) >= 2:
        pygame.draw.aalines(surf, col, False, pts)
    pygame.draw.circle(surf, col, pts[-1], 2)


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


def draw_candles(surf, rect, closes, n_candles=32, sma_windows=(10, 30)):
    """Dessine un graphe en chandeliers à partir d'une série de clôtures, avec
    des moyennes mobiles optionnelles (en nombre de pas). Les bougies sont
    agrégées depuis les clôtures (open/high/low/close par groupe de pas)."""
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
    bw = max(2, int(slot * 0.6))
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
# BARRE DE PROGRESSION / JAUGE
# ---------------------------------------------------------------------------
def draw_progress(surf, rect, ratio, accent=config.COL_AMBER, bg=None):
    """Dessine une jauge horizontale remplie à `ratio` (0..1)."""
    rect = pygame.Rect(rect)
    ratio = max(0.0, min(1.0, ratio))
    pygame.draw.rect(surf, bg or config.COL_PANEL, rect)
    pygame.draw.rect(surf, config.COL_BORDER, rect, 1)
    fill_w = int((rect.w - 2) * ratio)
    if fill_w > 0:
        pygame.draw.rect(surf, accent,
                         (rect.x + 1, rect.y + 1, fill_w, rect.h - 2))


def draw_tile(surf, rect, label, value, accent=config.COL_AMBER,
              value_color=config.COL_WHITE):
    """Tuile de statistique dense : libellé en haut, valeur en gros dessous."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, config.COL_PANEL, rect, border_radius=4)
    pygame.draw.rect(surf, config.COL_BORDER, rect, 1, border_radius=4)
    pygame.draw.rect(surf, accent, (rect.x, rect.y, rect.w, 2))
    draw_text(surf, label.upper(), (rect.x + 8, rect.y + 6), fonts.tiny(bold=True),
              config.COL_TEXT_DIM)
    draw_text(surf, str(value), (rect.x + 8, rect.y + 20), fonts.body(bold=True),
              value_color)


def draw_error_panel(surf, message, hint=None, top=40, title_color=config.COL_DOWN):
    """Écran de repli standard quand des données attendues (ticker, dataset…)
    sont manquantes/invalides. Affiche un message d'erreur + une indication
    optionnelle. N'affiche PAS de bouton retour : la scène appelante garde
    son propre `back_btn` (déjà créé dans on_enter) et le dessine après cet
    appel, pour rester cohérente avec le reste de l'écran."""
    draw_text(surf, message, (40, top), fonts.title(bold=True), title_color)
    if hint:
        draw_text(surf, hint, (40, top + 60), fonts.body(), config.COL_TEXT_DIM)


def draw_scrollbar(surf, panel_rect, list_area, scroll, max_scroll, content_h):
    """Dessine une scrollbar verticale fine (piste + curseur) le long du bord
    droit de `panel_rect`, sur la hauteur de `list_area`. Ne dessine rien si
    `max_scroll` <= 0 (pas besoin de défiler). Reproduit le calcul partagé par
    les écrans à liste défilante (deals/news/mandates/bonds...) : la piste
    fait 6px de large, collée 8px avant le bord droit du panneau ; le curseur
    a une hauteur proportionnelle au ratio visible/contenu (mini 24px) et sa
    position suit `scroll`/`max_scroll`.

    `panel_rect`  : rect du panneau englobant (pour ancrer la piste à droite).
    `list_area`   : rect de la zone de liste défilante (hauteur de la piste).
    `scroll`      : décalage de défilement courant (px).
    `max_scroll`  : décalage maximal (0 si tout le contenu est visible).
    `content_h`   : hauteur totale du contenu (pour le ratio du curseur).
    """
    if max_scroll <= 0:
        return
    panel_rect = pygame.Rect(panel_rect)
    list_area = pygame.Rect(list_area)
    track = pygame.Rect(panel_rect.right - 8, list_area.y, 6, list_area.h)
    pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=3)
    frac = list_area.h / (content_h or 1)
    bar_h = max(24, int(list_area.h * frac))
    bar_y = list_area.y + int((list_area.h - bar_h) * (scroll / max_scroll))
    pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 6, bar_h), border_radius=3)


class ScrollState:
    """État de défilement minimal pour un panneau-liste, réutilisable quand un
    même écran a PLUSIEURS zones défilantes indépendantes (contrairement au
    pattern `self.scroll`/`self._max_scroll` à un seul champ déjà utilisé par
    scene_structured.py/scene_bonds.py pour un écran à une seule liste).

    Usage par panneau :
        st = self._scrolls.setdefault("indices", widgets.ScrollState())
        ... molette : st.handle_wheel(event) dans handle_event
        ... dessin  : surf.set_clip(list_area) ; y = inner.y - st.scroll ; ... dessiner ...
                      surf.set_clip(prev_clip) ; st.set_bounds(list_area, content_h)
                      widgets.draw_scrollbar(surf, panel_rect, list_area, st.scroll, st.max_scroll, content_h)
    """

    def __init__(self):
        self.scroll = 0
        self.max_scroll = 0
        self.rect = None   # dernier rect de zone défilante (pour le hit-test molette)

    def scroll_by(self, dy):
        self.scroll = max(0, min(self.max_scroll, self.scroll + dy))

    def set_bounds(self, list_area, content_h):
        """À appeler après le dessin du contenu : enregistre la zone (pour le
        hit-test molette) et reclamp `scroll` à la hauteur de contenu réelle
        (gère le cas où le contenu est plus court que la zone -> max_scroll=0)."""
        self.rect = pygame.Rect(list_area)
        self.max_scroll = max(0, content_h - self.rect.h)
        self.scroll = min(self.scroll, self.max_scroll)

    def handle_wheel(self, event, step=48):
        """Si `event` est un clic-molette (bouton 4/5) sur `self.rect`, ajuste
        le défilement et renvoie True. Sinon renvoie False sans rien faire —
        appelant : `for st in self._scrolls.values(): if st.handle_wheel(event): return`."""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button not in (4, 5):
            return False
        if not self.rect or not self.rect.collidepoint(event.pos):
            return False
        self.scroll_by(-step if event.button == 4 else step)
        return True


def draw_chart_axes(surf, rect, lo, hi, y_fmt=lambda v: f"{v:.0f}", rows=5):
    """Dessine la grille horizontale + libellés d'axe Y d'un graphe en lignes
    (style atelier de graphes / option / quant). Commun à plusieurs écrans à
    panneaux de graphe (scene_graph, scene_quant...). Retourne (lo, hi, span)
    pour que l'appelant convertisse ensuite ses valeurs en pixels via
    `rect.bottom - (v - lo) / span * rect.h`.

    `rect`  : zone de tracé (hors marges d'axe, déjà réservées par l'appelant).
    `lo/hi` : bornes de l'axe Y.
    `y_fmt` : formatte la valeur affichée à côté de chaque ligne de grille.
    `rows`  : nombre d'intervalles de la grille (rows+1 lignes, haut compris).
    """
    rect = pygame.Rect(rect)
    span = (hi - lo) or 1.0
    for r in range(rows + 1):
        v = hi - span * r / rows
        yy = rect.y + int(rect.h * r / rows)
        pygame.draw.line(surf, config.COL_GRID, (rect.x, yy), (rect.right, yy), 1)
        draw_text(surf, y_fmt(v), (rect.x - 6, yy - 7), fonts.tiny(),
                  config.COL_TEXT_DIM, align="right")
    return lo, hi, span


def draw_chart_zero_line(surf, rect, lo, span, color=None):
    """Trace une ligne horizontale au niveau y=0 si elle tombe dans [lo, lo+span]
    (utile pour les graphes de variation % / spread centrés sur zéro)."""
    if lo <= 0 <= lo + span:
        rect = pygame.Rect(rect)
        zy = rect.bottom - int((0 - lo) / span * rect.h)
        pygame.draw.line(surf, color or config.COL_TEXT_DIM, (rect.x, zy), (rect.right, zy), 1)


def draw_chart_legend(surf, rect, items):
    """Dessine une légende compacte (carré coloré + libellé) en haut à gauche
    d'un panneau de graphe, avec retour à la ligne automatique. `items` est une
    liste de tuples (texte, couleur)."""
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


def draw_badge(surf, text, pos, accent=config.COL_AMBER, align="left"):
    """Petit badge/pilule coloré avec texte. Retourne le Rect."""
    font = fonts.tiny(bold=True)
    tw = font.size(text)[0]
    w, h = tw + 16, font.get_height() + 6
    x, y = pos
    if align == "right":
        x -= w
    elif align == "center":
        x -= w // 2
    rect = pygame.Rect(x, y, w, h)
    bg = _lerp_col(config.COL_BG, accent, 0.18)
    pygame.draw.rect(surf, bg, rect, border_radius=3)
    pygame.draw.rect(surf, accent, rect, 1, border_radius=3)
    draw_text(surf, text, (rect.x + 8, rect.y + 3), font, accent)
    return rect
