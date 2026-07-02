"""Tests des nouveaux badges (panthéon, arcs narratifs, difficulté)."""
from core import badges
from core.game_state import PlayerState
from data.story_arcs import ARCS


def test_alumnus_badge_needs_mentor_arc_done():
    p = PlayerState()
    assert badges.get("alumnus")["test"](p, None) is False
    p.flags["story_arcs_done"] = ["mentor"]
    assert badges.get("alumnus")["test"](p, None) is True


def test_well_connected_needs_all_arcs():
    p = PlayerState()
    ids = [a["id"] for a in ARCS]
    assert len(ids) >= 1
    p.flags["story_arcs_done"] = ids[:-1] if len(ids) > 1 else []
    assert badges.get("well_connected")["test"](p, None) is False
    p.flags["story_arcs_done"] = ids
    assert badges.get("well_connected")["test"](p, None) is True


def test_well_connected_progress_matches_total_arc_count():
    p = PlayerState()
    p.flags["story_arcs_done"] = [ARCS[0]["id"]]
    cur, target = badges.get("well_connected")["progress"](p, None)
    assert cur == 1
    assert target == len(ARCS)


def test_no_safety_net_needs_demanding_and_grade():
    p = PlayerState()
    test = badges.get("no_safety_net")["test"]
    assert test(p, None) is False
    p.flags["difficulty"] = "demanding"
    p.grade_index = 3
    assert test(p, None) is False
    p.grade_index = 4
    assert test(p, None) is True
    p.flags["difficulty"] = "normal"
    assert test(p, None) is False


def test_hof_legend_needs_top3_flag():
    p = PlayerState()
    assert badges.get("hof_legend")["test"](p, None) is False
    p.flags["hof_top3"] = True
    assert badges.get("hof_legend")["test"](p, None) is True


def test_check_new_awards_new_badges():
    p = PlayerState()
    p.flags["story_arcs_done"] = ["mentor"]
    earned = badges.check_new(p, None)
    ids = [b["id"] for b in earned]
    assert "alumnus" in ids
    assert "alumnus" in p.badges
    # ne se réattribue pas au tour suivant
    assert "alumnus" not in [b["id"] for b in badges.check_new(p, None)]
