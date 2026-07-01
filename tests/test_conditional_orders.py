"""Tests de core/conditional_orders.py : ordres stop-loss/take-profit sur les
positions longues du portefeuille — exécution automatique au franchissement
d'un seuil, à chaque pas de marché (via GameState.advance_step)."""
import pytest

from core import conditional_orders as CO
from core import portfolio as pf
from core.game_state import PlayerState
from core.market import Market


def _setup(cash=1_000_000.0):
    m = Market(seed=999)
    p = PlayerState()
    p.grade_index = 8
    p.cash = cash
    return p, m


def _set_price(m, tk, price):
    m.price[m.ticker_idx[tk]] = price


def _held_position(cash=1_000_000.0, qty=100, price=100.0):
    p, m = _setup(cash)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, price)
    pf.buy(p, m, tk, qty)
    return p, m, tk


# ------------------------------------------------------------------- place()
def test_place_stop_loss_on_held_position():
    p, m, tk = _held_position()
    r = CO.place(p, m, tk, "stop", 90.0)
    assert r["ok"] is True
    assert len(p.conditional_orders) == 1
    assert p.conditional_orders[0]["kind"] == "stop"
    assert p.conditional_orders[0]["trigger"] == 90.0


def test_place_rejects_without_position():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    r = CO.place(p, m, tk, "stop", 90.0)
    assert r["ok"] is False
    assert r["reason"] == "noposition"


def test_place_rejects_invalid_kind():
    p, m, tk = _held_position()
    r = CO.place(p, m, tk, "bogus", 90.0)
    assert r["ok"] is False
    assert r["reason"] == "kind"


def test_place_rejects_non_positive_trigger():
    p, m, tk = _held_position()
    r = CO.place(p, m, tk, "stop", 0.0)
    assert r["ok"] is False
    assert r["reason"] == "trigger"
    r = CO.place(p, m, tk, "stop", -5.0)
    assert r["ok"] is False


def test_place_clamps_qty_to_held_shares():
    p, m, tk = _held_position(qty=100)
    r = CO.place(p, m, tk, "target", 150.0, qty=9999)
    assert r["ok"] is True
    assert r["order"]["qty"] == 100.0


def test_place_ids_increment():
    p, m, tk = _held_position()
    r1 = CO.place(p, m, tk, "stop", 80.0)
    r2 = CO.place(p, m, tk, "target", 120.0)
    assert r2["order"]["id"] == r1["order"]["id"] + 1


# ------------------------------------------------------------------- cancel()
def test_cancel_removes_order():
    p, m, tk = _held_position()
    r = CO.place(p, m, tk, "stop", 80.0)
    oid = r["order"]["id"]
    assert CO.cancel(p, oid) is True
    assert p.conditional_orders == []


def test_cancel_unknown_id_returns_false():
    p, m, tk = _held_position()
    CO.place(p, m, tk, "stop", 80.0)
    assert CO.cancel(p, 999) is False
    assert len(p.conditional_orders) == 1


# --------------------------------------------------------------- execute_due()
def test_stop_loss_executes_when_price_falls_to_or_below_trigger():
    p, m, tk = _held_position(qty=100, price=100.0)
    CO.place(p, m, tk, "stop", 90.0)
    _set_price(m, tk, 85.0)
    executed = CO.execute_due(p, m)
    assert len(executed) == 1
    assert executed[0]["order"]["ticker"] == tk
    assert executed[0]["result"]["ok"] is True
    assert tk not in p.portfolio            # position entière vendue (qty="ALL")
    assert p.conditional_orders == []        # ordre à usage unique, retiré


def test_stop_loss_does_not_execute_above_trigger():
    p, m, tk = _held_position(qty=100, price=100.0)
    CO.place(p, m, tk, "stop", 90.0)
    _set_price(m, tk, 95.0)
    executed = CO.execute_due(p, m)
    assert executed == []
    assert len(p.conditional_orders) == 1
    assert tk in p.portfolio


def test_take_profit_executes_when_price_rises_to_or_above_trigger():
    p, m, tk = _held_position(qty=100, price=100.0)
    CO.place(p, m, tk, "target", 120.0)
    _set_price(m, tk, 125.0)
    executed = CO.execute_due(p, m)
    assert len(executed) == 1
    assert executed[0]["result"]["realized"] > 0
    assert tk not in p.portfolio


def test_execute_due_triggers_exactly_at_threshold():
    p, m, tk = _held_position(qty=100, price=100.0)
    CO.place(p, m, tk, "stop", 90.0)
    _set_price(m, tk, 90.0)   # exactement au seuil -> déclenche (<=)
    executed = CO.execute_due(p, m)
    assert len(executed) == 1


def test_execute_due_drops_order_silently_if_position_closed_elsewhere():
    p, m, tk = _held_position(qty=100, price=100.0)
    CO.place(p, m, tk, "stop", 90.0)
    pf.sell(p, m, tk, "ALL")                 # vente manuelle, hors ordre conditionnel
    _set_price(m, tk, 50.0)                  # aurait déclenché si la position existait encore
    executed = CO.execute_due(p, m)
    assert executed == []
    assert p.conditional_orders == []        # abandonné silencieusement


def test_execute_due_partial_qty_leaves_remaining_position():
    p, m, tk = _held_position(qty=100, price=100.0)
    CO.place(p, m, tk, "stop", 90.0, qty=40)
    _set_price(m, tk, 85.0)
    executed = CO.execute_due(p, m)
    assert len(executed) == 1
    assert executed[0]["result"]["qty"] == 40
    assert p.portfolio[tk]["shares"] == pytest.approx(60.0)


def test_execute_due_empty_when_no_orders():
    p, m, tk = _held_position()
    assert CO.execute_due(p, m) == []


def test_for_ticker_filters_by_ticker():
    p, m, tk = _held_position()
    CO.place(p, m, tk, "stop", 80.0)
    CO.place(p, m, tk, "target", 120.0)
    assert len(CO.for_ticker(p, tk)) == 2
    assert CO.for_ticker(p, "NOPE") == []


# ------------------------------------------------------- intégration advance_step
def test_advance_step_executes_conditional_orders_and_reports_them():
    from core.game_state import GameState
    p, m, tk = _held_position(qty=100, price=100.0)
    CO.place(p, m, tk, "stop", 90.0)
    _set_price(m, tk, 80.0)
    gs = GameState()
    gs.player = p
    summary = gs.advance_step(m)
    executed = summary["conditional_orders_executed"]
    assert executed is not None and len(executed) == 1
    assert executed[0]["order"]["ticker"] == tk
    assert tk not in p.portfolio
