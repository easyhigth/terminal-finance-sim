from core import legacy
from core import market
from core.game_state import PlayerState


def _mk(seed=7):
    m = market.Market(seed=seed)
    m.sync_to(market.WARMUP_STEPS)
    p = PlayerState(continent="Europe")
    p.cash = 1_000_000.0
    return p, m


def test_on_quarter_close_no_rivals_skips_rank_streak():
    p, m = _mk()
    assert p.rivals == []
    legacy.on_quarter_close(p, m)
    assert "top_rank_streak" not in p.flags


def test_on_quarter_close_rank_streak_increments_and_resets():
    p, m = _mk()
    p.rivals = [{"name": "Rival", "firm": "X", "track": "Quant", "score": 0}]
    from unittest.mock import patch
    with patch("core.rivals.player_rank", return_value=(1, 2)):
        legacy.on_quarter_close(p, m)
        legacy.on_quarter_close(p, m)
    assert p.flags["top_rank_streak"] == 2
    with patch("core.rivals.player_rank", return_value=(2, 2)):
        legacy.on_quarter_close(p, m)
    assert p.flags["top_rank_streak"] == 0


def test_on_quarter_close_profit_streak_tracks_growth():
    p, m = _mk()
    legacy.on_quarter_close(p, m)  # premier appel : pas de last_nw -> pas d'incrément
    assert p.flags.get("profit_streak", 0) == 0
    p.cash += 50_000.0
    legacy.on_quarter_close(p, m)
    assert p.flags["profit_streak"] == 1
    p.cash -= 100_000.0
    legacy.on_quarter_close(p, m)
    assert p.flags["profit_streak"] == 0


def test_on_quarter_close_integrity_streak():
    p, m = _mk()
    p.reputation = 90
    p.heat = 0
    p.cash = 10_000_000.0
    legacy.on_quarter_close(p, m)
    legacy.on_quarter_close(p, m)
    assert p.flags["integrity_streak"] == 2
    p.heat = 50
    legacy.on_quarter_close(p, m)
    assert p.flags["integrity_streak"] == 0


def test_check_new_awards_goal_once():
    p, m = _mk()
    p.flags["major_crises"] = 1
    earned = legacy.check_new(p, m)
    ids = [g["id"] for g in earned]
    assert "major_crisis_survivor" in ids
    assert "major_crisis_survivor" in p.legacy
    # second appel : déjà acquis, ne doit pas être ré-attribué
    earned2 = legacy.check_new(p, m)
    assert all(g["id"] != "major_crisis_survivor" for g in earned2)


def test_check_new_test_exception_is_swallowed():
    p, m = _mk()
    bad_goal = {"id": "broken", "name": "x", "desc": "x",
                "progress": lambda p, m: (0, 1),
                "test": lambda p, m: 1 / 0}
    original = legacy.GOALS[:]
    legacy.GOALS.append(bad_goal)
    try:
        earned = legacy.check_new(p, m)
        assert all(g["id"] != "broken" for g in earned)
        assert "broken" not in p.legacy
    finally:
        legacy.GOALS[:] = original


def test_get_and_all_goals():
    assert legacy.get("desk_no1")["id"] == "desk_no1"
    assert legacy.get("unknown") is None
    assert legacy.all_goals() is legacy.GOALS
