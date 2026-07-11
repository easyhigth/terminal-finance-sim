"""Tests des missions « état réel » EXCLUSIVES par voie
(core/portfolio_missions.py::TRACK_CHECKS/practical_items_for_track +
core/missions.py::_TRACK_FLAVOR) : au tier "portfolio" (VP+), un joueur
M&A/Risk/Quant/Advisory est interrogé sur SON métier plutôt que sur le quiz
générique de diversification, et General/Portfolio ne changent pas."""
import random

import pytest

from core import missions, portfolio_missions as PM
from core import portfolio as pf
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


# ------------------------------------------------------------------ pool_for_track
@pytest.mark.parametrize("track", ["M&A", "Risk", "Quant", "Advisory"])
def test_specialized_tracks_have_a_distinct_pool(track):
    generic_ids = {c[0] for c in PM.PRACTICAL_CHECKS}
    pool_ids = {c[0] for c in PM.pool_for_track(track)}
    assert pool_ids - generic_ids, f"{track} pool should include track-specific checks"


@pytest.mark.parametrize("track", ["General", "Portfolio", "Unknown"])
def test_general_and_portfolio_use_the_generic_pool(track):
    assert PM.pool_for_track(track) == PM.PRACTICAL_CHECKS


def test_every_track_check_id_is_unique_within_its_pool():
    for track, pool in PM.TRACK_CHECKS.items():
        ids = [c[0] for c in pool]
        assert len(ids) == len(set(ids)), track


# --------------------------------------------------------------------- checks purs
def test_owns_ma_target_false_then_true(player, market):
    assert not PM._owns_ma_target_ok(player, market)
    from core import ma
    from data.ma_targets import all_targets
    t = min(all_targets(), key=ma.ask_price)
    assert ma.acquire(player, t["ticker"], 0.5)["ok"]
    assert PM._owns_ma_target_ok(player, market)


def test_ma_leverage_ok_vacuously_true_without_targets(player, market):
    assert PM._ma_leverage_ok(player, market)


def test_ma_leverage_flags_an_overleveraged_target(player, market):
    from core import ma
    from data.ma_targets import all_targets
    t = min(all_targets(), key=ma.ask_price)
    assert ma.acquire(player, t["ticker"], 0.85)["ok"]
    inst = next(iter(player.ma_owned.values()))
    inst["debt_balance"] = inst["revenue"] * 5.0   # largement > 3x
    assert not PM._ma_leverage_ok(player, market)


def test_var_within_firm_budget_true_for_empty_book(player, market):
    assert PM._var_within_firm_budget_ok(player, market)


def test_holds_option_false_then_true(player, market):
    assert not PM._holds_option_ok(player, market)
    from core import options as opt
    tk = market.top_companies(n=1)[0]["ticker"]
    res = opt.buy(player, market, tk, "call", 1.00, 0.5, 10)
    assert res["ok"]
    assert PM._holds_option_ok(player, market)


def test_delta_hedged_vacuously_true_without_options(player, market):
    assert PM._delta_hedged_ok(player, market)


def test_delta_hedged_false_when_naked_long_call(player, market):
    from core import options as opt
    tk = market.top_companies(n=1)[0]["ticker"]
    assert opt.buy(player, market, tk, "call", 1.00, 0.5, 50)["ok"]
    # aucune action en face : delta net == delta brut => pas couvert
    assert not PM._delta_hedged_ok(player, market)


def test_has_active_mandate_false_then_true(player, market):
    assert not PM._has_active_mandate_ok(player, market)
    player.mandates.append({"id": 1, "client": "Test", "capital": 100_000.0,
                            "target_pct": 1.0, "horizon": 2, "max_beta": 2.0,
                            "reward_cash": 100.0, "reward_rep": 5, "penalty_rep": 5,
                            "type": "growth", "start_nw": 1_000_000.0,
                            "deadline_q": 99})
    assert PM._has_active_mandate_ok(player, market)


def test_mandate_constraints_vacuously_true_without_mandates(player, market):
    assert PM._mandate_constraints_ok(player, market)


# ---------------------------------------------------------------- items générés
@pytest.mark.parametrize("track", ["M&A", "Risk", "Quant", "Advisory"])
def test_practical_items_for_track_draw_from_the_track_pool(player, market, track):
    player.track = track
    items = PM.practical_items_for_track(player, market, count=2, rng=random.Random(1))
    assert len(items) == 2
    pool_prompts = {c[1] for c in PM.pool_for_track(track)} | {c[2] for c in PM.pool_for_track(track)}
    assert all(it["prompt"] in pool_prompts for it in items)


def test_practical_items_for_track_defaults_to_generic_for_general(player, market):
    player.track = "General"
    items = PM.practical_items_for_track(player, market, count=2, rng=random.Random(1))
    generic_prompts = {c[1] for c in PM.PRACTICAL_CHECKS} | {c[2] for c in PM.PRACTICAL_CHECKS}
    assert all(it["prompt"] in generic_prompts for it in items)


# --------------------------------------------------------------------- intégration
@pytest.mark.parametrize("track", ["M&A", "Risk", "Quant", "Advisory", "Portfolio", "General"])
def test_generate_portfolio_tier_uses_track_pool(player, market, track):
    player.track = track
    m = missions.generate(player.grade_index, market, rng=random.Random(3),
                          track=track, player=player)
    assert m["kind"] == "portfolio"
    assert len(m["items"]) == missions.MAX_ITEMS
    pool = PM.pool_for_track(track)
    pool_prompts = {c[1] for c in pool} | {c[2] for c in pool}
    n_practical = sum(1 for it in m["items"] if it["prompt"] in pool_prompts)
    assert n_practical == 2


@pytest.mark.parametrize("track", ["M&A", "Risk", "Quant", "Advisory", "Portfolio"])
def test_generate_brief_includes_track_flavor(player, market, track):
    m = missions.generate(player.grade_index, market, rng=random.Random(1),
                          track=track, player=player)
    assert m["brief"] != missions._L(*missions._TIER_BRIEFS["portfolio"])


def test_generate_brief_unchanged_for_general(player, market):
    m = missions.generate(player.grade_index, market, rng=random.Random(1),
                          track="General", player=player)
    assert m["brief"] == missions._L(*missions._TIER_BRIEFS["portfolio"])
