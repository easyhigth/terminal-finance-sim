"""Tests des mini-jeux de deals (core/deal_game.py + deals.apply_outcome)."""
import random

import pytest

from core import deal_game, deals
from core.game_state import PlayerState

KINDS = ["M&A", "Portfolio", "Risk", "Quant", "Advisory", "General"]


def _deal(kind, did=1):
    return {"id": did, "title": f"Deal {kind}", "kind": kind, "desc": "",
            "reward_cash": 100_000.0, "reward_rep": 8, "penalty_cash": 5_000.0,
            "penalty_rep": 3, "difficulty": 3, "days_left": 10}


@pytest.mark.parametrize("kind", KINDS)
def test_challenge_has_exactly_one_good_choice(kind):
    ch = deal_game.make_challenge(_deal(kind), random.Random(0))
    qualities = [c["quality"] for c in ch["choices"]]
    assert qualities.count("good") == 1          # un seul bon choix
    assert set(qualities) <= {"good", "ok", "bad"}
    assert ch["prompt"] and ch["context"] and ch["expl"]


@pytest.mark.parametrize("kind", KINDS)
def test_challenge_choices_count(kind):
    ch = deal_game.make_challenge(_deal(kind), random.Random(1))
    assert len(ch["choices"]) == 3


def test_apply_outcome_good_pays_full_and_counts_win():
    p = PlayerState(); p.cash = 0.0
    p.deals = [_deal("M&A", 1)]
    res = deals.apply_outcome(p, 1, "good")
    assert res["outcome"] == "success"
    assert p.cash == pytest.approx(100_000.0)
    assert p.deals_won == 1
    assert p.deals == []                          # deal retiré


def test_apply_outcome_partial_pays_half():
    p = PlayerState(); p.cash = 0.0
    p.deals = [_deal("Risk", 2)]
    res = deals.apply_outcome(p, 2, "ok")
    assert res["outcome"] == "partial"
    assert p.cash == pytest.approx(50_000.0)


def test_apply_outcome_bad_penalizes():
    p = PlayerState(); p.cash = 0.0; p.reputation = 50
    p.deals = [_deal("Quant", 3)]
    res = deals.apply_outcome(p, 3, "bad")
    assert res["outcome"] == "fail"
    assert p.cash < 0 and p.reputation < 50
    assert p.deals_won == 0


def test_apply_outcome_missing_deal():
    p = PlayerState()
    assert deals.apply_outcome(p, 999, "good")["ok"] is False
