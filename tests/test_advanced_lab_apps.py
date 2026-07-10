"""Tests des apps du lot B v2 : Desk FX (carry), Labo de vol (GARCH/Régimes),
onglet Δ-HEDGE du Desk Options, onglet IMMUNISATION du Desk Taux."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from core import option_strategies as OS

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
    for _ in range(120):
        a.market.step()
    a.scenes.go("desktop")
    return a


def _click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def _open(app, key):
    desk = app.scenes.current
    return desk, desk._open_scene_window(key)


def test_fxdesk_table_and_long_execution(app):
    desk, w = _open(app, "fxdesk")
    fxd = w.app_obj
    fxd.draw(app.screen, RECT)
    assert len(fxd._table) == 8                       # les 8 paires du jeu
    fxd.pair = "USD/ZAR"
    fxd.draw(app.screen, RECT)
    fxd.handle_event(_click(fxd._short_btn.center), RECT)
    assert app.gs.player.fx_positions                 # position réellement ouverte
    fxd.draw(app.screen, RECT)                        # liste positions : ok
    assert "portage" in fxd.msg


def test_vollab_garch_and_regimes_tabs(app):
    desk, w = _open(app, "vollab")
    vl = w.app_obj
    vl.draw(app.screen, RECT)
    assert vl._garch is not None
    vl.handle_event(_click(vl._tab_rects["regimes"].center), RECT)
    vl.draw(app.screen, RECT)
    assert vl._regime is not None


def test_vollab_link_opens_options_desk(app):
    desk, w = _open(app, "vollab")
    vl = w.app_obj
    vl.draw(app.screen, RECT)
    vl.handle_event(_click(vl._strat_btn.center), RECT)
    assert any(win.key == "greeks" for win in desk.wm.windows)


def test_greeks_dhedge_tab_flattens_delta(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    assert OS.execute_strategy(app.gs.player, app.market, tk, "call", 0.5, 60)["ok"]
    desk, w = _open(app, "greeks")
    ga = w.app_obj
    ga.tab = "dhedge"
    ga._cache_key = None
    ga.draw(app.screen, RECT)
    assert ga._dh_plan                                # un call sec a du delta
    ga.handle_event(_click(ga._flatten_btn.center), RECT)
    assert "aplati" in ga.msg
    from core import delta_hedge as DH
    rows = DH.book_delta_by_underlying(app.gs.player, app.market)
    assert abs(rows[0]["net_shares"]) <= 1


def test_rates_immunization_tab_buys_barbell(app):
    desk, w = _open(app, "rates")
    ra = w.app_obj
    ra.tab = "immun"
    ra.draw(app.screen, RECT)
    if ra._immun_btn is None:
        pytest.skip("univers n'encadrant pas l'horizon")
    ra.handle_event(_click(ra._immun_btn.center), RECT)
    assert "Barbell" in ra.msg
    assert len(app.gs.player.bonds) >= 2


def test_new_icons_gating(app):
    desk = app.scenes.current
    keys = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert {"fxdesk", "vollab", "valuation"} <= keys
    app.gs.player.grade_index = 0
    keys0 = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert not ({"fxdesk", "vollab", "valuation"} & keys0)
