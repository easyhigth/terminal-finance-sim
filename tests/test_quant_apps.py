"""Tests des apps quantitatives du bureau (Sharpe / Z-Score / Couverture),
réécrites sur core/quant_tools : vrais chiffres annualisés, benchmark = vrai
indice régional, couverture branchée sur core/hedging (puts réels) et
core/portfolio.short (paire). Remplace les anciens test_financial_apps*."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from core import portfolio as pf

pygame.font.init()

RECT = pygame.Rect(0, 0, 980, 620)


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


def _with_positions(app, n=3, shares=60):
    p = app.gs.player
    tks = [c["ticker"] for c in app.market.top_companies(n=n)]
    for tk in tks:
        assert pf.buy(p, app.market, tk, shares)["ok"]
    return tks


def _open(app, key):
    desk = app.scenes.current
    w = desk._open_scene_window(key)
    return desk, w


# ================================================================== SHARPE
def test_sharpe_app_native_and_empty_portfolio_message(app):
    desk, w = _open(app, "sharpe")
    assert w.key == "sharpe"
    w.app_obj.draw(app.screen, RECT)          # portefeuille vide : pas de crash
    assert w.app_obj._res is None


def test_sharpe_app_computes_annualized_results(app):
    _with_positions(app)
    desk, w = _open(app, "sharpe")
    sa = w.app_obj
    sa.draw(app.screen, RECT)
    res = sa._res
    assert res is not None
    assert res["bench"] is not None           # le VRAI indice a répondu
    assert res["index_name"] in app.market.index_region
    for grp in ("port", "bench", "min_var", "max_sharpe"):
        assert res[grp] is not None
    assert 0.0 < res["port"]["vol"] < 3.0     # vol annualisée plausible
    assert len(res["rows"]) == 3
    # max Sharpe optimisé ≥ Sharpe du portefeuille courant (même univers/fenêtre)
    assert res["max_sharpe"]["sharpe"] >= res["port"]["sharpe"] - 1e-6


def test_sharpe_app_recomputes_when_market_steps(app):
    _with_positions(app)
    desk, w = _open(app, "sharpe")
    sa = w.app_obj
    sa.draw(app.screen, RECT)
    key1 = sa._cache_key
    app.market.step()
    sa.draw(app.screen, RECT)
    assert sa._cache_key != key1              # invalidation automatique


def test_sharpe_rf_buttons_change_rate(app):
    _with_positions(app)
    desk, w = _open(app, "sharpe")
    sa = w.app_obj
    sa.draw(app.screen, RECT)
    rf0 = sa.rf
    sa.handle_event(_click(sa._rf_plus.center), RECT)
    assert sa.rf == pytest.approx(rf0 + 0.005)
    sa.handle_event(_click(sa._rf_minus.center), RECT)
    assert sa.rf == pytest.approx(rf0)


def test_sharpe_frontier_link_opens_frontier_app(app):
    _with_positions(app)
    desk, w = _open(app, "sharpe")
    sa = w.app_obj
    sa.draw(app.screen, RECT)
    sa.handle_event(_click(sa._frontier_btn.center), RECT)
    assert any(win.key == "frontier" for win in desk.wm.windows)


# ================================================================= Z-SCORE
def test_zscore_app_defaults_to_held_ticker_and_computes(app):
    tks = _with_positions(app)
    desk, w = _open(app, "zscore")
    za = w.app_obj
    assert za.ticker in tks
    za.draw(app.screen, RECT)
    assert za._res is not None
    assert abs(za._res["z"]) < 10             # borne de plausibilité


def test_zscore_all_analyses_compute(app):
    _with_positions(app)
    desk, w = _open(app, "zscore")
    za = w.app_obj
    for analysis, _lbl in [("price", ""), ("returns", ""), ("vol", ""), ("corr", "")]:
        za.analysis = analysis
        za._cache_key = None
        za.draw(app.screen, RECT)
        assert za._res is not None, analysis


def test_zscore_search_selects_ticker_and_rejects_unknown(app):
    desk, w = _open(app, "zscore")
    za = w.app_obj
    tk = app.market.top_companies(n=2)[1]["ticker"]
    za._try_select(tk)
    assert za.ticker == tk
    za._try_select("XXXXXX")
    assert "introuvable" in za.msg


def test_zscore_trade_button_opens_trading(app):
    _with_positions(app)
    desk, w = _open(app, "zscore")
    za = w.app_obj
    za.draw(app.screen, RECT)
    za.handle_event(_click(za._trade_btn.center), RECT)
    assert any(win.key == "trading" for win in desk.wm.windows)


# ============================================================== COUVERTURE
def test_hedge_app_put_quote_and_purchase(app):
    _with_positions(app)
    desk, w = _open(app, "hedge")
    ha = w.app_obj
    ha.draw(app.screen, RECT)
    ctx = ha._ctx
    assert ctx["quote"] is not None
    assert ctx["notional"] > 0 and ctx["premium"] > 0
    cash0 = app.gs.player.cash
    ha.handle_event(_click(ha._buy_btn.center), RECT)
    assert len(app.gs.player.hedges) == 1     # put réellement souscrit (core/hedging)
    assert app.gs.player.cash == pytest.approx(cash0 - ctx["premium"], rel=1e-6)
    ha.draw(app.screen, RECT)                 # liste des puts en cours : pas de crash


def test_hedge_put_locked_below_grade(app):
    _with_positions(app)
    app.gs.player.grade_index = 0
    desk, w = _open(app, "hedge")
    ha = w.app_obj
    ha.draw(app.screen, RECT)
    ha.handle_event(_click(ha._buy_btn.center), RECT)
    assert not getattr(app.gs.player, "hedges", [])
    assert "verrouillée" in ha.msg


def test_hedge_pair_mode_suggests_correlated_and_shorts(app):
    tks = _with_positions(app)
    desk, w = _open(app, "hedge")
    ha = w.app_obj
    ha.mode = "pair"
    ha.draw(app.screen, RECT)
    ctx = ha._ctx
    assert ha.pair_ticker in tks
    assert ctx["candidates"] and ha.pair_hedge == ctx["candidates"][0][0]
    assert ctx["hr"]["ratio"] != 0.0
    qty = ctx["hedge_qty"]
    assert qty >= 1
    ha.handle_event(_click(ha._short_btn.center), RECT)
    pos = app.gs.player.portfolio.get(ha.pair_hedge)
    assert pos is not None and pos["shares"] == -qty   # short réellement passé


def test_hedge_scene_window_redirects_to_native_app(app):
    """Ouvrir la scène "hedge" EN FENÊTRE (PLUS, palette) atterrit sur l'app
    native — plus d'hébergement flou du desk plein écran."""
    desk = app.scenes.current
    w = desk._open_scene_window("hedge")
    from apps.app_hedge import HedgeApp
    assert w.key == "hedge" and isinstance(w.app_obj, HedgeApp)


def test_desktop_shortcuts_never_shadow_copy_or_undo():
    from scenes.scene_desktop_common import DESKTOP_SHORTCUTS
    assert pygame.K_c not in DESKTOP_SHORTCUTS   # Ctrl+C = copier, universel
    assert pygame.K_z not in DESKTOP_SHORTCUTS   # Ctrl+Z = annuler, universel
    assert DESKTOP_SHORTCUTS[pygame.K_g] == "hedge"
    assert DESKTOP_SHORTCUTS[pygame.K_e] == "frontier"
