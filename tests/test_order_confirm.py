"""
tests/test_order_confirm.py — Confirmation des ordres à fort impact
(core/order_confirm.py, seuil consommé par apps/app_trading.py) : un
achat/vente qui engage plus de 30% du patrimoine net suspend l'exécution
et demande une confirmation explicite au lieu de partir directement — une
faute de frappe sur la quantité (ex. un zéro de trop) ne doit jamais
s'exécuter sans qu'on la voie venir.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main
from apps.app_trading import TradingApp
from core import order_confirm
from core import portfolio_margin as pm_mod


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 100_000.0
    return a


def test_impact_ratio_pure_math(app):
    p = app.gs.player
    nw = pm_mod.net_worth(p, app.market)
    assert order_confirm.impact_ratio(p, app.market, nw * 0.5) == pytest.approx(0.5)
    assert order_confirm.impact_ratio(p, app.market, 0) == 0.0


def test_impact_ratio_is_zero_when_net_worth_not_positive(app):
    p = app.gs.player
    p.cash = 0.0
    p.portfolio = {}
    assert order_confirm.impact_ratio(p, app.market, 1000.0) == 0.0


def test_needs_confirmation_below_and_above_threshold(app):
    p = app.gs.player
    nw = pm_mod.net_worth(p, app.market)
    assert order_confirm.needs_confirmation(p, app.market, nw * 0.10) is False
    assert order_confirm.needs_confirmation(p, app.market, nw * 0.50) is True


def _qty_for_ratio(app, tk, ratio):
    price = app.market.price_of(tk)
    nw = pm_mod.net_worth(app.gs.player, app.market)
    return (nw * ratio) / price


def test_small_order_executes_immediately_without_confirmation(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_text = f"{_qty_for_ratio(app, tk, 0.05):g}"
    ta._do_buy(tk)
    assert ta._confirm_pending is None
    assert tk in app.gs.player.portfolio


def test_high_impact_buy_is_suspended_until_confirmed(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_text = f"{_qty_for_ratio(app, tk, 0.60):g}"
    ta._do_buy(tk)
    assert ta._confirm_pending is not None
    assert ta._confirm_pending["side"] == "buy"
    assert ta._confirm_pending["ticker"] == tk
    assert tk not in app.gs.player.portfolio   # PAS exécuté tant que non confirmé

    ta._confirm_pending_execute()
    assert ta._confirm_pending is None
    assert tk in app.gs.player.portfolio


def test_cancelling_a_high_impact_order_never_executes_it(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_text = f"{_qty_for_ratio(app, tk, 0.60):g}"
    ta._do_buy(tk)
    assert ta._confirm_pending is not None

    ta._confirm_pending_cancel()
    assert ta._confirm_pending is None
    assert tk not in app.gs.player.portfolio


def test_escape_key_cancels_pending_confirmation(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_text = f"{_qty_for_ratio(app, tk, 0.60):g}"
    ta._do_buy(tk)
    esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")
    ta.handle_event(esc, pygame.Rect(0, 0, 800, 500))
    assert ta._confirm_pending is None
    assert tk not in app.gs.player.portfolio


def test_enter_key_confirms_pending_confirmation(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_text = f"{_qty_for_ratio(app, tk, 0.60):g}"
    ta._do_buy(tk)
    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="")
    ta.handle_event(enter, pygame.Rect(0, 0, 800, 500))
    assert ta._confirm_pending is None
    assert tk in app.gs.player.portfolio


def test_high_impact_sell_is_also_suspended(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    qty = _qty_for_ratio(app, tk, 0.60)
    ta.qty_text = f"{qty:g}"
    ta._execute_buy(tk, qty)   # position en place, sans passer par la confirmation
    held_before = app.gs.player.portfolio[tk]["shares"]

    ta.qty_text = f"{held_before:g}"
    ta._do_sell(tk)
    assert ta._confirm_pending is not None
    assert ta._confirm_pending["side"] == "sell"
    assert app.gs.player.portfolio[tk]["shares"] == held_before   # pas encore vendu

    ta._confirm_pending_execute()
    assert tk not in app.gs.player.portfolio
