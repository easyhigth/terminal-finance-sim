"""Tests de l'app Backtester du bureau (apps/app_backtester.py) : sélection
de titre (chips + recherche), sélection de stratégie, calcul via
core/backtester, recalcul au pas de marché, dessin sans crash."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from core import portfolio as pf

pygame.font.init()

RECT = pygame.Rect(0, 0, 960, 600)


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


def _open(app):
    desk = app.scenes.current
    w = desk._open_scene_window("backtester")
    return w.app_obj


def test_backtester_opens_with_default_ticker_and_computes(app):
    bt_app = _open(app)
    bt_app.draw(app.screen, RECT)
    assert bt_app.ticker is not None
    assert bt_app._res is not None
    assert "total_return" in bt_app._res


def test_backtester_recomputes_when_market_steps(app):
    bt_app = _open(app)
    bt_app.draw(app.screen, RECT)
    key1 = bt_app._cache_key
    app.market.step()
    bt_app.draw(app.screen, RECT)
    assert bt_app._cache_key != key1


def test_backtester_strategy_buttons_switch_strategy(app):
    bt_app = _open(app)
    bt_app.draw(app.screen, RECT)
    momentum_rect = bt_app._strategy_rects["momentum"]
    bt_app.handle_event(_click(momentum_rect.center))
    assert bt_app.strategy == "momentum"
    bt_app.draw(app.screen, RECT)
    assert bt_app._res is not None


def test_backtester_chip_click_changes_ticker(app):
    tks = [c["ticker"] for c in app.market.top_companies(n=3)]
    for tk in tks:
        assert pf.buy(app.gs.player, app.market, tk, 10)["ok"]
    bt_app = _open(app)
    bt_app.draw(app.screen, RECT)
    other = next(tk for tk in bt_app._chip_rects if tk != bt_app.ticker)
    bt_app.handle_event(_click(bt_app._chip_rects[other].center))
    assert bt_app.ticker == other


def test_backtester_search_selects_ticker_and_rejects_unknown(app):
    bt_app = _open(app)
    bt_app.draw(app.screen, RECT)
    tk = app.market.top_companies(n=1)[0]["ticker"]
    bt_app.handle_event(_click(bt_app._search_rect.center))
    assert bt_app._search_active
    for ch in tk:
        bt_app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=ch))
    bt_app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode=""))
    assert bt_app.ticker == tk
    assert not bt_app._search_active

    bt_app.handle_event(_click(bt_app._search_rect.center))
    for ch in "NOTATICKER":
        bt_app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=ch))
    bt_app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode=""))
    assert "inconnu" in bt_app.msg.lower()


def test_backtester_draws_without_crash_for_every_strategy(app):
    bt_app = _open(app)
    from core import backtester as BT
    for strat in BT.STRATEGIES:
        bt_app.strategy = strat
        bt_app._cache_key = None
        bt_app.draw(app.screen, RECT)
