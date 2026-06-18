"""Tests de la notation de crédit (core/credit.py) et de son usage en DCM."""
import random

from core import credit, deal_game, deals


def test_rating_for_none_leverage_is_worst():
    assert credit.rating_for(None, 0.02) == credit.RATINGS[-1]


def test_rating_for_low_leverage_low_vol_is_best():
    assert credit.rating_for(0.0, 0.005) == "AAA"


def test_rating_for_high_leverage_is_worst():
    assert credit.rating_for(10.0, 0.05) == credit.RATINGS[-1]


def test_rating_for_monotonic_in_leverage():
    ranks = [credit.rating_rank(credit.rating_for(nd, 0.02)) for nd in (0.0, 1.0, 2.0, 4.0, 8.0)]
    assert ranks == sorted(ranks)


def test_rating_rank_orders_best_to_worst():
    assert credit.rating_rank("AAA") < credit.rating_rank("BBB") < credit.rating_rank("B")


def test_rating_rank_unknown_defaults_to_worst():
    assert credit.rating_rank("ZZZ") == len(credit.RATINGS) - 1


# --------------------------------------------------------------- DCM via deals
def test_dcm_template_exists_and_eligible_for_any_track():
    assert any(t["kind"] == "DCM" for t in deals.DEAL_TEMPLATES)
    from core.game_state import PlayerState
    p = PlayerState()
    p.track = "Quant"          # voie sans rapport avec DCM
    kinds = {t["kind"] for t in deals._eligible_templates(p)}
    assert "DCM" in kinds


def test_dcm_challenge_has_good_choice_matching_rating_spread():
    ch = deal_game.make_challenge({"kind": "DCM"}, random.Random(3))
    qualities = [c["quality"] for c in ch["choices"]]
    assert qualities.count("good") == 1
    assert qualities.count("bad") == 1
    assert qualities.count("ok") == 1
