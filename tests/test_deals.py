"""Tests du cycle de vie des deals (core/deals.py)."""
import random

from core import deals
from core.game_state import PlayerState


def _player(track="General", grade=8, rep=50):
    p = PlayerState()
    p.track = track
    p.grade_index = grade
    p.reputation = rep
    p.cash = 1_000_000.0
    return p


def _force_deal(player, kind="General"):
    tmpl = next(t for t in deals.DEAL_TEMPLATES if t["kind"] == kind)
    deal = {
        "id": player.next_deal_id,
        "title": tmpl["title"],
        "kind": tmpl["kind"],
        "desc": tmpl["desc"],
        "reward_cash": 10_000.0,
        "reward_rep": 5,
        "penalty_cash": 500.0,
        "penalty_rep": 2,
        "difficulty": tmpl["difficulty"],
        "days_left": tmpl["days"],
    }
    player.next_deal_id += 1
    player.deals.append(deal)
    return deal


def test_maybe_generate_stops_at_max_active_deals():
    p = _player()
    for _ in range(deals.MAX_ACTIVE_DEALS):
        _force_deal(p)
    out = deals.maybe_generate(p, rng=random.Random(0))
    assert out == []
    assert len(p.deals) == deals.MAX_ACTIVE_DEALS


def test_age_deals_expires_and_penalizes():
    p = _player()
    deal = _force_deal(p)
    deal["days_left"] = 1
    cash_before, rep_before = p.cash, p.reputation
    expired = deals.age_deals(p)
    assert expired == [deal]
    assert p.deals == []
    assert p.cash == cash_before - deal["penalty_cash"]
    assert p.reputation == rep_before - deal["penalty_rep"]


def test_age_deals_logs_reputation_penalty_reason():
    """La pénalité de réputation d'un deal expiré doit être journalisée dans
    rep_log avec le titre du deal, pour que le joueur comprenne pourquoi sa
    réputation a baissé (cf. bilan du tour dans le terminal)."""
    p = _player()
    deal = _force_deal(p)
    deal["days_left"] = 1
    p.rep_log = []
    deals.age_deals(p)
    assert len(p.rep_log) == 1
    reason, delta = p.rep_log[0]
    assert delta == -deal["penalty_rep"]
    assert deal["title"] in reason


def test_age_deals_keeps_active_deal():
    p = _player()
    deal = _force_deal(p)
    deal["days_left"] = 30
    expired = deals.age_deals(p)
    assert expired == []
    assert p.deals == [deal]


def test_find_deal_by_id():
    p = _player()
    deal = _force_deal(p)
    assert deals.find_deal(p, deal["id"]) is deal
    assert deals.find_deal(p, deal["id"] + 999) is None


def test_success_probability_bounded_and_monotonic_in_reputation():
    low_rep, high_rep = _player(rep=0), _player(rep=100)
    deal = _force_deal(low_rep)
    deals.find_deal(high_rep, deal["id"])  # no-op, just ensure isolation
    high_rep.deals.append(deal)
    p_low = deals.success_probability(low_rep, deal)
    p_high = deals.success_probability(high_rep, deal)
    assert 0.10 <= p_low <= 0.95
    assert 0.10 <= p_high <= 0.95
    assert p_high >= p_low


def test_apply_outcome_good_rewards_player_and_removes_deal():
    p = _player()
    deal = _force_deal(p)
    cash_before, rep_before = p.cash, p.reputation
    res = deals.apply_outcome(p, deal["id"], "good")
    assert res["ok"] and res["outcome"] == "success"
    assert p.cash == cash_before + deal["reward_cash"]
    assert p.reputation == rep_before + deal["reward_rep"]
    assert p.deals_won == 1
    assert deals.find_deal(p, deal["id"]) is None


def test_apply_outcome_bad_penalizes_player():
    p = _player()
    deal = _force_deal(p)
    cash_before, rep_before = p.cash, p.reputation
    res = deals.apply_outcome(p, deal["id"], "bad")
    assert res["ok"] and res["outcome"] == "fail"
    assert p.cash == cash_before - deal["penalty_cash"]
    assert p.reputation == rep_before - deal["penalty_rep"]
    assert deals.find_deal(p, deal["id"]) is None


def test_apply_outcome_unknown_deal_returns_not_ok():
    p = _player()
    assert deals.apply_outcome(p, 9999, "good") == {"ok": False}


def test_resolve_deal_unknown_returns_not_ok():
    p = _player()
    res = deals.resolve_deal(p, 9999, rng=random.Random(0))
    assert res == {"ok": False, "success": False, "deal": None, "prob": 0.0}


def test_resolve_deal_removes_deal_on_resolution():
    p = _player()
    deal = _force_deal(p)
    deals.resolve_deal(p, deal["id"], rng=random.Random(0))
    assert deals.find_deal(p, deal["id"]) is None


def test_maybe_government_deal_requires_associate_grade():
    p = _player(grade=2)
    event = {"kind": "good", "country": "Testland", "region": "Europe"}
    assert deals.maybe_government_deal(p, event, rng=random.Random(0)) is None


def test_maybe_government_deal_caps_concurrent_gov_deals():
    p = _player(grade=8)
    event = {"kind": "good", "country": "Testland", "region": "Europe"}
    for _ in range(deals.MAX_GOV_DEALS):
        d = deals.maybe_government_deal(p, event, rng=random.Random(1))
        assert d is not None
    assert deals.maybe_government_deal(p, event, rng=random.Random(1)) is None
