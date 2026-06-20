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
    pending = [g for g in unlocks.UNLOCKS.values() if g > p.grade_index]
    assert grade == min(pending)
    assert label == unlocks.feature_label(
        next(f for f, g in unlocks.UNLOCKS.items() if g == grade)
    )


def test_next_unlock_none_when_everything_open():
    p = _player(grade=max(unlocks.UNLOCKS.values()))
    assert unlocks.next_unlock(p) is None


def test_intern_has_read_only_analysis_tools_from_day_one():
    """Dès le grade Intern (0), les outils d'analyse/sandbox sans impact
    économique (watchlist, alertes, recherche, ALM/RISK/QUANT en lecture/
    simulation) sont ouverts, pour donner une activité réelle avant que le
    trading/les mandats ne se débloquent."""
    p = _player(grade=0)
    for feature in ("analyst", "alm", "risk", "quant"):
        assert unlocks.unlocked(p, feature), feature
    for cmd in ("WATCHLIST", "ALERT", "COMPARE", "RESEARCH"):
        assert unlocks.cmd_unlocked(p, cmd), cmd
    # le trading et les mandats restent verrouillés (pas de changement d'équilibre)
    for feature in ("trade", "mandates", "deals", "ma"):
        assert not unlocks.unlocked(p, feature), feature
