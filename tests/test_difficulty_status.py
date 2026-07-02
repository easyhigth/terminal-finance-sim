"""Tests de core.difficulty.status_label (badge affiché en jeu)."""
from core import difficulty
from core.game_state import PlayerState


def test_normal_without_daily_challenge_has_no_status():
    p = PlayerState()
    assert difficulty.status_label(p) is None


def test_non_default_preset_shown():
    p = PlayerState()
    p.flags["difficulty"] = "demanding"
    assert difficulty.status_label(p) == "Exigeant"


def test_daily_challenge_shown_even_on_normal():
    p = PlayerState()
    difficulty.mark_daily(p)
    assert difficulty.status_label(p) == "Défi du jour"


def test_both_combine():
    p = PlayerState()
    p.flags["difficulty"] = "relaxed"
    difficulty.mark_daily(p)
    assert difficulty.status_label(p) == "Détendu · Défi du jour"


def test_is_daily_challenge():
    p = PlayerState()
    assert not difficulty.is_daily_challenge(p)
    difficulty.mark_daily(p)
    assert difficulty.is_daily_challenge(p)
