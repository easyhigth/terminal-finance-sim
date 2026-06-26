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


def draw_hint_bar(surf, anchor, hints, color=config.COL_TEXT_DIM):
    """Bandeau contextuel discret listant les touches pertinentes pour le
    focus clavier courant (ex. [↑↓] naviguer  [ENTRÉE] ouvrir  [ÉCHAP] retour),
    aligné à droite à partir du point `anchor` (coin haut-droit du texte).
    `hints` est une liste de (touche, action). No-op si vide."""
    if not hints:
        return
    text = "   ".join(f"[{k}] {a}" for k, a in hints)
    draw_text(surf, text, anchor, fonts.tiny(), color, align="right")


def hover_accent(active, base=config.COL_AMBER, hover_color=config.COL_CYAN):
    """Couleur d'un bloc cliquable neutre : `base` (ambre) au repos, `hover_color`
    (cyan) dès qu'il est survolé/sélectionné — convention visuelle commune à tous
    les éléments sélectionnables qui n'ont pas de couleur sémantique propre
    (vert=succès, rouge=danger, couleur de continent...). Si `base` n'est pas
    l'ambre par défaut (c'est-à-dire que l'appelant a déjà choisi une couleur
    sémantique), cette couleur est conservée au survol plutôt que d'être
    remplacée par du cyan."""
    if base != config.COL_AMBER:
        return base
    return hover_color if active else base


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


def draw_tooltip(surf, text, pos):
    """Bulle d'info affichant `text` en entier près de `pos` (coin du curseur).
    À appeler en dernier dans draw() pour rester au-dessus du reste."""
    font = fonts.tiny()
    pad = 6
    w, h = font.size(text)
    rect = pygame.Rect(pos[0] + 12, pos[1] + 18, w + pad * 2, h + pad * 2)
    if rect.right > config.SCREEN_WIDTH - 4:
        rect.x -= rect.right - (config.SCREEN_WIDTH - 4)
    if rect.bottom > config.SCREEN_HEIGHT - 4:
        rect.y = pos[1] - rect.h - 6
    pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect, border_radius=4)
    pygame.draw.rect(surf, config.COL_BORDER, rect, 1, border_radius=4)
    draw_text(surf, text, (rect.x + pad, rect.y + pad), font, config.COL_TEXT)


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


def wrap_text_lines(text, font, max_width):
    """Découpe `text` en lignes ne dépassant pas `max_width`, sans rien
    dessiner (même règle de coupe que `draw_text_wrapped`). Utile pour
    mesurer la hauteur d'un paragraphe avant de le rendre, par ex. pour
    dimensionner dynamiquement une carte selon son contenu."""
    words = text.split(" ")
    lines = []
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        if font.size(test)[0] <= max_width:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_text_wrapped(surf, text, pos, font, color, max_width, line_gap=4):
    """Dessine un paragraphe en gérant le retour à la ligne. Retourne la hauteur."""
    x, y = pos
    line_h = font.get_height() + line_gap
    start_y = y
    for line in wrap_text_lines(text, font, max_width):
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
            # interpolation fond/bordure/texte selon le survol animé ; les boutons
            # à accent neutre (ambre) glissent vers le cyan, les boutons à
            # couleur sémantique (vert/rouge...) gardent leur propre couleur.
            target = hover_accent(True, self.accent)
            bg = _lerp_col(config.COL_PANEL, config.COL_PANEL_HEAD, self._hover_t)
            border = _lerp_col(self.accent, target, self._hover_t)
            txt = _lerp_col(config.COL_TEXT, target, self._hover_t)
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
# CHAMP DE RECHERCHE — saisie filtrante avec curseur clignotant + bouton ✕
# ---------------------------------------------------------------------------
class SearchBox:
    """Champ de recherche texte autonome (état + saisie + dessin), pour
    factoriser le pattern répété à l'identique dans les écrans de trading à
    liste filtrable (scene_bonds/commodities/crypto). L'appelant garde la
    main sur le reset de scroll / la priorité ESC (souvent partagée avec la
    fermeture de popups), seuls saisie/effacement/dessin sont internalisés."""

    def __init__(self, rect, placeholder="Tapez pour rechercher…"):
        self.rect = pygame.Rect(rect)
        self.placeholder = placeholder
        self.text = ""
        self.clear_rect = None
        self._t = 0.0

    def update(self, dt):
        self._t += dt

    def handle_typing(self, event):
        """Gère KEYDOWN backspace/caractère imprimable. Retourne True si
        consommé (l'appelant gère ESCAPE et les autres touches lui-même)."""
        if event.type != pygame.KEYDOWN:
            return False
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
            return True
        if event.unicode and event.unicode.isprintable() and event.key != pygame.K_TAB:
            self.text += event.unicode
            return True
        return False

    def handle_clear_click(self, event):
        """Gère le clic sur le bouton ✕. Retourne True si géré."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.clear_rect and self.clear_rect.collidepoint(event.pos):
                self.text = ""
                return True
        return False

    @property
    def query(self):
        return self.text.strip().lower()

    def draw(self, surf, accent=config.COL_CYAN):
        pygame.draw.rect(surf, config.COL_PANEL, self.rect, border_radius=4)
        pygame.draw.rect(surf, accent, self.rect, 1, border_radius=4)
        cursor = "_" if int(self._t * 2) % 2 == 0 else " "
        label = (self.text + cursor) if self.text else (cursor + self.placeholder)
        col = config.COL_TEXT if self.text else config.COL_TEXT_DIM
        draw_text(surf, fit_text(label, fonts.small(), self.rect.w - 30),
                  (self.rect.x + 8, self.rect.y + 4), fonts.small(), col)
        self.clear_rect = None
        if self.text:
            self.clear_rect = pygame.Rect(self.rect.right - 22, self.rect.y, 22, self.rect.h)
            draw_text(surf, "✕", self.clear_rect.center, fonts.small(bold=True),
                      config.COL_TEXT_DIM, align="center")


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
    col = hover_accent(hover, accent) if enabled else config.COL_TEXT_DIM
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

    def draw(self, surf, rect, color=None, baseline=True, mouse_pos=None, y_fmt=None,
             show_pct=False, show_extrema=True):
        draw_series(surf, rect, self.values, color, baseline, mouse_pos=mouse_pos, y_fmt=y_fmt,
                   show_pct=show_pct, show_extrema=show_extrema)


def draw_series(surf, rect, vals, color=None, baseline=True, mouse_pos=None, y_fmt=None,
                show_pct=False, show_extrema=True, extrema_label=True):
    """Trace une polyligne à partir d'une liste de valeurs, dans `rect`.

    Si `mouse_pos` est fourni et survole `rect`, affiche un curseur (ligne
    pointillée verticale + point + étiquette de la valeur Y, et si `show_pct`
    la variation en % depuis le début) à l'abscisse la plus proche du curseur
    — cf. `draw_chart_crosshair`. Marque aussi les extrêmes de la série
    (cf. `draw_chart_extrema`), sauf si `show_extrema=False` (l'appelant
    annote déjà ses propres extrêmes, p. ex. record/plus bas d'une carrière).
    `extrema_label=False` garde les petits triangles d'extrêmes mais omet
    leur étiquette de valeur (l'appelant l'affiche ailleurs, hors du tracé,
    pour éviter tout chevauchement sur les graphes compacts)."""
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


# seuils d'alerte (rouge, ambre) des métriques de risque, en % — convention
# unique partagée par toutes les jauges de risque de l'UI.
ALERT_THRESHOLDS = {
    "max_drawdown": (15.0, 8.0),
    "top_weight": (35.0, 20.0),
}


def alert_color(value_pct, metric):
    """Rouge si `value_pct` (en %) dépasse le seuil haut de `metric`, ambre si
    le seuil bas, vert sinon (cf. `ALERT_THRESHOLDS`)."""
    red, amber = ALERT_THRESHOLDS[metric]
    if value_pct > red:
        return config.COL_DOWN
    if value_pct > amber:
        return config.COL_WARN
    return config.COL_UP


# notations de crédit (obligations souveraines/corporate, tranches ABS) —
# convention unique partagée : investment grade (AAA/AA/A) = vert, BBB
# (limite investment grade) = ambre, spéculatif (BB et en-dessous) ou non
# noté = rouge.
RATING_GREEN = ("AAA", "AA", "A")
RATING_AMBER = ("BBB",)


def rating_color(rating):
    """Vert/ambre/rouge selon la notation de crédit (cf. RATING_GREEN/AMBER)."""
    if rating in RATING_GREEN:
        return config.COL_UP
    if rating in RATING_AMBER:
        return config.COL_WARN
    return config.COL_DOWN


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

    Le curseur est aussi cliquable-glissable (sinon il a l'air draggable
    sans rien faire, et seule la molette défile) : tant que le bouton gauche
    est maintenu au-dessus de la piste (élargie horizontalement pour rester
    facile à attraper), le curseur suit la position verticale de la souris.
    Pas besoin d'état de glissement à conserver entre les frames : ce calcul
    est simplement repris à chaque appel de `draw_scrollbar` (appelé à
    chaque frame de dessin). Renvoie le `scroll` à jour : l'appelant doit
    récupérer cette valeur (`self.scroll = widgets.draw_scrollbar(...)`).
    """
    if max_scroll <= 0:
        return scroll
    panel_rect = pygame.Rect(panel_rect)
    list_area = pygame.Rect(list_area)
    track = pygame.Rect(panel_rect.right - 8, list_area.y, 6, list_area.h)
    pygame.draw.rect(surf, config.COL_PANEL, track, border_radius=3)
    frac = list_area.h / (content_h or 1)
    bar_h = max(24, int(list_area.h * frac))
    bar_y = list_area.y + int((list_area.h - bar_h) * (scroll / max_scroll))
    pygame.draw.rect(surf, config.COL_AMBER_DIM, (track.x, bar_y, 6, bar_h), border_radius=3)

    grab_zone = track.inflate(10, 0)
    mx, my = pygame.mouse.get_pos()
    if pygame.mouse.get_pressed()[0] and grab_zone.collidepoint(mx, my):
        rel = (my - bar_h // 2 - list_area.y) / max(1, list_area.h - bar_h)
        return max(0, min(max_scroll, int(rel * max_scroll)))
    return scroll


class TickFlash:
    """Suit, pour un ensemble de clés (ticker/indice...), la dernière valeur
    "en direct" vue et renvoie une couleur de flash qui s'éteint en ~300ms à
    chaque variation perceptible — l'effet "tick vert/rouge" des terminaux de
    marché, posé sur l'animation intraday (Round 11 Phase 3, `core/intraday.py`)
    sans dépendre d'un `dt` explicite (décroissance basée sur l'horloge murale
    `pygame.time.get_ticks()`, donc utilisable depuis `draw()` seul).

    Usage :
        flash = widgets.TickFlash()                  # un par panneau, stocké sur self
        col = flash.tick(name, live_value, up_color, down_color, base_color)
        widgets.draw_text(surf, txt, pos, font, col)
    """
    DECAY_MS = 300

    def __init__(self):
        self._last = {}   # key -> (value, dir, t_ms)

    def tick(self, key, value, up_color, down_color, base_color):
        now = pygame.time.get_ticks()
        prev = self._last.get(key)
        if prev is None:
            self._last[key] = (value, 0, now)
            return base_color
        prev_value, prev_dir, prev_t = prev
        if value > prev_value:
            self._last[key] = (value, 1, now)
            prev_dir, prev_t = 1, now
        elif value < prev_value:
            self._last[key] = (value, -1, now)
            prev_dir, prev_t = -1, now
        else:
            self._last[key] = (value, prev_dir, prev_t)
        if prev_dir == 0:
            return base_color
        intensity = max(0.0, 1.0 - (now - prev_t) / self.DECAY_MS)
        if intensity <= 0.0:
            return base_color
        flash = up_color if prev_dir > 0 else down_color
        return tuple(int(b + (f - b) * intensity) for b, f in zip(base_color, flash))


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


def draw_chart_x_labels(surf, rect, labels):
    """Libellés d'axe X sous une zone de tracé (`rect`), pour indiquer la
    période/l'étendue représentée (cf. items « axe des X manquant »).
    `labels` : liste de `(frac, texte)` où `frac` ∈ [0, 1] est la position
    relative le long de `rect.w` (0 = bord gauche, 1 = bord droit) ; l'appelant
    doit avoir réservé une marge sous `rect` pour ce texte."""
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
            label = f"{label}  ({'+' if pct >= 0 else ''}{pct:.1f}% depuis le début)"
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
        rect = pygame.Rect(rect)
        py = max(rect.top, min(rect.bottom, rect.bottom - int((self.pin - lo) / span * rect.h)))
        pygame.draw.line(surf, config.COL_WARN, (rect.x, py), (rect.right, py), 1)
        last = next((v for v in reversed(series) if v is not None), None)
        diff = (last - self.pin) / self.pin * 100 if (last is not None and self.pin) else 0.0
        pin_label = y_fmt(self.pin) if y_fmt else f"{self.pin:,.2f}"
        label = f"Réf. {pin_label}  ({'+' if diff >= 0 else ''}{diff:.1f}% vs actuel)"
        font = fonts.tiny(bold=True)
        ly = py - font.get_height() - 4 if py - font.get_height() - 4 > rect.top else py + 4
        draw_text(surf, label, (rect.x + 4, ly), font, config.COL_WARN)

    def _draw_range(self, surf, rect, series):
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
