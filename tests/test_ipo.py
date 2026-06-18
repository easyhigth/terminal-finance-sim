"""Tests du desk d'IPO (core/ipo.py)."""
import random

from core import ipo, market
from core.game_state import PlayerState


def _mk(grade_index=4, cash=10_000_000.0):
    m = market.Market(seed=42)
    m.sync_to(market.WARMUP_STEPS)
    p = PlayerState(continent="Europe", grade_index=grade_index)
    p.cash = cash
    return p, m


def test_maybe_offer_none_below_min_grade():
    p, m = _mk(grade_index=ipo.MIN_GRADE - 1)
    rng = random.Random(0)
    assert ipo.maybe_offer(p, rng, m) is None


def test_maybe_offer_creates_offer_with_expected_fields():
    p, m = _mk()
    rng = random.Random(1)
    offer = None
    for _ in range(50):
        offer = ipo.maybe_offer(p, rng, m)
        if offer:
            break
    assert offer is not None
    for key in ("id", "company_name", "sector", "price_min", "price_max",
                "shares_offered", "demand_multiple", "listing_step", "sentiment"):
        assert key in offer
    assert offer in p.ipo_offers


def test_maybe_offer_respects_max_active_offers():
    p, m = _mk()
    rng = random.Random(2)
    # force le maximum d'offres actives déjà atteint
    p.ipo_offers = [{"id": i} for i in range(ipo.MAX_ACTIVE_OFFERS)]
    assert ipo.maybe_offer(p, rng, m) is None


def test_subscribe_full_allocation_when_demand_multiple_is_one():
    p, m = _mk()
    p.ipo_offers = [{"id": 1, "company_name": "Nova Systems", "ticker": "NOV12",
                     "sector": "Tech", "price_min": 10.0, "price_max": 12.0,
                     "shares_offered": 1_000_000, "demand_multiple": 1.0,
                     "listing_step": m.step_count + 5, "sentiment": "neutral"}]
    cash0 = p.cash
    res = ipo.subscribe(p, 1, 100_000.0, m)
    assert res["ok"] is True
    assert res["refund"] == 0.0
    assert res["allocated_cash"] == 100_000.0
    assert p.cash == cash0 - 100_000.0
    assert len(p.ipos) == 1
    assert p.ipo_offers == []
    pos = p.ipos[0]
    assert pos["cost_basis"] == 100_000.0
    assert pos["shares"] == 100_000.0 / 10.0


def test_subscribe_partial_allocation_when_oversubscribed():
    p, m = _mk()
    p.ipo_offers = [{"id": 1, "company_name": "Quanta Labs", "ticker": "QUA45",
                     "sector": "Finance", "price_min": 20.0, "price_max": 25.0,
                     "shares_offered": 500_000, "demand_multiple": 4.0,
                     "listing_step": m.step_count + 5, "sentiment": "bullish"}]
    cash0 = p.cash
    res = ipo.subscribe(p, 1, 100_000.0, m)
    assert res["ok"] is True
    assert res["allocated_cash"] == 25_000.0
    assert res["refund"] == 75_000.0
    # le cash net débité = montant alloué seulement (réservé puis remboursé)
    assert p.cash == cash0 - 25_000.0
    assert len(p.ipos) == 1
    assert p.ipos[0]["cost_basis"] == 25_000.0


def test_subscribe_fails_with_insufficient_cash():
    p, m = _mk(cash=1_000.0)
    p.ipo_offers = [{"id": 1, "company_name": "X", "ticker": "X01", "sector": "Tech",
                     "price_min": 10.0, "price_max": 12.0, "shares_offered": 1000,
                     "demand_multiple": 1.0, "listing_step": m.step_count + 5,
                     "sentiment": "neutral"}]
    res = ipo.subscribe(p, 1, 100_000.0, m)
    assert res["ok"] is False
    assert res["reason"] == "cash"
    assert p.cash == 1_000.0
    assert p.ipos == []


def test_subscribe_fails_for_unknown_offer():
    p, m = _mk()
    res = ipo.subscribe(p, 999, 1_000.0, m)
    assert res["ok"] is False
    assert res["reason"] == "offer"


def test_decline_removes_offer():
    p, m = _mk()
    p.ipo_offers = [{"id": 1, "company_name": "X"}]
    assert ipo.decline(p, 1) is True
    assert p.ipo_offers == []
    assert ipo.decline(p, 1) is False


def test_evaluate_listings_keeps_positions_not_yet_due():
    p, m = _mk()
    p.ipos = [{"offer_id": 1, "ticker": "X01", "company_name": "X", "sector": "Tech",
              "shares": 1000.0, "cost_basis": 10_000.0, "issue_price": 10.0,
              "listing_step": m.step_count + 50, "demand_multiple": 1.0,
              "sentiment": "neutral"}]
    results = ipo.evaluate_listings(p, m)
    assert results == []
    assert len(p.ipos) == 1


def test_evaluate_listings_removes_due_positions_and_settles_cash():
    p, m = _mk()
    p.ipos = [{"offer_id": 1, "ticker": "X01", "company_name": "X", "sector": "Tech",
              "shares": 1000.0, "cost_basis": 10_000.0, "issue_price": 10.0,
              "listing_step": m.step_count, "demand_multiple": 1.0,
              "sentiment": "neutral"}]
    cash0 = p.cash
    results = ipo.evaluate_listings(p, m)
    assert len(results) == 1
    assert p.ipos == []
    res = results[0]
    expected_cash = cash0 + res["proceeds"]
    assert abs(p.cash - expected_cash) < 1e-6
    assert res["pnl"] == res["proceeds"] - 10_000.0


def test_evaluate_listings_is_deterministic_for_same_seed():
    p1, m1 = _mk()
    p2, m2 = _mk()
    pos = {"offer_id": 7, "ticker": "X01", "company_name": "X", "sector": "Tech",
           "shares": 1000.0, "cost_basis": 10_000.0, "issue_price": 10.0,
           "listing_step": m1.step_count, "demand_multiple": 1.0,
           "sentiment": "bullish"}
    p1.ipos = [dict(pos)]
    p2.ipos = [dict(pos)]
    r1 = ipo.evaluate_listings(p1, m1)
    r2 = ipo.evaluate_listings(p2, m2)
    assert r1[0]["listing_price"] == r2[0]["listing_price"]


def test_evaluate_listings_can_pop_or_flop_depending_on_sentiment_bias():
    # avec un fort biais haussier répété sur de nombreuses graines d'offre,
    # on s'attend à plus de pops (pnl>=0) que sous un biais baissier.
    pops_bull = 0
    pops_bear = 0
    n = 40
    for i in range(n):
        p, m = _mk()
        p.ipos = [{"offer_id": i, "ticker": "X01", "company_name": "X", "sector": "Tech",
                  "shares": 1000.0, "cost_basis": 10_000.0, "issue_price": 10.0,
                  "listing_step": m.step_count, "demand_multiple": 1.0,
                  "sentiment": "bullish"}]
        r = ipo.evaluate_listings(p, m)
        if r[0]["pop"]:
            pops_bull += 1
    for i in range(n):
        p, m = _mk()
        p.ipos = [{"offer_id": i, "ticker": "X01", "company_name": "X", "sector": "Tech",
                  "shares": 1000.0, "cost_basis": 10_000.0, "issue_price": 10.0,
                  "listing_step": m.step_count, "demand_multiple": 1.0,
                  "sentiment": "bearish"}]
        r = ipo.evaluate_listings(p, m)
        if r[0]["pop"]:
            pops_bear += 1
    assert pops_bull >= pops_bear


def test_holdings_reports_listed_status():
    p, m = _mk()
    p.ipos = [
        {"offer_id": 1, "ticker": "A01", "company_name": "A", "sector": "Tech",
         "shares": 100.0, "cost_basis": 1000.0, "issue_price": 10.0,
         "listing_step": m.step_count - 1, "demand_multiple": 1.0, "sentiment": "neutral"},
        {"offer_id": 2, "ticker": "B01", "company_name": "B", "sector": "Tech",
         "shares": 100.0, "cost_basis": 1000.0, "issue_price": 10.0,
         "listing_step": m.step_count + 10, "demand_multiple": 1.0, "sentiment": "neutral"},
    ]
    hold = ipo.holdings(p, m)
    assert len(hold) == 2
    by_ticker = {h["ticker"]: h for h in hold}
    assert by_ticker["A01"]["listed"] is True
    assert by_ticker["B01"]["listed"] is False
    assert by_ticker["B01"]["steps_left"] == 10
