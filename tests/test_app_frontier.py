"""Tests de la frontière efficiente INTERACTIVE (apps/app_frontier.py) :
la courbe se clique, le panneau cible liste les ordres exacts, et APPLIQUER
les exécute réellement via core/portfolio — c'est la différence avec
l'ancien labo en lecture seule (scene_frontier_lab), désormais redirigé ici."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pytest

pytest.importorskip("pygame")

import pygame

import main
from apps.app_frontier import FrontierApp
from core import portfolio as pf
from core import quant_tools as QT

pygame.font.init()

RECT = pygame.Rect(0, 0, 1140, 660)


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


def _with_positions(app, n=3, shares=80):
    p = app.gs.player
    tks = [c["ticker"] for c in app.market.top_companies(n=n)]
    for tk in tks:
        assert pf.buy(p, app.market, tk, shares)["ok"]
    return tks


def _open(app):
    desk = app.scenes.current
    w = desk._open_scene_window("frontier")
    return desk, w


def test_frontier_is_native_app_with_standing_icon(app):
    desk, w = _open(app)
    assert w.key == "frontier" and isinstance(w.app_obj, FrontierApp)
    labels = [lbl for _k, lbl, _kind, _acc in desk._icon_list()]
    assert labels.count("Frontière efficiente") == 1


def test_frontier_lab_scene_redirects_to_native_app(app):
    desk = app.scenes.current
    w = desk._open_scene_window("frontier_lab")
    assert w.key == "frontier"
    assert not any(win.key == "scene:frontier_lab" for win in desk.wm.windows)


def test_universe_includes_held_and_candidates(app):
    tks = _with_positions(app)
    desk, w = _open(app)
    fa = w.app_obj
    assert set(tks) <= set(fa.universe)
    assert set(tks) <= fa.selected              # les détenues démarrent cochées
    assert len(fa.universe) > len(tks)          # + candidates de diversification


def test_empty_portfolio_still_offers_a_universe(app):
    desk, w = _open(app)
    fa = w.app_obj
    assert len(fa.selected) >= 2                # investissable même sans position
    fa.draw(app.screen, RECT)
    assert fa._fr is not None


def test_click_on_curve_sets_target_and_builds_trades(app):
    _with_positions(app)
    desk, w = _open(app)
    fa = w.app_obj
    fa.draw(app.screen, RECT)
    assert fa._curve_px
    fa.handle_event(_click(fa._curve_px[3]), RECT)
    assert fa.target_idx == 3
    assert fa._trades is not None and fa._trades["budget"] > 0
    fa.draw(app.screen, RECT)                   # panneau cible : pas de crash


def test_arrow_keys_slide_along_the_frontier(app):
    _with_positions(app)
    desk, w = _open(app)
    fa = w.app_obj
    fa.draw(app.screen, RECT)
    fa._set_target(5)
    fa.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT), RECT)
    assert fa.target_idx == 6
    fa.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT), RECT)
    assert fa.target_idx == 5


def test_quick_buttons_select_min_var_and_max_sharpe(app):
    _with_positions(app)
    desk, w = _open(app)
    fa = w.app_obj
    fa.draw(app.screen, RECT)
    fa.handle_event(_click(fa._minvar_btn.center), RECT)
    assert fa.target_idx == fa._fr["i_min_var"]
    fa.handle_event(_click(fa._maxsharpe_btn.center), RECT)
    assert fa.target_idx == fa._fr["i_max_sharpe"]


def test_apply_needs_confirmation_then_executes_real_orders(app):
    tks = _with_positions(app)
    desk, w = _open(app)
    fa = w.app_obj
    fa.selected = set(tks)                       # univers = positions détenues
    fa._cache_key = None
    fa.draw(app.screen, RECT)
    fa._set_target(fa._fr["i_min_var"])
    fa.draw(app.screen, RECT)
    trades = fa._trades["trades"]
    assert trades, "le portefeuille équipondéré n'est pas min-var : il y a des ordres"
    target_w = fa._fr["weights"][fa._fr["i_min_var"]]
    # 1er clic : ouvre la CONFIRMATION, ne trade pas encore
    fa.handle_event(_click(fa._apply_btn.center), RECT)
    assert fa._confirm is True
    w0 = {tk: p["shares"] for tk, p in app.gs.player.portfolio.items()}
    fa.draw(app.screen, RECT)
    # ANNULER ne touche à rien
    fa.handle_event(_click(fa._no_btn.center), RECT)
    assert {tk: p["shares"] for tk, p in app.gs.player.portfolio.items()} == w0
    # EXÉCUTER passe les ordres réels
    fa.handle_event(_click(fa._apply_btn.center), RECT)
    fa.draw(app.screen, RECT)
    fa.handle_event(_click(fa._yes_btn.center), RECT)
    assert "exécuté" in fa.msg
    w_after, _tot = QT.current_weights(app.gs.player, app.market, fa._fr["tickers"])
    tw = np.asarray(target_w) / np.asarray(target_w).sum()
    assert np.abs(w_after - tw).max() < 0.08     # on a bien REJOINT la cible


def test_frontier_recomputes_when_market_steps(app):
    _with_positions(app)
    desk, w = _open(app)
    fa = w.app_obj
    fa.draw(app.screen, RECT)
    key1 = fa._cache_key
    app.market.step()
    fa.draw(app.screen, RECT)
    assert fa._cache_key != key1                 # la frontière est vivante


def test_toggling_universe_resets_target(app):
    _with_positions(app)
    desk, w = _open(app)
    fa = w.app_obj
    fa.draw(app.screen, RECT)
    fa._set_target(4)
    extra = next(tk for tk in fa.universe if tk not in fa.selected)
    fa.handle_event(_click(fa._row_rects[extra].center), RECT)
    assert extra in fa.selected
    assert fa.target_idx is None                 # cible invalidée, poids obsolètes
