"""Tests du desk d'options sur actions individuelles (core/options.py)."""
from core import options as O, market
from core.game_state import PlayerState


def _mk():
    m = market.Market(seed=7)
    m.sync_to(market.WARMUP_STEPS)
    p = PlayerState(continent="Europe")
    p.cash = 1_000_000.0
    return p, m


def _first_ticker(m):
    return m.companies[0]["ticker"]


def test_quote_returns_expected_fields():
    p, m = _mk()
    tk = _first_ticker(m)
    q = O.quote(p, m, tk, "call", 1.00, 0.5)
    assert q["ok"] is True
    for key in ("ticker", "option_type", "spot", "strike", "sigma", "rate", "premium"):
        assert key in q
    assert q["premium"] > 0
    assert q["strike"] == q["spot"] * 1.00


def test_quote_unknown_ticker_fails():
    p, m = _mk()
    q = O.quote(p, m, "NOPE_TICKER", "call", 1.00, 0.5)
    assert q["ok"] is False
    assert q["reason"] == "ticker"


def test_quote_otm_call_is_cheaper_than_itm():
    p, m = _mk()
    tk = _first_ticker(m)
    itm = O.quote(p, m, tk, "call", 0.90, 0.5)
    otm = O.quote(p, m, tk, "call", 1.10, 0.5)
    assert otm["premium"] < itm["premium"]


def test_buy_debits_cash_and_creates_position():
    p, m = _mk()
    tk = _first_ticker(m)
    cash0 = p.cash
    r = O.buy(p, m, tk, "call", 1.00, 0.5, 100)
    assert r["ok"] is True
    assert p.cash == cash0 - r["premium"]
    assert len(p.options) == 1
    assert p.options[0]["contracts"] == 100.0
    assert p.options[0]["ticker"] == tk
    assert p.options[0]["option_type"] == "call"


def test_buy_rejects_invalid_contracts():
    p, m = _mk()
    tk = _first_ticker(m)
    r = O.buy(p, m, tk, "put", 1.00, 0.5, 0)
    assert r["ok"] is False
    assert r["reason"] == "contracts"
    r2 = O.buy(p, m, tk, "put", 1.00, 0.5, -5)
    assert r2["ok"] is False
    assert r2["reason"] == "contracts"


def test_buy_rejects_invalid_option_type():
    p, m = _mk()
    tk = _first_ticker(m)
    r = O.buy(p, m, tk, "strangle", 1.00, 0.5, 10)
    assert r["ok"] is False
    assert r["reason"] == "option_type"


def test_buy_rejects_insufficient_cash():
    p, m = _mk()
    tk = _first_ticker(m)
    p.cash = 0.0
    r = O.buy(p, m, tk, "call", 1.00, 0.5, 100)
    assert r["ok"] is False
    assert r["reason"] == "cash"
    assert p.options == []


def test_buy_rejects_unknown_ticker():
    p, m = _mk()
    r = O.buy(p, m, "NOPE_TICKER", "call", 1.00, 0.5, 10)
    assert r["ok"] is False
    assert r["reason"] == "ticker"


def test_evaluate_due_keeps_position_not_yet_matured():
    p, m = _mk()
    tk = _first_ticker(m)
    O.buy(p, m, tk, "call", 1.00, 1.0, 10)
    results = O.evaluate_due(p, m)
    assert results == []
    assert len(p.options) == 1


def _set_price(m, ticker, value):
    i = m.ticker_idx[ticker]
    m.price[i] = value


def test_evaluate_due_call_pays_out_in_the_money():
    p, m = _mk()
    tk = _first_ticker(m)
    O.buy(p, m, tk, "call", 1.00, 0.25, 10)
    pos = p.options[0]
    strike = pos["strike"]
    _set_price(m, tk, strike * 2.0)
    m.step_count = pos["maturity_step"]
    cash_before = p.cash
    results = O.evaluate_due(p, m)
    assert len(results) == 1
    res = results[0]
    assert res["payoff"] > 0
    assert res["payoff"] == (strike * 2.0 - strike) * 10
    assert p.cash == cash_before + res["payoff"]
    assert p.options == []


def test_evaluate_due_call_expires_worthless_out_of_the_money():
    p, m = _mk()
    tk = _first_ticker(m)
    O.buy(p, m, tk, "call", 1.00, 0.25, 10)
    pos = p.options[0]
    strike = pos["strike"]
    _set_price(m, tk, strike * 0.5)
    m.step_count = pos["maturity_step"]
    cash_before = p.cash
    results = O.evaluate_due(p, m)
    assert len(results) == 1
    assert results[0]["payoff"] == 0.0
    assert p.cash == cash_before
    assert p.options == []


def test_evaluate_due_put_pays_out_in_the_money():
    p, m = _mk()
    tk = _first_ticker(m)
    O.buy(p, m, tk, "put", 1.00, 0.25, 10)
    pos = p.options[0]
    strike = pos["strike"]
    _set_price(m, tk, strike * 0.5)
    m.step_count = pos["maturity_step"]
    cash_before = p.cash
    results = O.evaluate_due(p, m)
    assert len(results) == 1
    res = results[0]
    assert res["payoff"] > 0
    assert res["payoff"] == (strike - strike * 0.5) * 10
    assert p.cash == cash_before + res["payoff"]
    assert p.options == []


def test_evaluate_due_put_expires_worthless_out_of_the_money():
    p, m = _mk()
    tk = _first_ticker(m)
    O.buy(p, m, tk, "put", 1.00, 0.25, 10)
    pos = p.options[0]
    strike = pos["strike"]
    _set_price(m, tk, strike * 2.0)
    m.step_count = pos["maturity_step"]
    cash_before = p.cash
    results = O.evaluate_due(p, m)
    assert len(results) == 1
    assert results[0]["payoff"] == 0.0
    assert p.cash == cash_before
    assert p.options == []


def test_holdings_lists_open_positions():
    p, m = _mk()
    tk = _first_ticker(m)
    O.buy(p, m, tk, "call", 0.95, 0.5, 50)
    hold = O.holdings(p, m)
    assert len(hold) == 1
    assert hold[0]["contracts"] == 50.0
    assert hold[0]["strike_pct"] == 0.95
    assert hold[0]["ticker"] == tk
    assert hold[0]["option_type"] == "call"


def test_holdings_value_positive_for_open_position():
    p, m = _mk()
    tk = _first_ticker(m)
    O.buy(p, m, tk, "put", 1.00, 0.5, 10)
    val = O.holdings_value(p, m)
    assert val > 0


def test_holdings_value_zero_without_positions():
    p, m = _mk()
    assert O.holdings_value(p, m) == 0.0
