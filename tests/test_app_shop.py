"""Tests de l'app native Boutique (apps/app_shop.py) — migration de
scenes/scene_shop.py hors de l'hébergement flou (netteté), le guichet
unique pour acheter n'importe quel actif. Vérifie l'ouverture, la
reconfiguration (recherche/filtre) à chaque appel, l'achat/vente toutes
classes, les popups de fiche, et les liens vers les scènes dédiées."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from apps.app_shop import ShopApp

pygame.font.init()

RECT = pygame.Rect(0, 0, 1100, 680)


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 5
    p.cash = 500_000.0
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
    w = desk._open_scene_window("shop", **kwargs)
    return desk, w


def test_shop_is_native_app_not_hosted(app):
    desk, w = _open(app)
    assert w.key == "shop" and isinstance(w.app_obj, ShopApp)


def test_shop_is_factory_only_no_duplicate_icon(app):
    """"shop" a déjà son icône via QUICK_APPS ("qshop") — pas de doublon."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    keys = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert "shop" not in keys
    assert "qshop" in keys


def test_reopen_reconfigures_search_and_filter(app):
    desk, w1 = _open(app, search="MVC")
    assert w1.app_obj.search == "MVC"
    w2 = desk._open_scene_window("shop", type_filter="Crypto")
    assert w2 is w1
    assert w2.app_obj.type_filter == "Crypto"
    assert w2.app_obj.search == ""   # reconfiguré, pas préservé


def test_catalogue_includes_all_asset_classes(app):
    desk, w = _open(app)
    shop = w.app_obj
    kinds = {r["kind"] for r in shop.rows}
    assert kinds == {"Action", "ETF", "Obligation", "Commodity", "Crypto", "Structuré", "Crédit"}


def test_buy_action_via_button(app):
    desk, w = _open(app)
    shop = w.app_obj
    tk = app.market.top_companies(n=1)[0]["ticker"]
    shop.type_filter = "Action"
    shop.search = tk
    shop.qty_text = "5"
    shop.draw(app.screen, RECT)
    ident = ("Action", tk)
    assert ident in shop._buy_rects
    shop.handle_event(_click(*shop._buy_rects[ident].center), RECT)
    assert app.gs.player.portfolio.get(tk, {}).get("shares") == 5


def test_sell_action_via_button(app):
    from core import portfolio as PF
    desk, w = _open(app)
    shop = w.app_obj
    tk = app.market.top_companies(n=1)[0]["ticker"]
    PF.buy(app.gs.player, app.market, tk, 10)
    shop.refresh_data()
    shop.type_filter = "Action"
    shop.search = tk
    shop.qty_text = "4"
    shop.draw(app.screen, RECT)
    ident = ("Action", tk)
    assert ident in shop._sell_rects
    shop.handle_event(_click(*shop._sell_rects[ident].center), RECT)
    assert app.gs.player.portfolio[tk]["shares"] == 6


def test_name_click_opens_company_popup(app):
    desk, w = _open(app)
    shop = w.app_obj
    tk = app.market.top_companies(n=1)[0]["ticker"]
    shop.type_filter = "Action"
    shop.search = tk
    shop.draw(app.screen, RECT)
    ident = ("Action", tk)
    assert ident in shop._name_rects
    shop.handle_event(_click(*shop._name_rects[ident].center), RECT)
    assert len(shop.popups) == 1


def test_type_and_sub_filters(app):
    desk, w = _open(app)
    shop = w.app_obj
    shop.draw(app.screen, RECT)
    shop.handle_event(_click(*shop._type_rects["Crypto"].center), RECT)
    assert shop.type_filter == "Crypto"
    shop.draw(app.screen, RECT)
    rows = shop._filtered_sorted()
    assert all(r["kind"] == "Crypto" for r in rows)


def test_scene_link_opens_hosted_window(app):
    desk, w = _open(app)
    shop = w.app_obj
    shop.draw(app.screen, RECT)
    shop.handle_event(_click(*shop._scene_link_rects["bonds"].center), RECT)
    assert any(win.key == "scene:bonds" for win in desk.wm.windows)


def test_search_pastes_via_ctrl_v(app, monkeypatch):
    from core import clipboard
    monkeypatch.setattr(clipboard, "paste", lambda: "MVC")
    desk, w = _open(app)
    shop = w.app_obj
    shop.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v,
                                          unicode="v", mod=pygame.KMOD_CTRL), RECT)
    assert shop.search == "MVC"


def test_narrow_window_draws_without_crash(app):
    desk, w = _open(app)
    shop = w.app_obj
    shop.draw(app.screen, pygame.Rect(0, 0, 720, 460))


def test_no_trade_below_unlock_grade(app):
    app.gs.player.grade_index = 0
    desk, w = _open(app)
    shop = w.app_obj
    shop.draw(app.screen, RECT)   # message de verrouillage, sans exception
    assert not shop._buy_rects
