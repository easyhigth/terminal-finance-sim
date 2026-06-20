"""Tests des matières premières et de leur courbe de futures (core/commodities.py)."""
import pytest

from core import commodities
from core.game_state import PlayerState
from core.market import Market


def _player(cash=50_000_000.0):
    p = PlayerState()
    p.cash = cash
    return p


# --------------------------------------------------------------- déterminisme
def test_spot_is_stable_for_same_market_state():
    m = Market(seed=42)
    a = commodities.spot(m, "GOLD")
    b = commodities.spot(m, "GOLD")
    assert a == b


def test_spot_changes_with_step_and_reconstructs_from_seed():
    a = Market(seed=42)
    s0 = commodities.spot(a, "GOLD")
    a.step()
    s1 = commodities.spot(a, "GOLD")
    assert s0 != s1

    # une nouvelle instance avec la même graine, avancée au même nombre de pas,
    # reproduit exactement le même spot (reconstruction via seed+step).
    b = Market(seed=42)
    b.step()
    assert commodities.spot(b, "GOLD") == s1


def test_different_seed_gives_different_spot():
    a = Market(seed=1); a.fast_forward(20)
    b = Market(seed=2); b.fast_forward(20)
    assert commodities.spot(a, "OIL") != commodities.spot(b, "OIL")


# --------------------------------------------------------------- futures_price
def test_futures_price_contango_increases_with_maturity():
    # OIL a un slope positif (0.06) -> contango : plus l'échéance est loin,
    # plus le future est cher que le spot.
    cid = "OIL"
    assert commodities._BY_ID[cid][5] > 0
    m = Market(seed=10)
    near = commodities.futures_price(m, cid, 1)
    far = commodities.futures_price(m, cid, 12)
    assert far > near > 0


def test_futures_price_backwardation_decreases_with_maturity():
    # GOLD a un slope négatif (-0.01) -> backwardation : le future à échéance
    # lointaine est moins cher que le proche.
    cid = "GOLD"
    assert commodities._BY_ID[cid][5] < 0
    m = Market(seed=10)
    near = commodities.futures_price(m, cid, 1)
    far = commodities.futures_price(m, cid, 12)
    assert far < near


def test_futures_price_flat_slope_equals_spot_at_all_maturities():
    # RIN a un slope nul -> la courbe est plate.
    cid = "RIN"
    assert commodities._BY_ID[cid][5] == 0
    m = Market(seed=10)
    sp = commodities.spot(m, cid)
    for mo in (1, 3, 6, 12):
        assert commodities.futures_price(m, cid, mo) == sp


# --------------------------------------------------------------- curve / roll_yield
def test_curve_returns_expected_maturities_and_prices():
    m = Market(seed=10)
    c = commodities.curve(m, "OIL")
    assert [mo for mo, _ in c] == [1, 3, 6, 12]
    for mo, price in c:
        assert price == commodities.futures_price(m, "OIL", mo)


def test_curve_custom_maturities():
    m = Market(seed=10)
    c = commodities.curve(m, "OIL", maturities=(2, 24))
    assert [mo for mo, _ in c] == [2, 24]


def test_roll_yield_is_negative_slope():
    for cid in ("OIL", "GOLD", "RIN"):
        slope = commodities._BY_ID[cid][5]
        m = Market(seed=10)
        assert commodities.roll_yield(m, cid) == -slope


def test_roll_yield_sign_matches_curve_structure():
    # contango (slope > 0) -> roll yield négatif ; backwardation -> positif.
    m = Market(seed=10)
    assert commodities.roll_yield(m, "OIL") < 0   # contango marqué
    assert commodities.roll_yield(m, "GOLD") > 0  # léger backwardation


# --------------------------------------------------------------- buy / sell
def test_buy_debits_cash_including_commission():
    p = _player(cash=1_000_000.0)
    m = Market(seed=10)
    cash_before = p.cash
    res = commodities.buy(p, m, "GOLD", 2)
    assert res["ok"]
    price = res["price"]
    expected_cost = price * commodities.MULTIPLIER * 2
    expected_fee = expected_cost * commodities.COMMISSION
    assert p.cash == cash_before - (expected_cost + expected_fee)
    assert res["total"] == expected_cost + expected_fee


def test_buy_creates_position_with_qty_and_avg():
    p = _player()
    m = Market(seed=10)
    commodities.buy(p, m, "GOLD", 3)
    pos = p.commodities["GOLD"]
    assert set(pos.keys()) == {"qty", "avg"}
    assert pos["qty"] == 3.0
    assert pos["avg"] == commodities.fill_price(m, "GOLD", 3, "buy")


def test_buy_twice_updates_average_price():
    p = _player()
    m = Market(seed=10)
    price1 = commodities.fill_price(m, "GOLD", 2, "buy")
    commodities.buy(p, m, "GOLD", 2)
    m.step()
    price2 = commodities.fill_price(m, "GOLD", 2, "buy")
    commodities.buy(p, m, "GOLD", 2)
    pos = p.commodities["GOLD"]
    assert pos["qty"] == 4.0
    assert pos["avg"] == (2 * price1 + 2 * price2) / 4


def test_buy_rejects_unknown_id():
    p = _player()
    m = Market(seed=10)
    assert commodities.buy(p, m, "NOPE", 1) == {"ok": False, "reason": "id"}


def test_buy_rejects_non_positive_qty():
    p = _player()
    m = Market(seed=10)
    assert commodities.buy(p, m, "GOLD", 0) == {"ok": False, "reason": "qty"}


def test_buy_rejects_insufficient_cash():
    p = _player(cash=1.0)
    m = Market(seed=10)
    res = commodities.buy(p, m, "GOLD", 1000)
    assert res == {"ok": False, "reason": "cash"}
    assert "GOLD" not in p.commodities


def test_sell_credits_cash_including_commission_and_realized_pnl():
    p = _player()
    m = Market(seed=10)
    commodities.buy(p, m, "GOLD", 5)
    cash_before = p.cash
    res = commodities.sell(p, m, "GOLD", 5)
    assert res["ok"]
    price = res["price"]
    proceeds = price * commodities.MULTIPLIER * 5
    fee = proceeds * commodities.COMMISSION
    assert p.cash == pytest.approx(cash_before + proceeds - fee)
    assert p.realized_pnl == res["realized"]


def test_sell_partial_reduces_qty_without_removing_position():
    p = _player()
    m = Market(seed=10)
    commodities.buy(p, m, "GOLD", 5)
    commodities.sell(p, m, "GOLD", 2)
    assert p.commodities["GOLD"]["qty"] == 3


def test_sell_full_position_removes_it():
    p = _player()
    m = Market(seed=10)
    commodities.buy(p, m, "GOLD", 5)
    commodities.sell(p, m, "GOLD", 5)
    assert "GOLD" not in p.commodities


def test_sell_all_keyword_closes_position():
    p = _player()
    m = Market(seed=10)
    commodities.buy(p, m, "GOLD", 5)
    res = commodities.sell(p, m, "GOLD", "ALL")
    assert res["ok"]
    assert "GOLD" not in p.commodities


def test_sell_more_than_held_caps_at_position_qty():
    p = _player()
    m = Market(seed=10)
    commodities.buy(p, m, "GOLD", 5)
    res = commodities.sell(p, m, "GOLD", 999)
    assert res["ok"]
    assert res["qty"] == 5
    assert "GOLD" not in p.commodities


def test_sell_without_position_fails():
    p = _player()
    m = Market(seed=10)
    assert commodities.sell(p, m, "GOLD", 1) == {"ok": False, "reason": "noposition"}


# --------------------------------------------------------------- holdings_value / roll_cost / holdings
def test_holdings_value_matches_sum_of_qty_times_spot():
    p = _player()
    m = Market(seed=10)
    commodities.buy(p, m, "GOLD", 2)
    commodities.buy(p, m, "OIL", 3)
    expected = (commodities.futures_price(m, "GOLD", 1) * commodities.MULTIPLIER * 2
                + commodities.futures_price(m, "OIL", 1) * commodities.MULTIPLIER * 3)
    assert commodities.holdings_value(p, m) == expected


def test_holdings_value_empty_portfolio_is_zero():
    p = _player()
    m = Market(seed=10)
    assert commodities.holdings_value(p, m) == 0.0


def test_roll_cost_negative_in_contango_position():
    p = _player()
    m = Market(seed=10)
    commodities.buy(p, m, "OIL", 5)  # contango -> roll yield négatif -> coût
    cost = commodities.roll_cost(p, m, 30)
    assert cost < 0


def test_roll_cost_positive_in_backwardation_position():
    p = _player()
    m = Market(seed=10)
    commodities.buy(p, m, "GOLD", 5)  # backwardation -> roll yield positif -> gain
    cost = commodities.roll_cost(p, m, 30)
    assert cost > 0


def test_roll_cost_scales_with_days():
    p = _player()
    m = Market(seed=10)
    commodities.buy(p, m, "OIL", 5)
    c30 = commodities.roll_cost(p, m, 30)
    c60 = commodities.roll_cost(p, m, 60)
    assert c60 == c30 * 2


def test_roll_cost_empty_portfolio_is_zero():
    p = _player()
    m = Market(seed=10)
    assert commodities.roll_cost(p, m, 30) == 0.0


def test_holdings_view_structure_and_sorted_by_value_desc():
    p = _player()
    m = Market(seed=10)
    commodities.buy(p, m, "GOLD", 1)
    commodities.buy(p, m, "OIL", 50)
    out = commodities.holdings(p, m)
    assert len(out) == 2
    expected_keys = {"id", "name", "qty", "avg", "price", "value", "pnl"}
    for h in out:
        assert set(h.keys()) == expected_keys
    # trié par valeur décroissante
    assert out[0]["value"] >= out[1]["value"]


def test_fill_price_more_expensive_for_illiquid_category():
    """Une matière première peu profonde (minéraux stratégiques) coûte plus
    cher à l'exécution qu'un métal précieux liquide, pour un même ordre (item 25/26)."""
    m = Market(seed=10)
    gold_mid = commodities.futures_price(m, "GOLD", 1)
    ree_mid = commodities.futures_price(m, "REE", 1)
    gold_fill = commodities.fill_price(m, "GOLD", 5, "buy")
    ree_fill = commodities.fill_price(m, "REE", 5, "buy")
    gold_cost_frac = gold_fill / gold_mid - 1
    ree_cost_frac = ree_fill / ree_mid - 1
    assert ree_cost_frac > gold_cost_frac
    assert commodities.quote(m, "GOLD")["liquidity"] == "Liquide"
    assert commodities.quote(m, "REE")["liquidity"] == "Illiquide"


def test_holdings_view_empty_when_no_positions():
    p = _player()
    m = Market(seed=10)
    assert commodities.holdings(p, m) == []


def test_fill_price_costs_more_under_market_stress():
    """Pour un même ordre, un marché en plein stress (last_stress_level proche de
    1.0) doit coûter plus cher à l'exécution qu'un marché calme — sur une matière
    première liquide comme sur une illiquide (item 9/15)."""
    m = Market(seed=10)
    for cid in ("GOLD", "REE"):
        m.last_stress_level = 0.0
        calm = commodities.fill_price(m, cid, 5, "buy")
        m.last_stress_level = 1.0
        stressed = commodities.fill_price(m, cid, 5, "buy")
        assert stressed > calm


def test_fill_price_deterministic_for_same_market_state():
    """Même état de marché (même stress) -> même prix d'exécution, à chaque appel."""
    m = Market(seed=10)
    m.last_stress_level = 0.35
    a = commodities.fill_price(m, "OIL", 10, "sell")
    b = commodities.fill_price(m, "OIL", 10, "sell")
    assert a == b
