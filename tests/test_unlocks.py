"""Tests du déblocage progressif des fonctionnalités selon le grade (core/unlocks.py)."""
from core import unlocks
from core.game_state import PlayerState


def _player(grade=0):
    p = PlayerState()
    p.grade_index = grade
    return p


def test_feature_locked_below_required_grade():
    p = _player(grade=0)
    assert not unlocks.unlocked(p, "trade")


def test_feature_unlocked_at_required_grade():
    p = _player(grade=unlocks.required_grade("trade"))
    assert unlocks.unlocked(p, "trade")


def test_unknown_feature_defaults_to_unlocked():
    p = _player(grade=0)
    assert unlocks.unlocked(p, "inconnu")


def test_cmd_unlocked_follows_mapped_feature():
    p = _player(grade=0)
    assert not unlocks.cmd_unlocked(p, "BUY")
    p.grade_index = unlocks.required_grade("trade")
    assert unlocks.cmd_unlocked(p, "BUY")


def test_cmd_unlocked_true_for_unmapped_command():
    p = _player(grade=0)
    assert unlocks.cmd_unlocked(p, "INCONNU")


def test_every_label_has_a_matching_unlock_entry():
    assert set(unlocks.LABELS) == set(unlocks.UNLOCKS)


def test_next_unlock_returns_lowest_pending_grade():
    p = _player(grade=0)
    label, grade = unlocks.next_unlock(p)
    assert grade == min(unlocks.UNLOCKS.values())
    assert label == unlocks.feature_label(
        next(f for f, g in unlocks.UNLOCKS.items() if g == grade)
    )


def test_next_unlock_none_when_everything_open():
    p = _player(grade=max(unlocks.UNLOCKS.values()))
    assert unlocks.next_unlock(p) is None
