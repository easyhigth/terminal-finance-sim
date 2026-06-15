"""Tests de la chronologie scénarisée (core/history.py)."""
from core.market import Market
from core.game_state import PlayerState
from core import history


def _player(quarter):
    p = PlayerState()
    p.quarter = quarter
    return p


def test_event_fires_at_its_quarter_once():
    m = Market(seed=1)
    p = _player(quarter=3)            # elapsed = 2 -> h_tighten
    ev = history.maybe_trigger(p, m)
    assert ev is not None and ev["id"] == "h_tighten"
    assert "h_tighten" in p.flags["history_fired"]
    assert len(m.crises) == 1
    # ne se redéclenche pas
    assert history.maybe_trigger(p, m) is None


def test_no_event_off_schedule():
    m = Market(seed=1)
    p = _player(quarter=4)            # elapsed = 3 -> aucun événement programmé
    assert history.maybe_trigger(p, m) is None


def test_systemic_crash_scheduled_year_one():
    m = Market(seed=1)
    p = _player(quarter=6)            # elapsed = 5 -> h_gfc
    ev = history.maybe_trigger(p, m)
    assert ev["id"] == "h_gfc" and ev["kind"] == "bad"


def test_localized_fields():
    ev = history._BY_ID["h_aiboom"]
    fr_name, fr_story = history.localized(ev, "fr")
    en_name, en_story = history.localized(ev, "en")
    assert fr_name != en_name and "AI" in en_name


def test_full_timeline_fires_over_run():
    m = Market(seed=1)
    p = PlayerState()
    fired = []
    for q in range(1, 26):
        p.quarter = q
        ev = history.maybe_trigger(p, m)
        if ev:
            fired.append(ev["id"])
    assert len(fired) == len(history.TIMELINE)   # toute la campagne s'est jouée
