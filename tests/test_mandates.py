"""Tests des mandats clients (core/mandates.py)."""
import random

import pytest

from core import mandates, market
from core.game_state import PlayerState


def _mk(grade_index=6):
    m = market.Market(seed=42)
    m.sync_to(market.WARMUP_STEPS)
    p = PlayerState(continent="Europe", grade_index=grade_index)
    return p, m


def test_maybe_offer_none_below_min_grade():
    p, _ = _mk(grade_index=mandates.MIN_GRADE - 1)
    rng = random.Random(0)
    assert mandates.maybe_offer(p, rng) is None


def test_maybe_offer_creates_offer_with_expected_fields():
    p, _ = _mk()
    rng = random.Random(1)
    offer = None
    for _ in range(50):
        offer = mandates.maybe_offer(p, rng)
        if offer:
            break
    assert offer is not None
    for key in ("id", "client", "capital", "target_pct", "horizon", "max_beta",
                "reward_cash", "reward_rep", "penalty_rep"):
        assert key in offer
    assert offer in p.mandate_offers


def test_cfa_certification_boosts_mandate_reward_cash():
    p_plain, _ = _mk()
    p_cfa, _ = _mk()
    p_cfa.certs["CFA"] = 3  # niveau max (cf. certifications.PROGRAMS["CFA"]["levels"])
    rng_plain, rng_cfa = random.Random(1), random.Random(1)
    offer_plain = offer_cfa = None
    for _ in range(50):
        offer_plain = offer_plain or mandates.maybe_offer(p_plain, rng_plain)
        offer_cfa = offer_cfa or mandates.maybe_offer(p_cfa, rng_cfa)
        if offer_plain and offer_cfa:
            break
    assert offer_plain is not None and offer_cfa is not None
    assert offer_cfa["reward_cash"] == pytest.approx(offer_plain["reward_cash"] * mandates.CFA_REWARD_BONUS)


def test_accept_moves_offer_to_active_with_snapshot():
    p, m = _mk()
    p.mandate_offers = [{"id": 1, "client": "Test Client", "capital": 500_000,
                         "target_pct": 5.0, "horizon": 2, "max_beta": 1.2,
                         "reward_cash": 1000.0, "reward_rep": 8, "penalty_rep": 5}]
    accepted = mandates.accept(p, 1, m)
    assert accepted is not None
    assert accepted["id"] == 1
    assert "start_nw" in accepted and "deadline_q" in accepted
    assert p.mandate_offers == []
    assert p.mandates == [accepted]


def test_accept_returns_full_when_max_active_reached():
    p, m = _mk()
    p.mandates = [{"id": 99}] * mandates.MAX_ACTIVE
    p.mandate_offers = [{"id": 1, "client": "X", "capital": 100_000, "target_pct": 1.0,
                         "horizon": 1, "max_beta": 1.0, "reward_cash": 0.0,
                         "reward_rep": 0, "penalty_rep": 0}]
    assert mandates.accept(p, 1, m) == "full"


def test_accept_returns_none_for_unknown_id():
    p, m = _mk()
    assert mandates.accept(p, 404, m) is None


def test_decline_removes_offer():
    p, _ = _mk()
    p.mandate_offers = [{"id": 1, "client": "X"}]
    assert mandates.decline(p, 1) is True
    assert p.mandate_offers == []
    assert mandates.decline(p, 1) is False


def _due_mandate(player, market_, target_pct=1_000_000.0, max_beta=10.0):
    """Mandat fabriqué pour échoir immédiatement, avec une cible quasi
    inatteignable par défaut (pour des tests d'échec déterministes)."""
    from core import portfolio
    return {"id": 1, "client": "Fonds de pension Helven", "capital": 500_000,
            "target_pct": target_pct, "horizon": 1, "max_beta": max_beta,
            "reward_cash": 5_000.0, "reward_rep": 8, "penalty_rep": 5,
            "start_nw": portfolio.net_worth(player, market_),
            "deadline_q": player.quarter}


def test_failure_reason_mentions_missed_target():
    m = {"target_pct": 5.0, "max_beta": 1.5}
    reason = mandates.failure_reason(m, growth=1.0, beta=0.5)
    assert "Rendement cible non atteint" in reason
    assert "Risque dépassé" not in reason


def test_failure_reason_mentions_excess_risk():
    m = {"target_pct": -100.0, "max_beta": 1.0}
    reason = mandates.failure_reason(m, growth=50.0, beta=2.0)
    assert "Risque dépassé" in reason
    assert "Rendement cible non atteint" not in reason


def test_failure_reason_mentions_both_when_both_missed():
    m = {"target_pct": 5.0, "max_beta": 1.0}
    reason = mandates.failure_reason(m, growth=-1.0, beta=2.0)
    assert "Rendement cible non atteint" in reason
    assert "Risque dépassé" in reason


def test_evaluate_due_failure_records_history_with_reason():
    p, m = _mk()
    p.mandates = [_due_mandate(p, m)]
    rep0 = p.reputation
    results = mandates.evaluate_due(p, m)
    assert len(results) == 1
    res = results[0]
    assert res["ok"] is False
    assert "reason" in res and res["reason"]
    assert p.mandates == []
    assert p.reputation == rep0 - res["penalty_rep"]
    assert p.mandate_history == [res]


def test_evaluate_due_success_records_history_and_rewards():
    p, m = _mk()
    p.mandates = [_due_mandate(p, m, target_pct=-1_000_000.0, max_beta=1000.0)]
    cash0 = p.cash
    rep0 = p.reputation
    results = mandates.evaluate_due(p, m)
    res = results[0]
    assert res["ok"] is True
    assert p.cash == cash0 + res["reward_cash"]
    assert p.reputation == rep0 + res["reward_rep"]
    assert p.flags.get("mandates_won") == 1
    assert p.mandate_history == [res]


def test_evaluate_due_failure_logs_reputation_reason():
    """La pénalité de réputation d'un mandat échoué doit être journalisée
    dans rep_log avec le nom du client, pour expliquer au joueur la baisse."""
    p, m = _mk()
    mandate = _due_mandate(p, m)
    p.mandates = [mandate]
    p.rep_log = []
    results = mandates.evaluate_due(p, m)
    assert len(p.rep_log) == 1
    reason, delta = p.rep_log[0]
    assert delta == -results[0]["penalty_rep"]
    assert mandate["client"] in reason


def test_evaluate_due_success_logs_reputation_reason():
    p, m = _mk()
    mandate = _due_mandate(p, m, target_pct=-1_000_000.0, max_beta=1000.0)
    p.mandates = [mandate]
    p.rep_log = []
    results = mandates.evaluate_due(p, m)
    assert len(p.rep_log) == 1
    reason, delta = p.rep_log[0]
    assert delta == results[0]["reward_rep"]
    assert mandate["client"] in reason


def test_evaluate_due_keeps_mandate_not_yet_due():
    p, m = _mk()
    future = _due_mandate(p, m)
    future["deadline_q"] = p.quarter + 5
    p.mandates = [future]
    results = mandates.evaluate_due(p, m)
    assert results == []
    assert p.mandates == [future]
    assert p.mandate_history == []


def test_mandate_history_capped_at_max_history():
    p, m = _mk()
    for i in range(mandates.MAX_HISTORY + 5):
        p.mandates = [_due_mandate(p, m)]
        mandates.evaluate_due(p, m)
    assert len(p.mandate_history) == mandates.MAX_HISTORY


def test_maybe_offer_attaches_type_and_extra_constraints():
    p, _ = _mk()
    rng = random.Random(2)
    offer = None
    for _ in range(80):
        offer = mandates.maybe_offer(p, rng)
        if offer:
            break
    assert offer is not None
    assert offer["type"] in mandates.MANDATE_TYPES
    if offer["type"] == "income":
        assert "target_yield" in offer and "min_liquidity" in offer
    elif offer["type"] in ("low_vol", "absolute_return"):
        assert "max_drawdown" in offer
    elif offer["type"] == "esg":
        assert offer["excluded_sectors"] == mandates.ESG_EXCLUDED_SECTORS


def test_check_constraints_ok_when_extra_fields_absent():
    p, m = _mk()
    bare = {"target_pct": -100.0, "max_beta": 10.0}
    check = mandates.check_constraints(p, m, bare, growth=5.0, beta=1.0)
    assert check["ok"] is True
    assert check["breaches"] == []
    assert check["values"]["drawdown"] is None


def test_check_constraints_flags_drawdown_breach():
    p, m = _mk()
    mandate = {"target_pct": -100.0, "max_beta": 10.0, "max_drawdown": 5.0}
    p.cash_history = [100, 60]   # 40% drawdown > limite de 5%
    check = mandates.check_constraints(p, m, mandate, growth=5.0, beta=1.0)
    assert check["ok"] is False
    assert "drawdown" in check["breaches"]


def test_check_constraints_flags_liquidity_breach():
    p, m = _mk()
    mandate = {"target_pct": -100.0, "max_beta": 10.0, "min_liquidity": 150.0}
    check = mandates.check_constraints(p, m, mandate, growth=5.0, beta=1.0)
    assert check["ok"] is False
    assert "liquidity" in check["breaches"]


def test_failure_reason_with_extra_breach():
    mandate = {"target_pct": -100.0, "max_beta": 10.0, "max_drawdown": 5.0}
    extra = {"drawdown": 40.0}
    reason = mandates.failure_reason(mandate, growth=5.0, beta=1.0, extra=extra)
    assert "Drawdown excessif" in reason


def test_failure_reason_extra_none_keeps_legacy_behaviour():
    m = {"target_pct": 5.0, "max_beta": 1.5}
    reason = mandates.failure_reason(m, growth=1.0, beta=0.5)
    assert "Rendement cible non atteint" in reason


# ---------------------------------------------------------------------------
# Profils clients (item 4) : assureur, fonds de pension, family office,
# client opportuniste, institutionnel prudent.
# ---------------------------------------------------------------------------

def test_client_profiles_cover_the_five_expected_keys():
    keys = {p["key"] for p in mandates.CLIENT_PROFILES}
    assert keys == {"assureur", "pension", "family_office", "opportuniste",
                     "institutionnel_prudent"}


def test_maybe_offer_attaches_client_profile_and_consistent_name():
    p, _ = _mk()
    rng = random.Random(7)
    offer = None
    for _ in range(80):
        offer = mandates.maybe_offer(p, rng)
        if offer:
            break
    assert offer is not None
    assert offer["client_profile"] in {pr["key"] for pr in mandates.CLIENT_PROFILES}
    profile = next(pr for pr in mandates.CLIENT_PROFILES if pr["key"] == offer["client_profile"])
    assert offer["client"] in profile["names"]


def test_profile_label_and_desc_known_and_unknown_key():
    assert mandates.profile_label("assureur") == "Assureur"
    assert mandates.profile_label("inconnu") == "inconnu"
    assert mandates.profile_desc("assureur")
    assert mandates.profile_desc("inconnu") == ""


def test_insurer_profile_tightens_drawdown_vs_opportunist():
    """Pour le même type de mandat (low_vol), l'assureur doit générer une
    contrainte de drawdown strictement plus serrée que le client opportuniste
    (item 4 : la rigueur des contraintes dépend du profil CLIENT, pas
    seulement du type de mandat)."""
    rng_a = random.Random(123)
    rng_o = random.Random(123)
    assureur = next(p for p in mandates.CLIENT_PROFILES if p["key"] == "assureur")
    opportuniste = next(p for p in mandates.CLIENT_PROFILES if p["key"] == "opportuniste")
    c_a = mandates._extra_constraints("low_vol", rng_a, assureur)
    c_o = mandates._extra_constraints("low_vol", rng_o, opportuniste)
    assert c_a["max_drawdown"] < c_o["max_drawdown"]


def test_insurer_and_pension_profiles_generate_duration_target():
    rng = random.Random(5)
    assureur = next(p for p in mandates.CLIENT_PROFILES if p["key"] == "assureur")
    offer = mandates._extra_constraints("growth", rng, assureur)
    assert "max_duration" in offer
    lo, hi = assureur["duration_target"]
    assert lo <= offer["max_duration"] <= hi


def test_pick_type_for_profile_only_returns_known_types():
    rng = random.Random(3)
    for profile in mandates.CLIENT_PROFILES:
        for _ in range(20):
            t = mandates._pick_type_for_profile(profile, rng)
            assert t in mandates.MANDATE_TYPES


def test_evaluate_due_early_terminates_strict_profile_on_breach():
    """Un mandat d'assureur (profil 'strict') doit être résilié avant
    échéance dès qu'une contrainte casse, sans attendre le trimestre de fin
    (item 4 : enforcement actif, pas seulement à l'échéance)."""
    p, m = _mk()
    mandate = _due_mandate(p, m, target_pct=-100.0, max_beta=1000.0)
    mandate["client_profile"] = "assureur"
    mandate["max_drawdown"] = 1.0          # limite quasi nulle -> cassée immédiatement
    mandate["deadline_q"] = p.quarter + 5  # échéance lointaine : ne devrait PAS être attendue
    p.mandates = [mandate]
    p.cash_history = [100, 50]             # 50% drawdown >> 1.0% limite
    rep0 = p.reputation
    results = mandates.evaluate_due(p, m)
    assert len(results) == 1
    res = results[0]
    assert res["ok"] is False
    assert res["early_terminated"] is True
    assert p.mandates == []
    assert p.reputation == rep0 - res["penalty_rep"]


def test_evaluate_due_non_strict_profile_not_early_terminated():
    """Un mandat de client opportuniste (non strict) doit survivre jusqu'à
    l'échéance même en cas de contrainte cassée en cours de route."""
    p, m = _mk()
    mandate = _due_mandate(p, m, target_pct=-100.0, max_beta=1000.0)
    mandate["client_profile"] = "opportuniste"
    mandate["max_drawdown"] = 1.0
    mandate["deadline_q"] = p.quarter + 5
    p.mandates = [mandate]
    p.cash_history = [100, 50]
    results = mandates.evaluate_due(p, m)
    assert results == []
    assert p.mandates == [mandate]


def test_evaluate_due_legacy_mandate_without_profile_not_early_terminated():
    """Rétrocompatibilité : un mandat sans `client_profile` (save antérieure
    à cette extension) ne doit jamais être résilié par anticipation."""
    p, m = _mk()
    mandate = _due_mandate(p, m, target_pct=-100.0, max_beta=1000.0)
    mandate["max_drawdown"] = 1.0
    mandate["deadline_q"] = p.quarter + 5
    p.mandates = [mandate]
    p.cash_history = [100, 50]
    results = mandates.evaluate_due(p, m)
    assert results == []
    assert p.mandates == [mandate]
