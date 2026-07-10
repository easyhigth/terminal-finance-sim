"""Tests de l'app Valorisation (DCF/SML/LBO) + panneau Kelly du Journal +
devis d'impact dans la boîte TWAP du Trading."""
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
    for _ in range(80):
        a.market.step()
    a.scenes.go("desktop")
    return a


def _click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def _open(app, key):
    desk = app.scenes.current
    return desk, desk._open_scene_window(key)


def test_valuation_all_tabs_draw(app):
    desk, w = _open(app, "valuation")
    va = w.app_obj
    va.draw(app.screen, RECT)                          # DCF
    va.tab = "sml"
    va._cache_key = None
    va.draw(app.screen, RECT)
    assert va._sml is not None and len(va._sml["rows"]) > 100
    va.tab = "lbo"
    va._cache_key = None
    va.draw(app.screen, RECT)
    assert va._bridge is not None


def test_valuation_wacc_buttons_change_value(app):
    desk, w = _open(app, "valuation")
    va = w.app_obj
    va.draw(app.screen, RECT)
    if va._dcf is None:
        pytest.skip("ticker par défaut non DCF-able")
    v0 = va._dcf["per_share"]
    va.handle_event(_click(va._adj_rects["wacc+"].center), RECT)
    va.draw(app.screen, RECT)
    assert va._dcf["per_share"] < v0                   # WACC ↑ ⇒ valeur ↓


def test_valuation_sml_row_click_switches_to_dcf(app):
    desk, w = _open(app, "valuation")
    va = w.app_obj
    va.tab = "sml"
    va._cache_key = None
    va.draw(app.screen, RECT)
    tk, r = next(iter(va._sml_rows_rects.items()))
    va.handle_event(_click(r.center), RECT)
    assert va.tab == "dcf" and va.ticker == tk


def test_valuation_lbo_sliders_move_bridge(app):
    desk, w = _open(app, "valuation")
    va = w.app_obj
    va.tab = "lbo"
    va._cache_key = None
    va.draw(app.screen, RECT)
    moic0 = va._bridge["moic"]
    va.handle_event(_click(va._adj_rects["lbo:debt_pct:+"].center), RECT)
    va.draw(app.screen, RECT)
    assert va._bridge["moic"] > moic0                  # plus de levier, plus de MOIC


def test_journal_kelly_panel_draws_with_history(app):
    import core.journal as J
    p = app.gs.player
    tk = app.market.top_companies(n=1)[0]["ticker"]
    for i in range(12):
        pf.buy(p, app.market, tk, 10)
        app.market.step()
        pf.sell(p, app.market, tk, 10)
    desk, w = _open(app, "tradejournal")
    w.app_obj.draw(app.screen, pygame.Rect(0, 0, 1100, 640))   # panneau Kelly : ok


def test_trading_twap_prompt_shows_impact_estimate(app):
    from core import orders as ORD
    tk = app.market.top_companies(n=1)[0]["ticker"]
    est = ORD.compare_cost(app.market, tk, 20_000, "buy", 8)
    assert est and est["savings"] > 0
    desk, w = _open(app, "trading")
    tr = w.app_obj
    tr._open_twap_prompt(tk, "buy")
    tr.draw(app.screen, RECT)                          # boîte avec devis : ok


def test_valuation_icon_gated_by_trade(app):
    desk = app.scenes.current
    keys = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert "valuation" in keys
    app.gs.player.grade_index = 0
    keys0 = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert "valuation" not in keys0
