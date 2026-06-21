"""Tests de la calculatrice scientifique (ui/calculator.py) : safe_eval pur,
aucune dépendance pygame réelle (juste les annotations de type dans le module)."""
import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from ui.calculator import Calculator, safe_eval


def _key_event(key, unicode=""):
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode, mod=0)


def _click_event(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)


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


def test_calculator_starts_focused_and_accepts_typed_digits():
    calc = Calculator(pos=(0, 0))
    assert calc.focused is True
    calc.handle(_key_event(pygame.K_1, "1"))
    calc.handle(_key_event(pygame.K_2, "2"))
    assert calc.expr == "12"


def test_calculator_typed_function_call_and_enter():
    calc = Calculator(pos=(0, 0))
    for ch in "log(100)":
        calc.handle(_key_event(pygame.K_a, ch))
    calc.handle(_key_event(pygame.K_RETURN, "\r"))
    assert calc.result == "2"


def test_calculator_backspace_removes_last_char():
    calc = Calculator(pos=(0, 0))
    calc.handle(_key_event(pygame.K_1, "1"))
    calc.handle(_key_event(pygame.K_2, "2"))
    calc.handle(_key_event(pygame.K_BACKSPACE, ""))
    assert calc.expr == "1"


def test_calculator_escape_unfocuses_without_consuming():
    calc = Calculator(pos=(0, 0))
    consumed = calc.handle(_key_event(pygame.K_ESCAPE, ""))
    assert consumed is False
    assert calc.focused is False


def test_calculator_click_outside_unfocuses_and_blocks_keys():
    calc = Calculator(pos=(0, 0))
    calc.handle(_click_event((500, 500)))  # hors du rect -> perd le focus
    assert calc.focused is False
    consumed = calc.handle(_key_event(pygame.K_1, "1"))
    assert consumed is False
    assert calc.expr == ""


def test_calculator_click_inside_refocuses():
    calc = Calculator(pos=(0, 0))
    calc.handle(_click_event((500, 500)))
    assert calc.focused is False
    calc.handle(_click_event(calc.rect.center))
    assert calc.focused is True
