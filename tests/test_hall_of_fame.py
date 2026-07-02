"""Tests du panthéon local (core/hall_of_fame.py, logique pure)."""
import datetime

import pytest

from core import hall_of_fame as hof
from core.game_state import PlayerState


@pytest.fixture(autouse=True)
def _isolated_file(tmp_path, monkeypatch):
    monkeypatch.setattr(hof, "_PATH", str(tmp_path / "hall_of_fame.json"))


def _player(name="Trainee", cash=100_000.0, best=250_000.0):
    p = PlayerState()
    p.name = name
    p.cash = cash
    p.best_cash = best
    return p


def test_empty_hall_returns_no_runs():
    assert hof.load() == []
    assert hof.top() == []


def test_record_returns_rank_and_persists():
    rank = hof.record(_player("A"), 62.0, date=datetime.date(2026, 7, 2))
    assert rank == 1
    runs = hof.load()
    assert len(runs) == 1
    r = runs[0]
    assert r["name"] == "A" and r["score"] == 62.0
    assert r["best_nw"] == 250_000.0
    assert r["date"] == "2026-07-02"


def test_ranking_is_by_score_desc():
    hof.record(_player("A"), 40.0)
    assert hof.record(_player("B"), 70.0) == 1
    assert hof.record(_player("C"), 55.0) == 2
    assert [r["name"] for r in hof.top()] == ["B", "C", "A"]


def test_tie_keeps_older_run_ahead():
    hof.record(_player("Ancien"), 50.0)
    assert hof.record(_player("Nouveau"), 50.0) == 2


def test_hall_is_capped_at_max_runs():
    for i in range(hof.MAX_RUNS + 4):
        hof.record(_player(f"P{i}"), float(i))
    assert len(hof.load()) == hof.MAX_RUNS
    # un run trop faible pour entrer au tableau ne reçoit pas de rang
    assert hof.record(_player("Faible"), -1.0) is None


def test_corrupt_file_is_ignored(tmp_path):
    with open(hof._PATH, "w", encoding="utf-8") as f:
        f.write("{pas du json[")
    assert hof.load() == []
    assert hof.record(_player("A"), 10.0) == 1
