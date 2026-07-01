"""
workbook.py — Classeur multi-feuilles pour l'app Tableur du bureau
(`apps/app_sheet.py`).

Contrairement à l'ancienne scène tableur plein écran (`scenes/scene_spreadsheet.py`,
un seul `Spreadsheet` ÉCRASÉ à chaque export), le classeur du bureau garde
PLUSIEURS feuilles (onglets, comme Excel) : exporter un état financier ou une
fiche cible M&A remplit la feuille ACTIVE si elle est vierge, sinon ouvre une
NOUVELLE feuille — jamais d'écrasement silencieux d'un travail en cours. Permet
aussi de préparer plusieurs modèles en parallèle (un par onglet) pendant que
d'autres fenêtres du bureau tournent en même temps.

Logique pure (pas de pygame) : testable seule.
"""
from core.spreadsheet_engine import Spreadsheet, idx_to_col


class SheetChart:
    """Un graphe inséré sur une feuille (comme un objet graphique Excel) :
    type + plage source + position/taille (en pixels, dans le canvas de la
    grille). Logique pure — l'app (`apps/app_sheet.py`) l'affiche et gère le
    glisser/redimensionner ; ce module ne connaît que l'état."""

    _next_id = 1

    def __init__(self, kind, range_str, x, y, w=280, h=180):
        self.id = SheetChart._next_id
        SheetChart._next_id += 1
        self.kind = kind            # "line" | "bar" | "scatter"
        self.range_str = range_str
        self.x, self.y, self.w, self.h = x, y, w, h


class WorkbookTab:
    def __init__(self, name, sheet):
        self.name = name
        self.sheet = sheet
        self.charts = []   # [SheetChart]


class Workbook:
    def __init__(self, n_rows, n_cols):
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.tabs = []
        self.active_index = 0
        self.add_tab()

    def add_tab(self, name=None):
        name = name or f"Feuille {len(self.tabs) + 1}"
        tab = WorkbookTab(name, Spreadsheet(self.n_rows, self.n_cols))
        self.tabs.append(tab)
        self.active_index = len(self.tabs) - 1
        return tab

    def close_tab(self, index):
        """Ferme un onglet (jamais le dernier restant)."""
        if len(self.tabs) <= 1 or not (0 <= index < len(self.tabs)):
            return
        del self.tabs[index]
        self.active_index = min(self.active_index, len(self.tabs) - 1)

    @property
    def active(self):
        return self.tabs[self.active_index]

    def is_blank(self, tab=None):
        tab = tab or self.active
        s = tab.sheet
        for r in range(1, self.n_rows + 1):
            for c in range(self.n_cols):
                if s.get_raw(f"{idx_to_col(c)}{r}") != "":
                    return False
        return True

    def import_financial(self, data):
        """Remplit la feuille ACTIVE si elle est vierge ; sinon crée une
        NOUVELLE feuille (nommée d'après l'export) — jamais d'écrasement d'un
        tableur déjà utilisé. Retourne l'onglet rempli (et le rend actif)."""
        if self.is_blank():
            tab = self.active
        else:
            tab = self.add_tab(name=data.get("title"))
        _seed_financial(tab.sheet, data, self.n_cols, self.n_rows)
        self.active_index = self.tabs.index(tab)
        return tab


def _seed_financial(s, data, n_cols, n_rows):
    """Remplit `s` à partir d'un export d'état financier/fiche
    (title/years/rows) — même format que `scene_spreadsheet._seed_import`."""
    title = data.get("title", "DONNÉES IMPORTÉES")
    years = data.get("years") or []
    rows = data.get("rows") or []
    s.set("A1", title)
    s.set("A2", "Poste")
    n_years = min(len(years), n_cols - 1)
    for k in range(n_years):
        tag = "N" if k == 0 else f"N-{k}"
        s.set(f"{idx_to_col(k + 1)}2", f"{years[k]} ({tag})")
    r = 3
    for label, vals in rows:
        if r > n_rows:
            break
        s.set(f"A{r}", label)
        for k in range(n_years):
            v = vals[k] if k < len(vals) else 0.0
            s.set(f"{idx_to_col(k + 1)}{r}", f"{v:.4f}")
        r += 1
