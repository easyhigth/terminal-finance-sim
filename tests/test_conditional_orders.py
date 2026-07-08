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


# =========================================================================
# Positions COURTES (short) — les shorts vivent dans player.portfolio avec
# un nombre de titres NÉGATIF (core/portfolio.short), pas dans un dict à part
# =========================================================================
def _short_position(cash=1_000_000.0, qty=100, price=100.0):
    p, m = _setup(cash)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, price)
    r = pf.short(p, m, tk, qty)
    assert r["ok"], r
    return p, m, tk


def test_place_stop_on_short_position():
    p, m, tk = _short_position()
    r = CO.place(p, m, tk, "stop", 110.0)
    assert r["ok"] is True
    assert p.conditional_orders[0]["is_short"] is True


def test_short_stop_executes_when_price_rises_to_trigger():
    """Stop-loss sur short : couvre quand le cours MONTE au seuil."""
    p, m, tk = _short_position(price=100.0)
    CO.place(p, m, tk, "stop", 110.0)
    _set_price(m, tk, 112.0)
    executed = CO.execute_due(p, m)
    assert len(executed) == 1
    assert tk not in p.portfolio            # position couverte intégralement
    assert p.conditional_orders == []


def test_short_stop_does_not_execute_below_trigger():
    p, m, tk = _short_position(price=100.0)
    CO.place(p, m, tk, "stop", 110.0)
    _set_price(m, tk, 105.0)
    assert CO.execute_due(p, m) == []
    assert len(p.conditional_orders) == 1


def test_short_target_executes_when_price_falls_to_trigger():
    """Take-profit sur short : couvre quand le cours BAISSE au seuil."""
    p, m, tk = _short_position(price=100.0)
    CO.place(p, m, tk, "target", 90.0)
    _set_price(m, tk, 88.0)
    executed = CO.execute_due(p, m)
    assert len(executed) == 1
    assert tk not in p.portfolio


def test_short_order_abandoned_if_position_flipped_to_long():
    """Un ordre posé sur un short est abandonné si la position a changé de
    côté entre-temps (couverte puis rachetée en long) — jamais d'exécution
    sur une position qui n'est plus celle visée."""
    p, m, tk = _short_position(price=100.0)
    CO.place(p, m, tk, "stop", 110.0)
    pf.cover(p, m, tk, "ALL")
    pf.buy(p, m, tk, 50)                    # maintenant LONG
    _set_price(m, tk, 120.0)
    assert CO.execute_due(p, m) == []
    assert p.conditional_orders == []       # ordre retiré silencieusement
    assert p.portfolio[tk]["shares"] == 50  # le long n'a pas été touché


def test_place_clamps_qty_to_short_size():
    p, m, tk = _short_position(qty=100)
    r = CO.place(p, m, tk, "stop", 110.0, qty=500)
    assert r["ok"] is True
    assert r["order"]["qty"] == 100.0


# =========================================================================
# Trailing stops — sémantique de STOP (le seuil suit le cours), jamais
# d'exécution immédiate côté favorable
# =========================================================================
def test_trailing_stop_long_does_not_fire_immediately():
    p, m, tk = _held_position(price=100.0)
    r = CO.place_trailing(p, m, tk, 5.0)
    assert r["ok"] is True
    # cours inchangé : le seuil est 5% SOUS le cours, rien ne doit partir
    assert CO.execute_due(p, m) == []
    assert len(p.conditional_orders) == 1


def test_trailing_stop_long_follows_price_up_then_fires_on_drawdown():
    p, m, tk = _held_position(price=100.0)
    CO.place_trailing(p, m, tk, 5.0)
    _set_price(m, tk, 120.0)                # le stop remonte à 114
    CO.update_trailing_stops(p, m)
    assert CO.execute_due(p, m) == []       # toujours au-dessus du seuil
    assert p.conditional_orders[0]["trigger"] == pytest.approx(114.0)
    _set_price(m, tk, 113.0)                # retombe sous 114 : vend
    CO.update_trailing_stops(p, m)
    executed = CO.execute_due(p, m)
    assert len(executed) == 1
    assert tk not in p.portfolio


def test_trailing_stop_short_does_not_fire_immediately():
    p, m, tk = _short_position(price=100.0)
    r = CO.place_trailing(p, m, tk, 5.0)
    assert r["ok"] is True
    assert CO.execute_due(p, m) == []


def test_trailing_stop_short_follows_price_down_then_fires_on_rebound():
    p, m, tk = _short_position(price=100.0)
    CO.place_trailing(p, m, tk, 5.0)
    _set_price(m, tk, 80.0)                 # le stop descend à 84
    CO.update_trailing_stops(p, m)
    assert CO.execute_due(p, m) == []
    assert p.conditional_orders[0]["trigger"] == pytest.approx(84.0)
    _set_price(m, tk, 85.0)                 # rebond au-dessus de 84 : couvre
    CO.update_trailing_stops(p, m)
    executed = CO.execute_due(p, m)
    assert len(executed) == 1
    assert tk not in p.portfolio


def test_prune_orphans_drops_closed_and_flipped_positions():
    """Après une liquidation forcée (appel de marge, APRÈS execute_due dans
    advance_step), les ordres des positions fermées sont purgés immédiatement
    — un ordre périmé ne doit jamais s'appliquer à une position rouverte."""
    p, m, tk = _held_position()
    CO.place(p, m, tk, "stop", 90.0)
    tk2 = m.companies[1]["ticker"]
    _set_price(m, tk2, 50.0)
    pf.buy(p, m, tk2, 10)
    CO.place(p, m, tk2, "target", 60.0)
    # tk fermé « de force » (équivalent liquidation) ; tk2 conservé
    del p.portfolio[tk]
    CO.prune_orphans(p)
    assert [o["ticker"] for o in p.conditional_orders] == [tk2]
    # position retournée (long -> short) : l'ordre long est purgé aussi
    pf.sell(p, m, tk2, "ALL")
    pf.short(p, m, tk2, 5)
    CO.prune_orphans(p)
    assert p.conditional_orders == []


def test_execute_due_purges_earlier_orders_when_later_one_closes_position():
    """Régression : un ordre en FIN de liste qui clôture toute la position ne
    doit pas laisser survivre les ordres du même titre placés AVANT lui (déjà
    passés dans `remaining` quand la position existait encore) — ils
    pourraient s'exécuter plus tard sur une position rouverte."""
    p, m, tk = _held_position(price=100.0)
    CO.place(p, m, tk, "stop", 50.0)      # loin : ne se déclenche pas
    CO.place(p, m, tk, "target", 100.0)   # au cours : vend TOUT immédiatement
    executed = CO.execute_due(p, m)
    assert len(executed) == 1
    assert tk not in p.portfolio
    assert p.conditional_orders == []     # le stop n'a pas survécu
