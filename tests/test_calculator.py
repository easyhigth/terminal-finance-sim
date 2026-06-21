"""Tests de la calculatrice scientifique (ui/calculator.py) : safe_eval pur,
aucune dépendance pygame réelle (juste les annotations de type dans le module)."""
import math

import pytest

from ui.calculator import safe_eval


def test_basic_arithmetic():
    val, ok = safe_eval("2+3*4")
    assert ok and val == pytest.approx(14)


def test_power_operator():
    val, ok = safe_eval("2^10")
    assert ok and val == pytest.approx(1024)


def test_log10():
    val, ok = safe_eval("log(100)")
    assert ok and val == pytest.approx(2.0)


def test_natural_log():
    val, ok = safe_eval("ln(e)")
    assert ok and val == pytest.approx(1.0)


def test_exp():
    val, ok = safe_eval("exp(1)")
    assert ok and val == pytest.approx(math.e)


def test_sqrt():
    val, ok = safe_eval("sqrt(16)")
    assert ok and val == pytest.approx(4.0)


def test_square_shortcut():
    val, ok = safe_eval("5**2")
    assert ok and val == pytest.approx(25.0)


def test_reciprocal_shortcut():
    val, ok = safe_eval("4**-1")
    assert ok and val == pytest.approx(0.25)


def test_pi_constant():
    val, ok = safe_eval("pi")
    assert ok and val == pytest.approx(math.pi)


def test_continuous_compounding_example():
    # capitalisation continue : 100 * e^(0.05*2)
    val, ok = safe_eval("100*exp(0.05*2)")
    assert ok and val == pytest.approx(100 * math.exp(0.1))


def test_unknown_function_rejected():
    val, ok = safe_eval("foo(1)")
    assert not ok and val is None


def test_unknown_name_rejected():
    val, ok = safe_eval("xyz")
    assert not ok and val is None


def test_malformed_expression_rejected():
    val, ok = safe_eval("log(")
    assert not ok and val is None


def test_empty_expression_rejected():
    val, ok = safe_eval("   ")
    assert not ok and val is None
