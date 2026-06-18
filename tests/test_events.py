"""Tests du moteur d'événements de marché (core/events.py)."""
import random

from core import events
from core.game_state import PlayerState


def _player(grade=0, continent="Europe"):
    p = PlayerState()
    p.grade_index = grade
    p.continent = continent
    p.cash = 100_000.0
    p.reputation = 50
    return p


def test_roll_events_deterministic_with_seeded_rng():
    p1, p2 = _player(grade=8), _player(grade=8)
    out1 = events.roll_events(p1, rng=random.Random(42))
    out2 = events.roll_events(p2, rng=random.Random(42))
    assert out1 == out2


def test_roll_events_respects_min_grade():
    p = _player(grade=0)
    out = events.roll_events(p, rng=random.Random(1), max_events=20)
    ids = {e["id"] for e in out}
    for eid in ids:
        tmpl = next(t for t in events.EVENT_TEMPLATES if t["id"] == eid)
        assert tmpl["min_grade"] <= 0


def test_roll_events_respects_region_filter():
    p = _player(grade=8, continent="Europe")
    for _ in range(20):
        out = events.roll_events(p, rng=random.Random(_), max_events=5)
        for e in out:
            tmpl = next(t for t in events.EVENT_TEMPLATES if t["id"] == e["id"])
            assert tmpl["regions"] is None or p.continent in tmpl["regions"]


def test_roll_events_applies_cash_and_reputation_deltas():
    p = _player(grade=8)
    cash_before, rep_before = p.cash, p.reputation
    out = events.roll_events(p, rng=random.Random(7))
    assert p.cash == cash_before + sum(e["cash"] for e in out)
    assert p.reputation == rep_before + sum(e["rep"] for e in out)


def test_roll_events_no_duplicate_ids_in_one_roll():
    p = _player(grade=8)
    out = events.roll_events(p, rng=random.Random(3), max_events=5)
    ids = [e["id"] for e in out]
    assert len(ids) == len(set(ids))
