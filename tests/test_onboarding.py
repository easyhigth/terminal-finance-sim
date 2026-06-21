from core import onboarding
from core.game_state import PlayerState


def test_active_step_none_when_done():
    p = PlayerState(continent="Europe")
    p.onboarding_done = True
    assert onboarding.active_step(p) is None


def test_active_step_none_when_out_of_range():
    p = PlayerState(continent="Europe")
    p.onboarding_step = len(onboarding.STEPS)
    assert onboarding.active_step(p) is None


def test_active_step_returns_current_step():
    p = PlayerState(continent="Europe")
    assert onboarding.active_step(p) is onboarding.STEPS[0]


def test_progress_none_when_check_fails():
    p = PlayerState(continent="Europe")
    assert onboarding.progress(p) is None
    assert p.onboarding_step == 0


def test_progress_advances_and_grants_reputation():
    p = PlayerState(continent="Europe")
    rep_before = p.reputation
    p.flags["onboarding_seen_career"] = True
    step = onboarding.progress(p)
    assert step is onboarding.STEPS[0]
    assert p.onboarding_step == 1
    assert p.reputation >= rep_before


def test_progress_marks_done_on_last_step():
    p = PlayerState(continent="Europe")
    p.onboarding_step = len(onboarding.STEPS) - 1
    last = onboarding.STEPS[-1]
    last["check"](p)  # sanity: callable
    p.flags["onboarding_seen_eval"] = True
    onboarding.progress(p)
    assert p.onboarding_done is True


def test_skip_marks_done():
    p = PlayerState(continent="Europe")
    onboarding.skip(p)
    assert p.onboarding_done is True
