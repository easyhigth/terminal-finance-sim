"""Tests du modèle de liquidité partagé (core/liquidity.py)."""
from core import liquidity as liq


def test_tier_params_increase_with_illiquidity():
    spreads = [liq.params(t)[0] for t in ("Liquide", "Peu liquide", "Illiquide")]
    impacts = [liq.params(t)[1] for t in ("Liquide", "Peu liquide", "Illiquide")]
    assert spreads == sorted(spreads)
    assert impacts == sorted(impacts)


def test_fill_price_buy_above_mid_sell_below_mid():
    mid = 100.0
    buy = liq.fill_price(mid, 1_000.0, 1_000_000.0, "Liquide", "buy")
    sell = liq.fill_price(mid, 1_000.0, 1_000_000.0, "Liquide", "sell")
    assert buy > mid > sell


def test_fill_price_impact_grows_with_order_size():
    mid = 100.0
    small = liq.fill_price(mid, 1_000.0, 1_000_000.0, "Peu liquide", "buy")
    big = liq.fill_price(mid, 900_000.0, 1_000_000.0, "Peu liquide", "buy")
    assert big > small > mid


def test_fill_price_capped_at_max_slippage():
    mid = 100.0
    huge = liq.fill_price(mid, 10 ** 12, 1.0, "Illiquide", "buy")
    half_spread, _ = liq.params("Illiquide")
    assert huge <= mid * (1 + half_spread + liq.MAX_SLIPPAGE) + 1e-6


def test_illiquid_tier_widens_spread_for_same_order():
    mid, order_value = 100.0, 50_000.0
    liquid = liq.fill_price(mid, order_value, 1e9, "Liquide", "buy")
    illiquid = liq.fill_price(mid, order_value, 1e9, "Illiquide", "buy")
    assert illiquid > liquid


def test_equity_tier_for_cap_thresholds():
    assert liq.equity_tier_for_cap(50e9) == "Liquide"
    assert liq.equity_tier_for_cap(5e9) == "Peu liquide"
    assert liq.equity_tier_for_cap(1e9) == "Illiquide"


def test_bond_tier_sovereign_vs_high_yield():
    sov = {"kind": "Souverain", "rating": "AAA"}
    corp_hy = {"kind": "Corporate", "rating": "B"}
    assert liq.bond_tier(sov) == "Liquide"
    assert liq.bond_tier(corp_hy) == "Illiquide"
    assert liq.bond_depth(sov) > liq.bond_depth(corp_hy)


def test_commodity_tier_energy_vs_strategic_minerals():
    assert liq.commodity_tier("Énergie") == "Liquide"
    assert liq.commodity_tier("Minéraux stratégiques") == "Illiquide"
    assert liq.commodity_depth("Énergie") > liq.commodity_depth("Minéraux stratégiques")
