"""Tests des runs fantômes (core/ghost.py) : compression de courbe, transport
dans les codes de partage, sélection par défi du jour, projection d'échelle."""
from core import challenge_share, ghost
from core.game_state import PlayerState


def test_compress_curve_normalises_and_downsamples():
    hist = [100.0 + i for i in range(200)]
    curve = ghost.compress_curve(hist)
    assert len(curve) == ghost.GHOST_POINTS
    assert curve[0] == 1.0
    assert curve[-1] == round(hist[-1] / hist[0], 4)


def test_compress_curve_degenerate_inputs():
    assert ghost.compress_curve([]) is None
    assert ghost.compress_curve([100.0]) is None
    assert ghost.compress_curve([0.0, 50.0]) is None


def test_curve_travels_through_share_code():
    entry = {"name": "Ami", "grade": "VP", "track": "Quant", "continent": "Europe",
             "quarters": 4, "days": 300, "best_nw": 2e6, "score": 71.0,
             "hardcore": False, "daily_date": "2026-07-17",
             "curve": [1.0, 1.05, 0.98, 1.2]}
    code = challenge_share.encode_entry(entry)
    decoded = challenge_share.decode_entry(code)
    assert decoded["curve"] == [1.0, 1.05, 0.98, 1.2]


def test_old_codes_without_curve_still_decode():
    entry = {"name": "Vieux", "grade": "VP", "track": "Quant", "continent": "Europe",
             "quarters": 4, "days": 300, "best_nw": 2e6, "score": 71.0,
             "hardcore": False, "daily_date": "2026-07-17"}
    code = challenge_share.encode_entry(entry)
    decoded = challenge_share.decode_entry(code)
    assert decoded is not None and decoded["curve"] is None


def test_ghosts_only_for_matching_daily(tmp_path, monkeypatch):
    from core import hall_of_fame as hof
    monkeypatch.setattr(hof, "_friends_path", lambda: str(tmp_path / "friends.json"))
    hof._save_friends([
        {"name": "A", "daily_date": "2026-07-17", "curve": [1.0, 1.1]},
        {"name": "B", "daily_date": "2026-01-01", "curve": [1.0, 0.9]},
        {"name": "C", "daily_date": "2026-07-17", "curve": None},
    ])
    p = PlayerState()
    assert ghost.ghosts_for(p) == []          # run classique : pas de fantôme
    p.flags["daily_challenge"] = "2026-07-17"
    ghosts = ghost.ghosts_for(p)
    assert [g["name"] for g in ghosts] == ["A"]


def test_project_scales_to_local_start():
    vals = ghost.project([1.0, 1.5, 2.0], start_value=200.0, n_points=5)
    assert len(vals) == 5
    assert vals[0] == 200.0 and vals[-1] == 400.0
