"""Tests de core/workbook.py : classeur multi-feuilles et mise en forme
conditionnelle (ConditionalFormat). Logique pure, sans pygame."""
import pytest

from core.workbook import ConditionalFormat, Workbook


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


def test_workbook_tab_cf_color_for_last_matching_rule_wins():
    """Comme Excel : si plusieurs règles s'appliquent à la même cellule, la
    DERNIÈRE de la liste l'emporte."""
    wb = Workbook(10, 5)
    wb.active.cf_rules.append(ConditionalFormat("A1:A5", ">", 0.0, "up"))
    wb.active.cf_rules.append(ConditionalFormat("A1:A5", ">", 50.0, "down"))
    assert wb.active.cf_color_for("A2", 100.0) == "down"
    assert wb.active.cf_color_for("A2", 10.0) == "up"
