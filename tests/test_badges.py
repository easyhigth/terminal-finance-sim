"""Tests des badges liés aux mécaniques récentes (couverture, swaps, contagion crypto)
— core/badges.py."""
from core import badges, crypto, hedging, market
from core import swaps as SW
from core.game_state import PlayerState


def _mk(seed=7):
    m = market.Market(seed=seed)
    m.sync_to(market.WARMUP_STEPS)
    p = PlayerState(continent="Europe")
    p.cash = 1_000_000.0
    return p, m


def _scale_index(m, idx, factor):
    """Force le niveau de l'indice `idx` en repondérant le prix de ses constituants
    (même technique que tests/test_hedging.py)."""
    members = m.index_members[idx]
    m.price[members] *= factor


def test_hedged_badge_on_open_put_position():
    p, m = _mk()
    hedging.buy_put(p, m, 100_000.0, 1.00, 0.5)
    earned = badges.check_new(p, m)
    ids = [b["id"] for b in earned]
    assert "hedged" in ids
    assert "hedged" in p.badges


def test_hedge_in_the_money_badge():
    p, m = _mk()
    hedging.buy_put(p, m, 100_000.0, 1.00, 0.5)
    pos = p.hedges[0]
    # fait chuter l'indice sous le strike : le put est dans la monnaie
    _scale_index(m, pos["underlying"], 0.5)
    earned = badges.check_new(p, m)
    ids = [b["id"] for b in earned]
    assert "hedge_in_the_money" in ids
    assert "hedge_in_the_money" in p.badges


def test_swapper_badge_on_entering_swap():
    p, m = _mk()
    r = SW.enter_swap(p, m, "USA", "receive_foreign", 500_000.0, 2)
    assert r["ok"] is True
    earned = badges.check_new(p, m)
    ids = [b["id"] for b in earned]
    assert "swapper" in ids
    assert "swapper" in p.badges


def _find_active_depeg_state():
    """Cherche un (seed, step) où un stablecoin est décroché — la contagion étant
    déterministe (cf. core/crypto.py), un balayage borné suffit et reste reproductible."""
    for seed in range(1, 30):
        m = market.Market(seed=seed)
        m.sync_to(market.WARMUP_STEPS)
        for step in range(0, 400, 5):
            m.step_count = step
            if crypto.active_depegs(m):
                return seed, step
    raise AssertionError("aucun depeg actif trouvé dans la plage balayée")


def test_contagion_trader_badge_while_depeg_active():
    seed, step = _find_active_depeg_state()
    m = market.Market(seed=seed)
    m.sync_to(market.WARMUP_STEPS)
    m.step_count = step
    assert crypto.active_depegs(m)  # garde-fou : un depeg est bien actif

    p = PlayerState(continent="Europe")
    p.cash = 1_000_000.0
    r = crypto.buy(p, m, "BITC", 1.0)
    assert r["ok"] is True

    earned = badges.check_new(p, m)
    ids = [b["id"] for b in earned]
    assert "contagion_trader" in ids
    assert "contagion_trader" in p.badges


def test_contagion_trader_badge_not_awarded_if_holding_depegged_stable():
    seed, step = _find_active_depeg_state()
    m = market.Market(seed=seed)
    m.sync_to(market.WARMUP_STEPS)
    m.step_count = step
    depegged = crypto.active_depegs(m)
    assert depegged

    p = PlayerState(continent="Europe")
    p.cash = 1_000_000.0
    crypto.buy(p, m, "BITC", 1.0)
    crypto.buy(p, m, depegged[0], 1000.0)  # détient le stablecoin décroché lui-même

    earned = badges.check_new(p, m)
    ids = [b["id"] for b in earned]
    assert "contagion_trader" not in ids


def test_badge_not_awarded_twice():
    p, m = _mk()
    hedging.buy_put(p, m, 100_000.0, 1.00, 0.5)
    first = badges.check_new(p, m)
    ids_first = [b["id"] for b in first]
    assert "hedged" in ids_first
    assert p.badges.count("hedged") == 1

    second = badges.check_new(p, m)
    ids_second = [b["id"] for b in second]
    assert "hedged" not in ids_second
    assert p.badges.count("hedged") == 1
