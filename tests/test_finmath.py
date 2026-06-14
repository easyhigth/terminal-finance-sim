"""Tests du moteur financier (core/finmath.py).

On vérifie les formules contre des valeurs calculées à la main ou contre des
identités financières connues (parité call-put, obligation au pair, etc.).
"""
import math

import numpy as np
import pytest

from core import finmath as fm


# --------------------------------------------------------------- valeur temps
def test_present_future_value_roundtrip():
    fv = fm.future_value(1000, 0.05, 10)
    assert fv == pytest.approx(1000 * 1.05 ** 10)
    # actualiser la valeur future redonne le capital initial
    assert fm.present_value(fv, 0.05, 10) == pytest.approx(1000)


def test_npv_known_value():
    # NPV à 10 % de [-100, 50, 60, 70]
    expected = -100 + 50 / 1.1 + 60 / 1.1 ** 2 + 70 / 1.1 ** 3
    assert fm.npv(0.1, [-100, 50, 60, 70]) == pytest.approx(expected)


def test_irr_zeroes_npv():
    cfs = [-100, 50, 60, 70]
    r = fm.irr(cfs)
    assert fm.npv(r, cfs) == pytest.approx(0.0, abs=1e-4)
    assert 0 < r < 1  # rendement plausible


# --------------------------------------------------------------- obligations
def test_bond_at_par_when_coupon_equals_ytm():
    # coupon = ytm -> l'obligation cote au pair (= face)
    price = fm.bond_price(1000, 0.05, 0.05, 10, freq=2)
    assert price == pytest.approx(1000, abs=1e-6)


def test_bond_price_inverse_to_yield():
    # le prix baisse quand le rendement exigé monte
    low = fm.bond_price(1000, 0.05, 0.04, 10)
    high = fm.bond_price(1000, 0.05, 0.07, 10)
    assert low > high


def test_modified_duration_below_macaulay():
    mac = fm.bond_duration(1000, 0.05, 0.05, 10)
    mod = fm.bond_modified_duration(1000, 0.05, 0.05, 10)
    assert 0 < mod < mac


# --------------------------------------------------------------- DCF / WACC
def test_wacc_known_value():
    # 60% equity à 10%, 40% dette à 5% avec impôt 30%
    w = fm.wacc(60, 40, 0.10, 0.05, 0.30)
    expected = 0.6 * 0.10 + 0.4 * 0.05 * 0.7
    assert w == pytest.approx(expected)


def test_dcf_enterprise_value_positive_and_growing():
    ev = fm.dcf_enterprise_value([100, 110, 120, 130, 140], 0.10, 0.02)
    assert ev > 0
    # une croissance terminale plus forte augmente la valeur
    ev_hi = fm.dcf_enterprise_value([100, 110, 120, 130, 140], 0.10, 0.04)
    assert ev_hi > ev


# --------------------------------------------------------------- Black-Scholes
def test_black_scholes_put_call_parity():
    S, K, T, r, sigma, q = 100, 100, 1.0, 0.03, 0.2, 0.0
    c = fm.black_scholes(S, K, T, r, sigma, "call", q)
    p = fm.black_scholes(S, K, T, r, sigma, "put", q)
    # C - P = S e^{-qT} - K e^{-rT}
    assert c - p == pytest.approx(S * math.exp(-q * T) - K * math.exp(-r * T), abs=1e-6)


def test_black_scholes_intrinsic_at_expiry():
    assert fm.black_scholes(120, 100, 0, 0.03, 0.2, "call") == pytest.approx(20)
    assert fm.black_scholes(80, 100, 0, 0.03, 0.2, "put") == pytest.approx(20)


def test_greeks_signs():
    g_call = fm.bs_greeks(100, 100, 1.0, 0.03, 0.2, "call")
    g_put = fm.bs_greeks(100, 100, 1.0, 0.03, 0.2, "put")
    assert 0 < g_call["delta"] < 1
    assert -1 < g_put["delta"] < 0
    assert g_call["gamma"] > 0
    assert g_call["vega"] > 0
    # delta_call - delta_put = e^{-qT} = 1 ici (q=0)
    assert g_call["delta"] - g_put["delta"] == pytest.approx(1.0, abs=1e-6)


# --------------------------------------------------------------- portefeuille
def test_portfolio_return_and_vol():
    w = np.array([0.5, 0.5])
    mu = np.array([0.10, 0.20])
    assert fm.portfolio_return(w, mu) == pytest.approx(0.15)
    cov = np.array([[0.04, 0.0], [0.0, 0.09]])
    # vol = sqrt(0.25*0.04 + 0.25*0.09)
    assert fm.portfolio_volatility(w, cov) == pytest.approx(math.sqrt(0.0325))


def test_optimizers_sum_to_one_and_long_only():
    mu = np.array([0.08, 0.12, 0.15])
    cov = np.array([[0.04, 0.01, 0.0],
                    [0.01, 0.06, 0.01],
                    [0.0, 0.01, 0.09]])
    for w in (fm.min_variance_portfolio(mu, cov), fm.max_sharpe_portfolio(mu, cov)):
        assert np.sum(w) == pytest.approx(1.0, abs=1e-4)
        assert np.all(w >= -1e-6)


def test_min_variance_has_lowest_vol():
    mu = np.array([0.08, 0.12, 0.15])
    cov = np.array([[0.04, 0.01, 0.0],
                    [0.01, 0.06, 0.01],
                    [0.0, 0.01, 0.09]])
    w_mv = fm.min_variance_portfolio(mu, cov)
    w_eq = np.ones(3) / 3
    assert fm.portfolio_volatility(w_mv, cov) <= fm.portfolio_volatility(w_eq, cov) + 1e-9


# --------------------------------------------------------------- risque
def test_value_at_risk_and_cvar():
    rets = [-0.10, -0.05, -0.02, 0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.08]
    var = fm.value_at_risk(rets, confidence=0.90)
    cvar = fm.conditional_var(rets, confidence=0.90)
    assert var > 0          # exprimée en perte positive
    assert cvar >= var      # la perte moyenne en queue dépasse la VaR


def test_parametric_var_scales_with_horizon():
    v1 = fm.parametric_var(1_000_000, 0.0, 0.02, 0.95, horizon=1)
    v10 = fm.parametric_var(1_000_000, 0.0, 0.02, 0.95, horizon=10)
    assert v10 > v1 > 0
    assert v10 == pytest.approx(v1 * math.sqrt(10), rel=1e-6)


# --------------------------------------------------------------- M&A / LBO
def test_accretion_dilution_sign():
    # synergies importantes -> relutif (EPS pro forma > EPS acquéreur)
    pf_eps, delta = fm.accretion_dilution(5.0, 100, 200, 20, synergies=100)
    assert delta > 0 and pf_eps > 5.0


def test_lbo_returns_consistency():
    moic, irr_val, exit_equity = fm.lbo_returns(
        entry_ev=1000, entry_ebitda=100, debt_pct=0.6,
        exit_multiple=10, years=5, ebitda_cagr=0.08)
    assert moic > 1 and exit_equity > 0
    # IRR cohérent avec le MOIC : (1+irr)^years == moic
    assert (1 + irr_val) ** 5 == pytest.approx(moic, rel=1e-6)


# --------------------------------------------------------------- ratios
def test_gordon_growth():
    # D1=2, re=8%, g=3% -> 2/0.05 = 40
    assert fm.gordon_growth(2.0, 0.08, 0.03) == pytest.approx(40.0)
    with pytest.raises(ValueError):
        fm.gordon_growth(2.0, 0.03, 0.05)   # re <= g interdit


def test_terminal_value():
    tv = fm.terminal_value(100, 0.09, 0.025)
    assert tv == pytest.approx(100 * 1.025 / (0.09 - 0.025))


def test_bond_convexity_positive_and_orders():
    conv_short = fm.bond_convexity(1000, 0.05, 0.05, 3)
    conv_long = fm.bond_convexity(1000, 0.05, 0.05, 15)
    assert conv_short > 0 and conv_long > conv_short   # plus longue = plus convexe


def test_forward_price_cost_of_carry():
    # sans revenu ni stockage : F = S(1+r)^T
    assert fm.forward_price(100, 0.05, 2) == pytest.approx(100 * 1.05 ** 2)
    # un rendement (dividende) abaisse le forward
    assert fm.forward_price(100, 0.05, 1, income_yield=0.03) < fm.forward_price(100, 0.05, 1)


def test_roll_yield_sign():
    assert fm.roll_yield(110, 100) > 0    # backwardation (near > far)
    assert fm.roll_yield(90, 100) < 0     # contango


def test_real_rate_fisher():
    assert fm.real_rate(0.05, 0.02) == pytest.approx((1.05 / 1.02) - 1)
    assert fm.real_rate(0.05, 0.02) < 0.05


def test_expected_loss():
    assert fm.expected_loss(0.02, 0.45, 1_000_000) == pytest.approx(9000.0)


def test_treynor_and_information_ratio():
    assert fm.treynor_ratio(0.12, 1.5, rf=0.02) == pytest.approx((0.10) / 1.5)
    port = [0.02, 0.01, 0.03, -0.01]
    bench = [0.01, 0.01, 0.01, 0.01]
    assert fm.information_ratio(port, bench) > 0
    assert fm.tracking_error(port, bench) > 0


def test_max_drawdown():
    curve = [100, 120, 90, 110, 80, 130]
    # pire chute pic->creux : de 120 à 80 = -33.3%
    assert fm.max_drawdown(curve) == pytest.approx((120 - 80) / 120, rel=1e-6)


def test_downside_deviation_and_sortino():
    rets = [0.02, -0.03, 0.01, -0.05, 0.04]
    dd = fm.downside_deviation(rets, target=0.0)
    assert dd > 0
    # le Sortino ignore la volatilité haussière → dénominateur plus petit que l'écart-type
    assert dd <= np.std(rets) + 1e-9
    assert isinstance(fm.sortino_ratio(rets), float)


def test_calmar_and_twr():
    assert fm.calmar_ratio(0.15, 0.30) == pytest.approx(0.5)
    assert fm.time_weighted_return([0.1, -0.05, 0.2]) == pytest.approx(1.1 * 0.95 * 1.2 - 1)


def test_dscr_and_cet1():
    assert fm.dscr(150, 100) == pytest.approx(1.5)
    assert fm.cet1_ratio(80, 1000) == pytest.approx(0.08)


def test_financial_ratios():
    r = fm.financial_ratios({
        "net_income": 20, "total_equity": 100, "total_assets": 200,
        "revenue": 100, "total_debt": 50,
    })
    assert r["ROE"] == pytest.approx(0.20)
    assert r["ROA"] == pytest.approx(0.10)
    assert r["Net Margin"] == pytest.approx(0.20)
    assert r["D/E"] == pytest.approx(0.50)
