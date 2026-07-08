"""Tests du partage sans serveur du score de Défi du jour
(core/challenge_share.py + extensions "amis" de core/hall_of_fame.py)."""
import datetime

import pytest

from core import challenge_share as cs
from core import difficulty
from core import hall_of_fame as hof
from core.game_state import PlayerState


@pytest.fixture(autouse=True)
def _isolated_files(tmp_path, monkeypatch):
    monkeypatch.setattr(hof, "_PATH", str(tmp_path / "hall_of_fame.json"))
    monkeypatch.setattr(hof, "_DAILY_PATH", str(tmp_path / "hall_of_fame_daily.json"))
    monkeypatch.setattr(hof, "_FRIENDS_PATH", str(tmp_path / "hall_of_fame_friends.json"))


def _daily_player(name="Trainee", date=None):
    p = PlayerState()
    p.name = name
    p.cash = 100_000.0
    p.best_cash = 250_000.0
    difficulty.mark_daily(p, date or datetime.date(2026, 7, 8))
    return p


# --------------------------------------------------------- encode/decode
def test_encode_decode_roundtrip():
    p = _daily_player()
    entry = hof.make_entry(p, 72.5)
    code = cs.encode_entry(entry)
    assert code.startswith("FSC1:")
    decoded = cs.decode_entry(code)
    assert decoded["name"] == "Trainee"
    assert decoded["score"] == 72.5
    assert decoded["daily_date"] == "2026-07-08"


def test_decode_rejects_garbage():
    assert cs.decode_entry("not a code") is None
    assert cs.decode_entry("") is None
    assert cs.decode_entry("FSC1:not-valid-base64!!!") is None


def test_decode_rejects_truncated_code():
    p = _daily_player()
    code = cs.encode_entry(hof.make_entry(p, 50.0))
    truncated = code[:len(code) - 6]
    assert cs.decode_entry(truncated) is None


def test_decode_rejects_tampered_checksum():
    p = _daily_player()
    code = cs.encode_entry(hof.make_entry(p, 50.0))
    # bascule un caractère au milieu du blob : le checksum ne doit plus matcher
    tampered = code[:20] + ("A" if code[20] != "A" else "B") + code[21:]
    assert cs.decode_entry(tampered) is None


def test_decode_rejects_non_daily_entry():
    """Un run CLASSIQUE (pas de défi du jour) n'a pas vocation à être
    partagé/comparé — encode_entry n'a de sens que pour un run de défi."""
    p = PlayerState()
    p.name = "Solo"
    entry = hof.make_entry(p, 50.0)
    assert entry["daily_date"] is None
    code = cs.encode_entry(entry)
    assert cs.decode_entry(code) is None


# --------------------------------------------------- import dans hall_of_fame
def test_import_friend_code_adds_to_friends_ranking():
    p = _daily_player(name="Ada")
    code = cs.encode_entry(hof.make_entry(p, 80.0))
    ok, entry = hof.import_friend_code(code)
    assert ok is True
    assert entry["name"] == "Ada"
    assert entry["friend"] is True
    friends = hof.friends_for_daily("2026-07-08")
    assert len(friends) == 1
    assert friends[0]["name"] == "Ada"


def test_import_friend_code_rejects_invalid():
    ok, reason = hof.import_friend_code("garbage")
    assert ok is False
    assert reason == "invalid"


def test_import_friend_code_rejects_duplicate():
    p = _daily_player(name="Ada")
    code = cs.encode_entry(hof.make_entry(p, 80.0))
    ok1, _ = hof.import_friend_code(code)
    ok2, reason = hof.import_friend_code(code)
    assert ok1 is True
    assert ok2 is False
    assert reason == "duplicate"


def test_friends_are_stored_separately_from_locally_played_runs():
    """Les scores importés ne doivent JAMAIS se mélanger aux runs réellement
    joués sur cette machine (load_daily) — deux fichiers distincts."""
    p = _daily_player(name="Ada")
    code = cs.encode_entry(hof.make_entry(p, 80.0))
    hof.import_friend_code(code)
    assert hof.load_daily() == []
    assert len(hof.load_friends()) == 1


def test_combined_daily_ranking_merges_and_sorts():
    p1 = _daily_player(name="Local")
    hof.record(p1, 60.0)
    p2 = _daily_player(name="Ada")
    code = cs.encode_entry(hof.make_entry(p2, 90.0))
    hof.import_friend_code(code)

    combined = hof.combined_daily_ranking("2026-07-08")
    assert [r["name"] for r in combined] == ["Ada", "Local"]   # trié par score décroissant
    assert combined[0]["friend"] is True
    assert not combined[1].get("friend")


def test_combined_daily_ranking_ignores_other_dates():
    p = _daily_player(name="Ada", date=datetime.date(2026, 1, 1))
    code = cs.encode_entry(hof.make_entry(p, 90.0))
    hof.import_friend_code(code)
    assert hof.combined_daily_ranking("2026-07-08") == []
