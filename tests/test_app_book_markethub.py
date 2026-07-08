"""Tests des apps natives Portefeuille (apps/app_book.py) et Marché
(apps/app_markethub.py) — migration depuis scenes/scene_book.py et
scenes/scene_markethub.py (rendu hébergé 1280×720 réduit par smoothscale →
flou) vers un dessin à la résolution de la fenêtre, cf. la même migration
faite pour Inbox/Alertes. Vérifie l'ouverture via le bureau, le dessin sans
exception dans toutes ses variantes (onglets du hub Marché, achat/vente du
Portefeuille, popups flottants), et que ces deux apps sont bien enregistrées
comme apps NATIVES (pas hébergées) — la régression corrigée dans la même
série (Inbox/Alertes/Portefeuille/Marché ne remettaient pas `start_open` à
False si ouvertes depuis le menu Démarrer) est couverte dans test_desktop.py.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from apps.app_book import BookApp
from apps.app_markethub import MarketHubApp
from core import portfolio as pf

pygame.font.init()


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.reputation = 80
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    for _ in range(30):
        a.market.step()
    return a


def test_book_and_markethub_are_native_apps_not_hosted(app):
    """Ouvrir "book"/"markethub" en fenêtre lance l'app NATIVE — plus
    d'hébergement flou de la scène plein écran (clé sans préfixe "scene:")."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    w1 = desk._open_scene_window("book")
    w2 = desk._open_scene_window("markethub")
    assert w1.key == "book" and isinstance(w1.app_obj, BookApp)
    assert w2.key == "markethub" and isinstance(w2.app_obj, MarketHubApp)


# --------------------------------------------------------------------- Book
def test_book_draws_with_and_without_positions(app):
    w = BookApp(app)
    w.on_open()
    rect = pygame.Rect(20, 20, 900, 560)
    surf = pygame.Surface((1280, 720))
    w.draw(surf, rect)   # sans positions
    tk = app.market.companies[0]["ticker"]
    pf.buy(app.gs.player, app.market, tk, 15)
    tk2 = app.market.companies[1]["ticker"]
    pf.short(app.gs.player, app.market, tk2, 5)
    w.update(0.05)
    w.draw(surf, rect)   # long + short : ne doit pas lever
    assert w._name_rects   # au moins une ligne de position cliquable


def test_book_narrow_window_stacks_side_panel_below_table(app):
    """Sous ~340px de table, le panneau latéral passe SOUS la table plutôt
    qu'à côté (cf. draw() — fenêtre trop étroite pour 2 colonnes)."""
    w = BookApp(app)
    w.on_open()
    rect = pygame.Rect(0, 0, 760, 500)   # min_size de l'app, cas limite
    surf = pygame.Surface((1280, 720))
    w.draw(surf, rect)   # ne doit pas lever même à la taille minimale


def test_book_quick_trade_buy_and_sell(app):
    w = BookApp(app)
    w.on_open()
    tk = app.market.companies[0]["ticker"]
    w.trade_kind = "Action"
    w.trade_key = tk
    w.qty_text = "10"
    w._do_buy()
    assert app.gs.player.portfolio.get(tk, {}).get("shares") == 10
    w.qty_text = "4"
    w._do_sell()
    assert app.gs.player.portfolio[tk]["shares"] == 6


def test_book_click_analyse_and_shop_buttons_route_via_desktop(app, monkeypatch):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("book")
    book = w.app_obj
    rect = pygame.Rect(20, 20, 900, 560)
    book.draw(app.screen, rect)
    opened = []
    monkeypatch.setattr(desk, "_open_scene_window", lambda name, **kw: opened.append(name))
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=book._pa_btn.center)
    assert book.handle_event(ev, rect) is True
    ev2 = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=book._shop_btn.center)
    assert book.handle_event(ev2, rect) is True
    assert opened == ["analytics", "shop"]


def test_book_popup_uses_window_relative_position(app):
    """Les fiches d'analyse (PopupMixin) s'ouvrent près de LA FENÊTRE, pas à
    une position fixe de l'écran entier (cf. _popup_pos surchargée)."""
    w = BookApp(app)
    w.on_open()
    w._last_rect = pygame.Rect(500, 300, 900, 560)
    tk = app.market.companies[0]["ticker"]
    w.open_company(tk)
    assert len(w.popups) == 1
    pos = w.popups[0].rect.topleft
    assert abs(pos[0] - 530) < 5 and abs(pos[1] - 330) < 5


# ---------------------------------------------------------------- MarketHub
@pytest.mark.parametrize("tab", ["overview", "sectors", "topflop", "heatmap", "fx", "watchlist"])
def test_markethub_draws_every_tab_without_crashing(app, tab):
    w = MarketHubApp(app)
    w.on_open()
    w.tab = tab
    app.gs.player.watchlist = [app.market.companies[0]["ticker"]]
    rect = pygame.Rect(0, 0, 980, 620)
    surf = pygame.Surface((1280, 720))
    w.draw(surf, rect)   # ne doit pas lever, y compris avec un historique réel


def test_markethub_click_index_row_opens_popup(app):
    w = MarketHubApp(app)
    w.on_open()
    rect = pygame.Rect(0, 0, 980, 620)
    surf = pygame.Surface((1280, 720))
    w.draw(surf, rect)
    assert w._index_row_rects
    name, r = next(iter(w._index_row_rects.items()))
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=r.center)
    assert w.handle_event(ev, rect) is True
    assert len(w.popups) == 1
    w.draw(surf, rect)   # le popup (>= 2 points d'historique réel) doit se dessiner sans lever


def test_markethub_ticker_click_opens_company_via_desktop(app, monkeypatch):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("markethub")
    mh = w.app_obj
    rect = pygame.Rect(0, 0, 980, 620)
    mh.draw(app.screen, rect)
    assert mh._ticker_rects
    tk, r = next(iter(mh._ticker_rects.items()))
    opened = []
    monkeypatch.setattr(desk, "_open_scene_window", lambda name, **kw: opened.append((name, kw)))
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=r.center)
    assert mh.handle_event(ev, rect) is True
    assert opened == [("company", {"ticker": tk})]


def test_markethub_narrow_window_does_not_crash(app):
    w = MarketHubApp(app)
    w.on_open()
    rect = pygame.Rect(0, 0, 620, 420)   # min_size de l'app
    surf = pygame.Surface((1280, 720))
    for tab in ("overview", "sectors", "topflop", "heatmap", "fx", "watchlist"):
        w.tab = tab
        w.draw(surf, rect)
