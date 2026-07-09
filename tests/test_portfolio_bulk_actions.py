"""Tests des actions de portefeuille en un geste (core/portfolio.py) :
rééquilibrage à poids égaux (factorisé depuis la commande REBALANCE) et
liquidation toutes classes (bouton « TOUT VENDRE » du Portefeuille, derrière
une confirmation) — plus leurs boutons dans apps/app_book.py."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from core import etfs as ETF
from core import portfolio as pf
from core.game_state import PlayerState
from core.market import Market

pygame.font.init()

RECT = pygame.Rect(0, 0, 980, 600)


def _player(cash=1_000_000.0):
    p = PlayerState()
    p.cash = cash
    p.grade_index = 9
    return p


# ------------------------------------------------------ rebalance (pur)
def test_rebalance_needs_two_positions():
    m = Market(seed=3)
    p = _player()
    assert pf.rebalance_equal_weights(p, m)["ok"] is False
    tk = m.companies[0]["ticker"]
    pf.buy(p, m, tk, 10)
    assert pf.rebalance_equal_weights(p, m)["ok"] is False


def test_rebalance_equalises_weights():
    m = Market(seed=3)
    p = _player()
    tk1, tk2 = m.companies[0]["ticker"], m.companies[1]["ticker"]
    pf.buy(p, m, tk1, 200)
    pf.buy(p, m, tk2, 10)
    r = pf.rebalance_equal_weights(p, m)
    assert r["ok"] is True
    v1 = p.portfolio[tk1]["shares"] * m.price_of(tk1)
    v2 = p.portfolio[tk2]["shares"] * m.price_of(tk2)
    # poids ~égaux à un titre entier près (l'arrondi int() empêche l'exact)
    assert abs(v1 - v2) / max(v1, v2) < 0.2


# --------------------------------------------------- liquidate_all (pur)
def test_liquidate_all_closes_longs_shorts_and_other_classes():
    m = Market(seed=3)
    p = _player()
    tk1, tk2 = m.companies[0]["ticker"], m.companies[1]["ticker"]
    pf.buy(p, m, tk1, 20)
    pf.short(p, m, tk2, 5)
    etf_id = ETF.all_quotes(m)[0]["id"]
    ETF.buy(p, m, etf_id, 3)
    assert p.portfolio and p.etfs

    r = pf.liquidate_all(p, m)
    assert r["closed"] >= 3
    assert p.portfolio == {}
    assert not p.etfs


def test_liquidate_all_empty_portfolio_is_noop():
    m = Market(seed=3)
    p = _player()
    r = pf.liquidate_all(p, m)
    assert r == {"closed": 0, "realized": 0.0}


# ------------------------------------------------------------ UI (BookApp)
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
    a.scenes.go("desktop")
    return a


def _click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def _book(app):
    desk = app.scenes.current
    w = desk._open_scene_window("book")
    return w.app_obj


def test_book_rebalance_button(app):
    book = _book(app)
    p = app.gs.player
    tk1, tk2 = (c["ticker"] for c in app.market.top_companies(n=2))
    pf.buy(p, app.market, tk1, 100)
    pf.buy(p, app.market, tk2, 5)
    book.draw(app.screen, RECT)
    assert book._rebalance_btn is not None
    book.handle_event(_click(book._rebalance_btn.center), RECT)
    assert "rééquilibré" in book.msg


def test_book_liquidate_requires_confirmation(app):
    book = _book(app)
    p = app.gs.player
    tk = app.market.top_companies(n=1)[0]["ticker"]
    pf.buy(p, app.market, tk, 10)
    book.draw(app.screen, RECT)
    book.handle_event(_click(book._liq_btn.center), RECT)
    assert book._liq_confirm is True
    assert p.portfolio          # rien liquidé sur le simple clic
    book.draw(app.screen, RECT)  # modale sans exception
    book.handle_event(_click(book._liq_yes_rect.center), RECT)
    assert book._liq_confirm is False
    assert p.portfolio == {}
    assert "liquidée" in book.msg


def test_book_liquidate_cancel_keeps_positions(app):
    book = _book(app)
    p = app.gs.player
    tk = app.market.top_companies(n=1)[0]["ticker"]
    pf.buy(p, app.market, tk, 10)
    book.draw(app.screen, RECT)
    book.handle_event(_click(book._liq_btn.center), RECT)
    book.draw(app.screen, RECT)
    book.handle_event(_click(book._liq_no_rect.center), RECT)
    assert book._liq_confirm is False
    assert p.portfolio


def test_book_liquidate_escape_cancels(app):
    book = _book(app)
    book._liq_confirm = True
    book.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE,
                                          unicode="", mod=0), RECT)
    assert book._liq_confirm is False
