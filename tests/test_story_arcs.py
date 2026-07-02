"""Tests des arcs narratifs de l'inbox (core/story_arcs.py, logique pure)."""
from core import story_arcs
from core.game_state import PlayerState
from core.market import WARMUP_STEPS, Market
from data.story_arcs import ARCS


class _FakeMarket:
    def __init__(self, step_count):
        self.step_count = step_count


def _player():
    p = PlayerState()
    p.market_seed = 42
    p.market_step = WARMUP_STEPS
    return p


def _run_until_done(p, max_steps=400):
    """Avance pas à pas et collecte tous les messages livrés."""
    delivered = []
    for step in range(WARMUP_STEPS, WARMUP_STEPS + max_steps):
        p.market_step = step
        delivered += story_arcs.on_step(p, _FakeMarket(step))
    return delivered


def test_arcs_content_is_well_formed():
    ids = [a["id"] for a in ARCS]
    assert len(ids) == len(set(ids))
    for arc in ARCS:
        assert arc["stages"], arc["id"]
        for st in arc["stages"]:
            assert st["delay"] >= 1
            assert st["sender"] and st["subject"] and st["body"]
        assert "effect" in arc


def test_arc_starts_delivers_all_stages_then_completes():
    p = _player()
    arc = ARCS[0]
    delivered = _run_until_done(p, max_steps=60)
    senders = [d["sender"] for d in delivered[:len(arc["stages"])]]
    assert senders == [s["sender"] for s in arc["stages"]]
    assert delivered[len(arc["stages"]) - 1]["finale"] is True
    assert arc["id"] in p.flags["story_arcs_done"]
    # les messages ont bien atterri dans l'inbox
    assert len(p.inbox) >= len(arc["stages"])


def test_finale_applies_effect():
    p = _player()
    rep_before, cash_before = p.reputation, p.cash
    _run_until_done(p, max_steps=400)
    total_rep = sum(a["effect"].get("rep", 0) for a in ARCS)
    total_cash = sum(a["effect"].get("cash", 0.0) for a in ARCS)
    assert p.reputation == min(100, rep_before + total_rep)
    assert p.cash == cash_before + total_cash


def test_all_arcs_play_once_and_never_repeat():
    p = _player()
    delivered = _run_until_done(p, max_steps=400)
    expected = sum(len(a["stages"]) for a in ARCS)
    assert len(delivered) == expected
    assert sorted(p.flags["story_arcs_done"]) == sorted(a["id"] for a in ARCS)
    # plus rien ne se passe ensuite
    p.market_step += 1
    assert story_arcs.on_step(p, _FakeMarket(p.market_step)) == []


def test_deterministic_for_same_steps():
    p1, p2 = _player(), _player()
    d1 = _run_until_done(p1, max_steps=100)
    d2 = _run_until_done(p2, max_steps=100)
    assert [d["subject"] for d in d1] == [d["subject"] for d in d2]


def test_real_market_signature_compatible():
    """on_step accepte le vrai Market (interface step_count)."""
    p = _player()
    m = Market(seed=42)
    m.sync_to(WARMUP_STEPS)
    assert story_arcs.on_step(p, m) == []


def test_new_arcs_use_known_inbox_categories():
    from scenes.scene_inbox import _KIND
    for arc in ARCS:
        for st in arc["stages"]:
            assert st["category"] in _KIND, (arc["id"], st["category"])


def test_six_arcs_present_with_unique_ids():
    ids = {a["id"] for a in ARCS}
    assert {"mentor", "journalist", "client_worried", "rival_truce",
            "regulator", "whale_client"} <= ids
