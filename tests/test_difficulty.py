"""Tests des presets de difficulté et du défi du jour (core/difficulty.py)."""
import datetime

from core import difficulty
from core.game_state import PlayerState


def test_default_is_normal_and_neutral():
    p = PlayerState()
    assert difficulty.get_id(p) == "normal"
    assert difficulty.salary_mult(p) == 1.0
    assert difficulty.maint_margin_mult(p) == 1.0


def test_apply_sets_flag_and_scales_cash():
    p = PlayerState(cash=100_000)
    difficulty.apply(p, "relaxed")
    assert p.flags["difficulty"] == "relaxed"
    assert p.cash == 150_000
    p2 = PlayerState(cash=100_000)
    difficulty.apply(p2, "demanding")
    assert p2.cash == 75_000


def test_unknown_preset_falls_back_to_normal():
    p = PlayerState(cash=100_000)
    difficulty.apply(p, "n_existe_pas")
    assert p.flags["difficulty"] == "normal"
    assert p.cash == 100_000


def test_salary_and_margin_react_to_difficulty():
    p = PlayerState()
    base_salary = p.salary_per_step()
    p.flags["difficulty"] = "relaxed"
    assert p.salary_per_step() > base_salary
    p.flags["difficulty"] = "demanding"
    assert p.salary_per_step() < base_salary
    assert difficulty.maint_margin_mult(p) > 1.0


def test_daily_seed_is_shared_and_date_dependent():
    d1 = datetime.date(2026, 7, 2)
    d2 = datetime.date(2026, 7, 3)
    assert difficulty.daily_seed(d1) == difficulty.daily_seed(d1)
    assert difficulty.daily_seed(d1) != difficulty.daily_seed(d2)
    assert 1 <= difficulty.daily_seed(d1) <= 2_000_000_000


def test_mark_daily_records_iso_date():
    p = PlayerState()
    difficulty.mark_daily(p, datetime.date(2026, 7, 2))
    assert p.flags["daily_challenge"] == "2026-07-02"
