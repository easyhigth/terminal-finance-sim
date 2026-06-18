"""Tests de la couverture par put protecteur (core/hedging.py)."""
from core import hedging as H, market
from core.game_state import PlayerState


def _mk():
    m = market.Market(seed=7)
    m.sync_to(market.WARMUP_STEPS)
    p = PlayerState(continent="Europe")
    p.cash = 1_000_000.0
    return p, m


def test_quote_returns_expected_fields():
    p, m = _mk()
    q = H.quote(p, m, 1.00, 0.5)
    for key in ("underlying", "spot", "strike", "sigma", "rate", "premium_rate"):
        assert key in q
    assert q["premium_rate"] > 0
    assert q["strike"] == q["spot"] * 1.00


def test_quote_otm_put_is_cheaper_than_atm():
    p, m = _mk()
    atm = H.quote(p, m, 1.00, 0.5)
    otm = H.quote(p, m, 0.90, 0.5)
    assert otm["premium_rate"] < atm["premium_rate"]


def test_buy_put_debits_cash_and_creates_position():
    p, m = _mk()
    cash0 = p.cash
    r = H.buy_put(p, m, 100_000.0, 1.00, 0.5)
    assert r["ok"] is True
    assert p.cash == cash0 - r["premium"]
    assert len(p.hedges) == 1
    assert p.hedges[0]["notional"] == 100_000.0


def test_buy_put_rejects_non_positive_notional():
    p, m = _mk()
    r = H.buy_put(p, m, 0.0, 1.00, 0.5)
    assert r["ok"] is False
    assert r["reason"] == "notional"


def test_buy_put_rejects_insufficient_cash():
    p, m = _mk()
    p.cash = 0.0
    r = H.buy_put(p, m, 100_000.0, 1.00, 0.5)
    assert r["ok"] is False
    assert r["reason"] == "cash"
    assert p.hedges == []


def test_evaluate_due_keeps_position_not_yet_matured():
    p, m = _mk()
    H.buy_put(p, m, 100_000.0, 1.00, 1.0)
    results = H.evaluate_due(p, m)
    assert results == []
    assert len(p.hedges) == 1


def _scale_index(m, idx, factor):
    """Force le niveau de l'indice `idx` en repondérant le prix de ses constituants."""
    members = m.index_members[idx]
    m.price[members] *= factor


def test_evaluate_due_pays_out_when_in_the_money():
    p, m = _mk()
    H.buy_put(p, m, 100_000.0, 1.00, 0.25)
    pos = p.hedges[0]
    idx = pos["underlying"]
    # force l'indice sous le strike à l'échéance
    _scale_index(m, idx, 0.5)
    m.step_count = pos["maturity_step"]
    cash_before = p.cash
    results = H.evaluate_due(p, m)
    assert len(results) == 1
    res = results[0]
    assert res["payoff"] > 0
    assert p.cash == cash_before + res["payoff"]
    assert p.hedges == []


def test_evaluate_due_expires_worthless_when_out_of_the_money():
    p, m = _mk()
    H.buy_put(p, m, 100_000.0, 1.00, 0.25)
    pos = p.hedges[0]
    idx = pos["underlying"]
    _scale_index(m, idx, 2.0)
    m.step_count = pos["maturity_step"]
    cash_before = p.cash
    results = H.evaluate_due(p, m)
    assert len(results) == 1
    assert results[0]["payoff"] == 0.0
    assert p.cash == cash_before
    assert p.hedges == []


def test_holdings_lists_open_positions():
    p, m = _mk()
    H.buy_put(p, m, 50_000.0, 0.95, 0.5)
    hold = H.holdings(p, m)
    assert len(hold) == 1
    assert hold[0]["notional"] == 50_000.0
    assert hold[0]["strike_pct"] == 0.95


def test_coverage_ratio_zero_without_positions_or_exposure():
    p, m = _mk()
    assert H.coverage_ratio(p, m) == 0.0
