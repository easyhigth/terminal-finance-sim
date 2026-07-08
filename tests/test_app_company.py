"""Tests de l'app native Fiche société (apps/app_company.py) — migration de
scenes/scene_company.py hors de l'hébergement flou (netteté), l'écran de
détail le plus consulté du jeu. Particularité par rapport à Mission/
Évaluation : PAS de règle « en cours conservé » — chaque ouverture avec un
nouveau ticker doit RECONFIGURER la fenêtre existante, jamais en ouvrir une
seconde ni garder un contenu périmé."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from apps.app_company import CompanyApp

pygame.font.init()

RECT = pygame.Rect(0, 0, 1080, 680)


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 5
    p.cash = 100_000.0
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    return a


def _click(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y))


def _open(app, **kwargs):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("company", **kwargs)
    return desk, w


def test_company_is_native_app_not_hosted(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    desk, w = _open(app, ticker=tk)
    assert w.key == "company" and isinstance(w.app_obj, CompanyApp)
    assert w.app_obj.ticker == tk


def test_no_ticker_defaults_to_top_company(app):
    desk, w = _open(app)
    assert w.app_obj.ticker


def test_reopening_with_different_ticker_reconfigures_same_window(app):
    """Cliquer « Analyse » sur une autre société doit remplacer le contenu
    de la fenêtre déjà ouverte, jamais en ouvrir une seconde."""
    tk1, tk2 = (c["ticker"] for c in app.market.top_companies(n=2))
    desk, w1 = _open(app, ticker=tk1)
    assert w1.app_obj.ticker == tk1
    w2 = desk._open_scene_window("company", ticker=tk2)
    assert w2 is w1                      # même fenêtre
    assert w2.app_obj.ticker == tk2       # contenu remplacé
    assert sum(1 for win in desk.wm.windows if win.key == "company") == 1


def test_all_tabs_draw_without_crash(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    desk, w = _open(app, ticker=tk)
    comp = w.app_obj
    from apps.app_company import _TABS
    for tab_id, _label in _TABS:
        comp.tab = tab_id
        comp.draw(app.screen, RECT)   # ne doit jamais lever


def test_buy_sell_open_trading_prefiltered(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    desk, w = _open(app, ticker=tk)
    comp = w.app_obj
    comp.draw(app.screen, RECT)
    assert comp._buy_rect is not None
    comp.handle_event(_click(*comp._buy_rect.center), RECT)
    trading_win = next(win for win in desk.wm.windows if win.key == "trading")
    assert trading_win.app_obj.search == tk


def test_unknown_ticker_shows_picker(app):
    desk, w = _open(app, ticker="NOPE_NOT_A_TICKER")
    comp = w.app_obj
    assert comp.metrics is None
    comp.draw(app.screen, RECT)   # mode recherche, sans exception


def test_picker_select_company_configures_ticker(app):
    desk, w = _open(app, ticker="NOPE_NOT_A_TICKER")
    comp = w.app_obj
    comp.search = ""   # efface le ticker invalide pour voir le top de capi par défaut
    items = comp._picker_items()
    assert items
    comp._select_company(items[0]["ticker"])
    assert comp.ticker == items[0]["ticker"]
    assert comp.metrics is not None


def test_picker_search_pastes_via_ctrl_v(app, monkeypatch):
    from core import clipboard
    monkeypatch.setattr(clipboard, "paste", lambda: "MVC")
    desk, w = _open(app, ticker="NOPE")
    comp = w.app_obj
    comp.search = ""
    comp.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v,
                                          unicode="v", mod=pygame.KMOD_CTRL), RECT)
    assert comp.search == "MVC"


def test_financials_fullscreen_button_opens_hosted_window(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    desk, w = _open(app, ticker=tk)
    comp = w.app_obj
    comp.tab = "financials"
    comp.draw(app.screen, RECT)
    assert comp._fa_rect is not None
    comp.handle_event(_click(*comp._fa_rect.center), RECT)
    assert any(win.key == "scene:financials" for win in desk.wm.windows)


def test_graph_fullscreen_button_opens_hosted_window(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    desk, w = _open(app, ticker=tk)
    comp = w.app_obj
    comp.tab = "chart"
    comp.draw(app.screen, RECT)
    assert comp._graph_rect is not None
    comp.handle_event(_click(*comp._graph_rect.center), RECT)
    assert any(win.key == "scene:graph" for win in desk.wm.windows)


def test_narrow_window_draws_without_crash(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    desk, w = _open(app, ticker=tk)
    comp = w.app_obj
    small = pygame.Rect(0, 0, 700, 460)
    from apps.app_company import _TABS
    for tab_id, _label in _TABS:
        comp.tab = tab_id
        comp.draw(app.screen, small)


def test_company_is_factory_only_no_standing_icon(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    keys = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert "company" not in keys


def test_configure_ignores_unknown_kwargs(app):
    """configure() doit ignorer silencieusement un kwarg hérité de l'ancien
    appel de scène hébergée (ex. return_to), jamais lever."""
    tk = app.market.top_companies(n=1)[0]["ticker"]
    desk, w = _open(app, ticker=tk, return_to="markethub", return_kwargs={"x": 1})
    assert w.app_obj.ticker == tk
