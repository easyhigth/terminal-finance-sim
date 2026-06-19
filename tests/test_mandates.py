"""Tests des mandats clients (core/mandates.py)."""
import random

from core import mandates, market
from core.game_state import PlayerState


def _mk(grade_index=6):
    m = market.Market(seed=42)
    m.sync_to(market.WARMUP_STEPS)
    p = PlayerState(continent="Europe", grade_index=grade_index)
    return p, m


def test_maybe_offer_none_below_min_grade():
    p, _ = _mk(grade_index=mandates.MIN_GRADE - 1)
    rng = random.Random(0)
    assert mandates.maybe_offer(p, rng) is None


def test_maybe_offer_creates_offer_with_expected_fields():
    p, _ = _mk()
    rng = random.Random(1)
    offer = None
    for _ in range(50):
        offer = mandates.maybe_offer(p, rng)
        if offer:
            break
    assert offer is not None
    for key in ("id", "client", "capital", "target_pct", "horizon", "max_beta",
                "reward_cash", "reward_rep", "penalty_rep"):
        assert key in offer
    assert offer in p.mandate_offers


def test_accept_moves_offer_to_active_with_snapshot():
    p, m = _mk()
    p.mandate_offers = [{"id": 1, "client": "Test Client", "capital": 500_000,
                         "target_pct": 5.0, "horizon": 2, "max_beta": 1.2,
                         "reward_cash": 1000.0, "reward_rep": 8, "penalty_rep": 5}]
    accepted = mandates.accept(p, 1, m)
    assert accepted is not None
    assert accepted["id"] == 1
    assert "start_nw" in accepted and "deadline_q" in accepted
    assert p.mandate_offers == []
    assert p.mandates == [accepted]


def test_accept_returns_full_when_max_active_reached():
    p, m = _mk()
    p.mandates = [{"id": 99}] * mandates.MAX_ACTIVE
    p.mandate_offers = [{"id": 1, "client": "X", "capital": 100_000, "target_pct": 1.0,
                         "horizon": 1, "max_beta": 1.0, "reward_cash": 0.0,
                         "reward_rep": 0, "penalty_rep": 0}]
    assert mandates.accept(p, 1, m) == "full"


def test_accept_returns_none_for_unknown_id():
    p, m = _mk()
    assert mandates.accept(p, 404, m) is None


def test_decline_removes_offer():
    p, _ = _mk()
    p.mandate_offers = [{"id": 1, "client": "X"}]
    assert mandates.decline(p, 1) is True
    assert p.mandate_offers == []
    assert mandates.decline(p, 1) is False


def _due_mandate(player, market_, target_pct=1_000_000.0, max_beta=10.0):
    """Mandat fabriqué pour échoir immédiatement, avec une cible quasi
    inatteignable par défaut (pour des tests d'échec déterministes)."""
    from core import portfolio
    return {"id": 1, "client": "Fonds de pension Helven", "capital": 500_000,
            "target_pct": target_pct, "horizon": 1, "max_beta": max_beta,
            "reward_cash": 5_000.0, "reward_rep": 8, "penalty_rep": 5,
            "start_nw": portfolio.net_worth(player, market_),
            "deadline_q": player.quarter}


def test_failure_reason_mentions_missed_target():
    m = {"target_pct": 5.0, "max_beta": 1.5}
    reason = mandates.failure_reason(m, growth=1.0, beta=0.5)
    assert "Rendement cible non atteint" in reason
    assert "Risque dépassé" not in reason


def test_failure_reason_mentions_excess_risk():
    m = {"target_pct": -100.0, "max_beta": 1.0}
    reason = mandates.failure_reason(m, growth=50.0, beta=2.0)
    assert "Risque dépassé" in reason
    assert "Rendement cible non atteint" not in reason


def test_failure_reason_mentions_both_when_both_missed():
    m = {"target_pct": 5.0, "max_beta": 1.0}
    reason = mandates.failure_reason(m, growth=-1.0, beta=2.0)
    assert "Rendement cible non atteint" in reason
    assert "Risque dépassé" in reason


def test_evaluate_due_failure_records_history_with_reason():
    p, m = _mk()
    p.mandates = [_due_mandate(p, m)]
    rep0 = p.reputation
    results = mandates.evaluate_due(p, m)
    assert len(results) == 1
    res = results[0]
    assert res["ok"] is False
    assert "reason" in res and res["reason"]
    assert p.mandates == []
    assert p.reputation == rep0 - res["penalty_rep"]
    assert p.mandate_history == [res]


def test_evaluate_due_success_records_history_and_rewards():
    p, m = _mk()
    p.mandates = [_due_mandate(p, m, target_pct=-1_000_000.0, max_beta=1000.0)]
    cash0 = p.cash
    rep0 = p.reputation
    results = mandates.evaluate_due(p, m)
    res = results[0]
    assert res["ok"] is True
    assert p.cash == cash0 + res["reward_cash"]
    assert p.reputation == rep0 + res["reward_rep"]
    assert p.flags.get("mandates_won") == 1
    assert p.mandate_history == [res]


def test_evaluate_due_keeps_mandate_not_yet_due():
    p, m = _mk()
    future = _due_mandate(p, m)
    future["deadline_q"] = p.quarter + 5
    p.mandates = [future]
    results = mandates.evaluate_due(p, m)
    assert results == []
    assert p.mandates == [future]
    assert p.mandate_history == []


def test_mandate_history_capped_at_max_history():
    p, m = _mk()
    for i in range(mandates.MAX_HISTORY + 5):
        p.mandates = [_due_mandate(p, m)]
        mandates.evaluate_due(p, m)
    assert len(p.mandate_history) == mandates.MAX_HISTORY


def test_maybe_offer_attaches_type_and_extra_constraints():
    p, _ = _mk()
    rng = random.Random(2)
    offer = None
    for _ in range(80):
        offer = mandates.maybe_offer(p, rng)
        if offer:
            break
    assert offer is not None
    assert offer["type"] in mandates.MANDATE_TYPES
    if offer["type"] == "income":
        assert "target_yield" in offer and "min_liquidity" in offer
    elif offer["type"] in ("low_vol", "absolute_return"):
        assert "max_drawdown" in offer
    elif offer["type"] == "esg":
        assert offer["excluded_sectors"] == mandates.ESG_EXCLUDED_SECTORS


def test_check_constraints_ok_when_extra_fields_absent():
    p, m = _mk()
    bare = {"target_pct": -100.0, "max_beta": 10.0}
    check = mandates.check_constraints(p, m, bare, growth=5.0, beta=1.0)
    assert check["ok"] is True
    assert check["breaches"] == []
    assert check["values"]["drawdown"] is None


def test_check_constraints_flags_drawdown_breach():
    p, m = _mk()
    mandate = {"target_pct": -100.0, "max_beta": 10.0, "max_drawdown": 5.0}
    p.cash_history = [100, 60]   # 40% drawdown > limite de 5%
    check = mandates.check_constraints(p, m, mandate, growth=5.0, beta=1.0)
    assert check["ok"] is False
    assert "drawdown" in check["breaches"]


def test_check_constraints_flags_liquidity_breach():
    p, m = _mk()
    mandate = {"target_pct": -100.0, "max_beta": 10.0, "min_liquidity": 150.0}
    check = mandates.check_constraints(p, m, mandate, growth=5.0, beta=1.0)
    assert check["ok"] is False
    assert "liquidity" in check["breaches"]


def test_failure_reason_with_extra_breach():
    mandate = {"target_pct": -100.0, "max_beta": 10.0, "max_drawdown": 5.0}
    extra = {"drawdown": 40.0}
    reason = mandates.failure_reason(mandate, growth=5.0, beta=1.0, extra=extra)
    assert "Drawdown excessif" in reason


def test_failure_reason_extra_none_keeps_legacy_behaviour():
    m = {"target_pct": 5.0, "max_beta": 1.5}
    reason = mandates.failure_reason(m, growth=1.0, beta=0.5)
    assert "Rendement cible non atteint" in reason
