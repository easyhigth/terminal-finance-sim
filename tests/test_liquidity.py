"""Tests du modèle de liquidité partagé (core/liquidity.py)."""
import pytest

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
    # unité : MILLIONS (comme market.price × market.shares / metrics mktcap)
    assert liq.equity_tier_for_cap(50e3) == "Liquide"      # 50 Md
    assert liq.equity_tier_for_cap(5e3) == "Peu liquide"   # 5 Md
    assert liq.equity_tier_for_cap(1e3) == "Illiquide"     # 1 Md


def test_equity_tier_spans_the_actual_roster():
    """Régression : les anciens seuils (en unités, pas en millions) étaient
    ×10⁶ trop hauts — TOUT le roster tombait en « Illiquide », spread max
    même pour les méga-capis. Les trois tiers doivent exister sur le vrai
    marché."""
    from core.market import Market
    m = Market(seed=29)
    tiers = {liq.equity_tier(m, c["ticker"]) for c in m.companies}
    assert tiers == {"Liquide", "Peu liquide", "Illiquide"}


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


# --------------------------------------------------------- stress (régime de marché)
def test_fill_price_stress_widens_spread_and_impact():
    """Même ordre, même tier de liquidité : un marché en plein stress (stress_level=1.0,
    cf. Market.last_stress_level) doit produire un coût d'exécution strictement plus
    élevé qu'un marché calme (stress_level=0.0) — sur chaque tier de liquidité."""
    mid, order_value, depth = 100.0, 1_000_000.0, 50_000_000.0
    for tier in liq.TIERS:
        calm = liq.fill_price(mid, order_value, depth, tier, "buy", stress_level=0.0)
        crisis = liq.fill_price(mid, order_value, depth, tier, "buy", stress_level=1.0)
        assert crisis > calm > mid


def test_fill_price_stress_level_is_clamped():
    """Un stress_level hors [0,1] (donnée corrompue/extrapolée) ne doit pas produire
    un coût négatif ou explosif au-delà du calibrage à stress maximal."""
    mid, order_value, depth = 100.0, 1_000_000.0, 50_000_000.0
    at_one = liq.fill_price(mid, order_value, depth, "Liquide", "buy", stress_level=1.0)
    above_one = liq.fill_price(mid, order_value, depth, "Liquide", "buy", stress_level=5.0)
    below_zero = liq.fill_price(mid, order_value, depth, "Liquide", "buy", stress_level=-2.0)
    at_zero = liq.fill_price(mid, order_value, depth, "Liquide", "buy", stress_level=0.0)
    assert above_one == pytest.approx(at_one)
    assert below_zero == pytest.approx(at_zero)


def test_fill_price_deterministic_given_same_inputs():
    """Même (mid, order_value, depth, tier, side, stress_level) -> même prix de fill,
    à chaque appel : aucun aléa non reproductible introduit par la sensibilité au
    régime/au stress (conforme au contrat de déterminisme du projet)."""
    args = (100.0, 250_000.0, 30_000_000.0, "Peu liquide", "sell", 0.6)
    assert liq.fill_price(*args) == liq.fill_price(*args)


def test_crypto_tier_liquid_stable_vs_illiquid_altcoin():
    assert liq.crypto_tier("USDX") == "Liquide"
    assert liq.crypto_tier("CBDC") == "Liquide"
    assert liq.crypto_tier("SOLR") == "Illiquide"
    assert liq.crypto_tier("DOGY") == "Illiquide"
    assert liq.crypto_depth("USDX") > liq.crypto_depth("DOGY")


def test_stress_effect_differs_by_asset_type_via_tier():
    """À stress de marché égal, un actif moins liquide (tier 'Illiquide', ex. crypto
    spéculative ou corporate high yield) doit rester plus coûteux à l'exécution
    qu'un actif liquide (tier 'Liquide', ex. souverain noté ou grande capi), et
    l'écart entre les deux doit se creuser sous stress plutôt que de se résorber."""
    mid, order_value, depth = 100.0, 1_000_000.0, 50_000_000.0
    calm_gap = (liq.fill_price(mid, order_value, depth, "Illiquide", "buy", 0.0)
                - liq.fill_price(mid, order_value, depth, "Liquide", "buy", 0.0))
    crisis_gap = (liq.fill_price(mid, order_value, depth, "Illiquide", "buy", 1.0)
                  - liq.fill_price(mid, order_value, depth, "Liquide", "buy", 1.0))
    assert calm_gap > 0
    assert crisis_gap > calm_gap
