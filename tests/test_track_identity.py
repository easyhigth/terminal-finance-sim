"""Tests des nouveaux outils EXCLUSIFS par voie (identité de carrière) :
core/precedent_transactions.py, core/football_field.py, core/pitch_book.py,
core/strategic_allocation.py, et leur verrouillage via
core/unlocks.TRACK_AFFINITY."""
import random

import pytest

from core import football_field as FF
from core import mandates as M
from core import pitch_book as PB
from core import precedent_transactions as PT
from core import strategic_allocation as SA
from core import unlocks
from core.game_state import PlayerState
from data.ma_targets import all_targets


def _player(grade=9, track="General"):
    p = PlayerState()
    p.grade_index = grade
    p.track = track
    return p


# --------------------------------------------------------- precedent_transactions
def test_precedent_deals_are_deterministic():
    a = PT.deals_for_sector("Tech")
    b = PT.deals_for_sector("Tech")
    assert a == b


def test_precedent_multiple_range_is_ordered():
    r = PT.multiple_range("Industrie")
    assert r["lo"] <= r["median"] <= r["hi"]
    assert len(r["deals"]) == PT.DEALS_PER_SECTOR


def test_precedent_ev_scales_with_ebitda():
    r1 = PT.precedent_ev(100.0, "Tech")
    r2 = PT.precedent_ev(200.0, "Tech")
    assert r2["median"] == pytest.approx(r1["median"] * 2, rel=1e-6)


def test_unknown_sector_falls_back_to_default_range():
    r = PT.multiple_range("SecteurInconnu")
    assert r["lo"] > 0


# --------------------------------------------------------------- football_field
def test_football_field_methods_are_ordered_ranges():
    t = all_targets()[0]
    f = FF.build(t)
    assert f["methods"]
    for m in f["methods"]:
        assert m["equity_lo"] <= m["equity_median"] <= m["equity_hi"]


def test_football_field_includes_public_comps_when_market_given():
    import main
    a = main.App()
    a.ensure_market()
    t = all_targets()[0]
    f = FF.build(t, a.market)
    labels = {m["label"] for m in f["methods"]}
    assert any("public" in l.lower() for l in labels)


def test_football_field_ask_matches_ma_ask_price():
    from core import ma
    t = all_targets()[1]
    f = FF.build(t)
    assert f["ask_ev"] == pytest.approx(ma.ask_price(t))


# ------------------------------------------------------------------- pitch_book
def test_fit_score_bounded_0_1():
    p = _player(track="Advisory")
    for prof in M.CLIENT_PROFILES:
        s = PB.fit_score(p, prof["key"])
        assert 0.0 <= s <= 1.0


def test_higher_ambition_lowers_win_probability():
    p = _player(track="Advisory", grade=8)
    key = M.CLIENT_PROFILES[0]["key"]
    low = PB.win_probability(p, key, 0.6)
    high = PB.win_probability(p, key, 1.4)
    assert high < low


def test_pitch_below_grade_is_still_computable_but_offer_capped_by_caller():
    """pitch_book lui-même ne vérifie pas le grade (c'est le rôle de
    core/unlocks.py / l'app) — mais un pitch gagné doit produire une offre
    valide quel que soit le grade d'entrée testé ici."""
    p = _player(grade=6, track="Advisory")
    rng = random.Random(1)
    key = M.CLIENT_PROFILES[0]["key"]
    result = PB.pitch(p, key, 1.0, rng)
    assert result["ok"]


def test_pitch_win_creates_a_real_mandate_offer():
    p = _player(grade=9, track="Advisory")
    p.reputation = 90
    rng = random.Random(7)
    key = M.CLIENT_PROFILES[0]["key"]
    # force un tirage gagnant : cherche une seed qui gagne
    won = False
    for seed in range(50):
        p2 = _player(grade=9, track="Advisory")
        p2.reputation = 90
        r = PB.pitch(p2, key, 0.6, random.Random(seed))
        if r.get("won"):
            assert len(p2.mandate_offers) == 1
            won = True
            break
    assert won


def test_pitch_loss_sets_cooldown_and_penalizes_reputation():
    p = _player(grade=9, track="Advisory")
    p.reputation = 50
    key = M.CLIENT_PROFILES[0]["key"]
    lost = False
    for seed in range(50):
        p2 = _player(grade=9, track="Advisory")
        p2.reputation = 50
        r = PB.pitch(p2, key, 1.5, random.Random(seed))
        if r.get("ok") and not r.get("won"):
            allowed, until = PB.can_pitch(p2, key)
            assert not allowed
            assert p2.reputation < 50
            lost = True
            break
    assert lost


def test_can_pitch_respects_cooldown_then_reopens():
    p = _player(grade=9, track="Advisory")
    key = M.CLIENT_PROFILES[0]["key"]
    p.flags["pitch_cooldowns"] = {key: p.quarter + 1}
    allowed, _until = PB.can_pitch(p, key)
    assert not allowed
    p.quarter += 1
    allowed, _until = PB.can_pitch(p, key)
    assert allowed


def test_pitch_unknown_profile_rejected():
    p = _player()
    r = PB.pitch(p, "does-not-exist")
    assert not r["ok"]


# ------------------------------------------------------------ strategic_allocation
def test_current_allocation_sums_to_total():
    import main
    a = main.App()
    a.ensure_market()
    p = _player()
    p.cash = 100_000.0
    alloc = SA.current_allocation(p, a.market)
    assert alloc["total"] == pytest.approx(100_000.0)
    assert alloc["pct"]["cash"] == pytest.approx(1.0)


def test_profiles_targets_sum_to_one():
    for prof in SA.PROFILES.values():
        assert sum(prof["targets"].values()) == pytest.approx(1.0, abs=1e-6)


def test_drift_flags_buckets_outside_band():
    alloc = {"pct": {"cash": 0.5, "equity": 0.5, "bonds": 0.0, "commodities": 0.0, "crypto": 0.0}}
    targets = SA.PROFILES["equilibre"]["targets"]
    d = SA.drift(alloc, targets)
    oob = SA.out_of_band(alloc, targets)
    assert set(oob) == {b for b, dv in d.items() if abs(dv) > SA.DRIFT_BAND}
    assert "bonds" in oob


def test_rebalance_plan_scales_existing_equity_toward_target():
    import main
    from core import portfolio as PF
    a = main.App()
    a.ensure_market()
    p = _player()
    p.cash = 200_000.0
    top = a.market.top_companies(n=2)
    for c in top:
        PF.buy(p, a.market, c["ticker"], 100)
    targets = {"cash": 0.9, "equity": 0.1, "bonds": 0.0, "commodities": 0.0, "crypto": 0.0}
    plan = SA.rebalance_plan(p, a.market, targets)
    assert plan["trades"]
    assert all(t["delta_qty"] < 0 for t in plan["trades"])  # doit VENDRE pour réduire equity


def test_apply_plan_executes_sells_before_buys():
    import main
    from core import portfolio as PF
    a = main.App()
    a.ensure_market()
    p = _player()
    p.cash = 500_000.0
    top = a.market.top_companies(n=2)
    for c in top:
        PF.buy(p, a.market, c["ticker"], 200)
    targets = {"cash": 0.9, "equity": 0.1, "bonds": 0.0, "commodities": 0.0, "crypto": 0.0}
    plan = SA.rebalance_plan(p, a.market, targets)
    results = SA.apply_plan(p, a.market, plan)
    assert results
    assert all(r.get("ok") for r in results)
    alloc_after = SA.current_allocation(p, a.market)
    assert alloc_after["pct"]["equity"] < 0.5


def test_rebalance_plan_with_no_wealth_returns_empty():
    import main
    a = main.App()
    a.ensure_market()
    p = _player()
    p.cash = 0.0
    plan = SA.rebalance_plan(p, a.market, SA.PROFILES["equilibre"]["targets"])
    assert plan["trades"] == []
    assert plan["notes"]


# ------------------------------------------------------------------- TRACK_AFFINITY
@pytest.mark.parametrize("feature,affinity", [
    ("valuation", "M&A"), ("creditdesk", "M&A"),
    ("attribution", "Portfolio"), ("backtester", "Portfolio"), ("pnlexplain", "Portfolio"),
    ("footballfield", "M&A"), ("pitchbook", "Advisory"), ("strategicalloc", "Portfolio"),
])
def test_new_feature_keys_are_locked_by_track_affinity(feature, affinity):
    assert unlocks.TRACK_AFFINITY[feature] == affinity
    other_track = "Risk" if affinity != "Risk" else "Quant"
    p = _player(grade=unlocks.required_grade(feature), track=other_track)
    assert not unlocks.unlocked(p, feature)
    p2 = _player(grade=unlocks.required_grade(feature), track=affinity)
    assert unlocks.unlocked(p2, feature)
    p3 = _player(grade=unlocks.required_grade(feature), track="General")
    assert unlocks.unlocked(p3, feature)


def test_every_new_feature_key_has_a_brief():
    from core import unlock_briefs
    for feature in ("valuation", "creditdesk", "attribution", "backtester", "pnlexplain",
                    "footballfield", "pitchbook", "strategicalloc"):
        assert feature in unlock_briefs.FEATURE_BRIEFS, feature
