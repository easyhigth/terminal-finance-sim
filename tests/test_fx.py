"""Tests du desk FX (core/fx.py) : spot, forward, déterminisme, gating."""
from core import fx as FX, market
from core.game_state import PlayerState


def _mk(grade_index=0):
    m = market.Market(seed=7)
    m.sync_to(market.WARMUP_STEPS)
    p = PlayerState(continent="Europe")
    p.cash = 1_000_000.0
    p.grade_index = grade_index
    return p, m


# ---------------------------------------------------------------- déterminisme
def test_spot_is_deterministic_for_same_seed_and_step():
    m1 = market.Market(seed=42)
    m1.sync_to(20)
    m2 = market.Market(seed=42)
    m2.sync_to(20)
    for pair in FX.PAIRS:
        assert FX.spot(m1, pair) == FX.spot(m2, pair)


def test_spot_differs_across_pairs():
    m = market.Market(seed=42)
    m.sync_to(20)
    values = {FX.spot(m, pair) for pair in FX.PAIRS}
    assert len(values) > 1


def test_spot_differs_with_different_seed():
    m1 = market.Market(seed=1)
    m1.sync_to(10)
    m2 = market.Market(seed=2)
    m2.sync_to(10)
    pair = FX.PAIRS[0]
    assert FX.spot(m1, pair) != FX.spot(m2, pair)


def test_quote_spot_returns_expected_fields():
    p, m = _mk()
    q = FX.quote_spot(m, "EUR/USD")
    assert q["ok"] is True
    for key in ("pair", "spot", "vol"):
        assert key in q


# ---------------------------------------------------------------- spot positions
def test_open_spot_does_not_debit_cash():
    p, m = _mk()
    cash0 = p.cash
    r = FX.open_spot(p, m, "EUR/USD", "long", 50000)
    assert r["ok"] is True
    assert p.cash == cash0
    assert len(p.fx_positions) == 1
    assert p.fx_positions[0]["pair"] == "EUR/USD"
    assert p.fx_positions[0]["direction"] == "long"


def test_open_spot_rejects_bad_inputs():
    p, m = _mk()
    assert FX.open_spot(p, m, "NOPE", "long", 1000)["ok"] is False
    assert FX.open_spot(p, m, "EUR/USD", "sideways", 1000)["ok"] is False
    assert FX.open_spot(p, m, "EUR/USD", "long", 0)["ok"] is False


def test_mark_to_market_long_profits_when_rate_rises():
    p, m = _mk()
    FX.open_spot(p, m, "EUR/USD", "long", 100000)
    pos = p.fx_positions[0]
    pos["entry_rate"] = 1.0  # force un point d'entrée connu
    # simule une hausse du taux
    cur = FX.spot(m, "EUR/USD")
    pos["entry_rate"] = cur * 0.9   # entrée plus basse que le spot courant -> gain en long
    pnl = FX.mark_to_market(p, m, pos)
    assert pnl > 0


def test_mark_to_market_short_profits_when_rate_falls():
    p, m = _mk()
    FX.open_spot(p, m, "EUR/USD", "short", 100000)
    pos = p.fx_positions[0]
    cur = FX.spot(m, "EUR/USD")
    pos["entry_rate"] = cur * 1.1   # entrée plus haute que le spot courant -> gain en short
    pnl = FX.mark_to_market(p, m, pos)
    assert pnl > 0


def test_close_spot_credits_cash_with_realized_pnl():
    p, m = _mk()
    FX.open_spot(p, m, "EUR/USD", "long", 100000)
    pos = p.fx_positions[0]
    cur = FX.spot(m, "EUR/USD")
    pos["entry_rate"] = cur * 0.9
    expected_pnl = FX.mark_to_market(p, m, pos)
    cash0 = p.cash
    r = FX.close_spot(p, m, 0)
    assert r["ok"] is True
    assert abs(r["pnl"] - expected_pnl) < 1e-9
    assert p.cash == cash0 + expected_pnl
    assert len(p.fx_positions) == 0


def test_close_spot_invalid_id_fails():
    p, m = _mk()
    r = FX.close_spot(p, m, 0)
    assert r["ok"] is False


def test_holdings_value_sums_latent_pnl():
    p, m = _mk()
    FX.open_spot(p, m, "EUR/USD", "long", 100000)
    FX.open_spot(p, m, "USD/JPY", "short", 50000)
    total = sum(FX.mark_to_market(p, m, pos) for pos in p.fx_positions)
    assert abs(FX.holdings_value(p, m) - total) < 1e-9


# ---------------------------------------------------------------- gating forward
def test_forward_unlocked_false_without_grade():
    p, m = _mk(grade_index=0)
    assert FX.forward_unlocked(p) is False


def test_forward_unlocked_true_with_sufficient_grade():
    p, m = _mk(grade_index=FX.FORWARD_MIN_GRADE)
    assert FX.forward_unlocked(p) is True


def test_open_forward_rejected_when_locked():
    p, m = _mk(grade_index=0)
    r = FX.open_forward(p, m, "EUR/USD", "long", 50000, 3)
    assert r["ok"] is False
    assert r["reason"] == "locked"


# ---------------------------------------------------------------- forward trading
def test_open_forward_no_cash_debit_when_unlocked():
    p, m = _mk(grade_index=FX.FORWARD_MIN_GRADE)
    cash0 = p.cash
    r = FX.open_forward(p, m, "EUR/USD", "long", 50000, 3)
    assert r["ok"] is True
    assert p.cash == cash0
    assert len(p.fx_forwards) == 1
    pos = p.fx_forwards[0]
    assert pos["locked_rate"] > 0
    assert pos["maturity_step"] > m.step_count


def test_evaluate_due_settles_at_maturity_long():
    p, m = _mk(grade_index=FX.FORWARD_MIN_GRADE)
    FX.open_forward(p, m, "EUR/USD", "long", 100000, 1)
    pos = p.fx_forwards[0]
    pos["locked_rate"] = FX.spot(m, "EUR/USD") * 0.9  # verrouillé bas -> gain en long si spot monte
    pos["maturity_step"] = m.step_count  # échéance immédiate pour le test
    cash0 = p.cash
    results = FX.evaluate_due(p, m)
    assert len(results) == 1
    assert results[0]["pnl"] > 0
    assert p.cash == cash0 + results[0]["payoff"]
    assert len(p.fx_forwards) == 0


def test_evaluate_due_settles_at_maturity_short():
    p, m = _mk(grade_index=FX.FORWARD_MIN_GRADE)
    FX.open_forward(p, m, "EUR/USD", "short", 100000, 1)
    pos = p.fx_forwards[0]
    pos["locked_rate"] = FX.spot(m, "EUR/USD") * 1.1  # verrouillé haut -> gain en short si spot baisse
    pos["maturity_step"] = m.step_count
    results = FX.evaluate_due(p, m)
    assert len(results) == 1
    assert results[0]["pnl"] > 0


def test_evaluate_due_keeps_unexpired_positions():
    p, m = _mk(grade_index=FX.FORWARD_MIN_GRADE)
    FX.open_forward(p, m, "EUR/USD", "long", 100000, 6)
    results = FX.evaluate_due(p, m)
    assert results == []
    assert len(p.fx_forwards) == 1


def test_quote_forward_rejects_unknown_tenor():
    p, m = _mk()
    q = FX.quote_forward(m, "EUR/USD", 99)
    assert q["ok"] is False
