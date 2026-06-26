"""Tests de la progression de carrière (core/career.py)."""
import random

import pytest

from core import career
from core.game_state import PlayerState


def _player(grade_index=2, reputation=50, quarter=1):
    p = PlayerState(grade_index=grade_index, reputation=reputation, quarter=quarter)
    p.grade_start_quarter = quarter
    return p


def test_log_appends_dated_entry():
    p = _player(quarter=3)
    p.day = 100
    career.log(p, "info", "test event")
    assert p.journal[-1] == {"day": 100, "quarter": 3, "kind": "info", "text": "test event"}


def test_log_caps_journal_at_80_entries():
    p = _player()
    for i in range(90):
        career.log(p, "info", f"event {i}")
    assert len(p.journal) == 80
    assert p.journal[-1]["text"] == "event 89"
    assert p.journal[0]["text"] == "event 10"


def test_promotion_requirements_basic_fields():
    p = _player(grade_index=0, reputation=0)
    reqs = career.promotion_requirements(p)
    labels = [r["label"] for r in reqs]
    assert "Réputation" in labels
    assert "Missions (ce grade)" in labels
    # grade 0 : pas de deals requis, pas d'ancienneté requise
    assert "Deals conclus (ce grade)" not in labels
    assert "Ancienneté (trimestres)" not in labels


def test_promotion_requirements_targets_always_positive():
    """Le panneau carrière (scene_career, scene_terminal) calcule un ratio
    current/target pour afficher une barre de progression : un `target` à 0
    provoquerait une division par zéro côté UI. Vérifie sur tout grade/
    réputation/quarter qu'aucun critère retourné n'a une cible nulle."""
    for gi in range(len(career.config.GRADES)):
        for quarter in (1, 2, 5, 10):
            p = _player(grade_index=gi, reputation=0, quarter=quarter)
            for r in career.promotion_requirements(p):
                assert r["target"] > 0, f"target nul pour {r['label']} (grade {gi})"


def test_promotion_requirements_adds_deals_and_tenure_at_higher_grade():
    p = _player(grade_index=4, quarter=5)
    reqs = career.promotion_requirements(p)
    labels = [r["label"] for r in reqs]
    assert "Deals conclus (ce grade)" in labels
    assert "Ancienneté (trimestres)" in labels


def test_promotion_requirements_met_flags():
    p = _player(grade_index=0, reputation=100)
    p.grade_missions = 10
    reqs = career.promotion_requirements(p)
    assert all(r["met"] for r in reqs)


def test_promotion_ready_false_when_criteria_unmet():
    p = _player(grade_index=0, reputation=0)
    assert not career.promotion_ready(p)


def test_promotion_ready_true_when_all_met():
    p = _player(grade_index=0, reputation=100)
    p.grade_missions = 10
    assert career.promotion_ready(p)


def test_promotion_ready_false_at_max_grade():
    p = _player(grade_index=11, reputation=100)
    p.grade_missions = 100
    p.grade_deals = 100
    assert not p.can_promote()
    assert not career.promotion_ready(p)


def test_promotion_requires_chosen_track_from_grade_2():
    p = _player(grade_index=2, reputation=100)
    p.grade_missions = 10
    p.grade_deals = 10
    reqs = career.promotion_requirements(p)
    track_req = next(r for r in reqs if r["kind"] == "track")
    assert track_req["met"] is False
    assert not career.promotion_ready(p)
    p.track = "Quant"
    assert all(r["kind"] != "track" for r in career.promotion_requirements(p))
    assert career.promotion_ready(p)


def test_promotion_does_not_require_track_below_grade_2():
    p = _player(grade_index=1, reputation=100)
    p.grade_missions = 10
    assert all(r["kind"] != "track" for r in career.promotion_requirements(p))
    assert career.promotion_ready(p)


def test_award_promotion_track_specific_titles_at_top_grades():
    p = _player(grade_index=10)
    p.track = "Quant"
    assert career.award_promotion(p) == "Head of Quant Strategies"
    p2 = _player(grade_index=11)
    p2.track = "M&A"
    assert career.award_promotion(p2) == "Légende des fusions-acquisitions"


def test_missing_criteria_lists_unmet_labels():
    p = _player(grade_index=0, reputation=0)
    missing = career.missing_criteria(p)
    assert "Réputation" in missing
    assert "Missions (ce grade)" in missing


def test_certification_bonus_reduces_requirements():
    from core import certifications
    p = _player(grade_index=2, reputation=0, quarter=1)
    p.track = "Portfolio"
    p.certs["CFA"] = certifications.PROGRAMS["CFA"]["levels"]
    reqs = career.promotion_requirements(p)
    rep_req = next(r for r in reqs if r["label"] == "Réputation")
    from core import missions as missions_mod
    base_thr = missions_mod.reputation_threshold(2)
    assert rep_req["target"] == max(50, base_thr - 7)


def test_award_promotion_grants_track_title_at_grade_6():
    p = _player(grade_index=6, quarter=1)
    p.track = "Quant"
    title = career.award_promotion(p)
    assert title == "Quant Star"
    assert "Quant Star" in p.titles


def test_award_promotion_none_at_irrelevant_grade():
    p = _player(grade_index=3)
    assert career.award_promotion(p) is None


def test_award_promotion_does_not_duplicate_title():
    p = _player(grade_index=10)
    career.award_promotion(p)
    career.award_promotion(p)
    assert p.titles.count("Managing Director émérite") == 1


def test_generate_objectives_returns_2_to_4_with_rewards():
    p = _player(grade_index=2)
    objs = career.generate_objectives(p, rng=random.Random(0))
    assert 2 <= len(objs) <= 4
    for o in objs:
        assert o["done"] is False
        assert o["reward_rep"] == 3
        assert o["reward_cash"] > 0


def test_generate_objectives_excludes_deals_below_grade_1():
    p = _player(grade_index=0)
    seen_kinds = set()
    for seed in range(30):
        objs = career.generate_objectives(p, rng=random.Random(seed))
        seen_kinds.update(o["kind"] for o in objs)
    assert "deals" not in seen_kinds


def test_objective_progress_missions():
    p = _player(grade_index=2)
    p.missions_done = 5
    obj = {"kind": "missions", "target": 3, "base": 2}
    cur, target, met = career.objective_progress(p, obj)
    assert cur == 3 and target == 3 and met


def test_objective_progress_cash_and_reputation():
    p = _player(grade_index=2, reputation=80)
    p.cash = 50000.0
    cur, target, met = career.objective_progress(p, {"kind": "cash", "target": 40000.0})
    assert cur == 50000.0 and met
    cur, target, met = career.objective_progress(p, {"kind": "reputation", "target": 90})
    assert cur == 80 and not met


def test_objective_label_contains_progress():
    p = _player(grade_index=2)
    p.missions_done = 3
    obj = {"kind": "missions", "target": 2, "base": 1}
    label = career.objective_label(p, obj)
    assert "2" in label and "2/2" in label


def test_ensure_objectives_regenerates_on_new_quarter():
    p = _player(grade_index=2, quarter=1)
    career.ensure_objectives(p, rng=random.Random(0))
    assert p.objectives_quarter == 1
    old = p.objectives
    p.quarter = 2
    changed = career.ensure_objectives(p, rng=random.Random(1))
    assert changed
    assert p.objectives_quarter == 2
    assert p.objectives is not old


def test_ensure_objectives_noop_if_same_quarter_and_present():
    p = _player(grade_index=2, quarter=1)
    career.ensure_objectives(p, rng=random.Random(0))
    objs_before = p.objectives
    changed = career.ensure_objectives(p, rng=random.Random(1))
    assert not changed
    assert p.objectives is objs_before


def test_close_quarter_awards_rewards_for_completed_objectives():
    p = _player(grade_index=2)
    p.objectives = [
        {"kind": "cash", "target": 100.0, "done": False, "reward_rep": 3, "reward_cash": 1000.0},
        {"kind": "reputation", "target": 999, "done": False, "reward_rep": 3, "reward_cash": 500.0},
    ]
    p.cash = 200.0
    p.reputation = 50
    summary = career.close_quarter(p)
    assert summary["done"] == 1
    assert summary["total"] == 2
    assert p.reputation == 53
    assert p.cash == pytest.approx(200.0 + 1000.0)


def test_close_quarter_perfect_bonus_when_all_objectives_met():
    p = _player(grade_index=1)
    p.objectives = [
        {"kind": "cash", "target": 0.0, "done": False, "reward_rep": 3, "reward_cash": 1000.0},
    ]
    p.cash = 10.0
    summary = career.close_quarter(p)
    assert summary["done"] == summary["total"] == 1
    # bonus "trimestre parfait" : +4 rep et cash supplémentaire
    assert p.reputation == 50 + 3 + 4
    assert p.cash == pytest.approx(10.0 + 1000.0 + 18000 * (1 + 1))


def test_close_quarter_no_objectives_is_noop():
    p = _player(grade_index=2)
    p.objectives = []
    summary = career.close_quarter(p)
    assert summary == {"done": 0, "total": 0, "rep": 0, "cash": 0.0}
    assert p.reputation == 50


def test_close_quarter_logs_partial_completion_reason():
    p = _player(grade_index=2)
    p.objectives = [
        {"kind": "cash", "target": 100.0, "done": False, "reward_rep": 3, "reward_cash": 1000.0},
        {"kind": "reputation", "target": 999, "done": False, "reward_rep": 3, "reward_cash": 500.0},
    ]
    p.cash = 200.0
    p.reputation = 50
    p.rep_log = []
    career.close_quarter(p)
    assert len(p.rep_log) == 1
    reason, delta = p.rep_log[0]
    assert delta == 3
    assert "1/2" in reason


def test_close_quarter_logs_perfect_quarter_reason():
    p = _player(grade_index=1)
    p.objectives = [
        {"kind": "cash", "target": 0.0, "done": False, "reward_rep": 3, "reward_cash": 1000.0},
    ]
    p.cash = 10.0
    p.rep_log = []
    career.close_quarter(p)
    assert len(p.rep_log) == 1
    reason, delta = p.rep_log[0]
    assert delta == 3 + 4
    assert "parfait" in reason.lower()
