"""Tests du classement séparé « Défi du jour » (core/hall_of_fame.py)."""
import datetime

import pytest

from core import difficulty
from core import hall_of_fame as hof
from core.game_state import PlayerState


@pytest.fixture(autouse=True)
def _isolated_files(tmp_path, monkeypatch):
    monkeypatch.setattr(hof, "_PATH", str(tmp_path / "hall_of_fame.json"))
    monkeypatch.setattr(hof, "_DAILY_PATH", str(tmp_path / "hall_of_fame_daily.json"))


def _player(name="Trainee", daily=False, date=None):
    p = PlayerState()
    p.name = name
    p.cash = 100_000.0
    p.best_cash = 250_000.0
    if daily:
        difficulty.mark_daily(p, date or datetime.date(2026, 7, 2))
    return p


def test_non_daily_run_has_no_daily_date():
    p = _player()
    hof.record(p, 50.0)
    entry = hof.load()[0]
    assert entry["daily_date"] is None
    assert hof.load_daily() == []


def test_daily_run_is_marked_and_stored_separately():
    p = _player(daily=True)
    hof.record(p, 50.0)
    entry = hof.load()[0]
    assert entry["daily_date"] == "2026-07-02"
    daily = hof.load_daily()
    assert len(daily) == 1
    assert daily[0]["daily_date"] == "2026-07-02"


def test_top_for_daily_filters_by_date_and_excludes_other_dates():
    hof.record(_player("A", daily=True, date=datetime.date(2026, 7, 2)), 40.0)
    hof.record(_player("B", daily=True, date=datetime.date(2026, 7, 2)), 70.0)
    hof.record(_player("C", daily=True, date=datetime.date(2026, 7, 3)), 90.0)
    hof.record(_player("D"), 99.0)   # run classique : jamais dans le classement du défi
    today = hof.top_for_daily(datetime.date(2026, 7, 2))
    assert [r["name"] for r in today] == ["B", "A"]


def test_daily_run_survives_general_table_eviction():
    """Un run de défi modeste ne doit pas disparaître du classement du défi
    juste parce que des runs classiques bien meilleurs saturent le panthéon
    général (deux tables indépendantes)."""
    p = _player("DailyPlayer", daily=True)
    hof.record(p, 1.0)   # score très faible
    for i in range(hof.MAX_RUNS + 5):
        hof.record(_player(f"Classique{i}"), 1000.0 + i)   # évince DailyPlayer du général
    assert "DailyPlayer" not in [r["name"] for r in hof.load()]
    assert "DailyPlayer" in [r["name"] for r in hof.top_for_daily(datetime.date(2026, 7, 2))]


def test_daily_rank_matches_own_entry():
    p_a = _player("A", daily=True)
    hof.record(p_a, 40.0)
    p_b = _player("B", daily=True)
    hof.record(p_b, 70.0)
    assert hof.daily_rank(p_b) == 1
    assert hof.daily_rank(p_a) == 2


def test_daily_rank_none_for_non_daily_player():
    p = _player()
    hof.record(p, 50.0)
    assert hof.daily_rank(p) is None
