"""
scene_spreadsheet.py — Tableur intégré (type Excel).
Grille de cellules cliquables, barre de formule, édition au clavier.
Affiche valeurs calculées dans la grille, formule brute dans la barre.
Pré-rempli avec un mini-modèle DCF pour illustrer l'usage.
"""
import pygame

from core import config
from core.scene_manager import Scene
from core.spreadsheet_engine import Spreadsheet, idx_to_col
from ui import fonts, widgets

CELL_W = 138
CELL_H = 26
HEAD_W = 44       # largeur colonne des numéros de ligne
GRID_X = 40
GRID_Y = 172
N_COLS = 8
N_ROWS = 13


class SpreadsheetScene(Scene):
    def on_enter(self, **kwargs):
        self.return_to = kwargs.get("return_to", "terminal")
        # réutilise le tableur stocké dans l'app (persistant entre visites)
        if not hasattr(self.app, "sheet") or self.app.sheet is None:
            self.app.sheet = Spreadsheet(N_ROWS, N_COLS)
            self._seed_demo(self.app.sheet)
        self.sheet = self.app.sheet
        self.sel = "A1"
        self.editing = False
        self.edit_buf = ""
        self.back_btn = widgets.Button(
            config.back_button_rect(180), f"← {self.return_to.upper()}", config.COL_TEXT_DIM)
        self.clear_btn = widgets.Button(
            (config.SCREEN_WIDTH-220, config.SCREEN_HEIGHT-50, 180, 42),
            "TOUT EFFACER", config.COL_DOWN)
        self.tuto_btn = widgets.Button(
            (230, config.SCREEN_HEIGHT-50, 150, 42), "📘 TUTO", config.COL_CYAN)

    def _seed_demo(self, s):
        """Mini-modèle DCF pour montrer l'outil."""
        s.set("A1", "DCF DEMO")
        s.set("A2", "Annee");   s.set("B2", "1"); s.set("C2", "2")
        s.set("D2", "3"); s.set("E2", "4"); s.set("F2", "5")
        s.set("A3", "FCF")
        s.set("B3", "100"); s.set("C3", "110"); s.set("D3", "121")
        s.set("E3", "133"); s.set("F3", "146")
        s.set("A5", "WACC"); s.set("B5", "0.10")
        s.set("A6", "Croiss. term."); s.set("B6", "0.025")
        s.set("A8", "VA FCF")
        s.set("B8", "=B3/POWER(1+B5,1)")
        s.set("C8", "=C3/POWER(1+B5,2)")
        s.set("D8", "=D3/POWER(1+B5,3)")
        s.set("E8", "=E3/POWER(1+B5,4)")
        s.set("F8", "=F3/POWER(1+B5,5)")
        s.set("A9", "Somme VA"); s.set("B9", "=SUM(B8:F8)")
        s.set("A10", "Val. terminale")
        s.set("B10", "=F3*(1+B6)/(B5-B6)")
        s.set("A11", "VA val. term.")
        s.set("B11", "=B10/POWER(1+B5,5)")
        s.set("A12", "ENTERPRISE VALUE")
        s.set("B12", "=B9+B11")

    # ----------------------------------------------------------------- events
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if self.editing:
                if event.key == pygame.K_RETURN:
                    self.sheet.set(self.sel, self.edit_buf)
                    self.editing = False
                    self._move(0, 1)
                elif event.key == pygame.K_ESCAPE:
                    self.editing = False
                elif event.key == pygame.K_BACKSPACE:
                    self.edit_buf = self.edit_buf[:-1]
                elif event.unicode and event.unicode.isprintable():
                    self.edit_buf += event.unicode
            else:
                if event.key == pygame.K_ESCAPE:
                    self.app.scenes.go(self.return_to)
                elif event.key in (pygame.K_RETURN, pygame.K_F2):
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
                    # commence l'édition directement
                    self.editing = True
                    self.edit_buf = event.unicode

        if self.back_btn.handle(event):
            self.app.scenes.go(self.return_to)
        if self.clear_btn.handle(event):
            self.app.sheet = Spreadsheet(N_ROWS, N_COLS)
            self.sheet = self.app.sheet
            self.editing = False
        if self.tuto_btn.handle(event):
            self.app.scenes.go("tutorials", tid="spreadsheet", return_to="spreadsheet")
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            ref = self._cell_at(event.pos)
            if ref:
                if self.editing:
                    self.sheet.set(self.sel, self.edit_buf)
                    self.editing = False
                self.sel = ref

    def _move(self, dc, dr):
        col = ord(self.sel[0]) - ord('A')
        row = int(self.sel[1:])
        col = max(0, min(N_COLS - 1, col + dc))
        row = max(1, min(N_ROWS, row + dr))
        self.sel = f"{chr(ord('A')+col)}{row}"

    def _cell_at(self, pos):
        x, y = pos
        gx = GRID_X + HEAD_W
        gy = GRID_Y + CELL_H
        if x < gx or y < gy:
            return None
        col = (x - gx) // CELL_W
        row = (y - gy) // CELL_H + 1
        if 0 <= col < N_COLS and 1 <= row <= N_ROWS:
            return f"{idx_to_col(col)}{row}"
        return None

    def update(self, dt):
        mp = pygame.mouse.get_pos()
        self.back_btn.update(mp)
        self.clear_btn.update(mp)
        self.tuto_btn.update(mp)

    # ------------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill(config.COL_BG)
        widgets.draw_text(surf, "TABLEUR INTÉGRÉ", (40, 24),
                          fonts.title(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, "Clic = sélectionner · Entrée/F2 = éditer · =formule (SUM, NPV, IRR, "
                                "POWER, IF...) · flèches = naviguer",
                          (42, 76), fonts.small(), config.COL_TEXT_DIM)

        self._draw_formula_bar(surf)
        self._draw_grid(surf)
        self._draw_help(surf)
        self.back_btn.draw(surf)
        self.clear_btn.draw(surf)
        self.tuto_btn.draw(surf)

    def _draw_formula_bar(self, surf):
        bar = pygame.Rect(40, 110, config.SCREEN_WIDTH-80, 56)
        widgets.draw_panel(surf, bar)
        widgets.draw_text(surf, self.sel, (bar.x+12, bar.y+18),
                          fonts.head(bold=True), config.COL_CYAN)
        # contenu : tampon d'édition ou formule brute
        content = self.edit_buf if self.editing else self.sheet.get_raw(self.sel)
        cursor = "_" if self.editing and pygame.time.get_ticks() % 1000 < 500 else ""
        widgets.draw_text(surf, "fx", (bar.x+70, bar.y+22), fonts.small(bold=True),
                          config.COL_TEXT_DIM)
        widgets.draw_text(surf, f"{content}{cursor}", (bar.x+100, bar.y+18),
                          fonts.body(), config.COL_WHITE)
        # valeur calculée à droite
        val = self.sheet.get_value(self.sel)
        vstr = self._fmt(val)
        widgets.draw_text(surf, f"= {vstr}", (bar.right-20, bar.y+18),
                          fonts.body(bold=True), config.COL_AMBER, align="right")

    def _draw_grid(self, surf):
        # en-têtes de colonnes
        for c in range(N_COLS):
            x = GRID_X + HEAD_W + c*CELL_W
            rect = pygame.Rect(x, GRID_Y, CELL_W, CELL_H)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, rect)
            pygame.draw.rect(surf, config.COL_BORDER, rect, 1)
            img = fonts.small(bold=True).render(idx_to_col(c), True, config.COL_AMBER)
            surf.blit(img, img.get_rect(center=rect.center))
        # coin
        corner = pygame.Rect(GRID_X, GRID_Y, HEAD_W, CELL_H)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, corner)
        pygame.draw.rect(surf, config.COL_BORDER, corner, 1)

        # lignes
        for r in range(1, N_ROWS+1):
            y = GRID_Y + r*CELL_H
            # numéro de ligne
            hrect = pygame.Rect(GRID_X, y, HEAD_W, CELL_H)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD, hrect)
            pygame.draw.rect(surf, config.COL_BORDER, hrect, 1)
            img = fonts.small().render(str(r), True, config.COL_TEXT_DIM)
            surf.blit(img, img.get_rect(center=hrect.center))
            # cellules
            for c in range(N_COLS):
                ref = f"{idx_to_col(c)}{r}"
                x = GRID_X + HEAD_W + c*CELL_W
                rect = pygame.Rect(x, y, CELL_W, CELL_H)
                selected = (ref == self.sel)
                bg = config.COL_PANEL_HEAD if selected else config.COL_PANEL
                pygame.draw.rect(surf, bg, rect)
                pygame.draw.rect(surf, config.COL_CYAN if selected else config.COL_GRID,
                                 rect, 2 if selected else 1)
                raw = self.sheet.get_raw(ref)
                if raw != "":
                    val = self.sheet.get_value(ref)
                    text = self._fmt(val)
                    is_num = isinstance(val, (int, float)) and not isinstance(val, bool)
                    col = config.COL_WHITE if is_num else config.COL_TEXT
                    if isinstance(val, str) and val.startswith("#"):
                        col = config.COL_DOWN
                    # nombres alignés à droite, texte à gauche
                    if is_num:
                        widgets.draw_text(surf, text, (rect.right-6, rect.y+5),
                                          fonts.small(), col, align="right")
                    else:
                        widgets.draw_text(surf, text[:14], (rect.x+5, rect.y+5),
                                          fonts.small(), col)

    def _draw_help(self, surf):
        y = GRID_Y + (N_ROWS+1)*CELL_H + 16
        panel = pygame.Rect(40, y, config.SCREEN_WIDTH-80, 90)
        inner = widgets.draw_panel(surf, panel, "Modèle pré-chargé : DCF", config.COL_UP)
        widgets.draw_text(surf, "Cellule B12 = Enterprise Value calculée par DCF. "
                                "Modifiez B5 (WACC) ou B6 (croissance) et voyez la valeur changer.",
                          (inner.x, inner.y), fonts.small(), config.COL_TEXT)
        ev = self.sheet.get_value("B12")
        widgets.draw_text(surf, f"Enterprise Value actuelle : {self._fmt(ev)}",
                          (inner.x, inner.y+28), fonts.body(bold=True), config.COL_AMBER)

    def _fmt(self, val):
        if isinstance(val, bool):
            return "VRAI" if val else "FAUX"
        if isinstance(val, (int, float)):
            if abs(val) >= 1000:
                return f"{val:,.2f}"
            return f"{val:.4g}"
        return str(val)
