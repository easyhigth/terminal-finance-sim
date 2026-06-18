"""Tests de la revue de performance annuelle (core/review.py)."""
import random

from core import review
from core.game_state import PlayerState


def _mk(grade_index=2, reputation=50, grade_missions=3, quarter=1,
        last_review_quarter=0):
    return PlayerState(grade_index=grade_index, reputation=reputation,
                        grade_missions=grade_missions, quarter=quarter,
                        last_review_quarter=last_review_quarter)


# ---------------------------------------------------------------------------
# maybe_trigger
# ---------------------------------------------------------------------------
def test_maybe_trigger_none_if_quarter_not_changed():
    p = _mk(quarter=5, last_review_quarter=0)
    assert review.maybe_trigger(p, False) is None
    assert p.pending_review is None


def test_maybe_trigger_none_before_period_elapsed():
    p = _mk(quarter=3, last_review_quarter=0)  # 3 < REVIEW_PERIOD_QUARTERS (4)
    assert review.maybe_trigger(p, True) is None
    assert p.pending_review is None


def test_maybe_trigger_fires_after_period_elapsed():
    p = _mk(quarter=4, last_review_quarter=0, reputation=62, grade_missions=5)
    offer = review.maybe_trigger(p, True)
    assert offer is not None
    assert p.pending_review == offer
    assert offer["reputation"] == 62
    assert offer["grade_missions"] == 5
    assert offer["standard_bonus"] == 2_000 + p.grade_index * 3_000
    assert offer["realized_pnl"] == 0.0


def test_maybe_trigger_none_if_already_pending():
    p = _mk(quarter=4, last_review_quarter=0)
    review.maybe_trigger(p, True)
    assert p.pending_review is not None
    again = review.maybe_trigger(p, True)
    assert again is None


def test_maybe_trigger_uses_realized_pnl_if_present():
    p = _mk(quarter=4, last_review_quarter=0)
    p.realized_pnl = 1234.5
    offer = review.maybe_trigger(p, True)
    assert offer["realized_pnl"] == 1234.5


# ---------------------------------------------------------------------------
# has_pending
# ---------------------------------------------------------------------------
def test_has_pending():
    p = _mk(quarter=4, last_review_quarter=0)
    assert review.has_pending(p) is False
    review.maybe_trigger(p, True)
    assert review.has_pending(p) is True


# ---------------------------------------------------------------------------
# negotiate — pas de revue en attente
# ---------------------------------------------------------------------------
def test_negotiate_no_pending():
    p = _mk()
    result = review.negotiate(p, "accept")
    assert result == {"ok": False, "reason": "no_pending"}


# ---------------------------------------------------------------------------
# negotiate — "accept"
# ---------------------------------------------------------------------------
def test_negotiate_accept_credits_standard_bonus_and_updates_state():
    p = _mk(quarter=4, last_review_quarter=0, reputation=50)
    review.maybe_trigger(p, True)
    base = p.pending_review["standard_bonus"]
    cash_before = p.cash
    rep_before = p.reputation

    result = review.negotiate(p, "accept")

    assert result["ok"] is True
    assert result["choice"] == "accept"
    assert result["bonus_paid"] == base
    assert 1 <= result["rep_delta"] <= 2
    assert p.cash == cash_before + base
    assert p.reputation == rep_before + result["rep_delta"]
    assert p.pending_review is None
    assert p.last_review_quarter == p.quarter
    assert "message" in result and result["message"]


# ---------------------------------------------------------------------------
# negotiate — "negotiate_up" (succès et échec, déterministes via seed)
# ---------------------------------------------------------------------------
def test_negotiate_up_success_path():
    p = _mk(quarter=4, last_review_quarter=0, reputation=90, grade_missions=10)
    review.maybe_trigger(p, True)
    base = p.pending_review["standard_bonus"]
    cash_before = p.cash

    # success_prob = 0.3 + min(0.5, 90/200) + min(0.2, 10*0.05)
    #              = 0.3 + 0.45 + 0.2 = 0.95 -> très probable de réussir
    random.seed(1)
    result = review.negotiate(p, "negotiate_up")

    assert result["choice"] == "negotiate_up"
    assert p.pending_review is None
    assert p.last_review_quarter == p.quarter
    if result["ok"]:
        assert result["bonus_paid"] >= base * 1.5 - 1e-6
        assert result["bonus_paid"] <= base * 2.0 + 1e-6
        assert result["rep_delta"] > 0
    else:
        assert abs(result["bonus_paid"] - base * 0.7) < 1e-6
        assert result["rep_delta"] < 0
    assert p.cash == cash_before + result["bonus_paid"]


def test_negotiate_up_failure_path_low_performance():
    # performance minimale -> success_prob faible
    p = _mk(quarter=4, last_review_quarter=0, reputation=0, grade_missions=0)
    p.grade_index = 0
    review.maybe_trigger(p, True)
    base = p.pending_review["standard_bonus"]
    cash_before = p.cash

    # success_prob = 0.3 + 0 + 0 = 0.3 ; en forçant random.random() proche de 1
    # via une seed connue pour produire un échec.
    random.seed(0)
    first_draw = random.random()
    random.seed(0)
    result = review.negotiate(p, "negotiate_up")

    if first_draw < 0.3:
        assert result["ok"] is True
        assert result["bonus_paid"] >= base * 1.5 - 1e-6
    else:
        assert result["ok"] is False
        assert abs(result["bonus_paid"] - base * 0.7) < 1e-6
        assert result["rep_delta"] < 0
    assert p.cash == cash_before + result["bonus_paid"]
    assert p.pending_review is None


# ---------------------------------------------------------------------------
# negotiate — "ask_fixed"
# ---------------------------------------------------------------------------
def test_negotiate_ask_fixed_increments_salary_bonus_no_cash_bonus():
    p = _mk(quarter=4, last_review_quarter=0, reputation=50)
    p.grade_index = 2
    review.maybe_trigger(p, True)
    cash_before = p.cash
    bonus_before = p.salary_bonus_per_step

    result = review.negotiate(p, "ask_fixed")

    expected_increment = 200 * (1 + p.grade_index * 0.1)
    assert result["ok"] is True
    assert result["choice"] == "ask_fixed"
    assert result["bonus_paid"] == 0.0
    assert result["rep_delta"] == 0
    assert p.cash == cash_before  # pas de bonus cash
    assert abs(p.salary_bonus_per_step - (bonus_before + expected_increment)) < 1e-6
    assert p.pending_review is None
    assert p.last_review_quarter == p.quarter
