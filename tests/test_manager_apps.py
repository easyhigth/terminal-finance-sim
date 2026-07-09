"""Tests des apps Attribution (Brinson/Facteurs) et Pairs Trading + onglet
SURFACE du Desk Options."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from core import portfolio as pf

pygame.font.init()

RECT = pygame.Rect(0, 0, 1080, 640)


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    for _ in range(60):
        a.market.step()
    a.scenes.go("desktop")
    return a


def _click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def _with_positions(app, n=4, shares=60):
    for c in app.market.top_companies(n=n):
        assert pf.buy(app.gs.player, app.market, c["ticker"], shares)["ok"]


def _open(app, key):
    desk = app.scenes.current
    return desk, desk._open_scene_window(key)


# ============================================================== Attribution
def test_attribution_app_both_tabs_draw(app):
    _with_positions(app)
    desk, w = _open(app, "attribution")
    at = w.app_obj
    at.draw(app.screen, RECT)                        # BRINSON
    assert at._br is not None
    at.handle_event(_click(at._tab_rects["factors"].center), RECT)
    at.draw(app.screen, RECT)                        # FACTEURS
    assert at._fr is not None


def test_attribution_empty_book_message(app):
    desk, w = _open(app, "attribution")
    w.app_obj.draw(app.screen, RECT)
    assert w.app_obj._br is None


# =============================================================== Pairs app
def test_pairs_app_scans_and_selects_best_pair(app):
    desk, w = _open(app, "pairs")
    pa = w.app_obj
    pa.draw(app.screen, RECT)
    assert len(pa._scan) >= 1
    assert pa.pair == (pa._scan[0][0], pa._scan[0][1])
    assert pa._eg is not None
    # cliquer une autre paire du scanner la sélectionne
    if len(pa._scan) >= 2:
        other = (pa._scan[1][0], pa._scan[1][1])
        pa.handle_event(_click(pa._pair_rects[other].center), RECT)
        assert pa.pair == other


def test_pairs_execution_requires_entry_signal(app):
    desk, w = _open(app, "pairs")
    pa = w.app_obj
    pa.draw(app.screen, RECT)
    from core import pairs as PAIRS
    sig = PAIRS.signal(pa._eg["z_last"])
    n_pos = len(app.gs.player.portfolio)
    pa.handle_event(_click(pa._exec_btn.center), RECT)
    if sig in ("long_spread", "short_spread"):
        assert len(app.gs.player.portfolio) == n_pos + 2   # 2 jambes posées
    else:
        assert len(app.gs.player.portfolio) == n_pos       # pas de signal → rien
        assert "signal" in pa.msg


def test_pairs_locked_below_leverage_grade(app):
    app.gs.player.grade_index = 0
    desk, w = _open(app, "pairs")
    pa = w.app_obj
    pa.draw(app.screen, RECT)
    pa.handle_event(_click(pa._exec_btn.center), RECT)
    assert not app.gs.player.portfolio
    assert "verrouillée" in pa.msg


# ========================================================== Surface de vol
def test_greeks_surface_tab_draws_grid(app):
    desk, w = _open(app, "greeks")
    ga = w.app_obj
    ga.tab = "surface"
    ga._cache_key = None
    ga.draw(app.screen, RECT)
    assert ga._surface is not None
    assert len(ga._surface["iv"]) == 3               # 3 maturités


def test_desktop_icons_for_new_apps_gated(app):
    desk = app.scenes.current
    keys = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert {"attribution", "pairs"} <= keys
    app.gs.player.grade_index = 0
    keys0 = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert "attribution" not in keys0                # trade : grade 4
    assert "pairs" not in keys0                      # leverage : grade 5+
