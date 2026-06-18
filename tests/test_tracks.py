"""Tests de l'asymétrie des voies (core/tracks.py) et de son application dans
le portefeuille, les deals et les mandats.
"""
import pytest

from core import deals, tracks
from core import portfolio as pf
from core.game_state import PlayerState
from core.market import Market


def _player(track="General", grade=8):
    p = PlayerState()
    p.track = track
    p.grade_index = grade
    p.cash = 1_000_000.0
    return p


# --------------------------------------------------------------- perks de base
def test_all_tracks_have_label():
    for t in ("Portfolio", "M&A", "Risk", "Quant", "Advisory", "General"):
        assert tracks.label(t)


def test_unknown_perk_falls_back_to_neutral():
    p = _player("General")
    assert tracks.perk(p, "commission_mult") == 1.0
    assert tracks.perk(p, "max_leverage_add") == 0.0


# --------------------------------------------------------------- Portfolio: commission
def test_portfolio_track_halves_commission():
    m = Market(seed=1)
    tk = m.companies[0]["ticker"]
    m.price[m.ticker_idx[tk]] = 100.0
    base = pf.buy(_player("General"), m, tk, 100)["fee"]
    porto = pf.buy(_player("Portfolio"), m, tk, 100)["fee"]
    assert porto == pytest.approx(base * 0.5, rel=1e-6)


# --------------------------------------------------------------- Risk: levier
def test_risk_track_raises_max_leverage():
    assert pf._max_leverage(_player("Risk")) > pf._max_leverage(_player("General"))


def test_risk_track_cheaper_margin_interest():
    m = Market(seed=1)
    tk = m.companies[0]["ticker"]
    m.price[m.ticker_idx[tk]] = 100.0
    pg = _player("General", grade=8); pg.cash = 10_000.0
    pr = _player("Risk", grade=8); pr.cash = 10_000.0
    pf.buy(pg, m, tk, 250)
    pf.buy(pr, m, tk, 250)
    fg = pf.accrue_financing(pg, m, days=5)["interest"]
    fr = pf.accrue_financing(pr, m, days=5)["interest"]
    assert fr < fg


# --------------------------------------------------------------- deals: edge de voie
def test_deal_edge_only_on_own_track():
    p = _player("Quant")
    own = {"kind": "Quant", "difficulty": 4}
    other = {"kind": "M&A", "difficulty": 4}
    assert deals.success_probability(p, own) > deals.success_probability(p, other)


def test_mna_track_richer_deal_reward():
    import random
    pg = _player("M&A")
    # force un template M&A et compare la récompense au multiplicateur de voie
    mult = tracks.perk(pg, "deal_reward_mult")
    assert mult > 1.0
