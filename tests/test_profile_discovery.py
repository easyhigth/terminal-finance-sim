"""Tests du suivi de découverte des apps du bureau (core/profile.py) :
chaque app ouverte au moins une fois est notée dans le profil machine —
diagnostic de découvrabilité (« quelles apps personne ne trouve ? »)."""
import core.profile as profile


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(profile, "_PATH", str(tmp_path / "profile.json"))


def test_record_and_query_apps_opened(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    assert profile.apps_opened() == set()
    profile.record_app_opened("trading")
    profile.record_app_opened("sheet")
    profile.record_app_opened("trading")   # idempotent
    assert profile.apps_opened() == {"trading", "sheet"}


def test_apps_never_opened(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    profile.record_app_opened("trading")
    assert profile.apps_never_opened(["trading", "watchlist", "journal"]) == \
        ["journal", "watchlist"]


def test_record_ignores_empty_key(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    profile.record_app_opened("")
    profile.record_app_opened(None)
    assert profile.apps_opened() == set()


def test_discovery_does_not_clobber_veteran_data(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    profile.record_grade_reached(6)
    profile.record_app_opened("trading")
    data = profile.load()
    assert data["best_grade_reached"] == 6
    assert data["apps_opened"] == ["trading"]
