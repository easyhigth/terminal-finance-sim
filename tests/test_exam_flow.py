"""core/exam_flow.serve : point de tirage UNIQUE des examens, partagé par la
scène plein écran et l'app native (fin des doublons de logique)."""
from core import config, exam_flow, question_log
from core.game_state import PlayerState


def _player(grade=3):
    p = PlayerState()
    p.grade_index = grade
    return p


def test_serve_promotion_returns_items_threshold_and_target_grade():
    p = _player(grade=3)
    items, thr, target = exam_flow.serve(p, mode="promotion")
    assert items and 0 < thr <= 1
    assert target == config.GRADES[4]          # grade suivant


def test_serve_excludes_already_seen_questions():
    p = _player(grade=3)
    first, _, _ = exam_flow.serve(p)
    question_log.mark_seen(p, first)
    second, _, _ = exam_flow.serve(p)          # avoid = questions déjà vues (défaut)
    seen = question_log.seen_set(p)
    assert all(question_log.identity(it) not in seen for it in second)


def test_serve_cert_uses_program_threshold_and_label():
    from core import certifications as C
    p = _player(grade=4)
    prog = next(iter(C.PROGRAMS))
    items, thr, target = exam_flow.serve(p, mode="cert", cert_program=prog, cert_level=0)
    assert items and thr == C.PASS_THRESHOLD
    assert C.PROGRAMS[prog]["name"] in target
