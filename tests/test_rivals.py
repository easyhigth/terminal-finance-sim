"""Tests des rivaux actifs (core/rivals.py)."""
import random

from core import career, rivals, market
from core.game_state import PlayerState


def _mk():
    m = market.Market(seed=123)
    m.sync_to(market.WARMUP_STEPS)
    p = PlayerState(continent="Europe")
    rivals.ensure(p)
    return p, m


def test_ensure_creates_rivals_with_action_fields():
    p, _ = _mk()
    assert len(p.rivals) == len(rivals.RIVAL_PROFILES)
    assert all("last" in r and "mood" in r for r in p.rivals)


def test_nemesis_is_above_player_or_none():
    p, m = _mk()
    nem = rivals.nemesis(p, m)
    board = rivals.leaderboard(p, m)
    if board[0]["is_player"]:
        assert nem is None
    else:
        assert nem is not None and nem["score"] >= rivals.player_score(p, m)


def test_act_snipe_removes_a_late_deal():
    p, m = _mk()
    p.deals = [{"id": 1, "title": "Deal tardif", "kind": "M&A",
                "reward_cash": 100_000, "days_left": 5}]
    rng = random.Random(0)
    # force le sniping : on boucle jusqu'à ce qu'il survienne (proba > 0)
    fired = False
    for _ in range(200):
        p.deals = [{"id": 1, "title": "Deal tardif", "kind": "M&A",
                    "reward_cash": 100_000, "days_left": 5}]
        rep0 = p.reputation
        evs = rivals.act(p, m, rng)
        if any(e["type"] == "snipe" for e in evs):
            assert p.deals == []                 # deal raflé -> retiré
            assert p.reputation == rep0 - 2      # pénalité de réputation
            fired = True
            break
    assert fired


def test_act_does_not_snipe_fresh_deals():
    p, m = _mk()
    rng = random.Random(1)
    for _ in range(100):
        p.deals = [{"id": 9, "title": "Deal récent", "kind": "M&A",
                    "reward_cash": 50_000, "days_left": 40}]   # pas en retard
        evs = rivals.act(p, m, rng)
        assert all(e["type"] != "snipe" for e in evs)
        assert len(p.deals) == 1


def test_act_poach_removes_mandate_offer():
    p, m = _mk()
    rng = random.Random(2)
    fired = False
    for _ in range(300):
        p.mandate_offers = [{"id": 7, "client": "Caisse XYZ", "capital": 1_000_000}]
        evs = rivals.act(p, m, rng)
        if any(e["type"] == "poach" for e in evs):
            assert p.mandate_offers == []
            fired = True
            break
    assert fired


def test_act_surge_increases_a_rival_score():
    p, m = _mk()
    rng = random.Random(3)
    fired = False
    for _ in range(300):
        before = [r["score"] for r in p.rivals]
        evs = rivals.act(p, m, rng)
        if any(e["type"] == "surge" for e in evs):
            after = [r["score"] for r in p.rivals]
            assert any(a > b for a, b in zip(after, before))
            fired = True
            break
    assert fired


def test_recent_activity_empty_when_no_rivals_named_in_journal():
    p, _ = _mk()
    career.log(p, "info", "Un événement sans rapport avec les rivaux.")
    assert rivals.recent_activity(p) == []


def test_recent_activity_returns_matching_entries_most_recent_first():
    p, _ = _mk()
    name = p.rivals[0]["name"]
    career.log(p, "info", "Premier événement sans rapport.")
    career.log(p, "deal", f"{name} rafle un deal.")
    career.log(p, "info", "Deuxième événement sans rapport.")
    career.log(p, "crisis", f"{name} débauche un mandat.")
    out = rivals.recent_activity(p)
    assert [e["text"] for e in out] == [f"{name} débauche un mandat.", f"{name} rafle un deal."]


def test_recent_activity_respects_limit():
    p, _ = _mk()
    name = p.rivals[0]["name"]
    for i in range(10):
        career.log(p, "info", f"{name} agit ({i}).")
    out = rivals.recent_activity(p, limit=3)
    assert len(out) == 3
    assert out[0]["text"] == f"{name} agit (9)."
