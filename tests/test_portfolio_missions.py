"""Tests des missions « état réel du portefeuille » (core/portfolio_missions.py)
et leur intégration dans core/missions.generate() au tier "portfolio"."""
import random

import pytest

from core import missions
from core import portfolio as pf
from core import portfolio_missions as PM
from core.game_state import PlayerState
from core.market import Market


@pytest.fixture()
def market():
    m = Market(seed=9)
    for _ in range(30):
        m.step()
    return m


@pytest.fixture()
def player():
    p = PlayerState()
    p.cash = 1_000_000.0
    p.grade_index = 8
    return p


# ---------------------------------------------------------------- checks purs
def test_sector_diversification_false_then_true(player, market):
    assert not PM._sector_diversification_ok(player, market)
    tks = [c["ticker"] for c in market.top_companies(n=60)]
    comp = {c["ticker"]: c for c in market.companies}
    seen_sectors = set()
    bought = 0
    for tk in tks:
        sec = comp[tk]["sector"]
        if sec in seen_sectors:
            continue
        assert pf.buy(player, market, tk, 5)["ok"]
        seen_sectors.add(sec)
        bought += 1
        if bought >= 3:
            break
    assert PM._sector_diversification_ok(player, market)


def test_cash_buffer_ok_true_when_all_cash(player, market):
    assert PM._cash_buffer_ok(player, market)


def test_cash_buffer_false_when_fully_invested(player, market):
    tk = market.top_companies(n=1)[0]["ticker"]
    price = market.price_of(tk)
    qty = int(player.cash * 0.95 / price)
    assert pf.buy(player, market, tk, qty)["ok"]
    assert not PM._cash_buffer_ok(player, market)


def test_has_bond_false_then_true(player, market):
    assert not PM._has_bond_ok(player, market)
    from core import bonds
    quotes = bonds.sovereign_quotes(market)
    assert bonds.buy_bond(player, market, quotes[0]["id"], 10)["ok"]
    assert PM._has_bond_ok(player, market)


def test_has_hedge_false_then_true_via_short(player, market):
    assert not PM._has_hedge_ok(player, market)
    tk = market.top_companies(n=1)[0]["ticker"]
    assert pf.short(player, market, tk, 5)["ok"]
    assert PM._has_hedge_ok(player, market)


def test_leverage_ok_true_when_unlevered(player, market):
    assert PM._leverage_ok(player, market)


# --------------------------------------------------------- items MCQ générés
def test_practical_item_reflects_true_state(player, market):
    item = PM.practical_item("has_bond", player, market, rng=random.Random(1))
    assert item["kind"] == "mcq"
    # "Non" est la bonne réponse (index 1) puisque le joueur n'a pas d'obligation
    assert item["choices"][item["answer"]].lower().startswith(("non", "no"))


def test_practical_item_unknown_id_is_none(player, market):
    assert PM.practical_item("nope", player, market) is None


def test_practical_items_are_distinct_checks(player, market):
    items = PM.practical_items(player, market, count=3, rng=random.Random(2))
    assert len(items) == 3
    prompts = {it["prompt"] for it in items}
    assert len(prompts) == 3


# --------------------------------------------------------------- intégration
def test_generate_portfolio_tier_includes_practical_items_when_player_given(player, market):
    m = missions.generate(player.grade_index, market, rng=random.Random(3),
                          track="General", player=player)
    assert m["kind"] == "portfolio"
    assert len(m["items"]) == missions.MAX_ITEMS
    practical_prompts = {c[1] for c in PM.PRACTICAL_CHECKS} | {c[2] for c in PM.PRACTICAL_CHECKS}
    n_practical = sum(1 for it in m["items"] if it["prompt"] in practical_prompts)
    assert n_practical == 2


def test_generate_portfolio_tier_without_player_is_pure_bank(market):
    m = missions.generate(8, market, rng=random.Random(4), track="General")
    assert m["kind"] == "portfolio"
    assert len(m["items"]) == missions.MAX_ITEMS


def test_generate_non_portfolio_tier_ignores_player(player, market):
    player.grade_index = 1
    m = missions.generate(1, market, rng=random.Random(5), track="General", player=player)
    assert m["kind"] == "report"
    assert len(m["items"]) == missions.MAX_ITEMS
