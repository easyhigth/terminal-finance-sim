"""Tests des classes d'actifs alternatives : commodities (futures) et crypto."""
import pytest

from core.market import Market
from core.game_state import PlayerState
from core import commodities as C
from core import crypto as K
from core import portfolio as pf


def _setup():
    m = Market(seed=2024)
    p = PlayerState()
    p.cash = 5_000_000.0
    return p, m


# --------------------------------------------------------------- commodities
def test_commodities_curve_structure():
    _, m = _setup()
    oil = C.quote(m, "OIL")
    gold = C.quote(m, "GOLD")
    assert oil["structure"] == "Contango" and oil["front"] > oil["spot"]
    assert gold["structure"] == "Backwardation" and gold["front"] < gold["spot"]


def test_commodity_roll_yield_sign():
    _, m = _setup()
    assert C.roll_yield(m, "OIL") < 0      # contango -> roll négatif
    assert C.roll_yield(m, "GOLD") > 0     # backwardation -> roll positif


def test_commodity_buy_sell_and_value():
    p, m = _setup()
    r = C.buy(p, m, "OIL", 10)
    assert r["ok"] and C.holdings_value(p, m) > 0
    s = C.sell(p, m, "OIL", "ALL")
    assert s["ok"] and "OIL" not in p.commodities


def test_commodity_roll_cost_negative_in_contango():
    p, m = _setup()
    C.buy(p, m, "GAS", 20)                 # fort contango
    assert C.roll_cost(p, m, days=90) < 0  # détenir coûte en contango


def test_commodity_price_deterministic():
    a, b = Market(seed=5), Market(seed=5)
    a.fast_forward(30); b.fast_forward(30)
    assert C.spot(a, "OIL") == pytest.approx(C.spot(b, "OIL"))


# --------------------------------------------------------------- crypto
def test_crypto_quotes_and_stablecoin_flag():
    _, m = _setup()
    qs = {q["id"]: q for q in K.all_quotes(m)}
    assert qs["USDX"]["stable"] is True
    assert qs["BITC"]["stable"] is False
    assert all(q["spot"] > 0 for q in qs.values())


def test_crypto_buy_sell():
    p, m = _setup()
    r = K.buy(p, m, "BITC", 2)
    assert r["ok"] and K.holdings_value(p, m) > 0
    s = K.sell(p, m, "BITC", "ALL")
    assert s["ok"] and "BITC" not in p.crypto


def test_stablecoin_starts_at_peg():
    m = Market(seed=2024)
    assert K.spot(m, "USDX") == pytest.approx(1.0, abs=0.05)   # au pair au départ


def test_alt_assets_in_net_worth():
    p, m = _setup()
    nw0 = pf.net_worth(p, m)
    C.buy(p, m, "OIL", 10)
    K.buy(p, m, "BITC", 1)
    nw1 = pf.net_worth(p, m)
    assert nw1 == pytest.approx(nw0, rel=3e-3)   # cash transféré en actifs (à la commission près)
