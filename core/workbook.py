"""
workbook.py — Classeur multi-feuilles pour l'app Tableur du bureau
(`apps/app_sheet.py`).

Contrairement à l'ancienne scène tableur plein écran (retirée — "spreadsheet" est
désormais un alias vers l'app du bureau, cf. scenes/scene_sheet_redirect.py ;
un seul `Spreadsheet` ÉCRASÉ à chaque export), le classeur du bureau garde
PLUSIEURS feuilles (onglets, comme Excel) : exporter un état financier ou une
fiche cible M&A remplit la feuille ACTIVE si elle est vierge, sinon ouvre une
NOUVELLE feuille — jamais d'écrasement silencieux d'un travail en cours. Permet
aussi de préparer plusieurs modèles en parallèle (un par onglet) pendant que
d'autres fenêtres du bureau tournent en même temps.

Logique pure (pas de pygame) : testable seule.
"""
from core.spreadsheet_engine import Spreadsheet, col_to_idx, idx_to_col

# Modèles prêts à l'emploi (bouton « Modèle ▾ » de l'app Tableur,
# apps/app_sheet.py) : au lieu de partir d'une grille totalement vide —
# intimidante pour qui ne sait pas par où commencer — quelques feuilles
# pré-construites pour les analyses courantes. Purement des formules du
# moteur existant (core/spreadsheet_engine) ; les modèles "en direct"
# utilisent les fonctions marché externes (NETWORTH/CASH, cf.
# apps/app_sheet.py::_market_fn), toujours valables sans dépendre d'un
# ticker particulier (contrairement à PRICE("TICKER"), qui varie d'une
# partie à l'autre selon le roster).
TEMPLATES = {
    "returns": {
        "title": "Rendement d'un investissement",
        "cells": [
            ("A1", "RENDEMENT D'UN INVESTISSEMENT"),
            ("A3", "Prix d'achat"), ("B3", "100"),
            ("A4", "Prix actuel"), ("B4", "110"),
            ("A5", "Quantité"), ("B5", "10"),
            ("A7", "Gain/perte (valeur)"), ("B7", "=(B4-B3)*B5"),
            ("A8", "Rendement (%)"), ("B8", "=(B4/B3-1)*100"),
        ],
    },
    "networth": {
        "title": "Suivi du patrimoine (en direct)",
        "cells": [
            ("A1", "SUIVI DU PATRIMOINE (EN DIRECT)"),
            ("A3", "Patrimoine net"), ("B3", "=NETWORTH()"),
            ("A4", "Trésorerie"), ("B4", "=CASH()"),
            ("A5", "Part investie (%)"), ("B5", "=(B3-B4)/B3*100"),
        ],
    },
    "loan": {
        "title": "Mensualité d'emprunt",
        "cells": [
            ("A1", "MENSUALITÉ D'EMPRUNT"),
            ("A3", "Montant emprunté"), ("B3", "100000"),
            ("A4", "Taux annuel (%)"), ("B4", "5"),
            ("A5", "Durée (mois)"), ("B5", "60"),
            ("A7", "Mensualité"), ("B7", "=PMT(B4/100/12,B5,B3)"),
        ],
    },
}


def template_list():
    """[(clé, titre), ...] pour le menu du bouton « Modèle ▾ »."""
    return [(k, tpl["title"]) for k, tpl in TEMPLATES.items()]


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


_CF_OPS = {
    ">":  lambda v, t: v > t,
    "<":  lambda v, t: v < t,
    ">=": lambda v, t: v >= t,
    "<=": lambda v, t: v <= t,
}


class ConditionalFormat:
    """Une règle de mise en forme conditionnelle (façon Excel, simplifiée) :
    si la valeur numérique d'une cellule de `range_str` vérifie `op value`,
    la cellule est peinte avec `color` (nom logique : "up"/"down"/"amber",
    résolu en couleur concrète par l'app — ce module reste sans pygame)."""

    _next_id = 1

    def __init__(self, range_str, op, value, color):
        self.id = ConditionalFormat._next_id
        ConditionalFormat._next_id += 1
        self.range_str = range_str
        self.op = op
        self.value = value
        self.color = color

    def _cells(self):
        try:
            a, b = self.range_str.split(":")
        except ValueError:
            a = b = self.range_str

        def split(ref):
            i = 0
            while i < len(ref) and ref[i].isalpha():
                i += 1
            return col_to_idx(ref[:i]), int(ref[i:])
        c1, r1 = split(a)
        c2, r2 = split(b)
        cells = set()
        for c in range(min(c1, c2), max(c1, c2) + 1):
            for r in range(min(r1, r2), max(r1, r2) + 1):
                cells.add(f"{idx_to_col(c)}{r}")
        return cells

    def matches(self, ref, value):
        if ref not in self._cells():
            return False
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        test = _CF_OPS.get(self.op)
        return bool(test and test(value, self.value))


class WorkbookTab:
    def __init__(self, name, sheet):
        self.name = name
        self.sheet = sheet
        self.charts = []          # [SheetChart]
        self.cf_rules = []        # [ConditionalFormat] mise en forme conditionnelle

    def cf_color_for(self, ref, value):
        """Couleur logique (dernière règle qui correspond gagne, comme Excel
        applique la dernière règle en cas de conflit) ou None si aucune."""
        color = None
        for rule in self.cf_rules:
            if rule.matches(ref, value):
                color = rule.color
        return color


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

    def import_template(self, key):
        """Remplit la feuille ACTIVE si elle est vierge ; sinon crée une
        NOUVELLE feuille nommée d'après le modèle — même règle que
        `import_financial`, jamais d'écrasement silencieux. Renvoie l'onglet
        rempli (et le rend actif), ou None si `key` est inconnue."""
        tpl = TEMPLATES.get(key)
        if not tpl:
            return None
        if self.is_blank():
            tab = self.active
        else:
            tab = self.add_tab(name=tpl["title"])
        for ref, val in tpl["cells"]:
            tab.sheet.set(ref, val)
        self.active_index = self.tabs.index(tab)
        return tab

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
    (title/years/rows) — format historique des exports d'états financiers."""
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
