"""
app_sheet.py — Application « Tableur » du bureau (type Excel, cellules libres).

Grille de cellules éditables avec barre de formule et moteur de calcul complet
(`=A1*B2`, SUM, NPV, IRR, POWER, IF…). Réutilise `core/spreadsheet_engine`
(le même moteur que la scène tableur historique) et PARTAGE `app.sheet`, si
bien que le classeur est le même que celui exporté depuis un état financier.
Feuille vierge par défaut : un vrai bac à sable pour les calculs du joueur.
"""
import pygame

from apps.base import DesktopApp
from core import config
from core.spreadsheet_engine import Spreadsheet, idx_to_col
from ui import fonts, widgets

N_ROWS = 24
N_COLS = 10
CELL_W = 92
CELL_H = 20
HEAD_W = 34
FORMULA_H = 30


class SheetApp(DesktopApp):
    title = "Tableur"
    icon = "▦"
    default_size = (720, 460)
    min_size = (420, 260)

    def on_open(self):
        if not getattr(self.app, "sheet", None):
            self.app.sheet = Spreadsheet(N_ROWS, N_COLS)
        self.sheet = self.app.sheet
        self.sel = "A1"
        self.editing = False
        self.edit_buf = ""
        self.scroll_y = 0
        self._grid_origin = None   # (x, y) du coin haut-gauche des cellules
        self._cell_rects = {}

    # --------------------------------------------------------------- helpers
    def _move(self, dc, dr):
        col = max(0, min(N_COLS - 1, (ord(self.sel[0]) - ord('A')) + dc))
        row = max(1, min(N_ROWS, int(self.sel[1:]) + dr))
        self.sel = f"{chr(ord('A') + col)}{row}"

    def _commit(self):
        if self.editing:
            self.sheet.set(self.sel, self.edit_buf)
            self.editing = False

    def _fmt(self, val):
        if isinstance(val, bool):
            return "VRAI" if val else "FAUX"
        if isinstance(val, (int, float)):
            return f"{val:,.2f}" if abs(val) >= 1000 else f"{val:.4g}"
        return str(val)

    # --------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            self.scroll_y = max(0, self.scroll_y + (-1 if event.button == 4 else 1))
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for ref, r in self._cell_rects.items():
                if r.collidepoint(event.pos):
                    self._commit()
                    self.sel = ref
                    return True
            return False
        if event.type == pygame.KEYDOWN:
            if self.editing:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._commit()
                    self._move(0, 1)
                elif event.key == pygame.K_ESCAPE:
                    self.editing = False
                elif event.key == pygame.K_BACKSPACE:
                    self.edit_buf = self.edit_buf[:-1]
                elif event.unicode and event.unicode.isprintable():
                    self.edit_buf += event.unicode
                return True
            else:
                if event.key in (pygame.K_RETURN, pygame.K_F2):
                    self.editing = True
                    self.edit_buf = self.sheet.get_raw(self.sel)
                elif event.key == pygame.K_BACKSPACE:
                    self.sheet.set(self.sel, "")
                elif event.key == pygame.K_UP:
                    self._move(0, -1)
                elif event.key == pygame.K_DOWN:
                    self._move(0, 1)
                elif event.key == pygame.K_LEFT:
                    self._move(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    self._move(1, 0)
                elif event.unicode and event.unicode.isprintable():
                    self.editing = True
                    self.edit_buf = event.unicode
                else:
                    return False
                self._ensure_visible()
                return True
        return False

    def _ensure_visible(self):
        row = int(self.sel[1:])
        vis = self._visible_rows()
        if row - 1 < self.scroll_y:
            self.scroll_y = row - 1
        elif row - 1 >= self.scroll_y + vis:
            self.scroll_y = row - vis
        self.scroll_y = max(0, min(self.scroll_y, N_ROWS - vis))

    def _visible_rows(self):
        if not self._grid_origin:
            return N_ROWS
        return max(1, (self._grid_bottom - self._grid_origin[1] - CELL_H) // CELL_H)

    # --------------------------------------------------------------- draw
    def draw(self, surf, rect):
        surf.fill(config.COL_PANEL, rect)
        pad = 8
        # barre de formule
        fr = pygame.Rect(rect.x + pad, rect.y + pad, rect.w - 2 * pad, FORMULA_H)
        pygame.draw.rect(surf, config.COL_BG, fr)
        pygame.draw.rect(surf, config.COL_BORDER, fr, 1)
        widgets.draw_text(surf, self.sel, (fr.x + 8, fr.y + 6), fonts.small(bold=True), config.COL_CYAN)
        widgets.draw_text(surf, "fx", (fr.x + 52, fr.y + 8), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        content = self.edit_buf if self.editing else self.sheet.get_raw(self.sel)
        cur = "_" if self.editing and pygame.time.get_ticks() % 1000 < 500 else ""
        widgets.draw_text(surf, widgets.fit_text(f"{content}{cur}", fonts.small(), rect.w - 220),
                          (fr.x + 76, fr.y + 6), fonts.small(), config.COL_WHITE)
        val = self.sheet.get_value(self.sel)
        widgets.draw_text(surf, f"= {self._fmt(val)}", (fr.right - 10, fr.y + 6),
                          fonts.small(bold=True), config.COL_AMBER, align="right")

        # grille
        gx = rect.x + pad
        gy = fr.bottom + 6
        self._grid_origin = (gx, gy)
        self._grid_bottom = rect.bottom - pad
        vis_rows = self._visible_rows()
        vis_cols = max(1, (rect.right - pad - gx - HEAD_W) // CELL_W)
        vis_cols = min(vis_cols, N_COLS)
        # en-têtes de colonnes
        for c in range(vis_cols):
            cr = pygame.Rect(gx + HEAD_W + c * CELL_W, gy, CELL_W, CELL_H)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, cr)
            pygame.draw.rect(surf, config.COL_BORDER, cr, 1)
            widgets.draw_text(surf, idx_to_col(c), cr.center, fonts.tiny(bold=True),
                              config.COL_AMBER, align="center")
        corner = pygame.Rect(gx, gy, HEAD_W, CELL_H)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, corner)
        pygame.draw.rect(surf, config.COL_BORDER, corner, 1)

        self._cell_rects = {}
        for vr in range(vis_rows):
            r = self.scroll_y + vr + 1
            if r > N_ROWS:
                break
            ry = gy + (vr + 1) * CELL_H
            hr = pygame.Rect(gx, ry, HEAD_W, CELL_H)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, hr)
            pygame.draw.rect(surf, config.COL_BORDER, hr, 1)
            widgets.draw_text(surf, str(r), hr.center, fonts.tiny(), config.COL_TEXT_DIM, align="center")
            for c in range(vis_cols):
                ref = f"{idx_to_col(c)}{r}"
                cell = pygame.Rect(gx + HEAD_W + c * CELL_W, ry, CELL_W, CELL_H)
                self._cell_rects[ref] = cell
                sel = (ref == self.sel)
                pygame.draw.rect(surf, config.COL_PANEL_HEAD if sel else config.COL_BG, cell)
                pygame.draw.rect(surf, config.COL_CYAN if sel else config.COL_GRID, cell, 2 if sel else 1)
                raw = self.sheet.get_raw(ref)
                if raw == "":
                    continue
                v = self.sheet.get_value(ref)
                is_num = isinstance(v, (int, float)) and not isinstance(v, bool)
                text = self._fmt(v)
                col = config.COL_WHITE if is_num else config.COL_TEXT
                if isinstance(v, str) and v.startswith("#"):
                    col = config.COL_DOWN
                if is_num:
                    widgets.draw_text(surf, widgets.fit_text(text, fonts.tiny(), CELL_W - 8),
                                      (cell.right - 4, cell.y + 3), fonts.tiny(), col, align="right")
                else:
                    widgets.draw_text(surf, widgets.fit_text(text, fonts.tiny(), CELL_W - 8),
                                      (cell.x + 4, cell.y + 3), fonts.tiny(), col)
