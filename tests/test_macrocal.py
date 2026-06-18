"""Tests du calendrier macro (core/macrocal.py)."""
import random

from core import macrocal as MACRO
from core import market
from core.game_state import PlayerState


def _mk(grade_index=2, cash=1_000_000.0):
    m = market.Market(seed=42)
    m.sync_to(market.WARMUP_STEPS)
    p = PlayerState(continent="Europe", grade_index=grade_index)
    p.cash = cash
    return p, m


def _mk_event(event_id=1, resolve_step=0, probs=None):
    probs = probs or {"positif": 0.35, "neutre": 0.30, "négatif": 0.35}
    return {
        "id": event_id,
        "event_type": "Inflation (CPI)",
        "resolve_step": resolve_step,
        "consensus": "en ligne",
        "probabilities": probs,
    }


# ---------------------------------------------------------------- maybe_schedule

def test_maybe_schedule_none_below_min_grade():
    p, m = _mk(grade_index=MACRO.MIN_GRADE - 1)
    rng = random.Random(0)
    assert MACRO.maybe_schedule(p, rng, m) is None


def test_maybe_schedule_respects_max_active_events():
    p, m = _mk()
    rng = random.Random(2)
    p.macro_events = [_mk_event(i) for i in range(MACRO.MAX_ACTIVE_EVENTS)]
    assert MACRO.maybe_schedule(p, rng, m) is None


def test_maybe_schedule_creates_event_with_expected_fields():
    p, m = _mk()
    rng = random.Random(1)
    event = None
    for _ in range(100):
        event = MACRO.maybe_schedule(p, rng, m)
        if event:
            break
    assert event is not None
    for key in ("id", "event_type", "resolve_step", "consensus", "probabilities"):
        assert key in event
    assert event in p.macro_events
    probs = event["probabilities"]
    assert set(probs.keys()) == set(MACRO.OUTCOMES)
    assert abs(sum(probs.values()) - 1.0) < 1e-6


# ---------------------------------------------------------------- place_bet

def test_place_bet_rejects_unknown_event():
    p, m = _mk()
    res = MACRO.place_bet(p, 999, "positif", 1000.0)
    assert res["ok"] is False
    assert res["reason"] == "event"


def test_place_bet_rejects_invalid_stake():
    p, m = _mk()
    p.macro_events = [_mk_event(1, resolve_step=m.step_count + 10)]
    res = MACRO.place_bet(p, 1, "positif", 0.0)
    assert res["ok"] is False
    assert res["reason"] == "stake"
    res2 = MACRO.place_bet(p, 1, "positif", -50.0)
    assert res2["ok"] is False
    assert res2["reason"] == "stake"


def test_place_bet_rejects_insufficient_cash():
    p, m = _mk(cash=100.0)
    p.macro_events = [_mk_event(1, resolve_step=m.step_count + 10)]
    res = MACRO.place_bet(p, 1, "positif", 1000.0)
    assert res["ok"] is False
    assert res["reason"] == "cash"
    assert p.cash == 100.0


def test_place_bet_rejects_invalid_outcome():
    p, m = _mk()
    p.macro_events = [_mk_event(1, resolve_step=m.step_count + 10)]
    res = MACRO.place_bet(p, 1, "haussier", 1000.0)
    assert res["ok"] is False
    assert res["reason"] == "outcome"


def test_place_bet_debits_cash_and_records_bet():
    p, m = _mk()
    p.macro_events = [_mk_event(1, resolve_step=m.step_count + 10,
                                 probs={"positif": 0.5, "neutre": 0.25, "négatif": 0.25})]
    cash0 = p.cash
    res = MACRO.place_bet(p, 1, "positif", 1000.0)
    assert res["ok"] is True
    assert p.cash == cash0 - 1000.0
    assert len(p.macro_bets) == 1
    bet = p.macro_bets[0]
    assert bet["event_id"] == 1
    assert bet["outcome"] == "positif"
    assert bet["stake"] == 1000.0
    assert bet["multiplier"] == 2.0  # 1/0.5


def test_place_bet_multiplier_capped():
    p, m = _mk()
    p.macro_events = [_mk_event(1, resolve_step=m.step_count + 10,
                                 probs={"positif": 0.05, "neutre": 0.05, "négatif": 0.90})]
    res = MACRO.place_bet(p, 1, "positif", 100.0)
    assert res["ok"] is True
    assert res["bet"]["multiplier"] <= MACRO.MAX_MULTIPLIER


# ---------------------------------------------------------------- resolve_due_events

def test_resolve_due_events_deterministic_same_seed_same_id():
    p1, m1 = _mk()
    p2, m2 = _mk()  # même seed (42)
    event = _mk_event(7, resolve_step=0)
    p1.macro_events = [dict(event)]
    p2.macro_events = [dict(event)]

    res1 = MACRO.resolve_due_events(p1, m1)
    res2 = MACRO.resolve_due_events(p2, m2)
    assert res1[0]["actual_outcome"] == res2[0]["actual_outcome"]


def test_resolve_due_events_only_removes_due_events():
    p, m = _mk()
    due = _mk_event(1, resolve_step=m.step_count)         # due now
    future = _mk_event(2, resolve_step=m.step_count + 100)  # not due
    p.macro_events = [due, future]
    results = MACRO.resolve_due_events(p, m)
    assert len(results) == 1
    assert results[0]["event"]["id"] == 1
    remaining_ids = [e["id"] for e in p.macro_events]
    assert remaining_ids == [2]


def test_resolve_due_events_winning_bet_credits_payout():
    p, m = _mk()
    event = _mk_event(1, resolve_step=m.step_count,
                       probs={"positif": 1.0, "neutre": 0.0, "négatif": 0.0})
    p.macro_events = [event]
    # pari forcé manuellement (sans passer par place_bet, pour contrôler le payout)
    p.macro_bets = [{"event_id": 1, "outcome": "positif", "stake": 500.0, "multiplier": 4.0}]
    cash0 = p.cash
    results = MACRO.resolve_due_events(p, m)
    assert results[0]["actual_outcome"] == "positif"
    bet_result = results[0]["bets_resolved"][0]
    assert bet_result["won"] is True
    assert bet_result["payout"] == 500.0 * 4.0
    assert p.cash == cash0 + 500.0 * 4.0
    assert p.macro_bets == []
    assert p.macro_bet_history  # historisé pour l'UI


def test_resolve_due_events_losing_bet_no_credit():
    p, m = _mk()
    event = _mk_event(1, resolve_step=m.step_count,
                       probs={"positif": 0.0, "neutre": 0.0, "négatif": 1.0})
    p.macro_events = [event]
    p.macro_bets = [{"event_id": 1, "outcome": "positif", "stake": 500.0, "multiplier": 2.0}]
    cash0 = p.cash
    results = MACRO.resolve_due_events(p, m)
    assert results[0]["actual_outcome"] == "négatif"
    bet_result = results[0]["bets_resolved"][0]
    assert bet_result["won"] is False
    assert bet_result["payout"] == 0.0
    assert p.cash == cash0  # stake déjà débité au moment du pari, rien de plus à perdre ici
    assert p.macro_bets == []


def test_resolve_due_events_removes_only_resolved_bets():
    p, m = _mk()
    due = _mk_event(1, resolve_step=m.step_count)
    future = _mk_event(2, resolve_step=m.step_count + 50)
    p.macro_events = [due, future]
    p.macro_bets = [
        {"event_id": 1, "outcome": "positif", "stake": 100.0, "multiplier": 2.0},
        {"event_id": 2, "outcome": "neutre", "stake": 200.0, "multiplier": 3.0},
    ]
    MACRO.resolve_due_events(p, m)
    remaining = [b["event_id"] for b in p.macro_bets]
    assert remaining == [2]


# ---------------------------------------------------------------- pending_bets_for

def test_pending_bets_for_filters_by_event():
    p, m = _mk()
    p.macro_bets = [
        {"event_id": 1, "outcome": "positif", "stake": 100.0, "multiplier": 2.0},
        {"event_id": 2, "outcome": "neutre", "stake": 200.0, "multiplier": 3.0},
        {"event_id": 1, "outcome": "négatif", "stake": 50.0, "multiplier": 1.5},
    ]
    result = MACRO.pending_bets_for(p, 1)
    assert len(result) == 2
    assert all(b["event_id"] == 1 for b in result)
