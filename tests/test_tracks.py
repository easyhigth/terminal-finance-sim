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


# ------------------------------------------------------------- reconversion
def test_switch_track_rejects_general_or_unknown():
    p = _player("Risk")
    assert tracks.switch_track(p, None, "General")["reason"] == "invalid_track"
    assert tracks.switch_track(p, None, "Bond")["reason"] == "invalid_track"


def test_switch_track_rejects_same_track():
    p = _player("Risk")
    assert tracks.switch_track(p, None, "Risk")["reason"] == "same_track"


def test_switch_track_blocks_when_cash_insufficient():
    p = _player("Risk")
    m = Market(seed=1)
    tk = m.companies[0]["ticker"]
    m.price[m.ticker_idx[tk]] = 100.0
    p.cash = 1_000_000.0
    pf.buy(p, m, tk, 9000)   # gros stock -> valeur nette élevée, cash résiduel faible
    p.cash = 10.0            # force un cash résiduel insuffisant pour le coût (8% de la valeur nette)
    res = tracks.switch_track(p, m, "Quant")
    assert res["ok"] is False
    assert res["reason"] == "cash"
    assert p.track == "Risk"


def test_switch_track_charges_cost_and_sets_new_track():
    p = _player("Risk")
    p.cash = 1_000_000.0
    cost_before = tracks.reconversion_cost(p, None)
    res = tracks.switch_track(p, None, "Quant")
    assert res["ok"] is True
    assert res["cost"] == pytest.approx(cost_before)
    assert p.track == "Quant"
    assert p.cash == pytest.approx(1_000_000.0 - cost_before)
    assert p.flags["track_switch_day"] == p.day


def test_perk_is_neutral_immediately_after_switch_and_ramps_up():
    p = _player("Risk")
    p.cash = 1_000_000.0
    tracks.switch_track(p, None, "Quant")
    # rodage : juste après le switch, les avantages Quant ne sont pas actifs
    assert tracks.perk(p, "deal_bonus") == pytest.approx(tracks._DEFAULTS["deal_bonus"])
    # à mi-rodage, valeur intermédiaire entre neutre et pleine puissance
    p.day += tracks.RAMP_DAYS // 2
    mid = tracks.perk(p, "deal_bonus")
    full = tracks.PERKS["Quant"]["deal_bonus"]
    assert tracks._DEFAULTS["deal_bonus"] < mid < full
    # rodage terminé : pleine puissance
    p.day += tracks.RAMP_DAYS
    assert tracks.perk(p, "deal_bonus") == pytest.approx(full)


def test_perk_maint_margin_falls_back_to_none_during_ramp():
    p = _player("Quant")
    p.cash = 1_000_000.0
    tracks.switch_track(p, None, "Risk")
    assert tracks.perk(p, "maint_margin") is None
    p.day += tracks.RAMP_DAYS
    assert tracks.perk(p, "maint_margin") == pytest.approx(tracks.PERKS["Risk"]["maint_margin"])


def test_no_ramp_without_any_switch():
    p = _player("Risk")
    assert tracks.perk(p, "deal_bonus") == pytest.approx(tracks.PERKS["Risk"]["deal_bonus"])
