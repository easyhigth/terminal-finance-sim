"""Tests de l'app native Deals (apps/app_deals.py) — migration de
scenes/scene_deals.py hors de l'hébergement flou (netteté), même principe
que Mission/Évaluation. Vérifie l'ouverture, la liste/recherche/filtres, le
mode historique, et que cliquer une ligne ouvre le mini-jeu "deal" EN
FENÊTRE (pas une bascule plein écran hors du bureau)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from apps.app_deals import DealsApp

pygame.font.init()

RECT = pygame.Rect(0, 0, 1040, 660)


def _deal(id_, title="Deal test", kind="M&A", days_left=10):
    return {"id": id_, "title": title, "kind": kind, "desc": "Un deal de test.",
            "reward_cash": 50_000.0, "reward_rep": 5, "penalty_cash": 20_000.0,
            "penalty_rep": 3, "difficulty": 2, "days_left": days_left}


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 5
    p.cash = 500_000.0
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    return a


def _click(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y))


def _open(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("deals")
    return desk, w


def test_deals_is_native_app_not_hosted(app):
    desk, w = _open(app)
    assert w.key == "deals" and isinstance(w.app_obj, DealsApp)


def test_deals_locked_below_grade_shows_message(app):
    app.gs.player.grade_index = 0
    desk, w = _open(app)
    d = w.app_obj
    d.draw(app.screen, RECT)   # ne doit pas lever, message de verrouillage


def test_deals_lists_active_deals(app):
    app.gs.player.deals = [_deal(1), _deal(2)]
    desk, w = _open(app)
    d = w.app_obj
    d.draw(app.screen, RECT)
    assert len(d._row_list) == 2


def test_deals_search_filters(app):
    app.gs.player.deals = [_deal(1, title="Fusion Alpha"), _deal(2, title="Cession Beta")]
    desk, w = _open(app)
    d = w.app_obj
    d.search = "alpha"
    d.draw(app.screen, RECT)
    assert len(d._row_list) == 1
    assert d._row_list[0]["title"] == "Fusion Alpha"


def test_deals_kind_filter(app):
    app.gs.player.deals = [_deal(1, kind="M&A"), _deal(2, kind="Risk")]
    desk, w = _open(app)
    d = w.app_obj
    d.draw(app.screen, RECT)
    d.handle_event(_click(*d._kind_rects["Risk"].center), RECT)
    assert d.kind_filter == "Risk"
    d.draw(app.screen, RECT)
    assert len(d._row_list) == 1 and d._row_list[0]["kind"] == "Risk"


def test_click_row_opens_deal_window_not_fullscreen(app):
    app.gs.player.deals = [_deal(7)]
    desk, w = _open(app)
    d = w.app_obj
    d.draw(app.screen, RECT)
    d.handle_event(_click(*d._row_rects[7].center), RECT)
    assert app.scenes.current_name == "desktop"   # jamais de bascule plein écran
    assert any(win.key == "scene:deal" for win in desk.wm.windows)


def test_history_mode_toggle_and_draw(app):
    app.gs.player.deals_history = [
        {"day": 10, "quarter": 1, "title": "Ancien deal", "kind": "M&A",
         "outcome": "success", "cash_delta": 1000.0, "rep_delta": 2},
    ]
    desk, w = _open(app)
    d = w.app_obj
    d.draw(app.screen, RECT)
    d.handle_event(_click(*d._mode_rects["history"].center), RECT)
    assert d.view_mode == "history"
    d.draw(app.screen, RECT)   # rendu historique sans exception


def test_deals_search_pastes_via_ctrl_v(app, monkeypatch):
    from core import clipboard
    monkeypatch.setattr(clipboard, "paste", lambda: "Fusion")
    desk, w = _open(app)
    d = w.app_obj
    d.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v,
                                       unicode="v", mod=pygame.KMOD_CTRL), RECT)
    assert d.search == "Fusion"


def test_deals_narrow_window_draws_without_crash(app):
    app.gs.player.deals = [_deal(1)]
    desk, w = _open(app)
    d = w.app_obj
    d.draw(app.screen, pygame.Rect(0, 0, 700, 480))


def test_deals_pauses_time_is_not_required():
    """Consulter le hub Deals n'est PAS un écran de travail forcé — seul le
    mini-jeu "deal" lui-même gèle le temps."""
    from core.sim_clock import FOCUS_SCENE_NAMES
    assert "deals" not in FOCUS_SCENE_NAMES
    assert "deal" in FOCUS_SCENE_NAMES
