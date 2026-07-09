"""Tests de l'app native Explorateur de marché (apps/app_explorer.py) —
migration de scenes/scene_explorer.py hors de l'hébergement flou (netteté).
Même règle que Boutique/Fiche société : chaque ouverture RECONFIGURE la
fenêtre existante (recherche/filtres pré-remplis conservés entre la
Boutique et l'Explorateur)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from apps.app_explorer import ExplorerApp

pygame.font.init()

RECT = pygame.Rect(0, 0, 1120, 680)


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
    for _ in range(5):
        a.market.step()
    a.scenes.go("desktop")
    return a


def _open(app, **kwargs):
    desk = app.scenes.current
    w = desk._open_scene_window("explorer", **kwargs)
    return desk, w


def _click(pos, button=1):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=pos)


def test_explorer_is_native_app_not_hosted(app):
    desk, w = _open(app)
    assert w.key == "explorer" and isinstance(w.app_obj, ExplorerApp)
    assert not any(win.key == "scene:explorer" for win in desk.wm.windows)


def test_reopen_reconfigures_existing_window_no_duplicate(app):
    desk, w = _open(app)
    desk2, w2 = _open(app, search="MVC", type_filter="Action")
    assert w2 is w
    assert w.app_obj.search == "MVC" and w.app_obj.type_filter == "Action"
    assert sum(1 for win in desk.wm.windows if win.key == "explorer") == 1


def test_dataset_covers_every_asset_class(app):
    desk, w = _open(app)
    kinds = {r["kind"] for r in w.app_obj.rows}
    assert kinds >= {"Action", "ETF", "Obligation", "Commodity", "Crypto",
                     "FX", "Gouvernement"}


def test_draws_wide_and_narrow_without_crash(app):
    desk, w = _open(app)
    w.app_obj.draw(app.screen, RECT)
    w.app_obj.draw(app.screen, pygame.Rect(0, 0, 760, 480))


def test_type_filter_and_search_narrow_the_list(app):
    desk, w = _open(app)
    ex = w.app_obj
    ex.type_filter = "Action"
    assert all(r["kind"] == "Action" for r in ex._filtered_sorted())
    tk = app.market.top_companies(n=1)[0]["ticker"]
    ex.search = tk
    assert any(r["key"] == tk for r in ex._filtered_sorted())


def test_row_click_on_action_opens_company_popup(app):
    desk, w = _open(app)
    ex = w.app_obj
    ex.draw(app.screen, RECT)
    ident = next(i for i in ex._row_rects if i[0] == "Action")
    ex._handle_row_click(ident, 1)
    assert len(ex.popups) == 1


def test_right_click_quick_adds_to_watchlist(app):
    desk, w = _open(app)
    ex = w.app_obj
    tk = app.market.top_companies(n=1)[0]["ticker"]
    ex._handle_row_click(("Action", tk), 3)
    assert tk in app.gs.player.watchlist


def test_bulk_add_selection_to_watchlists(app):
    desk, w = _open(app)
    ex = w.app_obj
    tks = [c["ticker"] for c in app.market.top_companies(n=3)]
    ex.selected = {("Action", tk) for tk in tks}
    ex._bulk_add()
    assert all(tk in app.gs.player.watchlist for tk in tks)
    assert not ex.selected


def test_shop_button_keeps_search_and_filter_context(app):
    desk, w = _open(app, search="or", type_filter="Commodity")
    ex = w.app_obj
    ex.draw(app.screen, RECT)
    ex.handle_event(_click(ex._shop_rect.center), RECT)
    shop = next(win for win in desk.wm.windows if win.key == "shop")
    assert shop.app_obj.search == "or"


def test_fx_and_government_rows_open_dedicated_windows(app):
    desk, w = _open(app)
    ex = w.app_obj
    fx_ident = next((r["kind"], r["key"]) for r in ex.rows if r["kind"] == "FX")
    ex._handle_row_click(fx_ident, 1)
    assert any(win.key == "scene:fx" for win in desk.wm.windows)
    gov_ident = next((r["kind"], r["key"]) for r in ex.rows if r["kind"] == "Gouvernement")
    ex._handle_row_click(gov_ident, 1)
    assert any(win.key == "scene:governments" for win in desk.wm.windows)


def test_explorer_is_factory_only_single_icon_via_quick_apps(app):
    desk = app.scenes.current
    labels = [lbl for _k, lbl, _kind, _acc in desk._icon_list()]
    assert labels.count("Explorateur") == 1
