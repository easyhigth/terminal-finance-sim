"""Tests de core/ui_state.py : persistance séparée de l'état UI du bureau.
Nécessite pygame (driver factice)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

import main
from core import config, ui_state
from core.workbook import Workbook


@pytest.fixture()
def app(tmp_path):
    from core import desktop_onboarding
    desktop_onboarding.mark_seen()
    old_save_dir = config.SAVE_DIR
    config.SAVE_DIR = str(tmp_path)
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.flags["desktop_seeded"] = True
    p.watchlist = ["MVC", "LWNH"]
    a.workbook = Workbook(12, 8)
    a.workbook.active.sheet.set("A1", "test")
    try:
        yield a
    finally:
        config.SAVE_DIR = old_save_dir


def test_ui_state_save_load_workbook(app):
    slot = "autosave"
    ui_state.save(slot, app)
    app.workbook.active.sheet.set("A1", "changed")
    data = ui_state.load(slot, app)
    assert data is not None
    assert app.workbook.active.sheet.get_raw("A1") == "test"


def test_ui_state_save_load_watchlist(app):
    slot = "autosave"
    ui_state.save(slot, app)
    app.gs.player.watchlist = []
    ui_state.load(slot, app)
    assert app.gs.player.watchlist == ["MVC", "LWNH"]


def test_ui_state_save_load_pages(app):
    slot = "slot1"
    # ouvre un second onglet avant sauvegarde
    app.pages.open_new_tab()
    assert len(app.pages.pages) == 2
    ui_state.save(slot, app)

    # charge dans un app frais : les pages doivent être restaurées
    a2 = main.App()
    a2.gs = app.gs
    a2.gs.attach_app(a2)
    a2.workbook = Workbook(12, 8)
    ui_state.load(slot, a2)
    assert len(a2.pages.pages) == 2
    # l'onglet actif doit être desktop après un chargement
    assert a2.pages.pages[a2.pages.active].scene_name == "desktop"


def test_ui_state_pending_layout_applied_on_desktop(app):
    slot = "slot1"
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk._open_scene_window("markethub")
    ui_state.save(slot, app)

    # simule un chargement : ui_state.load pose _pending_ui_layout
    a2 = main.App()
    a2.gs = app.gs
    a2.gs.attach_app(a2)
    a2.workbook = Workbook(12, 8)
    ui_state.load(slot, a2)
    assert getattr(a2, "_pending_ui_layout", None) is not None
    assert any(e.get("name") == "markethub" for e in a2._pending_ui_layout if e.get("kind") == "scene")

    # arrivée sur le bureau : le layout pending est appliqué
    a2.scenes.go("desktop")
    desk2 = a2.scenes.current
    assert any(w.key == "scene:markethub" for w in desk2.wm.windows)
    assert a2._pending_ui_layout is None


def test_ui_state_delete_slot(app):
    slot = "slot1"
    ui_state.save(slot, app)
    assert os.path.exists(ui_state._PATH(slot))
    ui_state.delete(slot)
    assert not os.path.exists(ui_state._PATH(slot))


def test_ui_state_load_missing_returns_none(app):
    assert ui_state.load("does_not_exist", app) is None


def test_game_state_save_triggers_ui_state_save(app):
    """GameState.save appelle ui_state.save quand l'app est attachée."""
    slot = "test_slot"
    app.scenes.go("desktop")
    app.gs.save(slot)
    assert os.path.exists(ui_state._PATH(slot))
    data = ui_state.load(slot, app)
    assert data is not None


def test_game_state_delete_removes_ui_state(app):
    slot = "test_slot"
    app.gs.save(slot)
    assert os.path.exists(ui_state._PATH(slot))
    from core.game_state import GameState
    GameState.delete(slot)
    assert not os.path.exists(ui_state._PATH(slot))
