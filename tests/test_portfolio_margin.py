"""Tests dédiés à core/portfolio_margin.py (levier, marge, financement).

core/portfolio.py réexporte cette API publique et tests/test_portfolio.py
l'exerce déjà indirectement via core.portfolio.xxx. Ici on importe le module
directement et on appelle ses fonctions, en s'appuyant sur core.portfolio
(buy/sell/short/cover) seulement pour construire des scénarios réalistes.
"""
import pytest

from core import portfolio as pf
from core import portfolio_margin as pm
from core.game_state import PlayerState
from core.market import Market


def _setup(grade_index=8, cash=1_000_000.0, track="General"):
    m = Market(seed=999)
    p = PlayerState()
    p.grade_index = grade_index
    p.cash = cash
    p.track = track
    return p, m


def _set_price(m, tk, price):
    m.price[m.ticker_idx[tk]] = price


# --------------------------------------------------------------- levier max
def test_max_leverage_scales_with_grade_and_caps_at_4x():
    assert pm.max_leverage(0) == pytest.approx(1.5)
    assert pm.max_leverage(0) < pm.max_leverage(6) <= pm.max_leverage(11)
    assert pm.max_leverage(11) == pytest.approx(4.0)
    # le plafond reste à 4x même pour un grade très élevé
    assert pm.max_leverage(50) == pytest.approx(4.0)


def test_private_max_leverage_includes_risk_track_perk():
    p_general, m = _setup(grade_index=4, track="General")
    p_risk, _ = _setup(grade_index=4, track="Risk")
    # la voie Risk ajoute +0.5 au levier max effectif
    assert pm._max_leverage(p_risk) == pytest.approx(pm._max_leverage(p_general) + 0.5)


def test_private_maint_margin_default_vs_risk_perk():
    p_general, _ = _setup(track="General")
    p_risk, _ = _setup(track="Risk")
    assert pm._maint_margin(p_general) == pytest.approx(pm.MAINT_MARGIN)
    # la voie Risk est plus clémente (0.20 < 0.25)
    assert pm._maint_margin(p_risk) == pytest.approx(0.20)
    assert pm._maint_margin(p_risk) < pm._maint_margin(p_general)


# --------------------------------------------------------------- net_worth / exposition
def test_net_worth_is_cash_plus_positions_value():
    p, m = _setup(cash=10_000.0)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 50.0)
    pf.buy(p, m, tk, 100)
    expected = p.cash + pm.positions_value(p, m)
    assert pm.net_worth(p, m) == pytest.approx(expected)


def test_net_worth_includes_all_asset_classes():
    """La valeur nette (= equity de base du levier/appel de marge) doit inclure
    options, FX et couvertures, pas seulement actions/obligations : sinon le
    levier d'un joueur long options/FX/hedges serait surévalué."""
    from core import fx, hedging, options
    p, m = _setup(grade_index=10, cash=500_000.0)
    base = pm.net_worth(p, m)
    assert base == pytest.approx(500_000.0)

    # une position FX spot ouverte (sans débit de cash) : son P&L latent compte
    pair = list(fx._BY_PAIR.keys())[0]
    fx.open_spot(p, m, pair, "long", 100_000.0)
    expected_fx = fx.holdings_value(p, m)
    assert pm.net_worth(p, m) == pytest.approx(base + expected_fx)

    # les helpers holdings_value des trois classes sont bien rebranchés
    assert hasattr(options, "holdings_value")
    assert hasattr(hedging, "holdings_value")


def test_positions_value_is_signed_long_vs_short():
    p_long, m = _setup(cash=100_000.0)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.buy(p_long, m, tk, 50)
    assert pm.positions_value(p_long, m) == pytest.approx(100.0 * 50)

    p_short, m2 = _setup(cash=100_000.0)
    tk2 = m2.companies[0]["ticker"]
    _set_price(m2, tk2, 100.0)
    pf.short(p_short, m2, tk2, 50)
    assert pm.positions_value(p_short, m2) == pytest.approx(-100.0 * 50)


def test_gross_exposure_sums_abs_long_and_short_notional():
    p, m = _setup(cash=1_000_000.0)
    tk_long = m.companies[0]["ticker"]
    tk_short = m.companies[1]["ticker"]
    _set_price(m, tk_long, 100.0)
    _set_price(m, tk_short, 50.0)
    pf.buy(p, m, tk_long, 100)     # 10 000 de long
    pf.short(p, m, tk_short, 40)   # 2 000 de short
    assert pm.gross_exposure(p, m) == pytest.approx(10_000.0 + 2_000.0)


def test_gross_excluding_omits_given_ticker():
    p, m = _setup(cash=1_000_000.0)
    tk1 = m.companies[0]["ticker"]
    tk2 = m.companies[1]["ticker"]
    _set_price(m, tk1, 100.0)
    _set_price(m, tk2, 50.0)
    pf.buy(p, m, tk1, 100)
    pf.buy(p, m, tk2, 40)
    g_all = pm.gross_exposure(p, m)
    g_excl = pm._gross_excluding(p, m, tk1)
    assert g_excl == pytest.approx(g_all - 100.0 * 100)


def test_leverage_zero_when_no_positions():
    p, m = _setup(cash=10_000.0)
    assert pm.leverage(p, m) == pytest.approx(0.0)


def test_leverage_is_gross_over_equity():
    p, m = _setup(cash=10_000.0)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.buy(p, m, tk, 50)   # 5000 d'expo, equity ~ 10000 (encore du cash)
    expected = pm.gross_exposure(p, m) / pm.net_worth(p, m)
    assert pm.leverage(p, m) == pytest.approx(expected)


# --------------------------------------------------------------- margin_status
def test_margin_status_fields_consistent_with_helpers():
    p, m = _setup(grade_index=8, cash=10_000.0)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.buy(p, m, tk, 200)
    st = pm.margin_status(p, m)
    assert st["equity"] == pytest.approx(pm.net_worth(p, m))
    assert st["gross"] == pytest.approx(pm.gross_exposure(p, m))
    assert st["max_leverage"] == pytest.approx(pm._max_leverage(p))
    assert st["borrowed"] == pytest.approx(max(0.0, -p.cash))
    assert not st["margin_call"]


def test_margin_status_flags_margin_call_on_equity_collapse():
    p, m = _setup(grade_index=8, cash=10_000.0)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.buy(p, m, tk, 300)        # forte exposition, partiellement sur marge
    _set_price(m, tk, 60.0)      # krach : l'equity s'effondre sous la marge de maintenance
    st = pm.margin_status(p, m)
    assert st["margin_call"] is True
    assert st["equity"] < pm._maint_margin(p) * st["gross"]


def test_margin_status_buying_power_shrinks_with_exposure():
    p, m = _setup(grade_index=8, cash=100_000.0)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    bp_before = pm.margin_status(p, m)["buying_power"]
    pf.buy(p, m, tk, 100)
    bp_after = pm.margin_status(p, m)["buying_power"]
    assert bp_after < bp_before


# --------------------------------------------------------------- _would_exceed_leverage
def test_would_exceed_leverage_blocks_oversized_order():
    p, m = _setup(grade_index=8, cash=10_000.0)   # max ~3.5x -> ~35k d'expo
    eq = pm.net_worth(p, m)
    maxlev = pm._max_leverage(p)
    assert pm._would_exceed_leverage(p, m, maxlev * eq * 10)
    assert not pm._would_exceed_leverage(p, m, maxlev * eq * 0.5)


def test_would_exceed_leverage_accounts_for_fee():
    p, m = _setup(grade_index=8, cash=10_000.0)
    eq = pm.net_worth(p, m)
    maxlev = pm._max_leverage(p)
    new_gross = maxlev * eq - 1.0
    # juste en dessous du plafond sans frais...
    assert not pm._would_exceed_leverage(p, m, new_gross, fee=0.0)
    # ... mais un gros frais réduit l'equity effective et fait basculer au-delà
    assert pm._would_exceed_leverage(p, m, new_gross, fee=eq)


def test_would_exceed_leverage_blocks_any_exposure_with_nonpositive_equity():
    p, m = _setup(grade_index=8, cash=0.0)
    assert pm.net_worth(p, m) <= 0
    assert pm._would_exceed_leverage(p, m, 1.0)
    assert not pm._would_exceed_leverage(p, m, 0.0)


def test_leverage_limit_blocks_oversized_buy_through_full_order_flow():
    p, m = _setup(grade_index=8, cash=10_000.0)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    assert pf.buy(p, m, tk, 1000)["reason"] == "leverage"
    assert pf.buy(p, m, tk, 200)["ok"]


# --------------------------------------------------------------- accrue_financing
def test_accrue_financing_deducts_interest_proportional_to_borrowed_cash():
    p, m = _setup(grade_index=8, cash=10_000.0)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.buy(p, m, tk, 250)            # achat à crédit -> cash négatif
    borrowed = max(0.0, -p.cash)
    assert borrowed > 0
    cash_before = p.cash
    fin = pm.accrue_financing(p, m, days=10)
    rate = m.macro["rate"]["v"] / 100.0
    expected_interest = borrowed * (rate + pm.MARGIN_SPREAD) * (10 / 365.0)
    assert fin["interest"] == pytest.approx(expected_interest, rel=1e-6)
    assert fin["borrow_fee"] == pytest.approx(0.0)
    assert p.cash == pytest.approx(cash_before - fin["total"])


def test_accrue_financing_deducts_short_borrow_fee_proportional_to_notional():
    p, m = _setup(cash=1_000_000.0)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.short(p, m, tk, 100)          # 10 000 de notionnel short
    cash_before = p.cash
    fin = pm.accrue_financing(p, m, days=365)
    expected_fee = 10_000.0 * pm.SHORT_FEE_ANNUAL
    assert fin["borrow_fee"] == pytest.approx(expected_fee, rel=1e-6)
    assert p.cash == pytest.approx(cash_before - fin["total"])


def test_accrue_financing_zero_when_no_debt_and_no_shorts():
    p, m = _setup(cash=1_000_000.0)
    fin = pm.accrue_financing(p, m, days=30)
    assert fin == {"interest": 0.0, "borrow_fee": 0.0, "total": 0.0}


def test_accrue_financing_risk_track_halves_margin_spread():
    p_general, m1 = _setup(grade_index=8, cash=10_000.0, track="General")
    tk1 = m1.companies[0]["ticker"]
    _set_price(m1, tk1, 100.0)
    pf.buy(p_general, m1, tk1, 250)

    p_risk, m2 = _setup(grade_index=8, cash=10_000.0, track="Risk")
    tk2 = m2.companies[0]["ticker"]
    _set_price(m2, tk2, 100.0)
    pf.buy(p_risk, m2, tk2, 250)

    fin_general = pm.accrue_financing(p_general, m1, days=30)
    fin_risk = pm.accrue_financing(p_risk, m2, days=30)
    # mêmes montants empruntés (mêmes ordres), mais surcoût de marge réduit pour Risk
    assert fin_risk["interest"] < fin_general["interest"]
