"""
app_sheet.py — Application « Tableur » du bureau (type Excel, classeur multi-
feuilles, cellules libres).

Grille de cellules éditables avec barre de formule, onglets de feuilles (comme
Excel), moteur de calcul complet (`=A1*B2`, SUM, NPV, IRR, POWER, IF…) et,
façon Excel : un CATALOGUE DE FORMULES cliquable (bouton « fx », insère la
fonction sans avoir à en connaître le nom), une SÉLECTION DE PLAGE (glisser la
souris sur plusieurs cellules) et l'INSERTION DE GRAPHIQUES (ligne, barres,
nuage de points) à partir de la plage sélectionnée — l'usage courant d'Excel
en finance (modèle + graphe), sans macro/VBA.

Réutilise `core/spreadsheet_engine` et PARTAGE `app.workbook` (`core/workbook.py`),
si bien qu'un export depuis un état financier ou une fiche M&A arrive dans CE
classeur : la feuille ACTIVE si elle est vierge, sinon une NOUVELLE feuille —
jamais d'écrasement silencieux d'un modèle en cours (cf. `Workbook.import_financial`).
Feuille vierge par défaut : un vrai bac à sable pour les calculs du joueur.
"""
import pygame

from apps.base import DesktopApp
from core import config
from core.spreadsheet_engine import col_to_idx, idx_to_col
from core.workbook import SheetChart, Workbook
from ui import fonts, widgets

N_ROWS = 24
N_COLS = 10
CELL_W = 92
CELL_H = 20
HEAD_W = 34
FORMULA_H = 30
TAB_BAR_H = 22
TOOLBAR_H = 24
TAB_W = 108

# Catalogue de fonctions (façon « Insérer une fonction » d'Excel) — cliquer
# insère `NOM(` dans la formule en cours. Réutilise le catalogue réel du
# moteur (core/spreadsheet_engine.FUNCTIONS) : chaque entrée y existe bien.
FUNCTION_CATALOG = [
    ("Maths", [("SUM", "Somme"), ("ABS", "Valeur absolue"), ("SQRT", "Racine carrée"),
               ("POWER", "Puissance"), ("EXP", "Exponentielle"), ("LN", "Log népérien"),
               ("LOG", "Logarithme"), ("ROUND", "Arrondi")]),
    ("Statistiques", [("AVERAGE", "Moyenne"), ("MEDIAN", "Médiane"), ("MIN", "Minimum"),
                       ("MAX", "Maximum"), ("COUNT", "Nombre de valeurs"),
                       ("STDEV", "Écart-type"), ("VAR", "Variance"),
                       ("CORREL", "Corrélation (X;Y)")]),
    ("Finance", [("NPV", "Valeur actuelle nette"), ("IRR", "Taux de rendement interne"),
                 ("PMT", "Mensualité d'emprunt"), ("PV", "Valeur actuelle"),
                 ("FV", "Valeur future")]),
    ("Logique", [("IF", "Condition SI")]),
]

CHART_TYPES = [("line", "Ligne"), ("bar", "Barres"), ("scatter", "Nuage")]


def _split_ref(ref):
    i = 0
    while i < len(ref) and ref[i].isalpha():
        i += 1
    return col_to_idx(ref[:i]), int(ref[i:])


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class SheetApp(DesktopApp):
    title = "Tableur"
    icon_kind = "sheet"
    default_size = (760, 520)
    min_size = (460, 320)

    def on_open(self):
        if not getattr(self.app, "workbook", None):
            self.app.workbook = Workbook(N_ROWS, N_COLS)
        self.workbook = self.app.workbook
        self.sel = "A1"
        self.editing = False
        self.edit_buf = ""
        self.scroll_y = 0
        self.msg = ""
        self._grid_origin = None   # (x, y) du coin haut-gauche des cellules
        self._cell_rects = {}
        self._tab_rects = {}       # index -> Rect
        self._add_tab_rect = None
        # sélection de plage (glisser la souris) — pour SUM rapide et graphes
        self.range_anchor = None
        self.range_end = None
        self._dragging_range = False
        # catalogue de formules ("fx")
        self.fx_open = False
        self._fx_rect = None
        self._fx_item_rects = {}
        self._fx_panel_rect = None
        self._chart_btn_rects = {}
        # graphiques : glisser une fenêtre de graphe déjà posée sur la feuille
        self._chart_rects = {}
        self._chart_title_rects = {}
        self._chart_close_rects = {}
        self._chart_drag = None
        self._chart_drag_off = (0, 0)
        self._chart_resize = None
        self._chart_resize_rects = {}

    @property
    def sheet(self):
        return self.workbook.active.sheet

    # --------------------------------------------------------------- import
    def import_data(self, data):
        """Reçoit un export (état financier, fiche M&A…) : remplit la feuille
        active si vierge, sinon ouvre une nouvelle feuille (cf. Workbook)."""
        self.workbook.import_financial(data)
        self.sel = "A1"
        self.scroll_y = 0
        self.editing = False

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

    def _range_bounds(self):
        """(c1, c2, r1, r2) de la plage sélectionnée (glisser la souris),
        repli sur la cellule seule si aucune plage n'a été tracée."""
        a = self.range_anchor or self.sel
        e = self.range_end or self.sel
        c1, r1 = _split_ref(a)
        c2, r2 = _split_ref(e)
        return min(c1, c2), max(c1, c2), min(r1, r2), max(r1, r2)

    def _insert_function(self, name):
        if not self.editing:
            self.editing = True
            self.edit_buf = "="
        elif not self.edit_buf.startswith("="):
            self.edit_buf = "=" + self.edit_buf
        self.edit_buf += f"{name}("
        self.fx_open = False

    # ----------------------------------------------------------- graphiques
    def _add_chart(self, kind):
        c1, c2, r1, r2 = self._range_bounds()
        if c1 == c2 and r1 == r2:
            self.msg = "Glissez la souris sur une plage de cellules avant d'insérer un graphique."
            return
        range_str = f"{idx_to_col(c1)}{r1}:{idx_to_col(c2)}{r2}"
        ncols = c2 - c1 + 1
        if kind == "scatter" and ncols != 2:
            self.msg = "Nuage de points : sélectionnez une plage à 2 colonnes (X ; Y)."
            return
        n = len(self.workbook.active.charts)
        chart = SheetChart(kind, range_str, x=24 + 18 * (n % 6), y=24 + 18 * (n % 6))
        data = self._chart_data(chart)
        if not data:
            self.msg = "Plage invalide ou vide pour ce graphique."
            return
        self.workbook.active.charts.append(chart)
        self.msg = f"Graphique « {dict(CHART_TYPES)[kind]} » ajouté ({range_str})."

    def _chart_data(self, chart):
        try:
            c1, r1 = _split_ref(chart.range_str.split(":")[0])
            c2, r2 = _split_ref(chart.range_str.split(":")[1])
        except (ValueError, IndexError):
            return None
        c1, c2 = min(c1, c2), max(c1, c2)
        r1, r2 = min(r1, r2), max(r1, r2)
        sheet = self.sheet
        col_vals = lambda c: [sheet.get_value(f"{idx_to_col(c)}{r}") for r in range(r1, r2 + 1)]
        ncols = c2 - c1 + 1
        if chart.kind == "scatter":
            if ncols != 2:
                return None
            xs = [v for v in col_vals(c1) if _is_num(v)]
            ys = [v for v in col_vals(c1 + 1) if _is_num(v)]
            n = min(len(xs), len(ys))
            return {"x": xs[:n], "y": ys[:n], "labels": None} if n else None
        if ncols == 1:
            y = [float(v) if _is_num(v) else 0.0 for v in col_vals(c1)]
            labels = [str(r) for r in range(r1, r2 + 1)]
        else:
            labels = [str(v) for v in col_vals(c1)]
            y = [float(v) if _is_num(v) else 0.0 for v in col_vals(c1 + 1)]
        return {"labels": labels, "y": y, "x": None} if y else None

    # --------------------------------------------------------------- events
    def handle_event(self, event, rect):
        if self.fx_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for name, r in self._fx_item_rects.items():
                    if r.collidepoint(event.pos):
                        self._insert_function(name)
                        return True
                if not (self._fx_panel_rect and self._fx_panel_rect.collidepoint(event.pos)) \
                        and not (self._fx_rect and self._fx_rect.collidepoint(event.pos)):
                    self.fx_open = False
                return True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.fx_open = False
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._fx_rect and self._fx_rect.collidepoint(event.pos):
                self.fx_open = not self.fx_open
                return True
            for kind, r in self._chart_btn_rects.items():
                if r.collidepoint(event.pos):
                    self._add_chart(kind)
                    return True
            for cid, r in self._chart_close_rects.items():
                if r.collidepoint(event.pos):
                    self.workbook.active.charts = [c for c in self.workbook.active.charts if c.id != cid]
                    return True
            for cid, r in self._chart_resize_rects.items():
                if r.collidepoint(event.pos):
                    self._chart_resize = next(c for c in self.workbook.active.charts if c.id == cid)
                    return True
            for cid, r in self._chart_title_rects.items():
                if r.collidepoint(event.pos):
                    chart = next(c for c in self.workbook.active.charts if c.id == cid)
                    self._chart_drag = chart
                    self._chart_drag_off = (event.pos[0] - (rect.x + chart.x),
                                            event.pos[1] - (rect.y + chart.y))
                    return True
            if self._add_tab_rect and self._add_tab_rect.collidepoint(event.pos):
                self._commit()
                self.workbook.add_tab()
                self.sel = "A1"
                self.scroll_y = 0
                return True
            for idx, r in self._tab_rects.items():
                if r.collidepoint(event.pos):
                    self._commit()
                    self.workbook.active_index = idx
                    self.sel = "A1"
                    self.scroll_y = 0
                    return True
            for ref, r in self._cell_rects.items():
                if r.collidepoint(event.pos):
                    self._commit()
                    self.sel = ref
                    self.range_anchor = ref
                    self.range_end = ref
                    self._dragging_range = True
                    return True
            return False
        if event.type == pygame.MOUSEMOTION:
            if self._chart_resize is not None:
                chart = self._chart_resize
                chart.w = max(160, event.pos[0] - (rect.x + chart.x))
                chart.h = max(110, event.pos[1] - (rect.y + chart.y))
                chart.w = min(chart.w, rect.w - chart.x)
                chart.h = min(chart.h, rect.h - chart.y)
                return True
            if self._chart_drag is not None:
                chart = self._chart_drag
                chart.x = event.pos[0] - rect.x - self._chart_drag_off[0]
                chart.y = event.pos[1] - rect.y - self._chart_drag_off[1]
                chart.x = max(0, min(chart.x, rect.w - chart.w))
                chart.y = max(0, min(chart.y, rect.h - chart.h))
                return True
            if self._dragging_range:
                for ref, r in self._cell_rects.items():
                    if r.collidepoint(event.pos):
                        self.range_end = ref
                        return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._chart_resize is not None:
                self._chart_resize = None
                return True
            if self._chart_drag is not None:
                self._chart_drag = None
                return True
            if self._dragging_range:
                self._dragging_range = False
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            self.scroll_y = max(0, self.scroll_y + (-1 if event.button == 4 else 1))
            return True
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
                    self.range_anchor = self.range_end = self.sel
                elif event.key == pygame.K_DOWN:
                    self._move(0, 1)
                    self.range_anchor = self.range_end = self.sel
                elif event.key == pygame.K_LEFT:
                    self._move(-1, 0)
                    self.range_anchor = self.range_end = self.sel
                elif event.key == pygame.K_RIGHT:
                    self._move(1, 0)
                    self.range_anchor = self.range_end = self.sel
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
        self._draw_tab_bar(surf, rect, pad)
        toolbar_y = rect.y + pad + TAB_BAR_H + 2
        self._draw_toolbar(surf, rect, pad, toolbar_y)
        # barre de formule
        fr = pygame.Rect(rect.x + pad, toolbar_y + TOOLBAR_H + 2, rect.w - 2 * pad, FORMULA_H)
        pygame.draw.rect(surf, config.COL_BG, fr)
        pygame.draw.rect(surf, config.COL_BORDER, fr, 1)
        widgets.draw_text(surf, self.sel, (fr.x + 8, fr.y + 6), fonts.small(bold=True), config.COL_CYAN)
        content = self.edit_buf if self.editing else self.sheet.get_raw(self.sel)
        cur = "_" if self.editing and pygame.time.get_ticks() % 1000 < 500 else ""
        widgets.draw_text(surf, widgets.fit_text(f"{content}{cur}", fonts.small(), rect.w - 220),
                          (fr.x + 12, fr.y + 6), fonts.small(), config.COL_WHITE)
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
        rc1, rc2, rr1, rr2 = self._range_bounds()
        has_range = not (rc1 == rc2 and rr1 == rr2)
        # en-têtes de colonnes
        for c in range(vis_cols):
            cr = pygame.Rect(gx + HEAD_W + c * CELL_W, gy, CELL_W, CELL_H)
            in_range = has_range and rc1 <= c <= rc2
            pygame.draw.rect(surf, config.COL_PANEL if in_range else config.COL_PANEL_HEAD, cr)
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
            in_range_row = has_range and rr1 <= r <= rr2
            hr = pygame.Rect(gx, ry, HEAD_W, CELL_H)
            pygame.draw.rect(surf, config.COL_PANEL if in_range_row else config.COL_PANEL_HEAD, hr)
            pygame.draw.rect(surf, config.COL_BORDER, hr, 1)
            widgets.draw_text(surf, str(r), hr.center, fonts.tiny(), config.COL_TEXT_DIM, align="center")
            for c in range(vis_cols):
                ref = f"{idx_to_col(c)}{r}"
                cell = pygame.Rect(gx + HEAD_W + c * CELL_W, ry, CELL_W, CELL_H)
                self._cell_rects[ref] = cell
                sel = (ref == self.sel)
                in_range = has_range and in_range_row and rc1 <= c <= rc2
                bg = config.COL_PANEL_HEAD if sel else (
                    (18, 40, 46) if in_range else config.COL_BG)
                pygame.draw.rect(surf, bg, cell)
                pygame.draw.rect(surf, config.COL_CYAN if (sel or in_range) else config.COL_GRID,
                                 cell, 2 if sel else 1)
                raw = self.sheet.get_raw(ref)
                if raw == "":
                    continue
                v = self.sheet.get_value(ref)
                is_num = _is_num(v)
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

        # graphiques posés sur cette feuille (par-dessus la grille)
        self._chart_rects, self._chart_title_rects = {}, {}
        self._chart_close_rects, self._chart_resize_rects = {}, {}
        for chart in self.workbook.active.charts:
            self._draw_chart(surf, rect, chart)

        if self.fx_open:
            self._draw_fx_panel(surf, rect)

    def _draw_tab_bar(self, surf, rect, pad):
        bar = pygame.Rect(rect.x + pad, rect.y + pad, rect.w - 2 * pad, TAB_BAR_H)
        self._tab_rects = {}
        mp = pygame.mouse.get_pos()
        prev_clip = surf.get_clip()
        surf.set_clip(bar)
        x = bar.x
        for idx, tab in enumerate(self.workbook.tabs):
            r = pygame.Rect(x, bar.y, TAB_W, TAB_BAR_H - 2)
            self._tab_rects[idx] = r
            active = (idx == self.workbook.active_index)
            bg = config.COL_BG if active else config.COL_PANEL_HEAD
            if r.collidepoint(mp) and not active:
                bg = config.COL_PANEL
            pygame.draw.rect(surf, bg, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_AMBER if active else config.COL_BORDER, r, 1, border_radius=3)
            widgets.draw_text(surf, widgets.fit_text(tab.name, fonts.tiny(bold=active), TAB_W - 10),
                              (r.x + 6, r.y + 4), fonts.tiny(bold=active),
                              config.COL_AMBER if active else config.COL_TEXT_DIM)
            x += TAB_W + 3
        surf.set_clip(prev_clip)
        self._add_tab_rect = pygame.Rect(min(x, bar.right - 22), bar.y, 22, TAB_BAR_H - 2)
        hov = self._add_tab_rect.collidepoint(mp)
        pygame.draw.rect(surf, config.COL_PANEL if hov else config.COL_PANEL_HEAD,
                         self._add_tab_rect, border_radius=3)
        widgets.draw_text(surf, "+", self._add_tab_rect.center, fonts.small(bold=True),
                          config.COL_AMBER, align="center")

    def _draw_toolbar(self, surf, rect, pad, y):
        bar = pygame.Rect(rect.x + pad, y, rect.w - 2 * pad, TOOLBAR_H)
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, bar, border_radius=3)
        mp = pygame.mouse.get_pos()
        x = bar.x + 4
        self._fx_rect = pygame.Rect(x, bar.y + 2, 46, TOOLBAR_H - 4)
        hov = self._fx_rect.collidepoint(mp) or self.fx_open
        pygame.draw.rect(surf, config.COL_PANEL if hov else config.COL_BG, self._fx_rect, border_radius=3)
        pygame.draw.rect(surf, config.COL_PRESTIGE, self._fx_rect, 1, border_radius=3)
        widgets.draw_text(surf, "fx ▾", self._fx_rect.center, fonts.tiny(bold=True),
                          config.COL_PRESTIGE, align="center")
        x = self._fx_rect.right + 10
        pygame.draw.line(surf, config.COL_BORDER, (x - 5, bar.y + 3), (x - 5, bar.bottom - 3), 1)
        self._chart_btn_rects = {}
        for kind, label in CHART_TYPES:
            w = fonts.tiny(bold=True).size(label)[0] + 16
            r = pygame.Rect(x, bar.y + 2, w, TOOLBAR_H - 4)
            self._chart_btn_rects[kind] = r
            hov = r.collidepoint(mp)
            pygame.draw.rect(surf, config.COL_PANEL if hov else config.COL_BG, r, border_radius=3)
            pygame.draw.rect(surf, config.COL_CYAN, r, 1, border_radius=3)
            widgets.draw_text(surf, label, r.center, fonts.tiny(bold=True), config.COL_CYAN, align="center")
            x += w + 6
        if self.msg:
            widgets.draw_text(surf, widgets.fit_text(self.msg, fonts.tiny(), bar.right - x - 8),
                              (x + 8, bar.y + 6), fonts.tiny(), config.COL_TEXT_DIM)

    def _draw_fx_panel(self, surf, rect):
        panel = pygame.Rect(self._fx_rect.x, self._fx_rect.bottom + 2, 230, 280)
        panel.right = min(panel.right, rect.right - 4)
        panel.bottom = min(panel.bottom, rect.bottom - 4)
        pygame.draw.rect(surf, config.COL_PANEL, panel)
        pygame.draw.rect(surf, config.COL_AMBER, panel, 2)
        self._fx_panel_rect = panel
        self._fx_item_rects = {}
        y = panel.y + 6
        mp = pygame.mouse.get_pos()
        prev_clip = surf.get_clip()
        surf.set_clip(panel)
        for cat, funcs in FUNCTION_CATALOG:
            widgets.draw_text(surf, cat.upper(), (panel.x + 6, y), fonts.tiny(bold=True), config.COL_CYAN)
            y += 16
            for name, hint in funcs:
                r = pygame.Rect(panel.x + 4, y, panel.w - 8, 16)
                self._fx_item_rects[name] = r
                if r.collidepoint(mp):
                    pygame.draw.rect(surf, config.COL_PANEL_HEAD, r)
                widgets.draw_text(surf, name, (r.x + 4, r.y + 1), fonts.tiny(bold=True), config.COL_AMBER)
                widgets.draw_text(surf, widgets.fit_text(hint, fonts.tiny(), 130),
                                  (r.right - 4, r.y + 1), fonts.tiny(), config.COL_TEXT_DIM, align="right")
                y += 16
            y += 6
        surf.set_clip(prev_clip)

    # --------------------------------------------------------- graphiques
    def _draw_chart(self, surf, rect, chart):
        # bornes vivantes : reste dans la fenêtre même si elle a été
        # redimensionnée/rétrécie depuis le placement du graphique.
        chart.w = max(160, min(chart.w, rect.w - 8))
        chart.h = max(110, min(chart.h, rect.h - 8))
        chart.x = max(0, min(chart.x, rect.w - chart.w))
        chart.y = max(0, min(chart.y, rect.h - chart.h))
        r = pygame.Rect(rect.x + chart.x, rect.y + chart.y, chart.w, chart.h)
        pygame.draw.rect(surf, config.COL_BG, r)
        pygame.draw.rect(surf, config.COL_AMBER, r, 2)
        title_r = pygame.Rect(r.x, r.y, r.w, 18)
        self._chart_title_rects[chart.id] = title_r
        self._chart_rects[chart.id] = r
        pygame.draw.rect(surf, config.COL_PANEL_HEAD, title_r)
        label = dict(CHART_TYPES).get(chart.kind, chart.kind)
        widgets.draw_text(surf, widgets.fit_text(f"{label} · {chart.range_str}", fonts.tiny(), r.w - 26),
                          (title_r.x + 4, title_r.y + 2), fonts.tiny(bold=True), config.COL_AMBER)
        close_r = pygame.Rect(title_r.right - 16, title_r.y + 1, 14, 14)
        self._chart_close_rects[chart.id] = close_r
        hov = close_r.collidepoint(pygame.mouse.get_pos())
        if hov:
            pygame.draw.rect(surf, config.COL_DOWN, close_r)
        pygame.draw.line(surf, config.COL_TEXT if hov else config.COL_TEXT_DIM,
                         (close_r.x + 3, close_r.y + 3), (close_r.right - 3, close_r.bottom - 3), 2)
        pygame.draw.line(surf, config.COL_TEXT if hov else config.COL_TEXT_DIM,
                         (close_r.x + 3, close_r.bottom - 3), (close_r.right - 3, close_r.y + 3), 2)
        body = pygame.Rect(r.x + 4, title_r.bottom + 2, r.w - 8, r.bottom - title_r.bottom - 6)
        data = self._chart_data(chart)
        if not data:
            widgets.draw_text(surf, "Plage invalide", body.center, fonts.tiny(), config.COL_DOWN, align="center")
        elif chart.kind == "scatter":
            self._draw_scatter(surf, body, data["x"], data["y"])
        elif chart.kind == "bar":
            self._draw_bar(surf, body, data["y"])
        else:
            self._draw_line(surf, body, data["y"])
        # poignée de redimensionnement (coin bas-droit, comme les fenêtres)
        grip = pygame.Rect(r.right - 12, r.bottom - 12, 12, 12)
        self._chart_resize_rects[chart.id] = grip
        for i in range(1, 4):
            pygame.draw.line(surf, config.COL_AMBER, (grip.right - i * 3, grip.bottom - 1),
                             (grip.right - 1, grip.bottom - i * 3), 1)

    def _axis_frame(self, surf, body, lo, hi):
        """Cadre + étiquettes min/médiane/max sur l'axe Y — lisibilité façon
        Excel plutôt qu'un graphe nu. Retourne le rect de tracé (réduit pour
        laisser la place aux étiquettes)."""
        label_w = 34
        plot = pygame.Rect(body.x + label_w, body.y + 2, max(10, body.w - label_w - 2), max(10, body.h - 12))
        pygame.draw.rect(surf, config.COL_GRID, plot, 1)
        mid = (lo + hi) / 2
        pygame.draw.line(surf, config.COL_GRID, (plot.x, plot.centery), (plot.right, plot.centery), 1)
        for val, y in ((hi, plot.y), (mid, plot.centery), (lo, plot.bottom)):
            widgets.draw_text(surf, widgets.fit_text(f"{val:,.2f}", fonts.tiny(), label_w - 2),
                              (body.x, max(body.y, min(y - 5, body.bottom - 10))), fonts.tiny(), config.COL_TEXT_DIM)
        return plot

    def _draw_line(self, surf, body, y):
        if not y:
            return
        lo, hi = min(y), max(y)
        if hi == lo:
            hi = lo + 1
        rect = self._axis_frame(surf, body, lo, hi)
        n = len(y)
        pts = [(rect.x + (i / max(1, n - 1)) * rect.w,
                rect.bottom - (v - lo) / (hi - lo) * rect.h) for i, v in enumerate(y)]
        if len(pts) >= 2:
            pygame.draw.lines(surf, config.COL_CYAN, False, pts, 2)
        for p in pts:
            pygame.draw.circle(surf, config.COL_CYAN, (int(p[0]), int(p[1])), 2)

    def _draw_bar(self, surf, body, y):
        if not y:
            return
        lo = min(0.0, min(y))
        hi = max(y) if max(y) > 0 else 1.0
        rect = self._axis_frame(surf, body, lo, hi)
        span = (hi - lo) or 1.0
        n = len(y)
        zero_y = rect.bottom - (0 - lo) / span * rect.h
        bw = max(2, int(rect.w / max(1, n)) - 3)
        for i, v in enumerate(y):
            bx = rect.x + i * (rect.w / max(1, n))
            vy = rect.bottom - (v - lo) / span * rect.h
            top, h = (min(vy, zero_y), abs(vy - zero_y))
            pygame.draw.rect(surf, config.COL_UP if v >= 0 else config.COL_DOWN,
                             (int(bx), int(top), bw, max(1, int(h))))

    def _draw_scatter(self, surf, body, xs, ys):
        if not xs or not ys:
            return
        loy, hiy = min(ys), max(ys)
        if hiy == loy:
            hiy = loy + 1
        lox, hix = min(xs), max(xs)
        if hix == lox:
            hix = lox + 1
        rect = self._axis_frame(surf, body, loy, hiy)
        for x, v in zip(xs, ys):
            px = rect.x + (x - lox) / (hix - lox) * rect.w
            py = rect.bottom - (v - loy) / (hiy - loy) * rect.h
            pygame.draw.circle(surf, config.COL_PRESTIGE, (int(px), int(py)), 3)
        widgets.draw_text(surf, widgets.fit_text(f"{lox:,.2g}", fonts.tiny(), 40),
                          (rect.x, rect.bottom + 1), fonts.tiny(), config.COL_TEXT_DIM)
        widgets.draw_text(surf, widgets.fit_text(f"{hix:,.2g}", fonts.tiny(), 40),
                          (rect.right, rect.bottom + 1), fonts.tiny(), config.COL_TEXT_DIM, align="right")
