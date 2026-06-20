"""Tests du portefeuille avec LEVIER & VENTE À DÉCOUVERT (core/portfolio.py).

L'accounting signé (long/short), les limites de levier, le financement et les
appels de marge sont là où se cachent les bugs : on les verrouille ici.
"""
import pytest

from core import portfolio as pf
from core.game_state import PlayerState
from core.market import Market


def _setup(grade_index=8, cash=1_000_000.0):
    m = Market(seed=999)
    p = PlayerState()
    p.grade_index = grade_index
    p.cash = cash
    return p, m


def _set_price(m, tk, price):
    m.price[m.ticker_idx[tk]] = price


# --------------------------------------------------------------- long
def test_buy_then_sell_realizes_pnl():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.buy(p, m, tk, 100)
    assert p.portfolio[tk]["shares"] == 100
    _set_price(m, tk, 120.0)
    res = pf.sell(p, m, tk, "ALL")
    assert res["ok"]
    # gain brut ~ (120-100)*100 = 2000, moins commissions
    assert res["realized"] == pytest.approx(2000 - 120*100*pf.COMMISSION - 100*100*pf.COMMISSION, rel=1e-6) \
        or res["realized"] > 1800
    assert tk not in p.portfolio


# --------------------------------------------------------------- short
def test_short_profits_when_price_falls():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    cash0 = p.cash
    r = pf.short(p, m, tk, 100)
    assert r["ok"] and p.portfolio[tk]["shares"] == -100
    assert p.cash > cash0                      # le short crédite la trésorerie
    _set_price(m, tk, 80.0)                     # le cours baisse -> le short gagne
    res = pf.cover(p, m, tk, "ALL")
    assert res["ok"] and res["realized"] > 0
    assert tk not in p.portfolio


def test_short_loses_when_price_rises():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.short(p, m, tk, 100)
    _set_price(m, tk, 130.0)
    # equity en baisse vs cash initial: la position courte perd quand le prix monte
    res = pf.cover(p, m, tk, "ALL")
    assert res["realized"] < 0


def test_cannot_buy_while_short_and_vice_versa():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.short(p, m, tk, 10)
    assert pf.buy(p, m, tk, 5)["reason"] == "isshort"
    pf.cover(p, m, tk, "ALL")
    pf.buy(p, m, tk, 10)
    assert pf.short(p, m, tk, 5)["reason"] == "islong"


# --------------------------------------------------------------- levier
def test_max_leverage_increases_with_grade():
    assert pf.max_leverage(0) < pf.max_leverage(6) <= pf.max_leverage(11)
    assert pf.max_leverage(11) == pytest.approx(4.0)


def test_leverage_limit_blocks_oversized_buy():
    p, m = _setup(grade_index=8, cash=10_000.0)   # max ~3.5x -> ~35k d'expo
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    # 1000 actions = 100k d'exposition pour 10k d'equity -> 10x, refusé
    assert pf.buy(p, m, tk, 1000)["reason"] == "leverage"
    # une taille raisonnable passe
    assert pf.buy(p, m, tk, 200)["ok"]


def test_buying_on_margin_makes_cash_negative():
    p, m = _setup(grade_index=8, cash=10_000.0)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.buy(p, m, tk, 250)            # 25k d'achat avec 10k -> marge
    assert p.cash < 0               # capital emprunté
    st = pf.margin_status(p, m)
    assert st["borrowed"] > 0 and st["leverage"] > 1.0


# --------------------------------------------------------------- financement
def test_accrue_financing_charges_borrow_and_short():
    p, m = _setup(grade_index=8, cash=10_000.0)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.buy(p, m, tk, 250)           # cash négatif -> intérêts
    cash_before = p.cash
    fin = pf.accrue_financing(p, m, days=5)
    assert fin["interest"] > 0
    assert p.cash == pytest.approx(cash_before - fin["total"])


# --------------------------------------------------------------- appel de marge
def test_margin_call_liquidates_when_equity_collapses():
    p, m = _setup(grade_index=8, cash=10_000.0)
    tk = m.companies[0]["ticker"]
    _set_price(m, tk, 100.0)
    pf.buy(p, m, tk, 300)                       # forte exposition sur marge
    _set_price(m, tk, 60.0)                      # krach : l'equity s'effondre
    gross_before = pf.gross_exposure(p, m)
    mc = pf.check_margin_call(p, m)
    assert mc is not None and mc["triggered"]
    assert pf.gross_exposure(p, m) < gross_before  # exposition réduite d'office


# --------------------------------------------------------------- dividendes
def test_slippage_grows_with_order_size():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    # un petit ordre subit surtout le demi-spread ; un ordre énorme subit l'impact
    small = pf.fill_price(m, tk, 1, "buy")
    big = pf.fill_price(m, tk, 5_000_000, "buy")
    mid = m.price_of(tk)
    assert small > mid                      # demi-spread à l'achat
    assert big > small                      # impact de marché croissant avec la taille
    # à la vente, le prix obtenu est sous le mid
    assert pf.fill_price(m, tk, 1, "sell") < mid


def test_slippage_capped():
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    huge = pf.fill_price(m, tk, 10 ** 15, "buy")
    assert huge <= m.price_of(tk) * (1 + pf.HALF_SPREAD + pf.MAX_SLIPPAGE) + 1e-6


# --------------------------------------------------------------- impact non-linéaire
def test_market_impact_is_sublinear_in_order_size():
    """Doubler la taille de l'ordre ne doit PAS doubler l'impact (courbe convexe en
    valeur absolue mais sous-linéaire par unité, alpha < 1 — pas un modèle linéaire)."""
    liquidity = 50_000_000_000.0
    small = pf.market_impact(1_000_000.0, liquidity, stress_level=0.0)
    big = pf.market_impact(2_000_000.0, liquidity, stress_level=0.0)
    assert big > small
    assert big < 2.0 * small      # sous-linéaire : pas de doublement de l'impact


def test_market_impact_higher_for_smaller_market_cap():
    """À valeur d'ordre égale, une société moins liquide (capi plus faible) doit
    subir un impact plus élevé que la même valeur d'ordre sur une grosse capi."""
    order_value = 5_000_000.0
    small_cap = pf.market_impact(order_value, 500_000_000.0, stress_level=0.1)
    large_cap = pf.market_impact(order_value, 50_000_000_000.0, stress_level=0.1)
    assert small_cap > large_cap


def test_market_impact_higher_under_stress():
    """Le même ordre doit produire un impact plus élevé en plein stress de marché
    (last_stress_level proche de 1.0) qu'en marché calme (proche de 0)."""
    order_value = 5_000_000.0
    liquidity = 5_000_000_000.0
    calm = pf.market_impact(order_value, liquidity, stress_level=0.0)
    crisis = pf.market_impact(order_value, liquidity, stress_level=1.0)
    assert crisis > calm
    assert crisis >= calm * 2.0   # le multiplicateur de stress doit se faire sentir


def test_market_impact_respects_safety_cap_even_under_max_stress():
    """Même pour un ordre pathologiquement gros en pleine panique, l'impact reste
    borné par MAX_SLIPPAGE (plafond de sécurité, pas de fill absurde)."""
    impact = pf.market_impact(10 ** 18, 1.0, stress_level=1.0)
    assert impact == pytest.approx(pf.MAX_SLIPPAGE)


def test_fill_price_uses_market_stress_level():
    """fill_price() doit lire market.last_stress_level (signal de stress existant,
    0..1, calculé chaque step() à partir de l'asymétrie de volatilité et du régime)
    plutôt qu'ignorer le stress courant du marché."""
    p, m = _setup()
    tk = m.companies[0]["ticker"]
    order_qty = 100
    m.last_stress_level = 0.0
    calm_fill = pf.fill_price(m, tk, order_qty, "buy")
    m.last_stress_level = 1.0
    stressed_fill = pf.fill_price(m, tk, order_qty, "buy")
    assert stressed_fill > calm_fill


def test_short_pays_dividends():
    p, m = _setup()
    # trouve une société qui verse un dividende
    tk = next(c["ticker"] for c in m.companies if c["div_yield"] > 0)
    _set_price(m, tk, 100.0)
    pf.short(p, m, tk, 100)
    d = pf.dividends(p, m, days=90)
    assert d < 0                                # un short PAIE les dividendes
