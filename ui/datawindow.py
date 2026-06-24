"""
datawindow.py — Fenêtre de données déplaçable (style Bloomberg).

Affiche un tableau (titre + colonnes + lignes) ou un graphe dans une fenêtre
que l'on peut déplacer par sa barre de titre, réduire (▾/▸) et redimensionner
(poignée en bas à droite, si `resizable=True`) et fermer via [x]. Plusieurs
peuvent coexister ; chaque scène en gère une pile. Rendu en overlay au-dessus
de la scène.

Usage :
    w = DataWindow("TOP — USA", ["Ticker", "Nom", "Capi"], rows, pos=(x, y))
    w.handle(event)  # gère drag/resize/minimize/fermeture ; True si consommé
    w.draw(surf)

Sous-classement (voir ui/popups.py) : surcharger `_handle_body(pos)` pour les
clics spécifiques au contenu, et `draw()` pour le rendu (en appelant d'abord
`self._draw_chrome(surf)`, qui renvoie le rect de contenu, ou None si réduite).
"""
import pygame

from core import config
from ui import fonts, widgets

TITLE_H = 24
ROW_H = 20
PAD = 10
RESIZE_GRIP = 14


class DataWindow:
    def __init__(self, title, columns, rows, pos=(120, 110), accent=config.COL_CYAN,
                 max_rows=18, chart=None, resizable=False, minimizable=True,
                 size=None, min_size=(220, 120)):
        self.title = title
        self.columns = columns          # liste de (label, largeur px)
        self.rows = rows[:max_rows]      # liste de tuples (même longueur que columns)
        self.accent = accent
        self.chart = chart              # liste de valeurs (mode graphe) ou None
        self._chart_area = None         # zone de tracé du graphe (mode chart), pour la sync entre fenêtres
        self.resizable = resizable
        self.minimizable = minimizable
        self.minimized = False
        self.min_w, self.min_h = min_size
        self.dragging = False
        self._resizing = False
        self.closed = False
        self.clicked_row = None       # index de ligne cliquée (consommé par l'appelant)
        self._row_rects = {}          # index -> Rect (dernier rendu)
        self._drag_off = (0, 0)
        self._resize_off = (0, 0)
        if size is not None:
            w, h = size
        elif chart is not None:
            w, h = 440, 280
        else:
            w = max(220, sum(c[1] for c in columns) + PAD * 2)
            h = TITLE_H + PAD + len(self.rows) * ROW_H + PAD + 16
        self.rect = pygame.Rect(pos[0], pos[1], w, h)
        self._full_h = self.rect.h    # hauteur restaurée après réduction

    # --------------------------------------------------------------- events
    def _title_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.w, TITLE_H)

    def _close_rect(self):
        return pygame.Rect(self.rect.right - TITLE_H, self.rect.y, TITLE_H, TITLE_H)

    def _min_rect(self):
        return pygame.Rect(self.rect.right - TITLE_H * 2, self.rect.y, TITLE_H, TITLE_H)

    def _resize_rect(self):
        return pygame.Rect(self.rect.right - RESIZE_GRIP, self.rect.bottom - RESIZE_GRIP,
                           RESIZE_GRIP, RESIZE_GRIP)

    def handle(self, event):
        """Retourne True si l'event est consommé (clic dans la fenêtre / drag /
        redimensionnement / réduction)."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._close_rect().collidepoint(event.pos):
                self.closed = True
                return True
            if self.minimizable and self._min_rect().collidepoint(event.pos):
                self.minimized = not self.minimized
                if self.minimized:
                    self._full_h = self.rect.h
                    self.rect.h = TITLE_H
                else:
                    self.rect.h = self._full_h
                return True
            if self.resizable and not self.minimized and self._resize_rect().collidepoint(event.pos):
                self._resizing = True
                self._resize_off = (event.pos[0] - self.rect.right, event.pos[1] - self.rect.bottom)
                return True
            if self._title_rect().collidepoint(event.pos):
                self.dragging = True
                self._drag_off = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
                return True
            if not self.minimized and self.rect.collidepoint(event.pos):
                self._handle_body(event.pos)
                return True            # clic dans le corps : consommé (focus)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                return True
            if self._resizing:
                self._resizing = False
                return True
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                mx, my = event.pos
                self.rect.x = max(0, min(config.SCREEN_WIDTH - self.rect.w,
                                         mx - self._drag_off[0]))
                self.rect.y = max(config.TOPBAR_H, min(config.SCREEN_HEIGHT - 40,
                                                       my - self._drag_off[1]))
                return True
            if self._resizing:
                mx, my = event.pos
                new_right = mx - self._resize_off[0]
                new_bottom = my - self._resize_off[1]
                self.rect.w = max(self.min_w, min(new_right, config.SCREEN_WIDTH - 4) - self.rect.x)
                self.rect.h = max(self.min_h, min(new_bottom, config.SCREEN_HEIGHT - 4) - self.rect.y)
                self._full_h = self.rect.h
                return True
        return False

    def _handle_body(self, pos):
        """Hook : clic dans le corps de la fenêtre (hors chrome). Les sous-classes
        surchargent ceci pour leurs propres zones cliquables (onglets, liens…)."""
        for idx, rr in self._row_rects.items():
            if rr.collidepoint(pos):
                self.clicked_row = idx
                return True
        return False

    # ----------------------------------------------------------------- draw
    def _draw_chrome(self, surf):
        """Dessine l'ombre, le corps, la bordure et la barre de titre (titre,
        bouton réduire, bouton fermer, poignée de redimensionnement).
        Retourne le Rect de contenu disponible, ou None si la fenêtre est réduite."""
        pygame.draw.rect(surf, (0, 0, 0), self.rect.move(0, 3), border_radius=5)
        pygame.draw.rect(surf, config.COL_PANEL, self.rect, border_radius=5)
        pygame.draw.rect(surf, self.accent, self.rect, 1, border_radius=5)
        tr = self._title_rect()
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, tr,
                         border_top_left_radius=5, border_top_right_radius=5,
                         border_bottom_left_radius=5 if self.minimized else 0,
                         border_bottom_right_radius=5 if self.minimized else 0)
        n_btn = 2 if self.minimizable else 1
        title_font = fonts.small(bold=True)
        title_w = self.rect.w - TITLE_H * n_btn - 8
        title_truncated = title_font.size(self.title)[0] > title_w
        widgets.draw_text(surf, widgets.fit_text(self.title, title_font, title_w),
                          (tr.x + 8, tr.y + 5), title_font, self.accent)
        cr = self._close_rect()
        widgets.draw_text(surf, "✕", (cr.centerx, cr.y + 5), fonts.small(bold=True),
                          config.COL_TEXT_DIM, align="center")
        if self.minimizable:
            mr = self._min_rect()
            sym = "▸" if self.minimized else "▾"
            widgets.draw_text(surf, sym, (mr.centerx, mr.y + 5), fonts.small(bold=True),
                              config.COL_TEXT_DIM, align="center")
        if title_truncated:
            title_rect = pygame.Rect(tr.x, tr.y, title_w + 8, tr.h)
            mp = pygame.mouse.get_pos()
            if title_rect.collidepoint(mp):
                widgets.draw_tooltip(surf, self.title, mp)
        if self.minimized:
            return None
        if self.resizable:
            rr = self._resize_rect()
            for dx in (0, 4):
                pygame.draw.line(surf, config.COL_BORDER,
                                 (rr.x + dx, rr.bottom), (rr.right, rr.y + dx), 1)
        return pygame.Rect(self.rect.x + PAD, tr.bottom + 6,
                           self.rect.w - 2 * PAD, self.rect.h - TITLE_H - PAD - 6)

    def draw(self, surf):
        content = self._draw_chrome(surf)
        if content is None:
            return
        # mode graphe
        if self.chart is not None:
            area = pygame.Rect(content.x, content.y + 8, content.w, content.h - 46)
            self._chart_area = area
            vals = self.chart
            if len(vals) >= 2:
                col = config.COL_UP if vals[-1] >= vals[0] else config.COL_DOWN
                mp = pygame.mouse.get_pos()
                widgets.draw_series(surf, area, vals, col, baseline=True,
                                    mouse_pos=mp, y_fmt=lambda v: f"{v:,.0f}", show_pct=True)
                sync = widgets._hover_sync
                if (not area.collidepoint(mp) and sync["frac"] is not None
                        and sync["source"] != id(self)):
                    lo, hi = min(vals), max(vals)
                    span = (hi - lo) or 1.0
                    widgets.draw_chart_ghost(surf, area, vals, lo, span, sync["frac"],
                                             y_fmt=lambda v: f"{v:,.0f}")
                perf = (vals[-1] / vals[0] - 1) * 100 if vals[0] else 0.0
                widgets.draw_text(surf, f"{vals[-1]:,.0f}", (area.x, area.bottom + 6),
                                  fonts.small(bold=True), config.COL_WHITE)
                widgets.draw_text(surf, f"{'+' if perf>=0 else ''}{perf:.1f}%",
                                  (area.right, area.bottom + 6), fonts.small(bold=True),
                                  col, align="right")
                widgets.draw_text(surf, f"haut {max(vals):,.0f} · bas {min(vals):,.0f}",
                                  (area.x, area.bottom + 22), fonts.tiny(), config.COL_TEXT_DIM)
            else:
                widgets.draw_text(surf, "Historique insuffisant (avancez le temps).",
                                  (area.x, area.y), fonts.small(), config.COL_TEXT_DIM)
            return
        # en-têtes de colonnes
        x0 = content.x
        y = content.y
        cx = x0
        for label, w in self.columns:
            widgets.draw_text(surf, label, (cx, y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
            cx += w
        y += 18
        pygame.draw.line(surf, config.COL_BORDER, (x0, y - 2),
                         (content.right, y - 2), 1)
        # lignes
        self._row_rects = {}
        mp = pygame.mouse.get_pos()
        for ri, row in enumerate(self.rows):
            rr = pygame.Rect(self.rect.x + 2, y - 1, self.rect.w - 4, ROW_H)
            self._row_rects[ri] = rr
            if rr.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, rr)
            cx = x0
            for (label, w), cell in zip(self.columns, row):
                text, col = cell if isinstance(cell, tuple) else (cell, config.COL_TEXT)
                s = str(text)
                font = fonts.small()
                while font.size(s)[0] > w - 6 and len(s) > 3:
                    s = s[:-2]
                widgets.draw_text(surf, s, (cx, y), font, col)
                cx += w
            y += ROW_H
