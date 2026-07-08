"""Tests de core/workbook.py : classeur multi-feuilles et mise en forme
conditionnelle (ConditionalFormat). Logique pure, sans pygame."""
import pytest

from core.workbook import TEMPLATES, ConditionalFormat, Workbook, template_list


def test_add_tab_creates_and_focuses_new_sheet():
    wb = Workbook(10, 5)
    assert len(wb.tabs) == 1
    wb.add_tab()
    assert len(wb.tabs) == 2
    assert wb.active_index == 1


def test_close_tab_never_removes_the_last_one():
    wb = Workbook(10, 5)
    wb.close_tab(0)
    assert len(wb.tabs) == 1


def test_is_blank_true_for_fresh_sheet_false_after_edit():
    wb = Workbook(10, 5)
    assert wb.is_blank() is True
    wb.active.sheet.set("A1", "hello")
    assert wb.is_blank() is False


def test_import_financial_fills_blank_active_sheet():
    wb = Workbook(10, 5)
    tab = wb.import_financial({"title": "États", "years": [2024], "rows": [("Revenus", [100.0])]})
    assert tab is wb.active
    assert wb.active.sheet.get_raw("A1") == "États"


def test_import_financial_opens_new_sheet_if_active_not_blank():
    wb = Workbook(10, 5)
    wb.active.sheet.set("A1", "modèle en cours")
    n_before = len(wb.tabs)
    tab = wb.import_financial({"title": "Cible M&A", "years": [], "rows": []})
    assert len(wb.tabs) == n_before + 1
    assert tab is wb.active
    assert tab.name == "Cible M&A"


# ------------------------------------------------------------ import CSV
def test_import_csv_returns_none_for_empty_rows():
    wb = Workbook(10, 5)
    assert wb.import_csv([]) is None


def test_import_csv_fills_blank_active_sheet():
    wb = Workbook(10, 5)
    tab = wb.import_csv([["MVC", "142.5"], ["NVDA", "98.1"]], name="Cours")
    assert tab is wb.active
    assert wb.active.sheet.get_raw("A1") == "MVC"
    assert wb.active.sheet.get_raw("B1") == "142.5"
    assert wb.active.sheet.get_raw("A2") == "NVDA"


def test_import_csv_opens_new_sheet_if_active_not_blank():
    wb = Workbook(10, 5)
    wb.active.sheet.set("A1", "modèle en cours")
    n_before = len(wb.tabs)
    tab = wb.import_csv([["x", "y"]], name="Import")
    assert len(wb.tabs) == n_before + 1
    assert tab is wb.active
    assert tab.name == "Import"


def test_import_csv_ignores_empty_string_cells():
    wb = Workbook(10, 5)
    tab = wb.import_csv([["A", "", "C"]])
    assert tab.sheet.get_raw("A1") == "A"
    assert tab.sheet.get_raw("B1") == ""
    assert tab.sheet.get_raw("C1") == "C"


def test_import_csv_is_bounded_to_sheet_size():
    wb = Workbook(2, 2)   # 2 lignes, 2 colonnes
    tab = wb.import_csv([["a", "b", "c"], ["d", "e"], ["f", "g"]])
    assert tab.sheet.get_raw("A1") == "a"
    assert tab.sheet.get_raw("B1") == "b"
    # 3e colonne et 3e ligne ignorées silencieusement (hors gabarit)
    assert tab.sheet.get_raw("A2") == "d"
    assert tab.sheet.get_raw("B2") == "e"


# --------------------------------------------- modèles prêts à l'emploi
def test_template_list_matches_templates_dict():
    listed = dict(template_list())
    assert set(listed) == set(TEMPLATES)
    for key, tpl in TEMPLATES.items():
        assert listed[key] == tpl["title"]


def test_import_template_unknown_key_returns_none():
    wb = Workbook(10, 5)
    assert wb.import_template("nope") is None


def test_import_template_fills_blank_active_sheet():
    wb = Workbook(24, 10)
    tab = wb.import_template("returns")
    assert tab is wb.active
    assert wb.active.sheet.get_raw("A1") == "RENDEMENT D'UN INVESTISSEMENT"


def test_import_template_opens_new_sheet_if_active_not_blank():
    wb = Workbook(24, 10)
    wb.active.sheet.set("A1", "modèle en cours")
    n_before = len(wb.tabs)
    tab = wb.import_template("returns")
    assert len(wb.tabs) == n_before + 1
    assert tab is wb.active
    assert tab.name == "Rendement d'un investissement"


def test_returns_template_formulas_evaluate_correctly():
    wb = Workbook(24, 10)
    tab = wb.import_template("returns")
    assert tab.sheet.get_value("B7") == pytest.approx(100.0)     # (110-100)*10
    assert tab.sheet.get_value("B8") == pytest.approx(10.0)      # (110/100-1)*100


def test_loan_template_pmt_formula_evaluates():
    wb = Workbook(24, 10)
    tab = wb.import_template("loan")
    val = tab.sheet.get_value("B7")
    assert isinstance(val, float) and val < 0   # mensualité = sortie de trésorerie


def test_networth_template_uses_live_market_functions():
    wb = Workbook(24, 10)
    tab = wb.import_template("networth")
    assert tab.sheet.get_raw("B3") == "=NETWORTH()"
    assert tab.sheet.get_raw("B4") == "=CASH()"


# --------------------------------------------- mise en forme conditionnelle
def test_conditional_format_matches_cell_inside_range_and_condition():
    rule = ConditionalFormat("A1:B3", ">", 100.0, "up")
    assert rule.matches("A2", 150.0) is True
    assert rule.matches("A2", 50.0) is False    # ne vérifie pas la condition
    assert rule.matches("C1", 150.0) is False   # hors de la plage


def test_conditional_format_single_cell_range():
    rule = ConditionalFormat("A1", "<", 0.0, "down")
    assert rule.matches("A1", -5.0) is True
    assert rule.matches("A1", 5.0) is False


def test_conditional_format_ignores_non_numeric_values():
    rule = ConditionalFormat("A1:A5", ">", 0.0, "up")
    assert rule.matches("A1", "texte") is False
    assert rule.matches("A1", True) is False    # bool exclu (isinstance bool < int)


@pytest.mark.parametrize("op,value,threshold,expected", [
    (">", 10.0, 5.0, True), (">", 5.0, 10.0, False),
    ("<", 5.0, 10.0, True), ("<", 10.0, 5.0, False),
    (">=", 5.0, 5.0, True), ("<=", 5.0, 5.0, True),
])
def test_conditional_format_operators(op, value, threshold, expected):
    rule = ConditionalFormat("A1", op, threshold, "amber")
    assert rule.matches("A1", value) is expected


def test_workbook_tab_cf_color_for_returns_none_without_matching_rule():
    wb = Workbook(10, 5)
    assert wb.active.cf_color_for("A1", 999.0) is None


def test_workbook_to_dict_from_dict_roundtrip():
    """Le classeur (cellules, graphiques, règles CF, onglets, index actif)
    se sérialise et se restaure correctement."""
    wb = Workbook(12, 8)
    wb.active.sheet.set("A1", "Titre")
    wb.active.sheet.set("B2", "=A1")
    wb.active.charts.append(type("Chart", (), {
        "kind": "line", "range_str": "A1:B2",
        "x": 10, "y": 20, "w": 200, "h": 150,
    })())
    wb.active.cf_rules.append(ConditionalFormat("A1:B2", ">", 0.0, "up"))
    wb.add_tab()
    wb.active.name = "Résumé"
    wb.active.sheet.set("A1", 42)

    d = wb.to_dict()
    restored = Workbook.from_dict(d, wb.n_rows, wb.n_cols)

    assert len(restored.tabs) == len(wb.tabs)
    assert restored.active_index == wb.active_index
    assert restored.active.name == "Résumé"
    assert restored.tabs[0].sheet.get_raw("A1") == "Titre"
    assert restored.tabs[0].sheet.get_raw("B2") == "=A1"
    assert restored.tabs[0].sheet.get_value("B2") == "Titre"
    assert len(restored.tabs[0].charts) == 1
    assert restored.tabs[0].charts[0].kind == "line"
    assert len(restored.tabs[0].cf_rules) == 1
    assert restored.tabs[0].cf_rules[0].color == "up"
    assert restored.active.sheet.get_value("A1") == 42.0


def test_workbook_tab_cf_color_for_last_matching_rule_wins():
    """Comme Excel : si plusieurs règles s'appliquent à la même cellule, la
    DERNIÈRE de la liste l'emporte."""
    wb = Workbook(10, 5)
    wb.active.cf_rules.append(ConditionalFormat("A1:A5", ">", 0.0, "up"))
    wb.active.cf_rules.append(ConditionalFormat("A1:A5", ">", 50.0, "down"))
    assert wb.active.cf_color_for("A2", 100.0) == "down"
    assert wb.active.cf_color_for("A2", 10.0) == "up"
