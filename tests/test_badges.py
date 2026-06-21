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


# ----------------------------------------------------- badges à enjeu (streaks)
def test_on_quarter_close_increments_clean_streak_when_heat_zero():
    p, m = _mk()
    p.heat = 0
    badges.on_quarter_close(p)
    badges.on_quarter_close(p)
    assert p.flags["clean_quarter_streak"] == 2


def test_on_quarter_close_resets_clean_streak_when_heat_positive():
    p, m = _mk()
    p.heat = 0
    badges.on_quarter_close(p)
    p.heat = 5
    badges.on_quarter_close(p)
    assert p.flags["clean_quarter_streak"] == 0


def test_check_streaks_awards_badge_once_target_reached():
    p, m = _mk()
    p.heat = 0
    for _ in range(8):
        badges.on_quarter_close(p)
    earned, revoked = badges.check_streaks(p)
    ids = [b["id"] for b in earned]
    assert "untouchable" in ids
    assert "untouchable" in p.streak_badges
    assert revoked == []


def test_check_streaks_does_not_reaward_already_held_badge():
    p, m = _mk()
    p.heat = 0
    for _ in range(8):
        badges.on_quarter_close(p)
    badges.check_streaks(p)
    earned_again, _ = badges.check_streaks(p)
    assert earned_again == []


def test_check_streaks_revokes_badge_when_streak_breaks():
    p, m = _mk()
    p.heat = 0
    for _ in range(8):
        badges.on_quarter_close(p)
    earned, _ = badges.check_streaks(p)
    assert any(b["id"] == "untouchable" for b in earned)

    p.heat = 5
    badges.on_quarter_close(p)
    earned2, revoked2 = badges.check_streaks(p)
    ids_revoked = [b["id"] for b in revoked2]
    assert "untouchable" in ids_revoked
    assert "untouchable" not in p.streak_badges
    assert earned2 == []


def test_check_streaks_can_reaward_after_rebuilding_streak():
    p, m = _mk()
    p.heat = 0
    for _ in range(8):
        badges.on_quarter_close(p)
    badges.check_streaks(p)
    p.heat = 5
    badges.on_quarter_close(p)
    badges.check_streaks(p)
    assert "untouchable" not in p.streak_badges

    p.heat = 0
    for _ in range(8):
        badges.on_quarter_close(p)
    earned3, _ = badges.check_streaks(p)
    assert any(b["id"] == "untouchable" for b in earned3)
    assert "untouchable" in p.streak_badges


def test_lasting_dominance_streak_badge_uses_legacy_top_rank_streak_flag():
    p, m = _mk()
    p.flags["top_rank_streak"] = 4
    earned, _ = badges.check_streaks(p)
    assert any(b["id"] == "lasting_dominance" for b in earned)


def test_blue_chip_streak_badge_uses_legacy_profit_streak_flag():
    p, m = _mk()
    p.flags["profit_streak"] = 6
    earned, _ = badges.check_streaks(p)
    assert any(b["id"] == "blue_chip" for b in earned)
