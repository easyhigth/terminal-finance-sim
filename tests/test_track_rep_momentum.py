"""Réputation segmentée par métier (core/track_rep) + momentum de carrière
(core/momentum) : accrual, statut spécialiste, séries chaudes/creuses, effets."""
from core import legacy, momentum, track_rep
from core.game_state import GameState, PlayerState


def _player(track="Quant", grade=5):
    p = PlayerState()
    p.track = track
    p.grade_index = grade
    return p


# ----------------------------------------------------------- réputation-métier
def test_reputation_gain_credits_current_track():
    p = _player()
    p.adjust_reputation(10, reason="mission")
    assert track_rep.get(p, "Quant") == 10
    assert track_rep.dominant(p) == ("Quant", 10)


def test_general_track_does_not_accumulate_segment():
    p = _player(track="General")
    p.adjust_reputation(10)
    assert track_rep.dominant(p) == (None, 0)


def test_negative_reputation_does_not_credit_segment():
    p = _player()
    p.adjust_reputation(-5)
    assert track_rep.get(p, "Quant") == 0


def test_specialist_threshold_and_offer_bonus():
    p = _player()
    p.adjust_reputation(track_rep.SPECIALIST_THRESHOLD, reason="grind")
    assert track_rep.specialist_track(p) == "Quant"
    assert track_rep.offer_mult(p) == track_rep.SPECIALIST_OFFER_BONUS
    # bonus seulement si la voie active EST la spécialité
    p.track = "M&A"
    assert track_rep.offer_mult(p) == 1.0


def test_check_new_specialist_fires_once():
    p = _player()
    p.adjust_reputation(track_rep.SPECIALIST_THRESHOLD, reason="grind")
    assert track_rep.check_new_specialist(p) == "Quant"
    assert track_rep.check_new_specialist(p) is None   # une seule fois


def test_track_rep_survives_save_roundtrip():
    gs = GameState()
    gs.player = _player()
    gs.player.adjust_reputation(20, reason="x")
    gs2 = GameState.from_dict(gs.to_dict())
    assert track_rep.get(gs2.player, "Quant") == 20


# ------------------------------------------------------------------- momentum
def test_profit_and_loss_streaks_from_quarter_close():
    p = _player()
    p.flags["legacy_last_nw"] = 100.0
    # trois trimestres en hausse -> hot
    for nw in (110.0, 120.0, 130.0):
        p.cash = nw
        legacy.on_quarter_close(p, _FakeMarket(nw))
    assert momentum.status(p) == "hot"
    # deux trimestres en baisse -> cold, profit_streak remis à zéro
    for nw in (120.0, 110.0):
        p.cash = nw
        legacy.on_quarter_close(p, _FakeMarket(nw))
    assert momentum.status(p) == "cold"
    assert momentum.profit_streak(p) == 0


def test_momentum_quarter_effect_moves_reputation():
    p = _player()
    p.flags["profit_streak"] = 3
    rep0 = p.reputation
    toast = momentum.apply_quarter_effect(p)
    assert toast is not None and p.reputation > rep0
    p.flags["profit_streak"] = 0
    p.flags["loss_streak"] = 3
    rep1 = p.reputation
    momentum.apply_quarter_effect(p)
    assert p.reputation < rep1


class _FakeMarket:
    """Marché minimal : legacy._net_worth n'a besoin que de valoriser un book
    vide -> il retombe sur le cash du joueur."""
    regime = "Calme"

    def __init__(self, _nw):
        pass
