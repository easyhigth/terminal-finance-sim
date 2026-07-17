"""Tests du focus du trimestre (core/focus.py) : perks par axe, malus
croisés légers, un changement par trimestre, effets branchés (commission,
offres, missions, réputation réseau)."""
from core import focus
from core import portfolio as pf
from core.game_state import GameState
from core.market import Market


def _player():
    gs = GameState()
    p = gs.player
    p.grade_index = 8
    p.cash = 1_000_000.0
    return gs, p


def test_no_focus_is_neutral():
    _gs, p = _player()
    assert focus.current(p) is None
    assert focus.perk(p, "commission_mult") == 1.0
    assert focus.perk(p, "offer_mult") == 1.0
    assert focus.perk(p, "rep_per_step") == 0.0


def test_trading_focus_cuts_commission_and_dims_offers():
    _gs, p = _player()
    assert focus.set_focus(p, "trading")["ok"]
    assert focus.perk(p, "commission_mult") < 1.0
    assert focus.perk(p, "offer_mult") < 1.0   # léger malus croisé


def test_one_change_per_quarter():
    _gs, p = _player()
    assert focus.set_focus(p, "clients")["ok"]
    res = focus.set_focus(p, "reseau")
    assert res["ok"] is False and res["reason"] == "quarter"
    p.quarter += 1
    assert focus.set_focus(p, "reseau")["ok"]


def test_commission_actually_drops_on_trades():
    _gs, p = _player()
    m = Market(seed=31)
    for _ in range(5):
        m.step()
    tk = m.companies[0]["ticker"]
    r_neutral = pf.buy(p, m, tk, 10)
    pf.sell(p, m, tk, 10)
    focus.set_focus(p, "trading")
    r_focus = pf.buy(p, m, tk, 10)
    assert r_focus["fee"] < r_neutral["fee"]


def test_network_focus_accrues_reputation_via_step():
    gs, p = _player()
    focus.set_focus(p, "reseau")
    m = Market(seed=31)
    for _ in range(3):
        m.step()
    network_credit = False
    for _ in range(12):   # 0.12/pas -> +1 après ~9 pas
        m.step()
        gs.advance_step(market=m)
        if any("Réseau" in reason or "Network" in reason for reason, _d in p.rep_log):
            network_credit = True
    assert network_credit
    assert "focus_rep_accum" in p.flags


def test_mission_rep_multiplier():
    from core import missions
    _gs, p = _player()
    mission = {"reward_rep": 10, "grade": 3}
    rep_neutral, _ = missions.compute_rewards(mission, 10, 10, player=p)
    focus.set_focus(p, "recherche")
    rep_focus, _ = missions.compute_rewards(mission, 10, 10, player=p)
    assert rep_focus > rep_neutral
