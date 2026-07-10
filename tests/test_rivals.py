"""Tests des rivaux actifs (core/rivals.py)."""
import random

import pytest

from core import career, ma, market, rivals
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
        p.rep_log = []
        rep0 = p.reputation
        evs = rivals.act(p, m, rng)
        if any(e["type"] == "snipe" for e in evs):
            assert p.deals == []                 # deal raflé -> retiré
            assert p.reputation == rep0 - 2      # pénalité de réputation
            # la pénalité doit être journalisée avec une raison explicite
            assert len(p.rep_log) == 1
            reason, delta = p.rep_log[0]
            assert delta == -2
            assert "Deal tardif" in reason
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


def test_act_surge_more_frequent_in_volatil_than_calme():
    p1, m1 = _mk()
    m1.regime = "Volatil"
    rng1 = random.Random(42)
    count_volatil = 0
    for _ in range(1000):
        evs = rivals.act(p1, m1, rng1)
        if any(e["type"] == "surge" for e in evs):
            count_volatil += 1

    p2, m2 = _mk()
    m2.regime = "Calme"
    rng2 = random.Random(42)
    count_calme = 0
    for _ in range(1000):
        evs = rivals.act(p2, m2, rng2)
        if any(e["type"] == "surge" for e in evs):
            count_calme += 1

    assert count_volatil > count_calme


def test_act_snipe_more_frequent_in_recession_than_expansion():
    p1, m1 = _mk()
    m1.regime = "Récession"
    rng1 = random.Random(7)
    count_recession = 0
    for _ in range(1000):
        p1.deals = [{"id": 1, "title": "Deal tardif", "kind": "M&A",
                     "reward_cash": 100_000, "days_left": 5}]
        evs = rivals.act(p1, m1, rng1)
        if any(e["type"] == "snipe" for e in evs):
            count_recession += 1

    p2, m2 = _mk()
    m2.regime = "Expansion"
    rng2 = random.Random(7)
    count_expansion = 0
    for _ in range(1000):
        p2.deals = [{"id": 1, "title": "Deal tardif", "kind": "M&A",
                     "reward_cash": 100_000, "days_left": 5}]
        evs = rivals.act(p2, m2, rng2)
        if any(e["type"] == "snipe" for e in evs):
            count_expansion += 1

    assert count_recession > count_expansion


def test_act_handles_depeg_check_without_error():
    # Vérifie que act() interroge crypto.active_depegs(market) sans planter,
    # avec un market réel construit comme dans les autres tests.
    p, m = _mk()
    rng = random.Random(11)
    for _ in range(20):
        p.mandate_offers = [{"id": 7, "client": "Caisse XYZ", "capital": 1_000_000}]
        evs = rivals.act(p, m, rng)
        assert isinstance(evs, list)


def test_act_claim_target_removes_a_target_and_records_owner():
    p, m = _mk()
    rng = random.Random(5)
    fired = False
    for _ in range(500):
        evs = rivals.act(p, m, rng)
        claims = [e for e in evs if e["type"] == "claim_target"]
        if claims:
            ev = claims[0]
            assert ev["ticker"] in p.rival_owned_targets
            assert ev["target"]
            assert ev["rival"]
            assert ev.get("text")
            fired = True
            break
    assert fired


def test_act_claim_target_excludes_already_claimed_and_owned_targets():
    p, m = _mk()
    rng = random.Random(9)
    seen_tickers = set()
    for _ in range(300):
        evs = rivals.act(p, m, rng)
        for e in evs:
            if e["type"] == "claim_target":
                assert e["ticker"] not in seen_tickers  # jamais réclamée deux fois
                seen_tickers.add(e["ticker"])
    # toutes les cibles réclamées doivent être enregistrées comme prises par un rival
    for ticker in seen_tickers:
        assert ticker in p.rival_owned_targets


def test_act_claim_target_deterministic_with_seeded_rng():
    p1, m1 = _mk()
    p2, m2 = _mk()
    rng1 = random.Random(123)
    rng2 = random.Random(123)
    claims1 = []
    claims2 = []
    for _ in range(50):
        evs1 = rivals.act(p1, m1, rng1)
        claims1.extend(e["ticker"] for e in evs1 if e["type"] == "claim_target")
    for _ in range(50):
        evs2 = rivals.act(p2, m2, rng2)
        claims2.extend(e["ticker"] for e in evs2 if e["type"] == "claim_target")
    assert claims1 == claims2
    assert p1.rival_owned_targets == p2.rival_owned_targets


def test_rival_events_populated_and_capped():
    p, m = _mk()
    rng = random.Random(13)
    for _ in range(400):
        rivals.act(p, m, rng)
    assert len(p.rival_events) <= rivals.RIVAL_EVENTS_MAX
    assert p.rival_events  # au moins une action a dû se produire en 400 tours
    for entry in p.rival_events:
        assert "text" in entry and "type" in entry


def test_contestable_targets_empty_by_default():
    p, _ = _mk()
    assert rivals.contestable_targets(p) == []


def test_contestable_targets_lists_rival_owned_tickers():
    p, m = _mk()
    target = ma.all_targets()[0]
    p.rival_owned_targets = [target["ticker"]]
    out = rivals.contestable_targets(p)
    assert [t["ticker"] for t in out] == [target["ticker"]]


def test_contest_target_not_claimed_is_rejected():
    p, _ = _mk()
    res = rivals.contest_target(p, "ZZZNOPE")
    assert res == {"ok": False, "reason": "not_claimed"}


def test_contest_target_insufficient_cash_is_rejected():
    p, m = _mk()
    target = ma.all_targets()[0]
    p.rival_owned_targets = [target["ticker"]]
    p.cash = 0.0
    res = rivals.contest_target(p, target["ticker"], rng=random.Random(0))
    assert res["ok"] is False
    assert res["reason"] == "cash"
    assert res["cost"] > 0
    assert p.rival_owned_targets == [target["ticker"]]  # inchangé


def test_contest_target_success_removes_target_and_weakens_rival():
    p, m = _mk()
    target = ma.all_targets()[0]
    p.rival_owned_targets = [target["ticker"]]
    p.cash = 10_000_000.0
    res = None
    for seed in range(100):
        p.rival_owned_targets = [target["ticker"]]
        p.cash = 10_000_000.0
        rivals.ensure(p)
        scores_before = {r["name"]: r["score"] for r in p.rivals}
        res = rivals.contest_target(p, target["ticker"], rng=random.Random(seed))
        if res["ok"] and res["success"]:
            assert target["ticker"] not in p.rival_owned_targets
            rival = next(r for r in p.rivals if r["name"] == res["rival"])
            assert rival["score"] <= scores_before[res["rival"]]
            break
    assert res is not None and res["ok"] and res["success"]


def test_contest_target_failure_costs_cash_without_reclaiming():
    p, m = _mk()
    target = ma.all_targets()[0]
    res = None
    for seed in range(100):
        p.rival_owned_targets = [target["ticker"]]
        p.cash = 10_000_000.0
        cash_before = p.cash
        res = rivals.contest_target(p, target["ticker"], rng=random.Random(seed))
        if res["ok"] and not res["success"]:
            assert target["ticker"] in p.rival_owned_targets
            assert p.cash == pytest.approx(cash_before - res["cost"])
            break
    assert res is not None and res["ok"] and not res["success"]


def test_recent_activity_respects_limit():
    p, _ = _mk()
    name = p.rivals[0]["name"]
    for i in range(10):
        career.log(p, "info", f"{name} agit ({i}).")
    out = rivals.recent_activity(p, limit=3)
    assert len(out) == 3
    assert out[0]["text"] == f"{name} agit (9)."

