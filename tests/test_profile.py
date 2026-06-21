import os

import pytest

from core import profile


@pytest.fixture(autouse=True)
def _isolated_profile_path(tmp_path, monkeypatch):
    monkeypatch.setattr(profile, "_PATH", os.path.join(str(tmp_path), "profile.json"))
    yield


def test_load_missing_file_returns_default():
    assert profile.load() == {"best_grade_reached": 0}


def test_record_grade_reached_creates_file_and_persists():
    profile.record_grade_reached(3)
    data = profile.load()
    assert data["best_grade_reached"] == 3
    assert os.path.isfile(profile._path())


def test_record_grade_reached_only_keeps_max():
    profile.record_grade_reached(5)
    profile.record_grade_reached(2)
    assert profile.load()["best_grade_reached"] == 5


def test_is_veteran_threshold():
    assert profile.is_veteran() is False
    profile.record_grade_reached(profile.VETERAN_GRADE)
    assert profile.is_veteran() is True


def test_load_corrupt_json_returns_default(tmp_path):
    path = profile._path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("not valid json {{{")
    assert profile.load() == {"best_grade_reached": 0}
