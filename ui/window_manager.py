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

from core import config
from ui import desktop_icons, fonts, widgets

TITLE_H = 26          # hauteur de la barre de titre
BORDER = 2            # épaisseur du liseré de fenêtre
RESIZE_GRIP = 14      # taille de la poignée de redimensionnement (coin bas-droit)
BTN_W = TITLE_H       # boutons carrés dans la barre de titre


class Window:
    """Une fenêtre du bureau : chrome + une application `DesktopApp`."""

    def __init__(self, key, app_obj, x, y, w, h):
        self.key = key            # identifiant d'app (unique : une fenêtre par app)
        self.app_obj = app_obj    # instance DesktopApp
        self.rect = pygame.Rect(x, y, w, h)
        self.minimized = False
        self._drag_off = None     # (dx, dy) pendant un déplacement
        self._resizing = False    # redimensionnement en cours

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
        # barre de titre
        tr = self.title_rect
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if focused else config.COL_PANEL, tr)
        pygame.draw.line(surf, accent, (tr.x, tr.bottom - 1), (tr.right, tr.bottom - 1), 1)
        icon_kind = getattr(self.app_obj, "icon_kind", "generic")
        icon_col = config.COL_AMBER if focused else config.COL_TEXT_DIM
        desktop_icons.draw(surf, (tr.x + 18, tr.centery), icon_kind, icon_col)
        widgets.draw_text(surf, self.app_obj.title, (tr.x + 32, tr.y + 5),
                          fonts.small(bold=True), icon_col)
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
            self.windows.remove(w)

    def focus(self, w):
        if w in self.windows and self.windows[-1] is not w:
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

    # --------------------------------------------------------------- évènements
    def _topmost_at(self, pos):
        for w in reversed(self.windows):
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
                drag._drag_off = None
                drag._resizing = False
                return True

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
                w._drag_off = (event.pos[0] - w.rect.x, event.pos[1] - w.rect.y)
                return True
            # sinon : clic dans le contenu → application
            return bool(w.app_obj.handle_event(event, w.content_rect))

        # molette / autres clics souris : à la fenêtre sous le curseur
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (3, 4, 5):
            w = self._topmost_at(event.pos)
            if w is not None:
                return bool(w.app_obj.handle_event(event, w.content_rect))
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

    # --------------------------------------------------------------- cycle
    def update(self, dt):
        for w in self.windows:
            if not w.minimized and hasattr(w.app_obj, "update"):
                w.app_obj.update(dt)

    def draw(self, surf):
        focused = self.focused
        for w in self.windows:
            if not w.minimized:
                w.draw(surf, w is focused)
