"""Tests des apps de la salle des marchés avancée (Desk Options / Risque
VaR / Desk Taux) : ouverture native, calculs branchés sur les vrais desks
(core/options, core/risk, core/bonds), exécution réelle, redirection de la
scène "options" et verrous de grade."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from core import bonds as B
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


def _with_positions(app, n=3, shares=60):
    tks = [c["ticker"] for c in app.market.top_companies(n=n)]
    for tk in tks:
        assert pf.buy(app.gs.player, app.market, tk, shares)["ok"]
    return tks


def _open(app, key):
    desk = app.scenes.current
    return desk, desk._open_scene_window(key)


# ============================================================ Desk Options
def test_greeks_app_native_and_options_scene_redirects(app):
    desk, w = _open(app, "greeks")
    from apps.app_greeks import GreeksApp
    assert w.key == "greeks" and isinstance(w.app_obj, GreeksApp)
    w2 = desk._open_scene_window("options")          # ancienne scène plein écran
    assert w2 is w                                    # même fenêtre, pas de doublon


def test_greeks_strategy_payoff_and_models_tabs_draw(app):
    _with_positions(app)
    desk, w = _open(app, "greeks")
    ga = w.app_obj
    for strat in ("call", "put", "straddle", "strangle", "protective_put"):
        ga.strategy = strat
        ga._cache_key = None
        ga.draw(app.screen, RECT)
        assert ga._q is not None, strat
    ga.tab = "models"
    ga._cache_key = None
    ga.draw(app.screen, RECT)
    assert ga._models is not None
    assert len(ga._models["rows"]) == 5              # les 5 modèles de la photo


def test_greeks_execute_straddle_books_two_legs(app):
    _with_positions(app)
    desk, w = _open(app, "greeks")
    ga = w.app_obj
    ga.strategy = "straddle"
    ga.draw(app.screen, RECT)
    cash0 = app.gs.player.cash
    ga.handle_event(_click(ga._exec_btn.center), RECT)
    assert len(app.gs.player.options) == 2
    assert app.gs.player.cash < cash0
    ga.tab = "book"
    ga._cache_key = None
    ga.draw(app.screen, RECT)                        # feuille de grecques : ok
    assert len(ga._book["rows"]) == 2


def test_greeks_locked_below_grade(app):
    _with_positions(app)
    app.gs.player.grade_index = 0
    desk, w = _open(app, "greeks")
    ga = w.app_obj
    ga.draw(app.screen, RECT)
    ga.handle_event(_click(ga._exec_btn.center), RECT)
    assert not getattr(app.gs.player, "options", [])
    assert "verrouillées" in ga.msg


# ============================================================ Risque (VaR)
def test_vardesk_empty_book_message(app):
    desk, w = _open(app, "vardesk")
    w.app_obj.draw(app.screen, RECT)
    assert w.app_obj._sim is None


def test_vardesk_computes_var_components_and_backtest(app):
    _with_positions(app)
    desk, w = _open(app, "vardesk")
    va = w.app_obj
    va.draw(app.screen, RECT)
    assert va._sim is not None and va._sim["var"] > 0
    assert va._comp is not None and len(va._comp["lines"]) == 3
    assert va._bt is not None
    # bascule 99 % : la VaR augmente
    var95 = va._sim["var"]
    va.handle_event(_click(va._conf_rects[0.99].center), RECT)
    va.draw(app.screen, RECT)
    assert va._sim["var"] > var95


def test_vardesk_stress_link_opens_stresstest_window(app):
    _with_positions(app)
    desk, w = _open(app, "vardesk")
    va = w.app_obj
    va.draw(app.screen, RECT)
    va.handle_event(_click(va._stress_btn.center), RECT)
    assert any(win.key == "scene:stresstest" for win in desk.wm.windows)


# ================================================================ Desk Taux
def test_rates_curve_draws_even_with_empty_book(app):
    desk, w = _open(app, "rates")
    ra = w.app_obj
    ra.draw(app.screen, RECT)
    assert len(ra._curve) >= 3                        # la courbe existe toujours
    assert ra._table["lines"] == []


def test_rates_book_dv01_and_scenarios(app):
    p = app.gs.player
    quotes = sorted(B.sovereign_quotes(app.market), key=lambda q: q["years"])
    for q in (quotes[0], quotes[-1]):
        assert B.buy_bond(p, app.market, q["id"], 30)["ok"]
    desk, w = _open(app, "rates")
    ra = w.app_obj
    ra.draw(app.screen, RECT)
    assert len(ra._table["lines"]) == 2
    assert ra._table["totals"]["dv01"] > 0
    up = next(s for s in ra._table["scenarios"] if s["name"] == "+100 bp parallèle")
    assert up["pnl"] < 0


def test_rates_bonds_link_opens_bond_market(app):
    desk, w = _open(app, "rates")
    ra = w.app_obj
    ra.draw(app.screen, RECT)
    ra.handle_event(_click(ra._bonds_btn.center), RECT)
    assert any(win.key == "scene:bonds" for win in desk.wm.windows)


# ============================================================== câblage
def test_desk_icons_gated_by_unlocks(app):
    desk = app.scenes.current
    keys = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert {"greeks", "vardesk", "rates"} <= keys     # grade 9 : tout visible
    app.gs.player.grade_index = 0
    keys0 = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert "greeks" not in keys0                      # options : grade 6
    assert "rates" not in keys0                       # trade : grade 4
    assert "vardesk" in keys0                         # risk : grade 0
