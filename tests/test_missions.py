"""Tests du générateur de missions (core/missions.py)."""
import random

import pytest

from core import missions
from core.market import Market


def _market():
    m = Market(seed=11)
    m.sync_to(60)
    return m


def test_reputation_threshold_increases_and_capped():
    assert missions.reputation_threshold(0) == 58
    assert missions.reputation_threshold(5) == 68
    assert missions.reputation_threshold(100) == 92


def test_mission_tier_by_grade():
    assert missions.mission_tier(0) == "report"
    assert missions.mission_tier(1) == "report"
    assert missions.mission_tier(2) == "graph"
    assert missions.mission_tier(3) == "graph"
    assert missions.mission_tier(4) == "decision"
    assert missions.mission_tier(5) == "decision"
    assert missions.mission_tier(6) == "portfolio"
    assert missions.mission_tier(11) == "portfolio"


@pytest.mark.parametrize("grade_index", [0, 2, 4, 6])
def test_generate_produces_well_formed_mission(grade_index):
    m = _market()
    rng = random.Random(grade_index)
    mission = missions.generate(grade_index, m, rng=rng)
    assert mission["grade"] == grade_index
    assert mission["kind"] == missions.mission_tier(grade_index)
    assert mission["items"]
    assert mission["reward_rep"] > 0
    assert mission["reward_cash"] == 0
    for item in mission["items"]:
        assert item["kind"] in ("mcq", "fill")
        assert item["prompt"]


def test_generate_is_deterministic_with_same_rng_seed():
    m = _market()
    a = missions.generate(2, m, rng=random.Random(42))
    b = missions.generate(2, m, rng=random.Random(42))
    assert a["title"] == b["title"]
    assert a["items"] == b["items"]


def test_check_fill_within_relative_tolerance():
    item = {"answer": 100.0, "tol": 0.05}
    assert missions.check_fill(item, 100.0)
    assert missions.check_fill(item, 104.9)
    assert not missions.check_fill(item, 110.0)


def test_check_fill_within_absolute_tolerance():
    item = {"answer": 10.0, "abstol": 1.0}
    assert missions.check_fill(item, 10.9)
    assert not missions.check_fill(item, 12.0)


def test_check_fill_zero_answer_uses_floor_tolerance():
    item = {"answer": 0.0, "tol": 0.05}
    assert missions.check_fill(item, 0.0)
    assert not missions.check_fill(item, 1.0)


def test_grade_focus_matches_tier_text():
    assert "comptes-rendus" in missions.grade_focus(0)
    assert "graphes" in missions.grade_focus(2)
    assert "investir" in missions.grade_focus(4)
    assert "Construire" in missions.grade_focus(6)


def test_compute_rewards_perfect_score():
    mission = {"reward_rep": 10, "grade": 2}
    rep, cash = missions.compute_rewards(mission, 4, 4)
    assert rep == 10
    assert cash == pytest.approx(9000 * 3, rel=1e-6)


def test_compute_rewards_zero_correct_gives_zero_rep():
    mission = {"reward_rep": 10, "grade": 2}
    rep, cash = missions.compute_rewards(mission, 0, 4)
    assert rep == 0
    assert cash == 0


def test_compute_rewards_partial_correct_is_at_least_one_rep():
    mission = {"reward_rep": 10, "grade": 0}
    rep, cash = missions.compute_rewards(mission, 1, 100)
    assert rep == 1   # arrondi à 0 mais plancher à 1 car correct > 0


def test_generate_decision_items_have_three_choices():
    m = _market()
    mission = missions.generate(4, m, rng=random.Random(3))
    for item in mission["items"]:
        assert set(item["choices"]) == {"ACHETER", "CONSERVER", "VENDRE"}


def test_generate_portfolio_items_unique_within_mission():
    m = _market()
    mission = missions.generate(7, m, rng=random.Random(9))
    prompts = [it["prompt"] for it in mission["items"]]
    assert len(prompts) == len(set(prompts))
