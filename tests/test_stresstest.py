"""Tests du stress test réglementaire périodique (core/stresstest.py)."""
import random

import pytest

from core.market import Market
from core.game_state import PlayerState
from core import portfolio as pf
from core import stresstest as ST


def _player_with_positions(quarter=1, last_stresstest_quarter=0, cash=2_000_000.0):
    m = Market(seed=2024)
    p = PlayerState(quarter=quarter, last_stresstest_quarter=last_stresstest_quarter)
    p.grade_index = 8
    p.cash = cash
    for tk in (m.companies[0]["ticker"], m.companies[10]["ticker"], m.companies[20]["ticker"]):
        m.price[m.ticker_idx[tk]] = 100.0
        pf.buy(p, m, tk, 200)
    return p, m


# ---------------------------------------------------------------------------
# maybe_trigger
# ---------------------------------------------------------------------------
def test_maybe_trigger_none_if_quarter_not_changed():
    p, m = _player_with_positions(quarter=5, last_stresstest_quarter=0)
    assert ST.maybe_trigger(p, False, m) is None
    assert p.pending_stresstest is None


def test_maybe_trigger_none_before_period_elapsed():
    p, m = _player_with_positions(quarter=1, last_stresstest_quarter=0)
    # 1 - 0 = 1 < STRESSTEST_PERIOD_QUARTERS (2)
    assert ST.maybe_trigger(p, True, m) is None
    assert p.pending_stresstest is None


def test_maybe_trigger_none_without_market():
    p, m = _player_with_positions(quarter=2, last_stresstest_quarter=0)
    assert ST.maybe_trigger(p, True, market=None) is None
    assert p.pending_stresstest is None


def test_maybe_trigger_fires_after_period_elapsed():
    p, m = _player_with_positions(quarter=2, last_stresstest_quarter=0)
    test = ST.maybe_trigger(p, True, m)
    assert test is not None
    assert p.pending_stresstest == test
    assert test["quarter"] == 2
    assert test["scenario"] in ("Krach actions", "Choc de taux +200bps",
                                 "Choc de volatilité", "Récession")
    assert "impact_total" in test
    assert "loss_ratio" in test
    assert test["fail_ratio"] == ST.FAIL_RATIO
    assert isinstance(test["passed"], bool)
    assert test["net_worth"] > 0


def test_maybe_trigger_none_if_already_pending():
    p, m = _player_with_positions(quarter=2, last_stresstest_quarter=0)
    ST.maybe_trigger(p, True, m)
    assert p.pending_stresstest is not None
    again = ST.maybe_trigger(p, True, m)
    assert again is None


def test_maybe_trigger_loss_ratio_consistent_with_impact():
    p, m = _player_with_positions(quarter=2, last_stresstest_quarter=0)
    test = ST.maybe_trigger(p, True, m)
    expected_loss = max(0.0, -test["impact_total"]) * 1e6
    assert test["loss"] == pytest.approx(expected_loss)
    expected_ratio = expected_loss / test["net_worth"]
    assert test["loss_ratio"] == pytest.approx(expected_ratio)
    assert test["passed"] == (test["loss_ratio"] <= ST.FAIL_RATIO)


# ---------------------------------------------------------------------------
# has_pending
# ---------------------------------------------------------------------------
def test_has_pending():
    p, m = _player_with_positions(quarter=2, last_stresstest_quarter=0)
    assert ST.has_pending(p) is False
    ST.maybe_trigger(p, True, m)
    assert ST.has_pending(p) is True


# ---------------------------------------------------------------------------
# acknowledge — pas de stress test en attente
# ---------------------------------------------------------------------------
def test_acknowledge_no_pending():
    p, m = _player_with_positions()
    result = ST.acknowledge(p, "accept")
    assert result == {"ok": False, "reason": "no_pending"}


def test_acknowledge_invalid_action():
    p, m = _player_with_positions(quarter=2, last_stresstest_quarter=0)
    ST.maybe_trigger(p, True, m)
    result = ST.acknowledge(p, "do_nothing")
    assert result == {"ok": False, "reason": "invalid_action"}
    # le pending reste inchangé en cas d'action invalide
    assert p.pending_stresstest is not None


# ---------------------------------------------------------------------------
# acknowledge — "accept"
# ---------------------------------------------------------------------------
def test_acknowledge_accept_updates_state_and_history():
    p, m = _player_with_positions(quarter=2, last_stresstest_quarter=0)
    test = ST.maybe_trigger(p, True, m)
    cash_before = p.cash
    rep_before = p.reputation

    result = ST.acknowledge(p, "accept")

    assert result["action"] == "accept"
    assert result["ok"] == test["passed"]
    assert p.cash == cash_before  # "accept" ne coûte rien en cash
    assert p.reputation == max(0, min(100, rep_before + result["rep_delta"]))
    assert p.pending_stresstest is None
    assert p.last_stresstest_quarter == p.quarter
    assert "message" in result and result["message"]
    assert len(p.stresstest_history) == 1
    assert p.stresstest_history[-1]["action"] == "accept"
    assert p.stresstest_history[-1]["passed"] == test["passed"]


def test_acknowledge_accept_failure_lowers_reputation():
    p, m = _player_with_positions(quarter=2, last_stresstest_quarter=0)
    test = ST.maybe_trigger(p, True, m)
    test["passed"] = False  # force le chemin échec indépendamment du scénario tiré
    p.pending_stresstest = test
    random.seed(0)
    result = ST.acknowledge(p, "accept")
    assert result["ok"] is False
    assert result["rep_delta"] < 0


def test_acknowledge_accept_success_no_negative_rep():
    p, m = _player_with_positions(quarter=2, last_stresstest_quarter=0)
    test = ST.maybe_trigger(p, True, m)
    test["passed"] = True
    p.pending_stresstest = test
    result = ST.acknowledge(p, "accept")
    assert result["ok"] is True
    assert result["rep_delta"] >= 0


# ---------------------------------------------------------------------------
# acknowledge — "hedge_now"
# ---------------------------------------------------------------------------
def test_acknowledge_hedge_now_costs_cash():
    p, m = _player_with_positions(quarter=2, last_stresstest_quarter=0)
    ST.maybe_trigger(p, True, m)
    cash_before = p.cash

    result = ST.acknowledge(p, "hedge_now")

    assert result["action"] == "hedge_now"
    assert result["cash_delta"] < 0
    assert p.cash == pytest.approx(cash_before + result["cash_delta"])
    assert p.pending_stresstest is None
    assert p.last_stresstest_quarter == p.quarter
    assert len(p.stresstest_history) == 1


def test_acknowledge_hedge_now_failure_softens_reputation_hit():
    p, m = _player_with_positions(quarter=2, last_stresstest_quarter=0)
    test = ST.maybe_trigger(p, True, m)
    test["passed"] = False
    p.pending_stresstest = test
    result = ST.acknowledge(p, "hedge_now")
    assert result["rep_delta"] <= 0
    assert result["rep_delta"] >= -1  # sanction limitée vs. "accept" (-2..-4)


# ---------------------------------------------------------------------------
# Plafonnement de l'historique
# ---------------------------------------------------------------------------
def test_stresstest_history_capped():
    p, m = _player_with_positions(quarter=2, last_stresstest_quarter=0)
    for i in range(ST.HISTORY_CAP + 5):
        p.quarter = 2 + i * ST.STRESSTEST_PERIOD_QUARTERS
        ST.maybe_trigger(p, True, m)
        assert p.pending_stresstest is not None
        ST.acknowledge(p, "accept")
    assert len(p.stresstest_history) == ST.HISTORY_CAP
