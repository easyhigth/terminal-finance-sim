import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from core import config
from core.scene_manager import Scene, SceneManager


class _DummyApp:
    pass


class _RecordingScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.entered_with = None

    def on_enter(self, **kwargs):
        self.entered_with = kwargs


@pytest.fixture(scope="module", autouse=True)
def _pygame_init():
    pygame.init()
    pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    yield


def test_scene_base_methods_are_noops():
    s = Scene(_DummyApp())
    s.handle_event(None)
    s.update(0.1)
    s.draw(None)  # ne doit jamais lever


def test_register_and_go_sets_current():
    mgr = SceneManager(_DummyApp())
    scene = _RecordingScene(mgr.app)
    mgr.register("home", scene)
    mgr.go("home", foo="bar")
    assert mgr.current is scene
    assert mgr.current_name == "home"
    assert scene.entered_with == {"foo": "bar"}
    assert mgr._fade == 1.0


def test_go_unknown_scene_raises():
    mgr = SceneManager(_DummyApp())
    with pytest.raises(KeyError):
        mgr.go("does-not-exist")


def test_palette_open_close_resets_query():
    mgr = SceneManager(_DummyApp())
    mgr.open_palette()
    assert mgr.palette_open is True
    assert mgr.palette_query == ""
    assert mgr.palette_sel == 0
    mgr.palette_query = "abc"
    mgr.close_palette()
    assert mgr.palette_open is False


def test_update_decays_fade_over_time():
    mgr = SceneManager(_DummyApp())
    scene = _RecordingScene(mgr.app)
    mgr.register("home", scene)
    mgr.go("home")
    assert mgr._fade == 1.0
    mgr.update(mgr.FADE_TIME / 2)
    assert 0.0 < mgr._fade < 1.0
    mgr.update(mgr.FADE_TIME)
    assert mgr._fade == 0.0


def test_draw_with_no_current_scene_is_noop():
    mgr = SceneManager(_DummyApp())
    surf = pygame.Surface((10, 10))
    mgr.draw(surf)  # ne doit pas lever malgré l'absence de scène courante
