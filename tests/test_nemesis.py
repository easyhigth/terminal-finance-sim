"""Tests du némésis personnel (core/rivals.py) : désignation au choix de
voie, message d'intro, tête-à-tête trimestriel avec réputation en jeu."""
from core import rivals
from core.game_state import GameState
from core.market import Market


def _setup(track="Quant"):
    gs = GameState()
    p = gs.player
    p.grade_index = 3
    p.cash = 500_000.0
    p.track = track
    m = Market(seed=77)
    for _ in range(5):
        m.step()
    return gs, p, m


def test_designation_picks_rival_of_same_track():
    _gs, p, _m = _setup("Quant")
    r = rivals.designate_nemesis(p)
    assert r is not None and r["track"] == "Quant"
    assert p.flags["nemesis"] == r["name"]
    # message d'intro reçu
    assert any(r["name"] in msg.get("sender", "") for msg in p.inbox)


def test_designation_is_idempotent():
    _gs, p, _m = _setup("Risk")
    rivals.designate_nemesis(p)
    n_msgs = len(p.inbox)
    rivals.designate_nemesis(p)
    assert len(p.inbox) == n_msgs   # pas de doublon d'intro


def test_head_to_head_needs_two_readings():
    _gs, p, m = _setup()
    rivals.designate_nemesis(p, notify=False)
    assert rivals.quarterly_head_to_head(p, m) is None   # premier relevé
    result = rivals.quarterly_head_to_head(p, m)
    assert result is not None
    assert set(result) >= {"win", "my_growth", "his_growth", "rival"}


def test_head_to_head_moves_reputation():
    _gs, p, m = _setup()
    rivals.designate_nemesis(p, notify=False)
    rivals.quarterly_head_to_head(p, m)
    before = p.reputation
    result = rivals.quarterly_head_to_head(p, m)
    expected = before + (rivals.H2H_REP_DELTA if result["win"] else -rivals.H2H_REP_DELTA)
    assert p.reputation == expected
    # le némésis a écrit
    assert any(result["rival"]["name"] in msg.get("sender", "") for msg in p.inbox)


def test_hook_runs_once_per_quarter():
    gs, p, m = _setup()
    rivals.designate_nemesis(p, notify=False)
    for _ in range(3):   # plusieurs pas dans le MÊME trimestre
        m.step()
        gs.advance_step(market=m)
    memo = p.flags.get("nemesis_h2h")
    assert isinstance(memo, dict) and memo.get("quarter") == p.quarter
