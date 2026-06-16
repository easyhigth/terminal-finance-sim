"""Tests du système de gouvernements, obligations étendues et événements politiques."""
import random

import pytest

from core.market import Market
from core.game_state import PlayerState
from core import governments as G
from core import bonds as B
from core import politics
from core import portfolio as pf
from data import companies as comp_data


_VALID_RATINGS = set(B._RATING_SPREAD.keys())
_REGIONS = set(comp_data.REGIONS)


def _setup():
    m = Market(seed=2024)
    p = PlayerState()
    p.cash = 5_000_000.0
    return p, m


# --------------------------------------------------------------- gouvernements
def test_government_data_integrity():
    codes = [g["code"] for g in G.GOVERNMENTS]
    assert len(codes) == len(set(codes))           # codes uniques
    assert "KR" in codes                           # Corée du Sud ajoutée
    for g in G.GOVERNMENTS:
        assert g["region"] in _REGIONS
        assert g["rating"] in _VALID_RATINGS
        assert 0.0 <= g["stability"] <= 1.0
        assert g["debt_gdp"] > 0
        assert len(g["history"]) >= 3              # historique crédible
        for h in g["history"]:
            assert h["kind"] in ("good", "bad", "info")
            assert h["fr"] and h["en"]


def test_every_region_has_a_government():
    covered = {g["region"] for g in G.GOVERNMENTS}
    assert covered == _REGIONS


def test_country_premium_rises_with_instability():
    stable = {"stability": 0.9, "debt_gdp": 50}
    fragile = {"stability": 0.4, "debt_gdp": 130}
    assert G.country_premium(fragile) > G.country_premium(stable)
    assert G.country_premium(None) == 0.0


# --------------------------------------------------------------- obligations
def test_universe_has_sovereign_and_corporate():
    _, m = _setup()
    sov = B.sovereign_quotes(m)
    corp = B.corporate_quotes(m)
    assert len(sov) >= 15        # au moins un souverain par pays + benchmarks
    assert len(corp) >= 10       # corporates curatés + sociétés du roster


def test_all_bonds_have_valid_fields():
    _, m = _setup()
    for q in B.all_quotes(m):
        assert q["rating"] in _VALID_RATINGS
        assert q["region"] in _REGIONS
        assert q["kind"] in ("Souverain", "Corporate")
        assert q["price"] > 0
        assert 0 < q["ytm"] < 0.20
        assert q["mod_duration"] > 0
        assert q["convexity"] > 0


def test_corporate_bonds_linked_to_real_companies():
    _, m = _setup()
    for q in B.corporate_quotes(m):
        if q["ticker"]:
            assert q["ticker"] in comp_data.COMPANY_BY_TICKER
            # la région de l'obligation correspond à celle de la société émettrice
            assert q["region"] == comp_data.COMPANY_BY_TICKER[q["ticker"]]["region"]


def test_each_government_issues_at_least_one_bond():
    _, m = _setup()
    sov = B.sovereign_quotes(m)
    for g in G.GOVERNMENTS:
        ids = [q for q in sov if q["gov"] == g["code"]]
        assert ids, f"{g['code']} n'a aucune obligation"


def test_legacy_benchmark_bonds_preserved():
    _, m = _setup()
    for bid in ("UST10", "UST2", "BUND10", "OAT10", "JGB10", "EM10",
                "CORP_IG", "CORP_HY"):
        assert B.quote(m, bid) is not None


def test_fragile_sovereign_yields_more_than_stable_same_curve():
    _, m = _setup()
    # Argentine (B, instable) vs Allemagne (AAA, stable) au même niveau de courbe
    ar = B.quote(m, "AR10Y")["ytm"]
    de = B.quote(m, "BUND10")["ytm"]
    assert ar > de


# --------------------------------------- réaction des spreads à la politique
def test_region_credit_bump_lowers_regional_bond_prices():
    _, m = _setup()
    p_before = B.quote(m, "IT10Y")["price"]      # souverain européen
    corp_before = B.quote(m, "CB_LWNH")["price"]  # corporate européen
    other_before = B.quote(m, "UST10")["price"]   # souverain US (autre région)
    m.bump_region_credit("Europe", 0.01)          # +100 bps sur l'Europe
    assert B.quote(m, "IT10Y")["price"] < p_before
    assert B.quote(m, "CB_LWNH")["price"] < corp_before
    # une autre région n'est pas affectée
    assert B.quote(m, "UST10")["price"] == pytest.approx(other_before)


def test_region_credit_bump_decays_over_steps():
    _, m = _setup()
    m.bump_region_credit("Europe", 0.01)
    assert m.region_credit_bump["Europe"] > 0
    m.fast_forward(15)
    assert m.region_credit_bump["Europe"] == pytest.approx(0.0, abs=1e-4)


def test_bump_does_not_affect_equity_determinism():
    # le bump de crédit ne tire aucun aléa : le chemin de prix actions reste
    # identique avec ou sans bump injecté.
    a = Market(seed=555); a.fast_forward(10)
    b = Market(seed=555); b.fast_forward(10)
    b.bump_region_credit("Europe", 0.02)
    a.fast_forward(5); b.fast_forward(5)
    import numpy as np
    assert np.allclose(a.price, b.price)


# --------------------------------------------------------------- politique
def test_politics_trigger_is_region_consistent():
    p, m = _setup()
    rng = random.Random(1)
    fired = []
    for _ in range(400):
        ev = politics.maybe_trigger(p, m, rng)
        if ev:
            fired.append(ev)
    assert fired, "aucun événement politique déclenché sur 400 tours"
    for ev in fired:
        assert ev["region"] in _REGIONS
        assert ev["kind"] in ("good", "bad", "info")
        assert ev["country"] and ev["story"]
        assert G.get(ev["gov"]) is not None


def test_politics_applies_crisis_and_credit_bump():
    p, m = _setup()
    rng = random.Random(0)
    ev = None
    while ev is None:
        ev = politics.maybe_trigger(p, m, rng)
    # un événement a été injecté : crise active + bump de crédit sur la région
    assert len(m.crises) >= 1
    assert abs(m.region_credit_bump[ev["region"]]) > 0.0


def test_politics_deterministic_with_seeded_rng():
    p1, m1 = _setup(); p2, m2 = _setup()
    r1, r2 = random.Random(123), random.Random(123)
    out1 = [politics.maybe_trigger(p1, m1, r1) for _ in range(50)]
    out2 = [politics.maybe_trigger(p2, m2, r2) for _ in range(50)]
    ids1 = [e["id"] if e else None for e in out1]
    ids2 = [e["id"] if e else None for e in out2]
    assert ids1 == ids2


# --------------------------------------------------------------- intégration
def test_net_worth_includes_new_bonds():
    p, m = _setup()
    nw0 = pf.net_worth(p, m)
    B.buy_bond(p, m, "KR10Y", 50)        # souverain Corée du Sud
    nw1 = pf.net_worth(p, m)
    assert nw1 == pytest.approx(nw0, rel=3e-3)
    assert "KR10Y" in p.bonds
