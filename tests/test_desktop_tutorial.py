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


def test_trading_steps_are_gated_by_trade_unlock():
    trading_steps = [s for s in dt.STEPS if s["id"] in ("first_buy", "stop_loss")]
    assert len(trading_steps) == 2
    for step in trading_steps:
        assert callable(step.get("gate"))


class _FakeWindow:
    def __init__(self, key, app_obj):
        self.key = key
        self.app_obj = app_obj


class _FakeWM:
    def __init__(self, windows):
        self.windows = windows


class _FakeApp:
    def __init__(self, grade_index, conditional_orders=None):
        from core.game_state import PlayerState
        self.gs = type("GS", (), {})()
        p = PlayerState()
        p.grade_index = grade_index
        p.conditional_orders = conditional_orders or []
        self.gs.player = p


class _FakeDesktop:
    def __init__(self, grade_index=0, windows=None, conditional_orders=None):
        self.app = _FakeApp(grade_index, conditional_orders)
        self.wm = _FakeWM(windows or [])


def test_active_step_skips_gated_trading_step_before_associate():
    # avance jusqu'à l'étape "first_buy" (index 5)
    for _ in range(5):
        dt.advance()
    desktop = _FakeDesktop(grade_index=0)   # Intern : trading verrouillé
    assert dt.active_step(desktop) is None
    assert dt.active_step() is not None   # sans desktop : gate ignoré


def test_active_step_resumes_once_trade_unlocked():
    for _ in range(5):
        dt.advance()
    desktop = _FakeDesktop(grade_index=1)   # Junior Analyst : trading débloqué
    idx, step = dt.active_step(desktop)
    assert idx == 5
    assert step["id"] == "first_buy"


def test_first_buy_check_reads_trading_order_feed():
    from core.desktop_tutorial import STEPS
    step = next(s for s in STEPS if s["id"] == "first_buy")
    empty_trading = type("App", (), {"order_feed": []})()
    desktop = _FakeDesktop(windows=[_FakeWindow("trading", empty_trading)])
    assert step["check"](desktop) is False
    bought_trading = type("App", (), {"order_feed": [{"text": "ACHAT 10×MVC @ 42.00"}]})()
    desktop2 = _FakeDesktop(windows=[_FakeWindow("trading", bought_trading)])
    assert step["check"](desktop2) is True


def test_stop_loss_check_reads_player_conditional_orders():
    from core.desktop_tutorial import STEPS
    step = next(s for s in STEPS if s["id"] == "stop_loss")
    desktop_none = _FakeDesktop(conditional_orders=[])
    assert step["check"](desktop_none) is False
    desktop_stop = _FakeDesktop(conditional_orders=[{"kind": "stop", "ticker": "MVC"}])
    assert step["check"](desktop_stop) is True
    desktop_target = _FakeDesktop(conditional_orders=[{"kind": "target", "ticker": "MVC"}])
    assert step["check"](desktop_target) is False
