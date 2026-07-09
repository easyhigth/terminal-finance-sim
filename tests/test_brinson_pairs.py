"""Tests du lot « analyse de gérant + stat arb » : core/brinson.py
(invariant Brinson : allocation + sélection + interaction = écart total ;
régression factorielle : R² ≈ 1 pour un portefeuille-indice), core/pairs.py
(Engle-Granger détecte une paire construite cointégrée, half-life, signaux,
exécution long/short réelle), surface de vol et edge de vol."""
import math

import numpy as np
import pytest

from core import brinson as BR
from core import option_pricing as OP
from core import pairs as PAIRS
from core import portfolio as pf
from core.game_state import PlayerState
from core.market import Market


@pytest.fixture()
def market():
    m = Market(seed=5)
    for _ in range(90):
        m.step()
    return m


@pytest.fixture()
def player():
    p = PlayerState()
    p.grade_index = 9
    p.cash = 5_000_000.0
    return p


def _buy_top(p, m, n=4, shares=60):
    tks = [c["ticker"] for c in m.top_companies(n=n)]
    for tk in tks:
        assert pf.buy(p, m, tk, shares)["ok"]
    return tks


# ================================================================= Brinson
def test_brinson_effects_sum_to_excess(market, player):
    _buy_top(player, market)
    br = BR.brinson(player, market, 60)
    assert br is not None
    t = br["totals"]
    total_effects = t["allocation"] + t["selection"] + t["interaction"]
    assert total_effects == pytest.approx(br["excess"], abs=1e-9)  # invariant


def test_brinson_none_without_positions(market, player):
    assert BR.brinson(player, market) is None


def test_brinson_rows_have_weights_and_benchmark_sums(market, player):
    _buy_top(player, market)
    br = BR.brinson(player, market, 60)
    assert all(0 <= r["w_p"] <= 1 and 0 <= r["w_b"] <= 1 for r in br["rows"])
    wp_tot = sum(r["w_p"] for r in br["rows"])
    assert wp_tot == pytest.approx(1.0, abs=0.05)   # tout le book est ventilé


def test_factor_regression_r2_high_for_index_like_portfolio(market, player):
    """Un portefeuille très diversifié (20 plus grosses capis) est un
    quasi-indice : les facteurs expliquent presque tout (R² élevé)."""
    for c in market.top_companies(n=20):
        pf.buy(player, market, c["ticker"], 20)
    fr = BR.factor_regression(player, market, 60)
    assert fr is not None
    assert fr["r2"] > 0.7
    world = next(r for r in fr["rows"] if r["label"] == "Monde")
    assert 0.5 < world["beta"] < 1.6                 # bêta marché plausible


def test_factor_returns_shape(market):
    fx = BR.factor_returns(market, 40)
    assert fx is not None
    X, labels = fx
    assert X.shape[0] == 40
    assert X.shape[1] == len(labels)
    assert labels[0] == "Monde"
    assert any(lbl.startswith("Secteur") for lbl in labels)
    assert any(lbl.startswith("Région") for lbl in labels)


# ============================================================ Pairs trading
def test_engle_granger_flags_a_constructed_cointegrated_pair(market, monkeypatch):
    """On FABRIQUE une paire cointégrée (B = 2·A + bruit stationnaire) et on
    vérifie que le test la détecte, avec une half-life finie."""
    rng = np.random.default_rng(3)
    a = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.02, 120)))
    noise = rng.normal(0, 0.01, 120)
    b = 2.0 * a * np.exp(noise)                      # attaché à A

    def fake_history(ticker, n=None, **_kw):
        s = a if ticker == "AAA" else b
        return list(s[-n:]) if n else list(s)
    monkeypatch.setattr(market, "history_of", fake_history)
    r = PAIRS.engle_granger(market, "AAA", "BBB", 110)
    assert r is not None
    assert r["cointegrated"] is True
    assert r["beta"] == pytest.approx(1.0, abs=0.15)  # log-log : pente 1
    assert math.isfinite(r["half_life"]) and r["half_life"] < 30


def test_engle_granger_rejects_independent_walks(market, monkeypatch):
    rng = np.random.default_rng(9)
    a = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.02, 120)))
    b = 80.0 * np.exp(np.cumsum(rng.normal(0, 0.02, 120)))

    def fake_history(ticker, n=None, **_kw):
        s = a if ticker == "AAA" else b
        return list(s[-n:]) if n else list(s)
    monkeypatch.setattr(market, "history_of", fake_history)
    r = PAIRS.engle_granger(market, "AAA", "BBB", 110)
    assert r is not None
    assert r["cointegrated"] is False                # marches indépendantes


def test_signal_thresholds():
    assert PAIRS.signal(2.5) == "short_spread"
    assert PAIRS.signal(-2.5) == "long_spread"
    assert PAIRS.signal(0.1) == "exit"
    assert PAIRS.signal(1.0) == "hold"


def test_best_pairs_sorted_by_adf(market):
    scan = PAIRS.best_pairs(market, n_universe=10, n_pairs=4)
    assert len(scan) == 4
    adfs = [x[2] for x in scan]
    assert adfs == sorted(adfs)                      # les + cointégrées d'abord


def test_execute_pair_places_long_and_short(market, player):
    tka, tkb = (c["ticker"] for c in market.top_companies(n=2))
    r = PAIRS.execute_pair(player, market, tka, tkb, "long_spread", 100_000.0)
    assert r["ok"] is True
    pos_a = player.portfolio[tka]
    pos_b = player.portfolio[tkb]
    assert pos_a["shares"] > 0                       # long A
    assert pos_b["shares"] < 0                       # short B
    # la jambe short est dimensionnée par β en valeur
    beta = abs(r["beta"])
    val_b = abs(pos_b["shares"]) * market.price_of(tkb)
    assert val_b == pytest.approx(beta * 100_000.0, rel=0.10)


def test_execute_pair_rejects_bad_direction(market, player):
    tka, tkb = (c["ticker"] for c in market.top_companies(n=2))
    assert PAIRS.execute_pair(player, market, tka, tkb, "up", 1000.0)["ok"] is False


# ===================================================== surface & vol edge
def test_vol_surface_has_smile_and_term_structure():
    sf = OP.vol_surface(100.0, 0.03, 0.25)
    iv = sf["iv"]
    # smile : l'aile put (80 %) plus chère que l'ATM, à courte maturité
    short_t = iv[0]
    i_atm = sf["strikes_pct"].index(1.00)
    assert short_t[0] is not None and short_t[i_atm] is not None
    assert short_t[0] > short_t[i_atm]
    # term structure : le skew de l'aile s'atténue avec la maturité
    long_t = iv[-1]
    skew_short = short_t[0] - short_t[i_atm]
    skew_long = long_t[0] - long_t[i_atm]
    assert skew_short > skew_long


def test_vol_edge_reads_entry_iv_from_premium(market, player):
    from core import option_strategies as OS
    tk = market.top_companies(n=1)[0]["ticker"]
    r = OS.execute_strategy(player, market, tk, "straddle", 0.5, 10)
    assert r["ok"]
    edge = OS.vol_edge(player, market)
    assert len(edge) == 2
    for e in edge:
        assert 0.02 < e["entry_iv"] < 2.0            # IV d'entrée plausible
        assert e["edge"] == pytest.approx(e["realized"] - e["entry_iv"])
