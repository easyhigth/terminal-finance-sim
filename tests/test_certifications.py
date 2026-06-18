"""Tests des certifications professionnelles (core/certifications.py)."""
import pytest

from core import certifications
from core.game_state import PlayerState


def _player(grade_index=2, cash=1_000_000.0, track="Portfolio"):
    p = PlayerState(grade_index=grade_index, track=track)
    p.cash = cash
    return p


def test_level_defaults_to_zero():
    p = _player()
    assert certifications.level(p, "CFA") == 0


def test_is_complete_false_initially():
    p = _player()
    assert not certifications.is_complete(p, "CFA")


def test_status_label_in_progress_and_obtained():
    p = _player()
    assert certifications.status_label(p, "CFA") == "niveau 0/3"
    p.certs["CFA"] = 3
    assert certifications.status_label(p, "CFA") == "OBTENU"


def test_can_attempt_blocked_by_grade():
    p = _player(grade_index=0)
    code, target, tier = certifications.can_attempt(p, "CFA")
    assert code == "grade"
    assert target == certifications.PROGRAMS["CFA"]["min_grade"]


def test_can_attempt_blocked_by_cash():
    p = _player(grade_index=2, cash=0.0)
    code, fee, tier = certifications.can_attempt(p, "CFA")
    assert code == "cash"
    assert fee == certifications.PROGRAMS["CFA"]["fee"][0]


def test_can_attempt_ok_when_grade_and_cash_sufficient():
    p = _player(grade_index=2, cash=1_000_000.0)
    code, fee, tier = certifications.can_attempt(p, "CFA")
    assert code == "ok"
    assert fee == certifications.PROGRAMS["CFA"]["fee"][0]
    assert tier == certifications.PROGRAMS["CFA"]["tier"]


def test_can_attempt_done_when_already_complete():
    p = _player(grade_index=2)
    p.certs["CFA"] = certifications.PROGRAMS["CFA"]["levels"]
    code, _, _ = certifications.can_attempt(p, "CFA")
    assert code == "done"


def test_pay_and_start_debits_fee_and_returns_tier_level():
    p = _player(grade_index=2, cash=1_000_000.0)
    fee0 = certifications.PROGRAMS["CFA"]["fee"][0]
    result = certifications.pay_and_start(p, "CFA")
    assert result == (certifications.PROGRAMS["CFA"]["tier"], 0)
    assert p.cash == pytest.approx(1_000_000.0 - fee0)


def test_pay_and_start_returns_none_when_not_allowed():
    p = _player(grade_index=0)
    assert certifications.pay_and_start(p, "CFA") is None


def test_pass_stage_increments_level_and_reputation():
    p = _player(grade_index=2)
    p.reputation = 50
    result = certifications.pass_stage(p, "CFA")
    assert p.certs["CFA"] == 1
    assert result["done"] is False
    assert result["title"] is None
    assert p.reputation == 50 + certifications.PROGRAMS["CFA"]["rep"][0]


def test_pass_stage_returns_none_when_already_complete():
    p = _player(grade_index=2)
    p.certs["CFA"] = certifications.PROGRAMS["CFA"]["levels"]
    assert certifications.pass_stage(p, "CFA") is None


def test_pass_stage_awards_title_on_completion():
    p = _player(grade_index=2)
    p.certs["CQF"] = 0   # CQF n'a qu'un seul niveau
    result = certifications.pass_stage(p, "CQF")
    assert result["done"] is True
    assert result["title"] == "CQF Charterholder"
    assert "CQF Charterholder" in p.titles


def test_pass_stage_does_not_duplicate_title():
    p = _player(grade_index=2)
    p.certs["CQF"] = 0
    certifications.pass_stage(p, "CQF")
    p.certs["CQF"] = 0   # simulateur d'un repassage incohérent (test de robustesse du titre)
    certifications.pass_stage(p, "CQF")
    assert p.titles.count("CQF Charterholder") == 1


def test_promotion_bonus_requires_matching_track_and_completion():
    p = _player(grade_index=2, track="Portfolio")
    assert certifications.promotion_bonus(p) == (0, 0)
    p.certs["CFA"] = certifications.PROGRAMS["CFA"]["levels"]
    assert certifications.promotion_bonus(p) == (7, 1)


def test_promotion_bonus_ignores_completion_in_other_track():
    p = _player(grade_index=2, track="M&A")
    p.certs["CFA"] = certifications.PROGRAMS["CFA"]["levels"]   # CFA est track "Portfolio"
    assert certifications.promotion_bonus(p) == (0, 0)


def test_available_for_returns_matching_programs():
    assert certifications.available_for("Risk") == ["FRM"]
    assert certifications.available_for("Quant") == ["CQF"]
    assert certifications.available_for("Advisory") == []


# ---------------------------------------------------------------- ACI (desk FX)
def test_aci_program_present_with_expected_schema():
    prog = certifications.PROGRAMS["ACI"]
    assert prog["name"] == "ACI"
    assert prog["full"] == "ACI Dealing Certificate"
    assert prog["track"] is None
    assert prog["levels"] == 1
    assert prog["min_grade"] == 5
    assert prog["fee"] == [30000]
    assert prog["rep"] == [10]
    assert prog["tier"] == 4


def test_aci_can_attempt_blocked_by_grade():
    p = _player(grade_index=4)
    code, target, tier = certifications.can_attempt(p, "ACI")
    assert code == "grade"
    assert target == certifications.PROGRAMS["ACI"]["min_grade"]


def test_aci_can_attempt_blocked_by_cash():
    p = _player(grade_index=5, cash=0.0)
    code, fee, tier = certifications.can_attempt(p, "ACI")
    assert code == "cash"
    assert fee == certifications.PROGRAMS["ACI"]["fee"][0]


def test_aci_can_attempt_ok_when_grade_and_cash_sufficient():
    p = _player(grade_index=5, cash=1_000_000.0)
    code, fee, tier = certifications.can_attempt(p, "ACI")
    assert code == "ok"
    assert fee == certifications.PROGRAMS["ACI"]["fee"][0]
    assert tier == certifications.PROGRAMS["ACI"]["tier"]


def test_aci_level_is_complete_status_label():
    p = _player(grade_index=5)
    assert certifications.level(p, "ACI") == 0
    assert not certifications.is_complete(p, "ACI")
    assert certifications.status_label(p, "ACI") == "niveau 0/1"
    p.certs["ACI"] = 1
    assert certifications.level(p, "ACI") == 1
    assert certifications.is_complete(p, "ACI")
    assert certifications.status_label(p, "ACI") == "OBTENU"


def test_aci_promotion_bonus_never_matches_any_track():
    # track=None pour ACI : ne doit jamais matcher la voie d'un joueur réel,
    # quel que soit le track et même une fois la certification complète.
    p = _player(grade_index=5, track="Risk")
    p.certs["ACI"] = certifications.PROGRAMS["ACI"]["levels"]
    assert certifications.promotion_bonus(p) == (0, 0)


def test_aci_unlocks_fx_forward_via_certification():
    """Intégration : core.fx.forward_unlocked(player) doit passer de False à
    True quand la certification ACI complète réduit le grade requis de 3."""
    from core import fx as FX
    from core.game_state import PlayerState

    grade = FX.FORWARD_MIN_GRADE - 1
    assert FX.FORWARD_MIN_GRADE - 3 <= grade < FX.FORWARD_MIN_GRADE

    p = PlayerState(grade_index=grade, track="Risk")
    p.cash = 1_000_000.0

    assert FX.forward_unlocked(p) is False

    p.certs["ACI"] = 1
    assert certifications.is_complete(p, "ACI")
    assert FX.forward_unlocked(p) is True
