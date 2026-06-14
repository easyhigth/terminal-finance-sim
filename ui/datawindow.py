"""
datawindow.py — Fenêtre de données déplaçable (style Bloomberg).

Affiche un tableau (titre + colonnes + lignes) dans une fenêtre que l'on peut
déplacer par sa barre de titre et fermer via [x]. Plusieurs peuvent coexister ;
le terminal en gère une pile. Rendu en overlay au-dessus du terminal.

Usage :
    w = DataWindow("TOP — USA", ["Ticker", "Nom", "Capi"], rows, pos=(x, y))
    w.handle(event)  # gère drag + fermeture ; renvoie True si l'event est consommé
    w.draw(surf)
"""
import pygame
from core import config
from ui import fonts, widgets

TITLE_H = 24
ROW_H = 20
PAD = 10


class DataWindow:
    def __init__(self, title, columns, rows, pos=(120, 110), accent=config.COL_CYAN,
                 max_rows=18, chart=None):
        self.title = title
        self.columns = columns          # liste de (label, largeur px)
        self.rows = rows[:max_rows]      # liste de tuples (même longueur que columns)
        self.accent = accent
        self.chart = chart              # liste de valeurs (mode graphe) ou None
        self.dragging = False
        self.closed = False
        self.clicked_row = None       # index de ligne cliquée (consommé par le terminal)
        self._row_rects = {}          # index -> Rect (dernier rendu)
        self._drag_off = (0, 0)
        if chart is not None:
            w, h = 360, 200
        else:
            w = max(220, sum(c[1] for c in columns) + PAD * 2)
            h = TITLE_H + PAD + len(self.rows) * ROW_H + PAD + 16
        self.rect = pygame.Rect(pos[0], pos[1], w, h)

    # --------------------------------------------------------------- events
    def _title_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.w, TITLE_H)

    def _close_rect(self):
        return pygame.Rect(self.rect.right - TITLE_H, self.rect.y, TITLE_H, TITLE_H)

    def handle(self, event):
        """Retourne True si l'event est consommé (clic dans la fenêtre / drag)."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._close_rect().collidepoint(event.pos):
                self.closed = True
                return True
            if self._title_rect().collidepoint(event.pos):
                self.dragging = True
                self._drag_off = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
                return True
            for idx, rr in self._row_rects.items():
                if rr.collidepoint(event.pos):
                    self.clicked_row = idx
                    return True
            if self.rect.collidepoint(event.pos):
                return True            # clic dans le corps : consommé (focus)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            mx, my = event.pos
            self.rect.x = max(0, min(config.SCREEN_WIDTH - self.rect.w,
                                     mx - self._drag_off[0]))
            self.rect.y = max(config.TOPBAR_H, min(config.SCREEN_HEIGHT - 40,
                                                   my - self._drag_off[1]))
            return True
        return False

    # ----------------------------------------------------------------- draw
    def draw(self, surf):
        # ombre + corps
        pygame.draw.rect(surf, (0, 0, 0), self.rect.move(0, 3), border_radius=5)
        pygame.draw.rect(surf, config.COL_PANEL, self.rect, border_radius=5)
        pygame.draw.rect(surf, self.accent, self.rect, 1, border_radius=5)
        # barre de titre
        tr = self._title_rect()
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, tr,
                         border_top_left_radius=5, border_top_right_radius=5)
        widgets.draw_text(surf, self.title, (tr.x + 8, tr.y + 5),
                          fonts.small(bold=True), self.accent)
        # bouton fermer
        cr = self._close_rect()
        widgets.draw_text(surf, "✕", (cr.centerx, cr.y + 5), fonts.small(bold=True),
                          config.COL_TEXT_DIM, align="center")
        # mode graphe
        if self.chart is not None:
            area = pygame.Rect(self.rect.x + PAD, tr.bottom + 14,
                               self.rect.w - 2 * PAD, self.rect.h - TITLE_H - 48)
            vals = self.chart
            if len(vals) >= 2:
                col = config.COL_UP if vals[-1] >= vals[0] else config.COL_DOWN
                widgets.draw_series(surf, area, vals, col, baseline=True)
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
        x0 = self.rect.x + PAD
        y = tr.bottom + 6
        cx = x0
        for label, w in self.columns:
            widgets.draw_text(surf, label, (cx, y), fonts.tiny(bold=True), config.COL_TEXT_DIM)
            cx += w
        y += 18
        pygame.draw.line(surf, config.COL_BORDER, (x0, y - 2),
                         (self.rect.right - PAD, y - 2), 1)
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
