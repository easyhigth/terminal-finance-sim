"""Tests de l'arbitrage de fusion (core/merger_arb.py) : déterminisme des
opérations et des issues, économie de l'entrée/résolution (conclusion = gain
au prix d'offre, rupture = perte), MTM qui converge vers l'offre, intégration
save-safe (evaluate_due dans advance_step + holdings_value dans net_worth)."""
import random

import pytest

from core import merger_arb as MA
from core.game_state import PlayerState
from core.market import Market


@pytest.fixture()
def market():
    m = Market(seed=42)
    m.sync_to(60)
    return m


def _player():
    p = PlayerState()
    p.cash = 10_000_000.0
    return p


def _first_active(m, max_steps=60):
    for _ in range(max_steps):
        sits = MA.active_situations(m)
        if sits:
            return sits[0]
        m.step()
    return None


# ---------------------------------------------------------------- déterminisme
def test_situations_are_deterministic_for_a_seed(market):
    a = MA.active_situations(market)
    b = MA.active_situations(market)
    assert [s["id"] for s in a] == [s["id"] for s in b]
    assert [s["ticker"] for s in a] == [s["ticker"] for s in b]


def test_deal_outcome_is_stable(market):
    for i in range(0, 12):
        assert MA.deal_outcome(market.seed, i, market.n) == \
               MA.deal_outcome(market.seed, i, market.n)


def test_active_situations_are_within_their_window(market):
    for _ in range(30):
        for s in MA.active_situations(market):
            assert s["announce_step"] <= market.step_count <= s["resolve_step"]
            assert s["steps_left"] >= 0
        market.step()


def test_offer_is_above_undisturbed_and_implied_below_offer(market):
    s = _first_active(market)
    assert s is not None
    assert s["offer"] > s["undisturbed"]
    assert s["implied"] <= s["offer"]           # on paie sous l'offre (deal spread)
    assert s["implied"] >= s["undisturbed"]     # mais au-dessus du cours pré-deal


# ------------------------------------------------------------------- position
def test_enter_debits_cash_and_records_position(market):
    p = _player()
    s = _first_active(market)
    cash0 = p.cash
    r = MA.enter(p, market, s["id"], 100)
    assert r["ok"]
    assert p.cash == pytest.approx(cash0 - r["cost"])
    assert len(p.arb_positions) == 1


def test_enter_rejects_insufficient_cash(market):
    p = _player()
    p.cash = 1.0
    s = _first_active(market)
    assert not MA.enter(p, market, s["id"], 100)["ok"]


def test_enter_rejects_duplicate_deal(market):
    p = _player()
    s = _first_active(market)
    assert MA.enter(p, market, s["id"], 10)["ok"]
    assert MA.enter(p, market, s["id"], 10)["reason"] == "deja"


def test_mtm_converges_toward_offer_near_resolution(market):
    p = _player()
    s = _first_active(market)
    MA.enter(p, market, s["id"], 100)
    pos = p.arb_positions[0]
    early = MA.mark_to_market(pos, market)["price"]
    # avance presque jusqu'à la résolution
    while market.step_count < pos["resolve_step"]:
        market.step()
    late = MA.mark_to_market(pos, market)["price"]
    assert abs(late - pos["offer"]) <= abs(early - pos["offer"])


def test_holdings_value_matches_sum_of_positions(market):
    p = _player()
    s = _first_active(market)
    MA.enter(p, market, s["id"], 100)
    assert MA.holdings_value(p, market) == pytest.approx(
        MA.mark_to_market(p.arb_positions[0], market)["value"])


# ------------------------------------------------------------------ résolution
def test_close_pays_offer_price(market):
    p = _player()
    s = _first_active(market)
    # cherche une opération qui SE CONCLUT
    while not MA.deal_outcome(market.seed, s["id"], market.n):
        market.step()
        s = _first_active(market)
    MA.enter(p, market, s["id"], 100)
    pos = p.arb_positions[0]
    offer = pos["offer"]
    while market.step_count < pos["resolve_step"]:
        market.step()
    due = MA.evaluate_due(p, market)
    assert len(due) == 1 and due[0]["closed"]
    assert due[0]["proceeds"] == pytest.approx(offer * 100)
    assert due[0]["pnl"] > 0
    assert p.arb_positions == []


def test_break_produces_a_loss():
    # graine connue avec une rupture (cf. exploration manuelle)
    m = Market(seed=3)
    m.sync_to(60)
    p = _player()
    broke = False
    for _ in range(60):
        for s in MA.active_situations(m):
            if not MA.deal_outcome(m.seed, s["id"], m.n) and not p.arb_positions:
                MA.enter(p, m, s["id"], 50)
                pos = p.arb_positions[0]
                while m.step_count < pos["resolve_step"]:
                    m.step()
                due = MA.evaluate_due(p, m)
                assert due and not due[0]["closed"]
                assert due[0]["pnl"] < 0
                broke = True
                break
        if broke:
            break
        m.step()
    assert broke


def test_exit_position_returns_mtm(market):
    p = _player()
    s = _first_active(market)
    MA.enter(p, market, s["id"], 100)
    pos_id = p.arb_positions[0]["id"]
    cash_before = p.cash
    r = MA.exit_position(p, market, pos_id)
    assert r["ok"]
    assert p.cash > cash_before
    assert p.arb_positions == []


# --------------------------------------------------------------- intégration
def test_advance_step_resolves_and_notifies():
    from core.game_state import GameState
    gs = GameState()
    gs.player.cash = 10_000_000.0
    m = Market(seed=42)
    m.sync_to(60)
    gs.market_seed = m.seed
    s = _first_active(m)
    while not MA.deal_outcome(m.seed, s["id"], m.n):
        m.step()
        s = _first_active(m)
    MA.enter(gs.player, m, s["id"], 50)
    resolve = gs.player.arb_positions[0]["resolve_step"]
    # mirroir du drain réel du terminal : on avance le marché PUIS on applique
    # les conséquences du pas (advance_step ne fait pas avancer le marché).
    while m.step_count < resolve:
        m.step()
        gs.advance_step(market=m)
    assert gs.player.arb_positions == []


def test_net_worth_includes_arb_positions(market):
    from core import portfolio_margin as pm
    p = _player()
    nw0 = pm.net_worth(p, market)
    s = _first_active(market)
    MA.enter(p, market, s["id"], 100)
    nw1 = pm.net_worth(p, market)
    # cash converti en position d'arb : la valeur nette est ~conservée
    assert nw1 == pytest.approx(nw0, rel=0.02)
