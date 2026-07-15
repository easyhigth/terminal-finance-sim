"""Tests des thématiques de marché (core/themes.py) : constituants stables et
déterministes, force/momentum dérivés du marché réel, classement de rotation,
achat de panier équipondéré best-effort."""
import pytest

from core import themes as T
from core.game_state import PlayerState
from core.market import Market


@pytest.fixture()
def market():
    m = Market(seed=7)
    m.sync_to(120)
    return m


def test_all_themes_have_labels_and_sectors():
    for tid, *_r in T.THEMES:
        assert T.theme_label(tid)
        assert T.theme_desc(tid)
        assert T.theme_sectors(tid)


def test_constituents_are_from_theme_sectors(market):
    for tid, *_r in T.THEMES:
        sectors = set(T.theme_sectors(tid))
        comp = {c["ticker"]: c for c in market.companies}
        for tk in T.constituents(market, tid):
            assert comp[tk]["sector"] in sectors


def test_constituents_are_stable_across_steps(market):
    before = T.constituents(market, "ai")
    for _ in range(20):
        market.step()
    after = T.constituents(market, "ai")
    assert before == after   # panier stable (choisi sur données statiques)


def test_constituents_capped_to_basket_size(market):
    assert len(T.constituents(market, "ai")) <= T.BASKET_SIZE


def test_theme_strength_has_expected_shape(market):
    s = T.theme_strength(market, "ai")
    assert set(s) == {"basket_return", "market_return", "relative"}
    assert s["relative"] == pytest.approx(s["basket_return"] - s["market_return"])


def test_heat_ranking_is_sorted_by_relative_strength(market):
    rows = T.heat_ranking(market)
    assert len(rows) == len(T.THEMES)
    rels = [r["strength"]["relative"] for r in rows]
    assert rels == sorted(rels, reverse=True)


def test_unknown_theme_is_empty(market):
    assert T.constituents(market, "nope") == []
    assert T.theme_strength(market, "nope")["relative"] == 0.0


def test_buy_basket_spreads_budget_equally(market):
    p = PlayerState()
    p.cash = 2_000_000.0
    res = T.buy_basket(p, market, "ai", 400_000)
    assert res["ok"]
    assert len(res["bought"]) >= 1
    # chaque ligne achetée est un constituant du thème
    cons = set(T.constituents(market, "ai"))
    assert all(tk in cons for tk, _q in res["bought"])
    assert res["spent"] <= 400_000 * 1.05    # ~budget (frais inclus)


def test_buy_basket_records_exposure(market):
    p = PlayerState()
    p.cash = 2_000_000.0
    assert T.basket_exposure(p, market, "ai") == 0.0
    T.buy_basket(p, market, "ai", 400_000)
    assert T.basket_exposure(p, market, "ai") > 0.0


def test_buy_basket_zero_budget_is_noop(market):
    p = PlayerState()
    p.cash = 1_000_000.0
    res = T.buy_basket(p, market, "ai", 0)
    assert not res["ok"]
    assert res["bought"] == []
