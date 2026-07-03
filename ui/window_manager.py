"""
window_manager.py — Gestionnaire de fenêtres façon « bureau d'ordinateur »
(refonte UI « Jeu PC », étape 1).

Le jeu passe d'une pile de scènes plein écran à un BUREAU où plusieurs
applications cohabitent dans des fenêtres déplaçables, ouvrables en même temps
(recherche, trading, tableur…) — comme un vrai poste de travail finance.

Ce module ne connaît RIEN de la logique métier : il dessine le chrome d'une
fenêtre (barre de titre, bouton fermer/réduire, poignée de redimensionnement),
gère le déplacement/redimensionnement/focus/ordre de superposition (z-order) et
route les évènements vers l'application FOCALISÉE. Chaque application est un
objet `DesktopApp` (cf. `apps/base.py`) qui dessine dans le rectangle de contenu
qu'on lui fournit — coordonnées ABSOLUES à l'écran, pas de translation de
surface, pour rester compatible avec les widgets existants (`ui/widgets.py`).
"""
import pygame

from core import audio, config
from ui import desktop_icons, fonts, widgets

TITLE_H = 26          # hauteur de la barre de titre
BORDER = 2            # épaisseur du liseré de fenêtre
RESIZE_GRIP = 14      # taille de la poignée de redimensionnement (coin bas-droit)
BTN_W = TITLE_H       # boutons carrés dans la barre de titre
DOCK_FLASH_MS = 240   # durée du liseré cyan pulsé après un ancrage/agrandissement


class Window:
    """Une fenêtre du bureau : chrome + une application `DesktopApp`."""

    def __init__(self, key, app_obj, x, y, w, h):
        self.key = key            # identifiant d'app (unique : une fenêtre par app)
        self.app_obj = app_obj    # instance DesktopApp
        self.rect = pygame.Rect(x, y, w, h)
        self.minimized = False
        self._drag_off = None     # (dx, dy) pendant un déplacement
        self._resizing = False    # redimensionnement en cours
        self._restore_rect = None # taille/pos avant ancrage/maximisation (toggle)
        self.attention = False    # réclame l'attention (clignote dans la barre des tâches)
        self.pinned = False       # « toujours au premier plan » (menu contextuel de la
                                  # barre de titre) — cf. WindowManager._z_order
        self._dock_flash_until = 0   # horloge murale : liseré pulsé après ancrage/agrandissement

    # --- sous-rectangles du chrome (recalculés à la volée depuis self.rect) ---
    @property
    def title_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.w, TITLE_H)

    @property
    def close_rect(self):
        return pygame.Rect(self.rect.right - BTN_W, self.rect.y, BTN_W, TITLE_H)

    @property
    def min_rect(self):
        return pygame.Rect(self.rect.right - 2 * BTN_W, self.rect.y, BTN_W, TITLE_H)

    @property
    def resize_rect(self):
        return pygame.Rect(self.rect.right - RESIZE_GRIP, self.rect.bottom - RESIZE_GRIP,
                           RESIZE_GRIP, RESIZE_GRIP)

    @property
    def content_rect(self):
        """Zone de dessin réservée à l'application (sous la barre de titre)."""
        return pygame.Rect(self.rect.x + BORDER, self.rect.y + TITLE_H,
                           self.rect.w - 2 * BORDER, self.rect.h - TITLE_H - BORDER)

    # ------------------------------------------------------------------ dessin
    def draw(self, surf, focused):
        accent = config.COL_AMBER if focused else config.COL_BORDER
        # ombre portée discrète
        shadow = pygame.Surface((self.rect.w + 8, self.rect.h + 8), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 90))
        surf.blit(shadow, (self.rect.x + 4, self.rect.y + 6))
        # corps
        pygame.draw.rect(surf, config.COL_BG, self.rect)
        pygame.draw.rect(surf, accent, self.rect, BORDER)
        # liseré cyan pulsé bref juste après un ancrage/agrandissement (feedback
        # visuel de docking, s'estompe tout seul via l'horloge murale)
        remaining = self._dock_flash_until - pygame.time.get_ticks()
        if remaining > 0:
            alpha = max(0, min(255, int(255 * remaining / DOCK_FLASH_MS)))
            flash = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
            pygame.draw.rect(flash, (*config.COL_CYAN, alpha), flash.get_rect(), BORDER + 2)
            surf.blit(flash, self.rect.topleft)
        # barre de titre
        tr = self.title_rect
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if focused else config.COL_PANEL, tr)
        pygame.draw.line(surf, accent, (tr.x, tr.bottom - 1), (tr.right, tr.bottom - 1), 1)
        icon_kind = getattr(self.app_obj, "icon_kind", "generic")
        icon_col = config.COL_AMBER if focused else config.COL_TEXT_DIM
        desktop_icons.draw(surf, (tr.x + 18, tr.centery), icon_kind, icon_col)
        widgets.draw_text(surf, self.app_obj.title, (tr.x + 32, tr.y + 5),
                          fonts.small(bold=True), icon_col)
        if self.pinned:
            # petite épingle VECTORIELLE (tête + pointe) juste avant les boutons
            # réduire/fermer — pas de glyphe Unicode « 📌 », non garanti par la
            # police embarquée (même précaution que le reste de ce module).
            px, py = tr.right - 3 * BTN_W + BTN_W // 2, tr.centery
            pygame.draw.circle(surf, config.COL_AMBER, (px, py - 3), 3)
            pygame.draw.polygon(surf, config.COL_AMBER,
                                [(px - 2, py), (px + 2, py), (px, py + 5)])
        # boutons réduire / fermer (dessin vectoriel, cf. ui/desktop_icons.py —
        # les glyphes Unicode « – »/« ✕ » ne s'affichent pas de façon fiable)
        mr, cr = self.min_rect, self.close_rect
        mp = pygame.mouse.get_pos()
        if mr.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_PANEL, mr)
        pygame.draw.line(surf, config.COL_TEXT, (mr.centerx - 5, mr.centery), (mr.centerx + 5, mr.centery), 2)
        if cr.collidepoint(mp):
            pygame.draw.rect(surf, config.COL_DOWN, cr)
        xcol = config.COL_WHITE if cr.collidepoint(mp) else config.COL_TEXT
        pygame.draw.line(surf, xcol, (cr.centerx - 5, cr.centery - 5), (cr.centerx + 5, cr.centery + 5), 2)
        pygame.draw.line(surf, xcol, (cr.centerx - 5, cr.centery + 5), (cr.centerx + 5, cr.centery - 5), 2)
        # contenu de l'application (clippé à sa zone)
        cont = self.content_rect
        prev_clip = surf.get_clip()
        surf.set_clip(cont)
        try:
            self.app_obj.draw(surf, cont)
        finally:
            surf.set_clip(prev_clip)
        # poignée de redimensionnement (trois traits en coin bas-droit)
        rr = self.resize_rect
        for i in range(1, 4):
            pygame.draw.line(surf, accent, (rr.right - i * 4, rr.bottom - 2),
                             (rr.right - 2, rr.bottom - i * 4), 1)


class WindowManager:
    """Pile de fenêtres (dernier = au premier plan) + routage des évènements."""

    def __init__(self, app):
        self.app = app
        self.windows = []     # ordre = z-order (fin de liste = au premier plan)
        # zone de travail utile (sous la barre supérieure, au-dessus de la barre
        # des tâches) — cible des ancrages ; le bureau l'ajuste (cf. DesktopScene).
        self.work_area = pygame.Rect(0, config.TOPBAR_H, config.SCREEN_WIDTH,
                                     config.SCREEN_HEIGHT - config.TOPBAR_H)
        self._snap_preview = None     # Rect d'aperçu d'ancrage pendant un glisser
        self._last_title_click = (None, -10000)   # (window, ms) pour le double-clic
        self.on_close = None   # callable(Window) optionnel, appelé AVANT la fermeture
                               # (ex. DesktopScene mémorise la dernière fenêtre fermée
                               # pour le raccourci "rouvrir", cf. Ctrl+Maj+Z)

    def _z_order(self):
        """Ordre de dessin/détection de clic : les fenêtres ÉPINGLÉES
        (`Window.pinned`) passent TOUJOURS au-dessus des autres, quel que
        soit l'ordre de focus/ouverture (self.windows) — l'ordre relatif
        NORMAL est conservé À L'INTÉRIEUR de chaque groupe (épinglées entre
        elles, non-épinglées entre elles). Utilisé par draw() et
        _topmost_at() pour que ce qui est visuellement au-dessus soit aussi
        ce qui reçoit le clic."""
        return [w for w in self.windows if not w.pinned] + [w for w in self.windows if w.pinned]

    # --------------------------------------------------------------- ouverture
    def open(self, key, factory, x=None, y=None):
        """Ouvre (ou ramène au premier plan) la fenêtre d'app `key`. `factory`
        est un callable renvoyant une instance `DesktopApp` (appelé seulement
        si la fenêtre n'existe pas encore)."""
        for w in self.windows:
            if w.key == key:
                w.minimized = False
                self.focus(w)
                return w
        app_obj = factory()
        dw, dh = getattr(app_obj, "default_size", (760, 480))
        # placement en cascade pour ne pas empiler pile au même endroit
        n = len(self.windows)
        px = 60 + (n % 5) * 34 if x is None else x
        py = 54 + (n % 5) * 30 if y is None else y
        dw = min(dw, config.SCREEN_WIDTH - px - 20)
        dh = min(dh, config.SCREEN_HEIGHT - py - 60)
        w = Window(key, app_obj, px, py, dw, dh)
        self.windows.append(w)
        if hasattr(app_obj, "on_open"):
            app_obj.on_open()
        return w

    def close(self, w):
        if w in self.windows:
            if self.on_close is not None:
                self.on_close(w)
            self.windows.remove(w)

    def focus(self, w):
        if w in self.windows:
            w.attention = False   # prendre le focus éteint le clignotement
            if self.windows[-1] is not w:
                self.windows.remove(w)
                self.windows.append(w)

    def toggle_minimize(self, w):
        w.minimized = not w.minimized

    @property
    def focused(self):
        for w in reversed(self.windows):
            if not w.minimized:
                return w
        return None

    def open_windows(self):
        return [w for w in self.windows if not w.minimized]

    def cycle_focus(self, reverse=False):
        """Alt+Tab : passe à la fenêtre suivante (round-robin déterministe,
        trié par clé — pas par ordre de focus récent, pour un cycle complet
        et prévisible même avec beaucoup de fenêtres ouvertes)."""
        visible = self.open_windows()
        if len(visible) < 2:
            return
        order = sorted(visible, key=lambda w: w.key)
        cur = self.focused
        i = order.index(cur) if cur in order else 0
        ni = (i - 1) % len(order) if reverse else (i + 1) % len(order)
        self.focus(order[ni])

    # --------------------------------------------------------------- évènements
    def _topmost_at(self, pos):
        for w in reversed(self._z_order()):
            if not w.minimized and w.rect.collidepoint(pos):
                return w
        return None

    def handle_event(self, event):
        """Route un évènement. Retourne True s'il a été consommé par une
        fenêtre (chrome ou application), False s'il « traverse » vers le
        bureau (clic sur le fond, etc.)."""
        # déplacement / redimensionnement en cours : on suit la souris
        if event.type == pygame.MOUSEMOTION:
            drag = self._active_drag()
            if drag is not None:
                self._apply_drag(drag, event.pos)
                return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            drag = self._active_drag()
            if drag is not None:
                was_moving = drag._drag_off is not None
                drag._drag_off = None
                drag._resizing = False
                # relâché sur une zone d'ancrage -> on y colle la fenêtre
                if was_moving and self._snap_preview is not None:
                    self.dock(drag, self._snap_preview)
                self._snap_preview = None
                return True
            # Aucune fenêtre du BUREAU n'est en train d'être glissée, mais
            # l'appli focalisée peut avoir son PROPRE état de glisser en cours
            # (ex. un popup de données ou la calculatrice déplacés À
            # L'INTÉRIEUR d'une scène hébergée, cf. ui/datawindow.py/
            # ui/calculator.py) : sans cette transmission, le MOUSEBUTTONUP ne
            # lui parvient jamais (seul MOUSEMOTION est routé plus bas), donc
            # son drapeau `dragging` ne repasse jamais à False — le popup
            # reste « collé » à la souris indéfiniment (bug corrigé ici).
            w = self.focused
            if w is not None:
                return bool(w.app_obj.handle_event(event, w.content_rect))
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            w = self._topmost_at(event.pos)
            if w is None:
                return False
            self.focus(w)
            if w.close_rect.collidepoint(event.pos):
                self.close(w)
                return True
            if w.min_rect.collidepoint(event.pos):
                self.toggle_minimize(w)
                return True
            if w.resize_rect.collidepoint(event.pos):
                w._resizing = True
                return True
            if w.title_rect.collidepoint(event.pos):
                # double-clic sur la barre de titre = maximiser / restaurer
                now = pygame.time.get_ticks()
                lw, lt = self._last_title_click
                if lw is w and now - lt < 400:
                    self.maximize_toggle(w)
                    self._last_title_click = (None, -10000)
                    return True
                self._last_title_click = (w, now)
                w._drag_off = (event.pos[0] - w.rect.x, event.pos[1] - w.rect.y)
                return True
            # sinon : clic dans le contenu → application. Le clic est de toute
            # façon dans le rectangle de la fenêtre : il ne doit JAMAIS
            # « traverser » vers le bureau (icônes/barre des tâches) derrière,
            # que l'appli fasse quelque chose de ce clic ou non.
            w.app_obj.handle_event(event, w.content_rect)
            return True

        # molette / autres clics souris : à la fenêtre sous le curseur (même
        # règle : absorbés dès qu'ils tombent dans une fenêtre)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (3, 4, 5):
            w = self._topmost_at(event.pos)
            if w is not None:
                w.app_obj.handle_event(event, w.content_rect)
                return True
            return False

        # clavier et mouvements : à la fenêtre focalisée
        if event.type in (pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEMOTION):
            w = self.focused
            if w is not None:
                return bool(w.app_obj.handle_event(event, w.content_rect))
        return False

    def _active_drag(self):
        for w in self.windows:
            if w._drag_off is not None or w._resizing:
                return w
        return None

    def _apply_drag(self, w, pos):
        if w._resizing:
            min_w, min_h = getattr(w.app_obj, "min_size", (300, 200))
            w.rect.w = max(min_w, pos[0] - w.rect.x + RESIZE_GRIP // 2)
            w.rect.h = max(min_h, pos[1] - w.rect.y + RESIZE_GRIP // 2)
            w.rect.w = min(w.rect.w, config.SCREEN_WIDTH - w.rect.x)
        elif w._drag_off is not None:
            nx = pos[0] - w._drag_off[0]
            ny = pos[1] - w._drag_off[1]
            # garde la barre de titre attrapable à l'écran
            nx = max(-w.rect.w + 80, min(config.SCREEN_WIDTH - 80, nx))
            ny = max(config.TOPBAR_H, min(config.SCREEN_HEIGHT - TITLE_H, ny))
            w.rect.topleft = (nx, ny)
            # aperçu d'ancrage si le curseur touche un bord de la zone de travail
            self._snap_preview = self._snap_target(pos)

    EDGE = 16
    CORNER = 40   # zone de coin plus large que EDGE : un coin exact (16x16) serait
                  # quasi impossible à viser à la souris sur un écran de cette taille

    def _quarter_rect(self, side):
        """Rect d'un quart de `work_area` : side = "tl"/"tr"/"bl"/"br"."""
        wa = self.work_area
        half_w, half_h = wa.w // 2, wa.h // 2
        x = wa.x if side[1] == "l" else wa.x + half_w
        y = wa.y if side[0] == "t" else wa.y + half_h
        w = half_w if side[1] == "l" else wa.w - half_w
        h = half_h if side[0] == "t" else wa.h - half_h
        return pygame.Rect(x, y, w, h)

    def _snap_target(self, pos):
        """Zone d'ancrage selon la position du curseur près d'un bord (ou
        coin) de la `work_area` : un COIN = quart d'écran (poste à 4
        fenêtres ouvertes en permanence — marché/portefeuille/tableur/
        watchlist) ; bord haut seul = maximiser ; gauche/droite seuls =
        moitié d'écran (comportement historique, inchangé hors des coins)."""
        wa = self.work_area
        mx, my = pos
        near_top = my <= wa.y + self.CORNER
        near_bottom = my >= wa.bottom - self.CORNER
        near_left = mx <= wa.x + self.CORNER
        near_right = mx >= wa.right - self.CORNER
        if near_top and near_left:
            return self._quarter_rect("tl")
        if near_top and near_right:
            return self._quarter_rect("tr")
        if near_bottom and near_left:
            return self._quarter_rect("bl")
        if near_bottom and near_right:
            return self._quarter_rect("br")
        if my <= wa.y + self.EDGE:
            return wa.copy()
        if mx <= wa.x + self.EDGE:
            return pygame.Rect(wa.x, wa.y, wa.w // 2, wa.h)
        if mx >= wa.right - self.EDGE:
            return pygame.Rect(wa.x + wa.w // 2, wa.y, wa.w - wa.w // 2, wa.h)
        return None

    def maximize_toggle(self, w):
        """Maximise la fenêtre sur la zone de travail, ou la restaure si elle
        l'est déjà (double-clic sur la barre de titre)."""
        if w.rect == self.work_area and w._restore_rect is not None:
            w.rect = w._restore_rect.copy()
            w._restore_rect = None
        else:
            w._restore_rect = w.rect.copy()
            w.rect = self.work_area.copy()
        self._dock_feedback(w)

    def dock(self, w, rect):
        """Ancre `w` sur `rect` (moitié d'écran, plein écran…), en gardant
        `_restore_rect` pour revenir en arrière — utilisé aussi bien par le
        glisser-vers-le-bord (`handle_event`) que par le menu contextuel
        (`scene_desktop_menus._snap_window`), pour un seul point de vérité sur
        le feedback (son + liseré pulsé)."""
        if w._restore_rect is None:
            w._restore_rect = w.rect.copy()
        w.rect = rect.copy()
        self._dock_feedback(w)

    def _dock_feedback(self, w):
        audio.play("snap")
        w._dock_flash_until = pygame.time.get_ticks() + DOCK_FLASH_MS

    # --------------------------------------------------------------- cycle
    def update(self, dt):
        for w in self.windows:
            if not w.minimized and hasattr(w.app_obj, "update"):
                w.app_obj.update(dt)

    def draw(self, surf):
        # aperçu d'ancrage (sous les fenêtres) pendant un glisser vers un bord
        if self._snap_preview is not None:
            overlay = pygame.Surface((self._snap_preview.w, self._snap_preview.h), pygame.SRCALPHA)
            overlay.fill((*config.COL_CYAN, 40))
            surf.blit(overlay, self._snap_preview.topleft)
            pygame.draw.rect(surf, config.COL_CYAN, self._snap_preview, 2)
        focused = self.focused
        for w in self._z_order():
            if not w.minimized:
                w.draw(surf, w is focused)
