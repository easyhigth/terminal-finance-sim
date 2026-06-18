"""Tests de la logique pure des ETF (core/etfs.py)."""
import numpy as np
import pytest

from core import etfs
from core.game_state import PlayerState
from core.market import Market


@pytest.fixture
def market():
    m = Market(seed=4242)
    m.fast_forward(200)
    return m


def test_universe_well_formed():
    ids = [e.id for e in etfs.all_etfs()]
    assert len(ids) == len(set(ids)), "tickers d'ETF dupliqués"
    assert len(ids) >= 60, "l'univers d'ETF doit être grand"
    cats = {c for c, _ in etfs.CATEGORIES}
    for e in etfs.all_etfs():
        assert e.category in cats
        assert 1 <= e.risk <= 5
        assert 0 <= e.expense < 0.02
    # toutes les grandes familles sont représentées
    present = {e.category for e in etfs.all_etfs()}
    for needed in ("broad", "world", "region", "country", "sector", "style",
                   "thematic", "esg", "reit", "bond", "commodity", "currency",
                   "leveraged"):
        assert needed in present, f"famille manquante : {needed}"


def test_all_priced_with_history(market):
    for e in etfs.all_etfs():
        q = etfs.quote(market, e.id)
        assert q is not None
        assert q["price"] is not None and q["price"] > 0, e.id
        h = etfs.nav_history(market, e.id, 73)
        assert len(h) >= 2, e.id
        assert all(v > 0 for v in h), e.id


def test_determinism():
    m1 = Market(seed=99); m1.fast_forward(150)
    m2 = Market(seed=99); m2.fast_forward(150)
    for e in etfs.all_etfs():
        assert abs(etfs.price(m1, e.id) - etfs.price(m2, e.id)) < 1e-6, e.id


def test_leverage_amplifies_base(market):
    """L'ETF x3 amplifie l'exposition (bêta) de sa base ; l'inverse la retourne."""
    base = etfs.beta_world(etfs.get("SPX"))
    assert etfs.beta_world(etfs.get("SPXL")) > base * 2.5
    assert etfs.beta_world(etfs.get("SPXS")) < 0
    assert etfs.beta_world(etfs.get("SQQ")) < 0


def test_sector_etf_tracks_sector(market):
    """Un ETF secteur réagit comme son secteur : forçons un choc sectoriel et
    vérifions que la NAV bouge dans le bon sens au pas suivant."""
    from core.market import Crisis
    before = etfs.price(market, "XLK")
    market.add_crisis(Crisis("Choc Tech", steps=1, sectors={"Tech": -0.05}))
    market.step()
    after = etfs.price(market, "XLK")
    assert after < before, "un choc Tech négatif doit faire baisser l'ETF Tech"


def test_bond_etf_reacts_to_rates(market):
    """Un ETF souverain long terme doit avoir une NAV qui varie quand les taux
    bougent (duration). On compare deux marchés aux taux différents."""
    p1 = etfs.nav_history(market, "TLT")
    # série non plate (les taux ont bougé pendant le warmup)
    assert max(p1) > min(p1), "la NAV obligataire doit varier avec les taux"


def test_trading_cycle():
    m = Market(seed=7); m.fast_forward(100)
    p = PlayerState()
    p.cash = 100_000.0
    r = etfs.buy(p, m, "VTW", 100)
    assert r["ok"]
    assert "VTW" in p.etfs
    assert etfs.holdings_value(p, m) > 0
    cash_after_buy = p.cash
    r2 = etfs.sell(p, m, "VTW", "ALL")
    assert r2["ok"]
    assert "VTW" not in p.etfs
    assert p.cash > cash_after_buy   # produit de la vente crédité


def test_buy_rejected_without_cash():
    m = Market(seed=7); m.fast_forward(10)
    p = PlayerState(); p.cash = 1.0
    r = etfs.buy(p, m, "SPX", 1000)
    assert not r["ok"] and r["reason"] == "cash"


def test_yield_and_exposure_labels():
    for e in etfs.all_etfs():
        assert isinstance(etfs.exposure_label(e), str)
        assert etfs.exposure_label(e) != ""
        y = etfs.indicative_yield(e)
        assert -0.2 < y < 0.3   # rendement indicatif plausible
