"""Tests du tutoriel guidé du bureau (core/desktop_tutorial.py) et du
déblocage progressif des icônes (ICON_FEATURE de scenes/scene_desktop.py)."""
import pytest

from core import desktop_tutorial as dt
from core import unlocks


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(dt, "_PATH", str(tmp_path / "desktop_tutorial.json"))


def test_fresh_state_starts_at_step_zero():
    assert not dt.done()
    idx, step = dt.active_step()
    assert idx == 0
    assert step is dt.STEPS[0]


def test_advance_walks_all_steps_then_done():
    for i in range(len(dt.STEPS) - 1):
        finished = dt.advance()
        assert not finished
        idx, _step = dt.active_step()
        assert idx == i + 1
    assert dt.advance() is True
    assert dt.done()
    assert dt.active_step() is None


def test_skip_marks_done_and_reset_restarts():
    dt.skip()
    assert dt.done()
    dt.reset()
    assert not dt.done()
    idx, _ = dt.active_step()
    assert idx == 0


def test_steps_have_titles_hints_and_checks():
    for step in dt.STEPS:
        assert dt.step_title(step)
        assert dt.step_hint(step)
        assert callable(step["check"])


def test_icon_feature_keys_reference_real_icons_and_features():
    from scenes.scene_desktop import APPS, ICON_FEATURE, QUICK_APPS
    icon_keys = {k for k, *_ in APPS} | {k for k, *_ in QUICK_APPS}
    for key, feat in ICON_FEATURE.items():
        assert key in icon_keys
        assert feat in unlocks.UNLOCKS


def test_tutorial_targets_are_desktop_icons():
    from scenes.scene_desktop import APPS, QUICK_APPS
    icon_keys = {k for k, *_ in APPS} | {k for k, *_ in QUICK_APPS} | {"terminal", "track"}
    for step in dt.STEPS:
        if step["target"] is not None:
            assert step["target"] in icon_keys
