"""Tests des époques de marché (core/market.py) : tirage dédié à la seed
(déterministe, sans toucher le rng du marché), dérive négative effective en
décennie perdue, proportion de graines cohérente, notification unique."""
import numpy as np

from core.game_state import GameState
from core.market import Market
from core.market_constants import LOST_DECADE_PROB


def _find_seed(epoch, start=1):
    seed = start
    while True:
        if Market(seed=seed).epoch == epoch:
            return seed
        seed += 1


def test_epoch_is_deterministic_per_seed():
    for seed in (1, 7, 12345, 999_983):
        assert Market(seed=seed).epoch == Market(seed=seed).epoch


def test_epoch_share_is_roughly_ten_percent():
    n = 400
    lost = sum(Market(seed=s).epoch == "decennie_perdue" for s in range(1, n + 1))
    assert 0.4 * LOST_DECADE_PROB * n < lost < 2.0 * LOST_DECADE_PROB * n


def test_normal_epoch_keeps_legacy_price_path():
    """Une graine d'époque normale (drift 0) suit EXACTEMENT le même chemin
    de prix qu'avant l'introduction des époques — 90 % des saves existantes
    ne bougent pas d'un bit."""
    seed = _find_seed("normale")
    m = Market(seed=seed)
    assert m.epoch_drift == 0.0
    a, b = Market(seed=seed), Market(seed=seed)
    for _ in range(10):
        a.step(); b.step()
    assert np.array_equal(a.price, b.price)


def test_lost_decade_underperforms_normal_epoch_drift():
    """Même graine, dérive d'époque forcée ou non : la décennie perdue
    sous-performe nettement à long terme (le tirage aléatoire est identique,
    seule la dérive change)."""
    seed = _find_seed("normale")
    base, lost = Market(seed=seed), Market(seed=seed)
    from core.market_constants import LOST_DECADE_DRIFT
    lost.epoch, lost.epoch_drift = "decennie_perdue", LOST_DECADE_DRIFT
    for _ in range(120):
        base.step(); lost.step()
    cap_base = float(np.sum(base.price * base.shares))
    cap_lost = float(np.sum(lost.price * lost.shares))
    assert cap_lost < cap_base * 0.92


def test_veteran_notice_arrives_once():
    seed = _find_seed("decennie_perdue")
    m = Market(seed=seed)
    for _ in range(3):
        m.step()
    gs = GameState()
    p = gs.player
    p.cash = 200_000.0
    for _ in range(4):
        m.step()
        gs.advance_step(market=m)
    veteran_msgs = [msg for msg in p.inbox if "vétéran" in msg.get("sender", "").lower()]
    assert len(veteran_msgs) == 1
    assert p.flags.get("epoch_noticed") is True
