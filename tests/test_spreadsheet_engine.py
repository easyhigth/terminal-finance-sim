"""Tests du moteur de tableur (core/spreadsheet_engine.py).

Couvre : conversion colonnes <-> index, tokenisation, littéraux, opérateurs
arithmétiques/comparaison, références de cellules (simples et plages),
fonctions intégrées (SUM/AVERAGE/MIN/MAX/IF/NPV/IRR/PMT/ROUND/...), gestion
des erreurs (#ERR, #CYCLE), cache et sérialisation (to_dict/load_dict).
"""
import math

import pytest

from core import spreadsheet_engine as se
from core.spreadsheet_engine import Spreadsheet, Tok, col_to_idx, idx_to_col, tokenize


# --------------------------------------------------------------- col <-> idx
def test_col_to_idx_basic():
    assert col_to_idx("A") == 0
    assert col_to_idx("B") == 1
    assert col_to_idx("Z") == 25
    assert col_to_idx("AA") == 26
    assert col_to_idx("AB") == 27


def test_idx_to_col_basic():
    assert idx_to_col(0) == "A"
    assert idx_to_col(1) == "B"
    assert idx_to_col(25) == "Z"
    assert idx_to_col(26) == "AA"
    assert idx_to_col(27) == "AB"


def test_col_idx_roundtrip():
    for idx in range(0, 200):
        assert col_to_idx(idx_to_col(idx)) == idx


# --------------------------------------------------------------- tokenize
def test_tokenize_number_and_operator():
    toks = tokenize("1+2")
    assert [t.kind for t in toks] == [Tok.NUM, Tok.OP, Tok.NUM]
    assert toks[0].val == 1.0 and toks[2].val == 2.0


def test_tokenize_scientific_notation():
    toks = tokenize("1.5e3")
    assert toks[0].kind == Tok.NUM
    assert toks[0].val == 1500.0


def test_tokenize_cell_ref_vs_function_name():
    toks = tokenize("A1+SUM(B2)")
    kinds = [t.kind for t in toks]
    assert kinds[0] == Tok.REF
    assert toks[0].val == "A1"
    func_tok = next(t for t in toks if t.kind == Tok.FUNC)
    assert func_tok.val == "SUM"


def test_tokenize_string_literal():
    toks = tokenize('"hello"')
    assert toks[0].kind == Tok.STR
    assert toks[0].val == "hello"


def test_tokenize_comparison_operators():
    toks = tokenize("A1>=B1<>C1")
    ops = [t.val for t in toks if t.kind == Tok.OP]
    assert ops == [">=", "<>"]


def test_tokenize_colon_for_ranges():
    toks = tokenize("A1:B3")
    assert [t.kind for t in toks] == [Tok.REF, Tok.COLON, Tok.REF]


def test_tokenize_raises_on_unexpected_char():
    with pytest.raises(ValueError):
        tokenize("1 & 2")


# --------------------------------------------------------------- Spreadsheet basique
def test_set_and_get_raw():
    sh = Spreadsheet()
    sh.set("A1", "42")
    assert sh.get_raw("A1") == "42"
    assert sh.get_raw("Z9") == ""  # cellule jamais définie


def test_get_value_plain_number():
    sh = Spreadsheet()
    sh.set("A1", "3.5")
    assert sh.get_value("A1") == 3.5


def test_get_value_plain_text_passthrough():
    sh = Spreadsheet()
    sh.set("A1", "bonjour")
    assert sh.get_value("A1") == "bonjour"


def test_get_value_empty_cell_is_zero():
    sh = Spreadsheet()
    assert sh.get_value("A1") == 0.0
    sh.set("A2", "")
    assert sh.get_value("A2") == 0.0
    sh.set("A3", None)
    assert sh.get_value("A3") == 0.0


# --------------------------------------------------------------- formules arithmétiques
def test_formula_addition_and_precedence():
    sh = Spreadsheet()
    sh.set("A1", "=1+2*3")
    assert sh.get_value("A1") == 7.0


def test_formula_parentheses_override_precedence():
    sh = Spreadsheet()
    sh.set("A1", "=(1+2)*3")
    assert sh.get_value("A1") == 9.0


def test_formula_power_and_unary_minus():
    sh = Spreadsheet()
    sh.set("A1", "=-2^2")
    # unary se lie avant pow dans ce parseur (unary() appelle atom, pow() appelle unary)
    # donc -2^2 = (-2)^2 = 4
    assert sh.get_value("A1") == (-2.0) ** 2.0


def test_formula_division():
    sh = Spreadsheet()
    sh.set("A1", "=10/4")
    assert sh.get_value("A1") == 2.5


def test_formula_division_by_zero_yields_err():
    sh = Spreadsheet()
    sh.set("A1", "=10/0")
    assert sh.get_value("A1") == "#ERR"


def test_formula_comparison_operators():
    sh = Spreadsheet()
    sh.set("A1", "=1<2")
    sh.set("A2", "=2<=2")
    sh.set("A3", "=3=3")
    sh.set("A4", "=3<>3")
    sh.set("A5", "=5>4")
    sh.set("A6", "=4>=5")
    assert sh.get_value("A1") is True
    assert sh.get_value("A2") is True
    assert sh.get_value("A3") is True
    assert sh.get_value("A4") is False
    assert sh.get_value("A5") is True
    assert sh.get_value("A6") is False


# --------------------------------------------------------------- références
def test_formula_references_another_cell():
    sh = Spreadsheet()
    sh.set("A1", "10")
    sh.set("A2", "=A1*2")
    assert sh.get_value("A2") == 20.0


def test_formula_chained_references():
    sh = Spreadsheet()
    sh.set("A1", "1")
    sh.set("A2", "=A1+1")
    sh.set("A3", "=A2+1")
    assert sh.get_value("A3") == 3.0


def test_formula_self_reference_yields_cycle_marker_then_err():
    sh = Spreadsheet()
    sh.set("A1", "=A1+1")
    # la détection de cycle renvoie "#CYCLE" en interne, qui casse l'arithmétique
    # -> exception interceptée -> "#ERR" pour la cellule
    assert sh.get_value("A1") == "#ERR"


def test_formula_mutual_cycle_yields_err():
    sh = Spreadsheet()
    sh.set("A1", "=A2+1")
    sh.set("A2", "=A1+1")
    assert sh.get_value("A1") == "#ERR"
    assert sh.get_value("A2") == "#ERR"


def test_unknown_function_yields_err():
    sh = Spreadsheet()
    sh.set("A1", "=NOTAFUNC(1)")
    assert sh.get_value("A1") == "#ERR"


# --------------------------------------------------------------- cache
def test_value_is_cached_until_set_invalidates():
    sh = Spreadsheet()
    sh.set("A1", "5")
    sh.set("A2", "=A1*2")
    assert sh.get_value("A2") == 10.0
    sh.set("A1", "100")  # invalide le cache
    assert sh.get_value("A2") == 200.0


# --------------------------------------------------------------- plages et fonctions
def test_expand_range_single_column():
    sh = Spreadsheet()
    refs = sh.expand_range("A1", "A3")
    assert refs == ["A1", "A2", "A3"]


def test_expand_range_rectangle_and_order_independent():
    sh = Spreadsheet()
    refs = sh.expand_range("B2", "A1")
    assert set(refs) == {"A1", "A2", "B1", "B2"}


def test_sum_over_range():
    sh = Spreadsheet()
    sh.set("A1", "1")
    sh.set("A2", "2")
    sh.set("A3", "3")
    sh.set("B1", "=SUM(A1:A3)")
    assert sh.get_value("B1") == 6.0


def test_sum_ignores_non_numeric_cells():
    sh = Spreadsheet()
    sh.set("A1", "1")
    sh.set("A2", "texte")
    sh.set("A3", "3")
    sh.set("B1", "=SUM(A1:A3)")
    assert sh.get_value("B1") == 4.0


def test_average_min_max_count():
    sh = Spreadsheet()
    for ref, v in [("A1", "2"), ("A2", "4"), ("A3", "6")]:
        sh.set(ref, v)
    sh.set("B1", "=AVERAGE(A1:A3)")
    sh.set("B2", "=MIN(A1:A3)")
    sh.set("B3", "=MAX(A1:A3)")
    sh.set("B4", "=COUNT(A1:A3)")
    assert sh.get_value("B1") == 4.0
    assert sh.get_value("B2") == 2.0
    assert sh.get_value("B3") == 6.0
    assert sh.get_value("B4") == 3.0


def test_average_of_empty_range_is_zero():
    sh = Spreadsheet()
    sh.set("B1", "=AVERAGE(A1:A3)")
    # cellules vides valent 0.0 chacune (et non ignorées) car get_value renvoie 0.0
    assert sh.get_value("B1") == 0.0


def test_abs_sqrt_power_exp_ln_log():
    sh = Spreadsheet()
    sh.set("A1", "=ABS(-5)")
    sh.set("A2", "=SQRT(9)")
    sh.set("A3", "=POWER(2,10)")
    sh.set("A4", "=EXP(0)")
    sh.set("A5", "=LN(1)")
    sh.set("A6", "=LOG(100,10)")
    sh.set("A7", "=LOG(100)")
    assert sh.get_value("A1") == 5.0
    assert sh.get_value("A2") == 3.0
    assert sh.get_value("A3") == 1024.0
    assert sh.get_value("A4") == 1.0
    assert sh.get_value("A5") == 0.0
    assert sh.get_value("A6") == pytest.approx(2.0)
    assert sh.get_value("A7") == pytest.approx(2.0)


def test_round_function():
    sh = Spreadsheet()
    sh.set("A1", "=ROUND(3.14159,2)")
    sh.set("A2", "=ROUND(3.7)")
    assert sh.get_value("A1") == 3.14
    assert sh.get_value("A2") == 4.0


def test_stdev_and_var():
    sh = Spreadsheet()
    sh.set("A1", "2")
    sh.set("A2", "4")
    sh.set("A3", "4")
    sh.set("A4", "4")
    sh.set("A5", "5")
    sh.set("A6", "5")
    sh.set("A7", "7")
    sh.set("A8", "9")
    sh.set("B1", "=STDEV(A1:A8)")
    sh.set("B2", "=VAR(A1:A8)")
    expected_std = se._stdev([2, 4, 4, 4, 5, 5, 7, 9])
    assert sh.get_value("B1") == pytest.approx(expected_std)
    assert sh.get_value("B2") == pytest.approx(expected_std ** 2)


def test_stdev_single_value_is_zero():
    sh = Spreadsheet()
    sh.set("A1", "5")
    sh.set("B1", "=STDEV(A1:A1)")
    assert sh.get_value("B1") == 0.0


def test_if_function_true_and_false_branches():
    sh = Spreadsheet()
    sh.set("A1", "=IF(1>0,10,20)")
    sh.set("A2", "=IF(1<0,10,20)")
    sh.set("A3", "=IF(1<0,10)")  # pas de branche fausse -> 0.0
    assert sh.get_value("A1") == 10.0
    assert sh.get_value("A2") == 20.0
    assert sh.get_value("A3") == 0.0


def test_npv_matches_manual_formula():
    sh = Spreadsheet()
    sh.set("A1", "=NPV(0.1,-100,30,40,50)")
    rate, flows = 0.1, [-100, 30, 40, 50]
    expected = sum(cf / (1 + rate) ** (t + 1) for t, cf in enumerate(flows))
    assert sh.get_value("A1") == pytest.approx(expected)


def test_irr_of_simple_cashflows():
    sh = Spreadsheet()
    # investissement de 100 qui rapporte 110 un an plus tard -> IRR = 10%
    sh.set("A1", "=IRR(-100,110)")
    assert sh.get_value("A1") == pytest.approx(0.10, abs=1e-6)


def test_pmt_zero_rate_is_linear():
    sh = Spreadsheet()
    sh.set("A1", "=PMT(0,10,1000)")
    assert sh.get_value("A1") == pytest.approx(-100.0)


def test_pmt_matches_manual_formula():
    sh = Spreadsheet()
    sh.set("A1", "=PMT(0.05,10,1000)")
    rate, nper, pv = 0.05, 10, 1000
    expected = -pv * rate * (1 + rate) ** nper / ((1 + rate) ** nper - 1)
    assert sh.get_value("A1") == pytest.approx(expected)


# --------------------------------------------------------------- sérialisation
def test_to_dict_and_load_dict_roundtrip():
    sh = Spreadsheet()
    sh.set("A1", "5")
    sh.set("A2", "=A1*2")
    snapshot = sh.to_dict()
    sh2 = Spreadsheet()
    sh2.load_dict(snapshot)
    assert sh2.get_value("A2") == 10.0
    assert sh2.to_dict() == snapshot


def test_load_dict_clears_previous_cache():
    sh = Spreadsheet()
    sh.set("A1", "1")
    sh.get_value("A1")  # peuple le cache
    sh.load_dict({"A1": "99"})
    assert sh.get_value("A1") == 99.0


# --------------------------------------------------------------- intégration / grille
def test_spreadsheet_default_dimensions():
    sh = Spreadsheet()
    assert sh.rows == 20
    assert sh.cols == 8


def test_custom_dimensions():
    sh = Spreadsheet(rows=5, cols=3)
    assert sh.rows == 5
    assert sh.cols == 3


def test_nested_function_and_reference_combo():
    sh = Spreadsheet()
    sh.set("A1", "10")
    sh.set("A2", "20")
    sh.set("A3", "30")
    sh.set("B1", "=ROUND(AVERAGE(A1:A3)/3,2)")
    assert sh.get_value("B1") == pytest.approx(round((10 + 20 + 30) / 3 / 3, 2))


# ------------------------------------------------ nouvelles fonctions finance
def test_median_odd_and_even():
    sh = Spreadsheet()
    sh.set("A1", "1"); sh.set("A2", "3"); sh.set("A3", "2")
    sh.set("B1", "=MEDIAN(A1:A3)")
    assert sh.get_value("B1") == 2.0
    sh.set("A4", "10")
    sh.set("B2", "=MEDIAN(A1:A4)")
    assert sh.get_value("B2") == pytest.approx((2 + 3) / 2)


def test_correl_perfect_positive():
    sh = Spreadsheet()
    for i, (x, y) in enumerate([(1, 2), (2, 4), (3, 6), (4, 8)], start=1):
        sh.set(f"A{i}", str(x))
        sh.set(f"B{i}", str(y))
    sh.set("C1", "=CORREL(A1:A4,B1:B4)")
    assert sh.get_value("C1") == pytest.approx(1.0)


def test_pv_and_fv_roundtrip():
    sh = Spreadsheet()
    sh.set("A1", "=PV(0.05,10,-100)")
    pv = sh.get_value("A1")
    assert pv > 0
    sh.set("A2", "=FV(0.05,10,-100)")
    fv = sh.get_value("A2")
    assert fv > 0
