"""
tests/test_desktop.py — Bureau « Jeu PC » (étape 1) : gestionnaire de fenêtres,
applications (recherche/trading/tableur) et avance du temps depuis le bureau.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main
from apps.app_research import ResearchApp
from apps.app_sheet import SheetApp
from apps.app_trading import TradingApp
from ui.window_manager import TITLE_H, WindowManager


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.reputation = 80
    return a


def _click(x, y, button=1):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=(x, y))


# ------------------------------------------------------------- window manager
def test_open_focus_and_close(app):
    wm = WindowManager(app)
    w1 = wm.open("a", lambda: ResearchApp(app))
    w2 = wm.open("b", lambda: SheetApp(app))
    assert wm.focused is w2                       # dernière ouverte = au premier plan
    wm.focus(w1)
    assert wm.focused is w1
    # ré-ouvrir une clé existante ne crée pas de doublon, la ramène au premier plan
    again = wm.open("b", lambda: SheetApp(app))
    assert again is w2 and len(wm.windows) == 2
    wm.close(w2)
    assert len(wm.windows) == 1 and wm.focused is w1


def test_minimize_hides_from_focus(app):
    wm = WindowManager(app)
    w = wm.open("a", lambda: ResearchApp(app))
    wm.toggle_minimize(w)
    assert w.minimized and wm.focused is None
    assert wm.open_windows() == []


def test_titlebar_drag_moves_window(app):
    wm = WindowManager(app)
    w = wm.open("a", lambda: SheetApp(app), x=100, y=100)
    start = w.rect.topleft
    wm.handle_event(_click(w.title_rect.centerx, w.title_rect.centery))
    wm.handle_event(pygame.event.Event(pygame.MOUSEMOTION,
                                       pos=(w.title_rect.centerx + 40, w.title_rect.centery + 30)))
    wm.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1,
                                       pos=(w.title_rect.centerx + 40, w.title_rect.centery + 30)))
    assert w.rect.topleft != start
    assert w.rect.x == start[0] + 40 and w.rect.y == start[1] + 30


def test_close_button_click_closes(app):
    wm = WindowManager(app)
    w = wm.open("a", lambda: SheetApp(app))
    wm.handle_event(_click(w.close_rect.centerx, w.close_rect.centery))
    assert w not in wm.windows


# ------------------------------------------------------------------- apps
def test_trading_app_buys(app):
    tk = app.market.companies[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_text = "3"
    ta._do_buy(tk)
    assert tk in app.gs.player.portfolio
    assert app.gs.player.portfolio[tk]["shares"] >= 3


def test_sheet_app_shares_workbook_and_computes(app):
    sa = SheetApp(app)
    sa.on_open()
    sa.sheet.set("A1", "2")
    sa.sheet.set("A2", "3")
    sa.sheet.set("A3", "=A1+A2")
    assert sa.sheet.get_value("A3") == 5
    # partage le classeur avec app.sheet
    assert app.sheet is sa.sheet


def test_research_app_selects_and_draws(app):
    ra = ResearchApp(app)
    ra.on_open()
    assert ra.sel is not None
    rect = pygame.Rect(0, 0, 820, 520)
    ra.draw(app.screen, rect)          # ne doit pas lever
    # clic sur une ligne sélectionne
    ra.draw(app.screen, rect)
    if ra._row_rects:
        tk, r = next(iter(ra._row_rects.items()))
        ra.handle_event(_click(r.centerx, r.centery), rect)
        assert ra.sel == tk


# ------------------------------------------------------- avance du temps
def test_desktop_drains_market_steps(app):
    # le terminal doit être initialisé (moteur de la boucle de jeu)
    app.scenes.go("terminal")
    app.scenes.current.update(0.016)
    app.scenes.go("desktop")
    desk = app.scenes.current
    step_before = app.market.step_count
    app.pending_market_steps = 2
    desk.update(0.016)
    assert app.market.step_count >= step_before + 1
    assert app.pending_market_steps < 2


def test_desktop_launch_opens_windows(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    for key in ("research", "trading", "sheet"):
        desk._launch(key)
    assert len(desk.wm.windows) == 3
    desk.update(0.016)
    desk.draw(app.screen)


# --------------------------------------------------- scènes hébergées (étape 2)
def test_scene_host_wraps_and_draws(app):
    from apps.scene_host import SceneHostApp
    host = SceneHostApp(app, "risk", "Risque")
    host.bind_opener(lambda name, **kw: None)
    host.on_open()
    rect = pygame.Rect(60, 60, 900, 540)
    host.update(0.016)
    host.draw(app.screen, rect)          # offscreen + smoothscale, ne doit pas lever
    # un clic (coordonnées fenêtre) est transformé en espace logique
    host.handle_event(_click(rect.centerx, rect.centery), rect)


def test_scene_host_navigation_opens_window_not_switch(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    # ouvre une scène hébergée via le menu Démarrer
    w = desk._open_scene_window("markethub")
    assert any(win.key == "scene:markethub" for win in desk.wm.windows)
    # la navigation interne de la scène ouvre une AUTRE fenêtre (routeur)
    w.app_obj.router.go("bonds")
    assert any(win.key == "scene:bonds" for win in desk.wm.windows)
    # le bureau reste la scène courante (pas de bascule plein écran)
    assert app.scenes.current_name == "desktop"


def test_desktop_launcher_lists_scenes(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.start_open = True
    desk.draw(app.screen)
    assert len(desk._launcher_rects) > 20      # toutes les scènes du hub PLUS
    # ouvrir un item par clic
    r, scene, kw = desk._launcher_rects[0]
    desk.handle_event(_click(r.centerx, r.centery))
    assert any(win.key == f"scene:{scene}" for win in desk.wm.windows)


def test_every_launcher_scene_hosts_without_error(app):
    """Chaque scène du menu Démarrer doit pouvoir être hébergée en fenêtre
    (on_enter + update + draw + un clic) sans lever d'exception."""
    from scenes.scene_more import SECTIONS
    app.scenes.go("desktop")
    desk = app.scenes.current
    names = {scene for _t, items in SECTIONS for _l, scene, _kw in items}
    for name in sorted(names):
        w = desk._open_scene_window(name)
        assert w is not None, name
        w.app_obj.update(0.016)
        rect = pygame.Rect(50, 50, 900, 540)
        w.app_obj.draw(app.screen, rect)
        w.app_obj.handle_event(_click(rect.centerx, rect.centery), rect)
        w.app_obj.draw(app.screen, rect)
        desk.wm.close(w)


def test_ticker_scenes_get_default_asset(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("company")   # sans ticker -> défaut fourni
    assert w is not None
    assert "ticker" in w.app_obj._kwargs
