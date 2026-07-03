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
    from core import desktop_onboarding
    desktop_onboarding.mark_seen()   # neutralise la carte d'accueil (1re visite)
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


def test_internal_popup_drag_releases_on_mouseup_not_stuck_to_cursor(app):
    """Régression : un popup (DataWindow) glissé À L'INTÉRIEUR d'une scène
    hébergée (ex. fiche société ouverte depuis le terminal) doit se détacher
    du curseur au relâchement de la souris. Avant correctif, WindowManager ne
    transmettait MOUSEBUTTONUP à l'appli focalisée QUE si le WindowManager
    lui-même draguait la fenêtre OS — un drag interne à l'appli ne recevait
    donc jamais le relâchement et restait collé au curseur indéfiniment."""
    from apps.scene_host import SceneHostApp
    app.scenes.go("terminal")
    wm = WindowManager(app)
    host = SceneHostApp(app, "terminal", "Terminal", {})
    w = wm.open("scene:terminal", lambda: host)
    w.rect = pygame.Rect(0, 40, 1180, 620)
    host.on_open()
    term = host.scene
    tk = app.market.top_companies(n=1)[0]["ticker"]
    term._open_company_popup(tk)
    popup = term.datawins[0]

    def to_screen(logical_pos):
        lx, ly = logical_pos
        r = w.content_rect
        return (int(r.x + lx * r.w / 1280), int(r.y + ly * r.h / 720))

    title_screen = to_screen((popup.rect.x + 10, popup.rect.y + 5))
    wm.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=title_screen))
    assert popup.dragging is True

    moved_screen = to_screen((popup.rect.x + 80, popup.rect.y + 60))
    wm.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=moved_screen))
    assert popup.dragging is True   # toujours en cours de glisser

    wm.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=moved_screen))
    assert popup.dragging is False   # relâché : ne doit plus suivre la souris

    # une nouvelle motion, sans nouveau clic, ne doit plus bouger le popup
    rect_after_release = popup.rect.copy()
    wm.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=to_screen((200, 200))))
    assert popup.rect == rect_after_release


def test_internal_calculator_drag_releases_on_mouseup(app):
    """Même régression que ci-dessus, pour la calculatrice flottante des
    scènes mission/évaluation (ui/calculator.py, même patron de glisser)."""
    from apps.scene_host import SceneHostApp
    from ui.calculator import Calculator
    app.gs.player.grade_index = 3
    app.scenes.go("terminal")
    wm = WindowManager(app)
    host = SceneHostApp(app, "mission", "Mission", {})
    w = wm.open("scene:mission", lambda: host)
    w.rect = pygame.Rect(0, 40, 1180, 620)
    host.on_open()
    mission = host.scene
    mission.calc = Calculator(pos=(500, 110))
    calc = mission.calc

    def to_screen(logical_pos):
        lx, ly = logical_pos
        r = w.content_rect
        return (int(r.x + lx * r.w / 1280), int(r.y + ly * r.h / 720))

    title_screen = to_screen((calc.rect.x + 10, calc.rect.y + 5))
    wm.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=title_screen))
    assert calc.dragging is True

    moved_screen = to_screen((calc.rect.x + 50, calc.rect.y + 40))
    wm.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=moved_screen))
    wm.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=moved_screen))
    assert calc.dragging is False


def test_internal_shortcuts_panel_drag_releases_on_mouseup(app):
    """Même régression, pour le panneau de raccourcis clavier (ui/shortcutspanel
    .py) ouvert DEPUIS le terminal hébergé — même mécanisme de glisser interne."""
    from apps.scene_host import SceneHostApp
    app.scenes.go("terminal")
    wm = WindowManager(app)
    host = SceneHostApp(app, "terminal", "Terminal", {})
    w = wm.open("scene:terminal", lambda: host)
    w.rect = pygame.Rect(0, 40, 1180, 620)
    host.on_open()
    term = host.scene
    term._toggle_shortcuts_panel()
    panel = term.shortcuts_panel

    def to_screen(logical_pos):
        lx, ly = logical_pos
        r = w.content_rect
        return (int(r.x + lx * r.w / 1280), int(r.y + ly * r.h / 720))

    title_screen = to_screen((panel.rect.x + 10, panel.rect.y + 5))
    wm.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=title_screen))
    assert panel.dragging is True

    moved_screen = to_screen((panel.rect.x + 40, panel.rect.y + 30))
    wm.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=moved_screen))
    wm.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=moved_screen))
    assert panel.dragging is False


def test_internal_sheet_chart_drag_releases_on_mouseup_via_window_manager(app):
    """Même régression, pour un graphique inséré dans le Tableur (app native,
    pas une scène hébergée) — passe par le VRAI WindowManager cette fois
    (les autres tests sheet_app_drag_chart_* appellent handle_event directement
    sur l'app, sans passer par le routage du WindowManager)."""
    wm = WindowManager(app)
    w = wm.open("sheet", lambda: SheetApp(app))
    w.rect = pygame.Rect(0, 40, 940, 560)
    sa = w.app_obj
    sa.on_open()
    for i, v in enumerate((1, 2, 3), start=1):
        sa.sheet.set(f"A{i}", str(v))
    sa.range_anchor, sa.range_end = "A1", "A3"
    sa._add_chart("line")
    sa.draw(app.screen, w.content_rect)
    chart = sa.workbook.active.charts[0]
    title_r = sa._chart_title_rects[chart.id]
    x0, y0 = chart.x, chart.y

    wm.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=title_r.center))
    new_pos = (title_r.centerx + 40, title_r.centery + 30)
    wm.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=new_pos, buttons=(1, 0, 0)))
    assert (chart.x, chart.y) != (x0, y0)   # a suivi la souris pendant le glisser
    moved_after_up = (chart.x, chart.y)
    wm.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=new_pos))
    # une motion supplémentaire, sans nouveau clic, ne doit plus bouger le graphique
    wm.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(200, 200), buttons=(0, 0, 0)))
    assert (chart.x, chart.y) == moved_after_up


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
    # partage le classeur avec app.workbook
    assert app.workbook is sa.workbook


def test_sheet_app_import_fills_blank_then_new_tab(app):
    sa = SheetApp(app)
    sa.on_open()
    assert len(sa.workbook.tabs) == 1
    data = {"title": "ACME — Compte de résultat", "years": [2024, 2023],
            "rows": [("Chiffre d'affaires", [100.0, 90.0])]}
    sa.import_data(data)
    assert len(sa.workbook.tabs) == 1          # feuille vierge -> remplie sur place
    assert sa.sheet.get_raw("A3") == "Chiffre d'affaires"
    # un second export (feuille désormais non vierge) ouvre une NOUVELLE feuille
    data2 = {"title": "BETA — Bilan", "years": [2024],
             "rows": [("Trésorerie", [50.0])]}
    sa.import_data(data2)
    assert len(sa.workbook.tabs) == 2
    assert sa.workbook.active_index == 1
    assert sa.sheet.get_raw("A3") == "Trésorerie"
    # la première feuille reste intacte
    assert sa.workbook.tabs[0].sheet.get_raw("A3") == "Chiffre d'affaires"


# ----------------------------------------------- tableur "façon Excel" (fx, plages, graphes)
def test_sheet_app_fx_picker_inserts_function(app):
    sa = SheetApp(app)
    sa.on_open()
    sa._insert_function("NPV")
    assert sa.editing is True
    assert sa.edit_buf == "=NPV("
    assert sa.fx_open is False


def test_sheet_app_fx_picker_appends_to_existing_formula(app):
    sa = SheetApp(app)
    sa.on_open()
    sa.editing = True
    sa.edit_buf = "=ROUND("
    sa._insert_function("AVERAGE")
    assert sa.edit_buf == "=ROUND(AVERAGE("


def test_sheet_app_range_drag_selection(app):
    sa = SheetApp(app)
    sa.on_open()
    rect = pygame.Rect(0, 0, 900, 600)
    sa.draw(app.screen, rect)   # peuple _cell_rects
    a1 = sa._cell_rects["A1"].center
    b3 = sa._cell_rects["B3"].center
    sa.handle_event(_click(*a1), rect)
    assert sa._dragging_range is True
    sa.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=b3, buttons=(1, 0, 0)), rect)
    sa.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=b3), rect)
    assert sa._dragging_range is False
    c1, c2, r1, r2 = sa._range_bounds()
    assert (c1, c2, r1, r2) == (0, 1, 1, 3)   # A1:B3


def test_sheet_app_add_line_chart_from_range(app):
    sa = SheetApp(app)
    sa.on_open()
    for i, v in enumerate((10, 20, 15, 30), start=1):
        sa.sheet.set(f"A{i}", str(v))
    sa.range_anchor, sa.range_end = "A1", "A4"
    sa._add_chart("line")
    assert len(sa.workbook.active.charts) == 1
    chart = sa.workbook.active.charts[0]
    assert chart.kind == "line" and chart.range_str == "A1:A4"
    data = sa._chart_data(chart)
    assert data["y"] == [10.0, 20.0, 15.0, 30.0]


def test_sheet_app_add_scatter_requires_two_columns(app):
    sa = SheetApp(app)
    sa.on_open()
    for i, (x, y) in enumerate([(1, 2), (2, 4), (3, 6)], start=1):
        sa.sheet.set(f"A{i}", str(x))
        sa.sheet.set(f"B{i}", str(y))
    sa.range_anchor, sa.range_end = "A1", "A3"   # une seule colonne -> refusé
    sa._add_chart("scatter")
    assert len(sa.workbook.active.charts) == 0
    assert "2 colonnes" in sa.msg
    sa.range_anchor, sa.range_end = "A1", "B3"
    sa._add_chart("scatter")
    assert len(sa.workbook.active.charts) == 1
    data = sa._chart_data(sa.workbook.active.charts[0])
    assert data["x"] == [1.0, 2.0, 3.0]
    assert data["y"] == [2.0, 4.0, 6.0]


def test_sheet_app_add_bar_chart_with_labels_column(app):
    sa = SheetApp(app)
    sa.on_open()
    labels = ["Q1", "Q2", "Q3"]
    vals = [100, 150, 90]
    for i, (lab, v) in enumerate(zip(labels, vals), start=1):
        sa.sheet.set(f"A{i}", lab)
        sa.sheet.set(f"B{i}", str(v))
    sa.range_anchor, sa.range_end = "A1", "B3"
    sa._add_chart("bar")
    chart = sa.workbook.active.charts[0]
    data = sa._chart_data(chart)
    assert data["labels"] == labels
    assert data["y"] == [100.0, 150.0, 90.0]


def test_sheet_app_close_chart_removes_it(app):
    sa = SheetApp(app)
    sa.on_open()
    for i, v in enumerate((1, 2, 3), start=1):
        sa.sheet.set(f"A{i}", str(v))
    sa.range_anchor, sa.range_end = "A1", "A3"
    sa._add_chart("line")
    rect = pygame.Rect(0, 0, 900, 600)
    sa.draw(app.screen, rect)   # peuple _chart_close_rects
    cid = sa.workbook.active.charts[0].id
    close_r = sa._chart_close_rects[cid]
    sa.handle_event(_click(close_r.centerx, close_r.centery), rect)
    assert sa.workbook.active.charts == []


def test_sheet_app_drag_chart_moves_it(app):
    sa = SheetApp(app)
    sa.on_open()
    for i, v in enumerate((1, 2, 3), start=1):
        sa.sheet.set(f"A{i}", str(v))
    sa.range_anchor, sa.range_end = "A1", "A3"
    sa._add_chart("line")
    rect = pygame.Rect(50, 50, 900, 600)
    sa.draw(app.screen, rect)
    chart = sa.workbook.active.charts[0]
    title_r = sa._chart_title_rects[chart.id]
    x0, y0 = chart.x, chart.y
    sa.handle_event(_click(title_r.centerx, title_r.centery), rect)
    new_pos = (title_r.centerx + 40, title_r.centery + 30)
    sa.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=new_pos, buttons=(1, 0, 0)), rect)
    sa.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=new_pos), rect)
    assert (chart.x, chart.y) != (x0, y0)


def test_sheet_app_resize_chart_via_grip(app):
    sa = SheetApp(app)
    sa.on_open()
    for i, v in enumerate((1, 2, 3), start=1):
        sa.sheet.set(f"A{i}", str(v))
    sa.range_anchor, sa.range_end = "A1", "A3"
    sa._add_chart("line")
    rect = pygame.Rect(50, 50, 900, 600)
    sa.draw(app.screen, rect)
    chart = sa.workbook.active.charts[0]
    grip = sa._chart_resize_rects[chart.id]
    w0, h0 = chart.w, chart.h
    sa.handle_event(_click(grip.centerx, grip.centery), rect)
    assert sa._chart_resize is chart
    new_pos = (grip.centerx + 60, grip.centery + 40)
    sa.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=new_pos, buttons=(1, 0, 0)), rect)
    sa.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=new_pos), rect)
    assert sa._chart_resize is None
    assert (chart.w, chart.h) != (w0, h0)
    assert chart.w >= 160 and chart.h >= 110   # taille plancher respectée


def test_sheet_app_chart_clamped_to_shrunk_window(app):
    """Si la fenêtre est redimensionnée plus petite après coup, le graphique
    reste visible/utilisable (borné à la zone de contenu courante)."""
    sa = SheetApp(app)
    sa.on_open()
    for i, v in enumerate((1, 2, 3), start=1):
        sa.sheet.set(f"A{i}", str(v))
    sa.range_anchor, sa.range_end = "A1", "A3"
    sa._add_chart("line")
    big_rect = pygame.Rect(0, 0, 900, 600)
    sa.draw(app.screen, big_rect)
    chart = sa.workbook.active.charts[0]
    chart.x, chart.y = 700, 500   # pousse le graphe loin dans le coin
    small_rect = pygame.Rect(0, 0, 460, 320)   # taille mini de la fenêtre
    sa.draw(app.screen, small_rect)
    assert chart.x + chart.w <= small_rect.w
    assert chart.y + chart.h <= small_rect.h


# --------------------------------------------------------- navigation Alt+Tab
def test_alt_tab_cycles_focused_window(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    for key in ("research", "trading", "sheet"):
        desk._launch(key)
    focused_before = desk.wm.focused
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=pygame.KMOD_ALT)
    desk.handle_event(ev)
    assert desk.wm.focused is not focused_before
    # un second Alt+Tab avance encore (round-robin, pas juste un aller-retour)
    focused_mid = desk.wm.focused
    desk.handle_event(ev)
    assert desk.wm.focused is not focused_mid


# ------------------------------------------------- ancrage / maximisation (PR3)
def _down(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y))


def _motion(x, y):
    return pygame.event.Event(pygame.MOUSEMOTION, pos=(x, y), buttons=(1, 0, 0))


def _up(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(x, y))


def test_window_snaps_to_left_half_on_drag_to_edge(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("research")
    wm = desk.wm
    tr = w.title_rect
    wm.handle_event(_down(tr.centerx, tr.centery))
    # glisse vers le bord gauche -> aperçu d'ancrage
    wm.handle_event(_motion(2, wm.work_area.centery))
    assert wm._snap_preview is not None
    wm.handle_event(_up(2, wm.work_area.centery))
    assert w.rect.x == wm.work_area.x
    assert w.rect.w == wm.work_area.w // 2
    assert w.rect.h == wm.work_area.h
    assert wm._snap_preview is None


def test_double_click_title_maximizes_and_restores(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("trading")
    wm = desk.wm
    before = w.rect.copy()
    tr = w.title_rect
    wm.handle_event(_down(tr.centerx, tr.centery))
    wm.handle_event(_up(tr.centerx, tr.centery))
    wm.handle_event(_down(tr.centerx, tr.centery))   # 2e clic rapproché
    assert w.rect == wm.work_area                    # maximisé
    tr2 = w.title_rect
    wm.handle_event(_up(tr2.centerx, tr2.centery))
    wm.handle_event(_down(tr2.centerx, tr2.centery))
    wm.handle_event(_up(tr2.centerx, tr2.centery))
    wm.handle_event(_down(tr2.centerx, tr2.centery))  # re-double-clic -> restaure
    assert w.rect == before


def test_desktop_work_area_excludes_taskbar(app):
    from core import config as cfg
    from scenes.scene_desktop import TASKBAR_H, TOPBAR_H
    app.scenes.go("desktop")
    desk = app.scenes.current
    wa = desk.wm.work_area
    assert wa.y == TOPBAR_H
    assert wa.bottom == cfg.SCREEN_HEIGHT - TASKBAR_H


# --------------------------------------------- palette Ctrl+K -> fenêtre (PR3)
def test_palette_navigate_opens_window_on_desktop(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    mgr = app.scenes
    mgr._palette_navigate("markethub", {})
    assert app.scenes.current_name == "desktop"      # pas de bascule plein écran
    assert any(w.key == "scene:markethub" for w in desk.wm.windows)


def test_palette_navigate_fullscreen_outside_desktop():
    a = main.App()
    a.ensure_market()
    a.scenes.go("terminal")
    a.scenes._palette_navigate("markethub", {})
    assert a.scenes.current_name == "markethub"


# ------------------------------------------------------------ calculatrice
def test_calculator_app_computes_expression(app):
    from apps.app_calculator import CalculatorApp
    ca = CalculatorApp(app)
    ca.on_open()
    ca.expr = "2+3*4"
    ca._press("=")
    assert ca.result == "14"


def test_calculator_desktop_icon_opens_window(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk._launch("calculator")
    assert any(w.key == "calculator" for w in desk.wm.windows)


# ------------------------------------------- formules de marché en direct (PR1)
def test_sheet_live_price_formula(app):
    sa = SheetApp(app)
    sa.on_open()
    tk = app.market.companies[0]["ticker"]
    sa.sheet.set("A1", f'=PRICE("{tk}")')
    assert sa.sheet.get_value("A1") == pytest.approx(app.market.price_of(tk))


def test_sheet_live_price_updates_after_market_step(app):
    sa = SheetApp(app)
    sa.on_open()
    tk = app.market.companies[0]["ticker"]
    sa.sheet.set("A1", f'=PRICE("{tk}")')
    v0 = sa.sheet.get_value("A1")
    for _ in range(3):
        app.market.step()
    sa._sync_market()   # comme le fait draw() à chaque frame
    v1 = sa.sheet.get_value("A1")
    assert v1 == pytest.approx(app.market.price_of(tk))
    assert v1 != v0     # le marché a bougé -> la cellule aussi


def test_sheet_networth_cash_and_shares_formulas(app):
    from core import portfolio as PF
    from core import portfolio_margin as PM
    sa = SheetApp(app)
    sa.on_open()
    tk = app.market.companies[0]["ticker"]
    PF.buy(app.gs.player, app.market, tk, 4)
    sa._sync_market()
    sa.sheet.set("A1", "=CASH()")
    sa.sheet.set("A2", "=NETWORTH()")
    sa.sheet.set("A3", f'=SHARES("{tk}")')
    assert sa.sheet.get_value("A1") == pytest.approx(app.gs.player.cash)
    assert sa.sheet.get_value("A2") == pytest.approx(PM.net_worth(app.gs.player, app.market))
    assert sa.sheet.get_value("A3") == 4.0


def test_sheet_unknown_ticker_returns_na_not_crash(app):
    sa = SheetApp(app)
    sa.on_open()
    sa.sheet.set("A1", '=PRICE("ZZZZ")')
    assert sa.sheet.get_value("A1") == "#N/A"


def test_sheet_live_formula_feeds_a_chart(app):
    """Une colonne de =PRICE(...) alimente un graphique qui reflète le marché."""
    sa = SheetApp(app)
    sa.on_open()
    tks = [c["ticker"] for c in app.market.top_companies(n=3)]
    for i, tk in enumerate(tks, start=1):
        sa.sheet.set(f"A{i}", f'=PRICE("{tk}")')
    sa.range_anchor, sa.range_end = "A1", "A3"
    sa._add_chart("bar")
    assert len(sa.workbook.active.charts) == 1
    data = sa._chart_data(sa.workbook.active.charts[0])
    assert data["y"] == [pytest.approx(app.market.price_of(t)) for t in tks]


# --------------------------------------------- liens cliquables entre apps (PR2)
def test_research_trade_link_opens_and_prefills_trading(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("research")
    ra = w.app_obj
    assert ra.desktop is desk               # back-ref posée au lancement
    tk = app.market.companies[0]["ticker"]
    ra.sel = tk
    ra._do_action("trade")
    tw = next((win for win in desk.wm.windows if win.key == "trading"), None)
    assert tw is not None
    assert tw.app_obj.search == tk          # trading pré-filtré sur le ticker
    assert desk.wm.focused is tw            # ramené au premier plan


def test_research_sheet_link_pushes_live_quote(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    ra = desk._launch("research").app_obj
    tk = app.market.companies[0]["ticker"]
    ra.sel = tk
    ra._do_action("sheet")
    sw = next(win for win in desk.wm.windows if win.key == "sheet")
    sheet = sw.app_obj.sheet
    assert sheet.get_raw("A1") == tk
    assert sheet.get_raw("B1") == f'=PRICE("{tk}")'
    assert sheet.get_value("B1") == pytest.approx(app.market.price_of(tk))


def test_research_analyse_link_opens_company_window(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    ra = desk._launch("research").app_obj
    ra.sel = app.market.companies[0]["ticker"]
    ra._do_action("analyse")
    assert any(win.key == "scene:company" for win in desk.wm.windows)


def test_research_action_bar_click_via_draw(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("research")
    ra = w.app_obj
    ra.sel = app.market.companies[0]["ticker"]
    rect = pygame.Rect(0, 0, 820, 520)
    ra.draw(app.screen, rect)               # peuple _action_rects
    assert "trade" in ra._action_rects
    r = ra._action_rects["trade"]
    ra.handle_event(_click(r.centerx, r.centery), rect)
    assert any(win.key == "trading" for win in desk.wm.windows)


def test_desktop_export_routes_to_native_sheet_app(app):
    """Le bouton « → TABLEUR » d'un écran hébergé (financials, ma_target…)
    doit atterrir dans l'app Tableur native (classeur multi-feuilles), pas
    dans l'ancienne scène plein écran."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    data = {"title": "ACME — Bilan", "years": [2024], "rows": [("Actif", [10.0])]}
    w = desk._open_scene_window("spreadsheet", import_data=data)
    assert w.key == "sheet"
    assert not any(win.key == "scene:spreadsheet" for win in desk.wm.windows)
    assert w.app_obj.sheet.get_raw("A3") == "Actif"


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
    # le bureau crée et initialise lui-même le moteur (terminal persistant)
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
    n_before = len(desk.wm.windows)   # le terminal (moteur) est déjà ouvert, minimisé
    for key in ("research", "trading", "sheet"):
        desk._launch(key)
    assert len(desk.wm.windows) == n_before + 3
    desk.update(0.016)
    desk.draw(app.screen)


# ------------------------------------------------- le terminal comme fenêtre
def test_terminal_is_a_persistent_window_on_the_desktop(app):
    """Le terminal n'est plus une scène plein écran à part : c'est une app
    hébergée, ouverte (minimisée) dès l'arrivée sur le bureau — le moteur
    tourne qu'elle soit visible ou non — et ramenée au premier plan par
    l'icône, TOUJOURS la même instance (état préservé)."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = next(win for win in desk.wm.windows if win.key == "scene:terminal")
    assert w.minimized is True                 # bureau propre au démarrage
    assert w.app_obj is desk._terminal_host     # même instance que le moteur
    # l'icône "Terminal" ouvre/ramène cette MÊME fenêtre (pas de doublon)
    desk._launch("terminal")
    assert w.minimized is False
    assert desk.wm.focused is w
    assert sum(1 for win in desk.wm.windows if win.key == "scene:terminal") == 1
    # fermer la fenêtre ne tue pas le moteur : le temps continue de s'écouler
    desk.wm.close(w)
    assert desk._terminal_host is not None
    step_before = app.market.step_count
    app.pending_market_steps = 1
    desk.update(0.016)
    assert app.market.step_count >= step_before + 1
    # réouvrir via l'icône recrée la fenêtre autour de la MÊME instance persistante
    desk._launch("terminal")
    assert any(win.key == "scene:terminal" and win.app_obj is desk._terminal_host
              for win in desk.wm.windows)


def test_terminal_internal_navigation_opens_desktop_window():
    """Une commande tapée DANS le terminal hébergé (ex. SHOP) ouvre une
    fenêtre sur le bureau plutôt que de basculer tout l'écran — le terminal
    se comporte comme n'importe quelle autre app du bureau."""
    a = main.App()
    a.ensure_market()
    a.gs.player.grade_index = 9
    a.gs.player.cash = 5_000_000.0
    a.scenes.go("desktop")
    desk = a.scenes.current
    term = desk._terminal_host.scene
    term.app.scenes.go("shop", return_to="terminal")
    assert a.scenes.current_name == "desktop"          # jamais de bascule plein écran
    assert any(w.key == "scene:shop" for w in desk.wm.windows)


def test_back_button_closes_own_window_instead_of_forcing_terminal_open(app):
    """Régression : cliquer « retour »/« continuer » dans une scène hébergée
    (ex. mission, dont return_to vaut "terminal" par défaut) doit FERMER la
    fenêtre courante — pas ouvrir/focaliser en plus la fenêtre "terminal" en
    laissant la fenêtre appelante ouverte derrière. Avant correctif,
    self.app.scenes.go(self.return_to) ouvrait toujours une fenêtre
    supplémentaire sans jamais fermer l'appelante."""
    app.gs.player.grade_index = 3
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("mission")
    mission = w.app_obj.scene
    assert mission.return_to == "terminal"
    assert any(win.key == "scene:mission" for win in desk.wm.windows)

    mission.app.scenes.back(mission.return_to)

    assert not any(win.key == "scene:mission" for win in desk.wm.windows)
    assert app.scenes.current_name == "desktop"   # jamais de bascule plein écran


def test_back_does_not_force_open_a_window_that_was_not_already_open(app):
    """Après le correctif, `back()` ne fait QUE fermer la fenêtre appelante —
    il n'ouvre plus jamais la fenêtre cible (return_to) si elle n'était pas
    déjà ouverte, contrairement à l'ancien comportement basé sur go()."""
    app.gs.player.grade_index = 9
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.wm.close(next(w for w in desk.wm.windows if w.key == "scene:terminal"))
    w = desk._open_scene_window("book")
    book = w.app_obj.scene
    book.app.scenes.back(book.return_to)
    assert not any(win.key == "scene:book" for win in desk.wm.windows)
    assert not any(win.key == "scene:terminal" for win in desk.wm.windows)


def test_deliberate_forward_navigation_to_terminal_still_opens_it(app):
    """Contrairement à un bouton retour, une navigation délibérée vers le
    terminal (ex. « Acheter » depuis la fiche société, qui pré-remplit une
    commande BUY) doit continuer à ouvrir/focaliser la fenêtre terminal SANS
    fermer la fenêtre appelante — seul go(self.return_to) est requalifié en
    back(), pas les go() explicites vers un autre nom de scène."""
    app.gs.player.grade_index = 9
    app.gs.player.cash = 5_000_000.0
    app.scenes.go("desktop")
    desk = app.scenes.current
    tk = app.market.top_companies(n=1)[0]["ticker"]
    w = desk._open_scene_window("company", ticker=tk, return_to="markethub")
    comp = w.app_obj.scene
    comp.update(0.016)
    comp.draw(app.screen)
    comp.handle_event(_click(comp.buy_btn.rect.centerx, comp.buy_btn.rect.centery))
    assert any(win.key == "scene:company" for win in desk.wm.windows)
    assert any(win.key == "scene:terminal" for win in desk.wm.windows)
    term = desk._terminal_host.scene
    assert term.cmd.startswith(f"BUY {tk}")


def test_terminal_has_no_local_clickable_cheat_button(app):
    """Le bouton CHEAT ne doit exister qu'à un seul endroit : la bande
    d'onglets du bureau (ui/simclock_widget, cf. core/pages.py) — la scène
    terminale ne doit plus en dessiner/exposer de copie locale cliquable
    (double accès source de confusion, corrigé)."""
    app.cheats = True
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk._launch("terminal")
    term = desk._terminal_host.scene
    term.update(0.016)
    term.draw(app.screen)
    assert not hasattr(term, "_cheat_btn_rect")
    assert getattr(app, "cheat_panel", None) is None


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
    desk._open_start_menu()
    desk.draw(app.screen)
    assert len(desk._launcher_rects) > 20      # toutes les scènes du catalogue
    # ouvrir un item par clic (le premier, "Marché", n'est jamais verrouillé)
    r, scene, kw, locked, _label, _desc = desk._launcher_rects[0]
    assert not locked
    desk.handle_event(_click(r.centerx, r.centery))
    assert any(win.key == f"scene:{scene}" for win in desk.wm.windows)


def test_every_launcher_scene_hosts_without_error(app):
    """Chaque scène du menu Démarrer doit pouvoir être hébergée en fenêtre
    (on_enter + update + draw + un clic) sans lever d'exception."""
    from core.app_catalog import SECTIONS
    app.scenes.go("desktop")
    desk = app.scenes.current
    names = {scene for _t, items in SECTIONS for _l, scene, _kw, _desc in items}
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


# --------------------------------------------------------- app liée à la voie
def test_track_icon_appears_after_choosing_a_track_and_opens_scene(app):
    from scenes.scene_desktop import TRACK_APP
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    assert "track" not in desk._icon_rects      # "General" -> pas d'icône dédiée
    app.gs.player.track = "M&A"
    desk.draw(app.screen)
    assert "track" in desk._icon_rects
    assert desk._track_scene == TRACK_APP["M&A"][0] == "ma"
    rect, kind, _label = desk._icon_rects["track"]
    assert kind == "ma"
    desk.handle_event(_click(rect.centerx, rect.centery))
    assert any(w.key == "scene:ma" for w in desk.wm.windows)


# ----------------------------------------------------- popups de choix -> fenêtre
def test_dilemma_routes_to_window_when_on_desktop():
    a = main.App()
    a.ensure_market()
    a.gs.player.grade_index = 9
    a.gs.player.cash = 5_000_000.0
    a.scenes.go("desktop")
    assert a.scenes.current_name == "desktop"
    a.route_scene("dilemma", return_to="terminal")
    desk = a.scenes.current
    assert a.scenes.current_name == "desktop"   # le bureau reste la scène courante
    assert any(w.key == "scene:dilemma" for w in desk.wm.windows)


def test_route_scene_falls_back_to_classic_switch_outside_desktop():
    a = main.App()
    a.ensure_market()
    a.scenes.go("terminal")
    a.route_scene("dilemma", return_to="terminal")
    assert a.scenes.current_name == "dilemma"


# ------------------------------------------- rail retiré -> icônes du bureau
def test_terminal_rail_is_gone(app):
    """Le rail latéral de commandes rapides a été retiré du terminal : plus
    d'attribut `rail`, plus de zone clavier "rail", plus de rects cliquables."""
    app.scenes.go("terminal")
    term = app.scenes.current
    term.update(0.016)
    term.draw(app.screen)
    assert not hasattr(term, "rail")
    assert not hasattr(term, "rail_w")
    assert "rail" not in term.zones.zone_order
    assert not hasattr(term, "_rail_rects")


def test_quick_apps_open_matching_scene_windows(app):
    from scenes.scene_desktop import QUICK_APPS
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    for key, _label, _kind, scene in QUICK_APPS:
        if scene is None:      # "save" : action instantanée, pas une fenêtre
            continue
        desk._launch(key)
        assert any(w.key == f"scene:{scene}" for w in desk.wm.windows), key


def test_quick_save_action_saves_without_opening_window(app):
    from core import config as cfg
    from core.game_state import GameState
    app.scenes.go("desktop")
    desk = app.scenes.current
    n_before = len(desk.wm.windows)
    desk._launch("save")
    assert len(desk.wm.windows) == n_before   # pas de fenêtre ouverte
    assert GameState.load(cfg.SAVE_SLOTS[0]) is not None


# --------------------------------------------- atterrissage bureau partout
def test_continue_from_menu_lands_on_desktop():
    """Le bouton CONTINUER du menu (reprise de l'autosave) atterrit sur le
    bureau, pas sur le terminal plein écran."""
    from core import config as cfg
    a = main.App()
    a.ensure_market()
    a.gs.player.grade_index = 5
    a.gs.save(cfg.AUTOSAVE_SLOT)
    a.scenes.go("menu")
    a.scenes.current._continue()
    assert a.scenes.current_name == "desktop"


def test_new_tab_opens_on_desktop():
    a = main.App()
    a.ensure_market()
    n_before = len(a.pages.pages)
    a.pages.open_new_tab()
    assert len(a.pages.pages) == n_before + 1
    assert a.pages.current_page.manager.current_name == "desktop"


# ============================================= PR4 : conscience ambiante ========
# ------------------------------------------------------- app Watchlist
def test_research_star_toggles_watchlist(app):
    """L'étoile ★ de l'app Recherche ajoute/retire la valeur sélectionnée de
    `player.watchlist` (source partagée avec la commande WATCHLIST)."""
    r = ResearchApp(app)
    r.desktop = None
    r.on_open()
    tk = r.sel
    assert tk not in app.gs.player.watchlist
    r._do_action("watch")
    assert tk in app.gs.player.watchlist
    r._do_action("watch")                       # re-clic = retire
    assert tk not in app.gs.player.watchlist


def test_research_watchlist_capped_at_ten(app):
    r = ResearchApp(app)
    r.on_open()
    app.gs.player.watchlist = [f"X{i}" for i in range(10)]
    r._do_action("watch")                       # plein : n'ajoute pas
    assert r.sel not in app.gs.player.watchlist
    assert len(app.gs.player.watchlist) == 10


def test_watchlist_app_lists_and_removes(app):
    from apps.app_watchlist import WatchlistApp
    tk = app.market.top_companies(n=1)[0]["ticker"]
    app.gs.player.watchlist = [tk]
    w = WatchlistApp(app)
    w.desktop = None
    w.on_open()
    rect = pygame.Rect(40, 40, 420, 460)
    w.draw(app.screen, rect)                    # ne doit pas lever
    assert tk in w._row_rects
    # clic sur le × retire la valeur
    dr = w._del_rects[tk]
    w.handle_event(_click(dr.centerx, dr.centery), rect)
    assert tk not in app.gs.player.watchlist


def test_watchlist_row_click_opens_trading(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    tk = app.market.top_companies(n=1)[0]["ticker"]
    app.gs.player.watchlist = [tk]
    w = desk._launch("watchlist")
    assert w is not None
    rect = pygame.Rect(40, 40, 420, 460)
    w.app_obj.draw(app.screen, rect)
    r = w.app_obj._row_rects[tk]
    w.app_obj.handle_event(_click(r.centerx, r.centery), rect)
    tw = next((win for win in desk.wm.windows if win.key == "trading"), None)
    assert tw is not None
    assert tw.app_obj.search == tk.upper()


def test_watchlist_desktop_icon_opens_app(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    assert "watchlist" in desk._icon_rects
    rect, kind, _label = desk._icon_rects["watchlist"]
    assert kind == "star"
    desk.handle_event(_click(rect.centerx, rect.centery))
    assert any(win.key == "watchlist" for win in desk.wm.windows)


# ------------------------------------------------- barre des tâches clignotante
def test_forced_popup_flags_attention_and_focus_clears_it():
    a = main.App()
    a.ensure_market()
    a.gs.player.grade_index = 9
    a.gs.player.cash = 5_000_000.0
    a.scenes.go("desktop")
    desk = a.scenes.current
    a.route_scene("dilemma", return_to="terminal")   # popup FORCÉ
    w = next(win for win in desk.wm.windows if win.key == "scene:dilemma")
    assert w.attention is True                       # clignote dans la barre des tâches
    desk.wm.focus(w)                                 # la regarder éteint le clignotement
    assert w.attention is False


def test_player_launched_window_has_no_attention(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("markethub")         # ouverture par le joueur
    assert getattr(w, "attention", False) is False


# ---------------------------------------------------- widget patrimoine ambiant
def test_ambient_widget_opens_portfolio(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)                            # calcule self._ambient_rect
    assert desk._ambient_rect is not None
    r = desk._ambient_rect
    desk.handle_event(_click(r.centerx, r.centery))
    assert any(win.key == "scene:book" for win in desk.wm.windows)


# ============================================= PR5 : onboarding + clic droit =====
def _rclick(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(x, y))


# ----------------------------------------------------------- carte d'accueil
def test_onboarding_seen_flag_roundtrip():
    from core import desktop_onboarding
    desktop_onboarding.reset()
    assert desktop_onboarding.seen() is False
    desktop_onboarding.mark_seen()
    assert desktop_onboarding.seen() is True


def test_desktop_shows_onboarding_until_dismissed():
    from core import desktop_onboarding
    desktop_onboarding.reset()
    a = main.App()
    a.ensure_market()
    a.scenes.go("desktop")
    desk = a.scenes.current
    desk.draw(a.screen)
    assert desk._onboard_btn is not None            # carte affichée (1re visite)
    # clic sur « Commencer » : marque vu, la carte disparaît
    desk.handle_event(_click(desk._onboard_btn.centerx, desk._onboard_btn.centery))
    assert desktop_onboarding.seen() is True
    desktop_onboarding.mark_seen()                  # laisse l'état propre pour la suite


def test_onboarding_click_outside_card_dismisses_and_passes_through():
    from core import desktop_onboarding
    desktop_onboarding.reset()
    a = main.App()
    a.ensure_market()
    a.gs.player.grade_index = 9
    a.scenes.go("desktop")
    desk = a.scenes.current
    desk.draw(a.screen)
    # clic sur une icône du bureau (hors carte) : referme l'accueil ET ouvre l'app
    r, _kind, _label = desk._icon_rects["research"]
    desk.handle_event(_click(r.centerx, r.centery))
    assert desktop_onboarding.seen() is True
    assert any(w.key == "research" for w in desk.wm.windows)
    desktop_onboarding.mark_seen()


# --------------------------------------------------------- menus contextuels
def test_right_click_icon_opens_context_menu(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    r, _kind, _label = desk._icon_rects["research"]
    desk.handle_event(_rclick(r.centerx, r.centery))
    assert desk._ctx_menu is not None
    assert len(desk._ctx_menu["items"]) >= 1
    # dessiner peuple les rects cliquables ; cliquer « Ouvrir » lance l'app
    desk.draw(app.screen)
    item_r, _cb = desk._ctx_menu["rects"][0]
    desk.handle_event(_click(item_r.centerx, item_r.centery))
    assert desk._ctx_menu is None
    assert any(w.key == "research" for w in desk.wm.windows)


def test_right_click_window_title_menu_closes_window(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("research")
    desk.draw(app.screen)
    desk.handle_event(_rclick(w.title_rect.centerx, w.title_rect.centery))
    assert desk._ctx_menu is not None
    desk.draw(app.screen)
    # « Fermer » est le dernier item du menu fenêtre
    close_r, _cb = desk._ctx_menu["rects"][-1]
    desk.handle_event(_click(close_r.centerx, close_r.centery))
    assert w not in desk.wm.windows


def test_right_click_desktop_background_menu(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    # un point du fond, loin des icônes (côté droit, sous la barre supérieure)
    from core import config as cfg
    px = cfg.SCREEN_WIDTH - 40
    py = TITLE_H + 120
    desk.handle_event(_rclick(px, py))
    assert desk._ctx_menu is not None
    labels = [lbl for lbl, _cb in desk._ctx_menu["items"]]
    assert any("Applications" in l or "menu" in l.lower() for l in labels)


def test_context_menu_dismissed_by_outside_click(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    r, _kind, _label = desk._icon_rects["trading"]
    desk.handle_event(_rclick(r.centerx, r.centery))
    assert desk._ctx_menu is not None
    desk.draw(app.screen)
    # clic loin du menu : le referme sans lancer d'action
    n_before = len(desk.wm.windows)
    desk.handle_event(_click(5, 5))
    assert desk._ctx_menu is None
    assert len(desk.wm.windows) == n_before


def test_context_menu_keyboard_navigation_wraps_and_activates(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    r, _kind, _label = desk._icon_rects["research"]
    desk.handle_event(_rclick(r.centerx, r.centery))
    n_items = len(desk._ctx_menu["items"])
    assert desk._ctx_menu["cursor"] == 0

    down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0, unicode="")
    desk.handle_event(down)
    assert desk._ctx_menu["cursor"] == 1

    up = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP, mod=0, unicode="")
    desk.handle_event(up)
    desk.handle_event(up)
    assert desk._ctx_menu["cursor"] == n_items - 1   # remonte en haut -> boucle en bas

    # ENTRÉE sur "Ouvrir" (1er item) active l'action et referme le menu
    up_to_open = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP, mod=0, unicode="")
    for _ in range(n_items - 1):
        desk.handle_event(up_to_open)
    assert desk._ctx_menu["cursor"] == 0
    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="")
    desk.handle_event(enter)
    assert desk._ctx_menu is None
    assert any(w.key == "research" for w in desk.wm.windows)


def test_context_menu_escape_closes_without_action(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    r, _kind, _label = desk._icon_rects["trading"]
    desk.handle_event(_rclick(r.centerx, r.centery))
    n_before = len(desk.wm.windows)
    esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")
    desk.handle_event(esc)
    assert desk._ctx_menu is None
    assert len(desk.wm.windows) == n_before


def test_context_menu_snap_left_positions_window(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("sheet")
    desk._snap_window(w, "left")
    wa = desk.wm.work_area
    assert w.rect.x == wa.x and w.rect.w == wa.w // 2
    assert w._restore_rect is not None              # peut revenir à la taille d'avant


# ==================================================== épinglage de fenêtre ====
def test_pin_toggle_via_context_menu_item(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("research")
    assert w.pinned is False
    items = dict(desk._window_menu_items(w))
    items["Épingler (toujours au premier plan)"]()
    assert w.pinned is True
    items2 = dict(desk._window_menu_items(w))
    items2["Détacher (premier plan)"]()
    assert w.pinned is False


def test_pinned_window_stays_on_top_after_other_window_focused(app):
    wm = WindowManager(app)
    w1 = wm.open("a", lambda: ResearchApp(app))
    w2 = wm.open("b", lambda: SheetApp(app))
    w1.rect.topleft = w2.rect.topleft = (100, 100)
    w1.pinned = True
    wm.focus(w2)   # w2 est la dernière ouverte/focalisée...
    assert wm._topmost_at((150, 150)) is w1   # ...mais w1 reste au-dessus (épinglée)


def test_two_pinned_windows_keep_relative_order_between_them(app):
    wm = WindowManager(app)
    w1 = wm.open("a", lambda: ResearchApp(app))
    w2 = wm.open("b", lambda: SheetApp(app))
    w1.rect.topleft = w2.rect.topleft = (100, 100)
    w1.pinned = w2.pinned = True
    assert wm._topmost_at((150, 150)) is w2   # ordre normal conservé entre épinglées
    wm.focus(w1)
    assert wm._topmost_at((150, 150)) is w1


def test_unpinned_windows_unaffected_when_none_pinned(app):
    wm = WindowManager(app)
    wm.open("a", lambda: ResearchApp(app))
    wm.open("b", lambda: SheetApp(app))
    assert wm._z_order() == wm.windows


# ==================================== feedback son/visuel de docking ==========
def test_maximize_toggle_sets_dock_flash(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("trading")
    wm = desk.wm
    assert w._dock_flash_until == 0
    wm.maximize_toggle(w)
    assert w._dock_flash_until > pygame.time.get_ticks()


def test_snap_drag_to_edge_sets_dock_flash(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("research")
    wm = desk.wm
    tr = w.title_rect
    wm.handle_event(_down(tr.centerx, tr.centery))
    wm.handle_event(_motion(2, wm.work_area.centery))
    wm.handle_event(_up(2, wm.work_area.centery))
    assert w._dock_flash_until > pygame.time.get_ticks()


def test_context_menu_snap_sets_dock_flash(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("sheet")
    desk._snap_window(w, "left")
    assert w._dock_flash_until > pygame.time.get_ticks()


def test_dock_flash_fades_and_stops_drawing(app):
    """Le liseré de docking s'éteint tout seul après DOCK_FLASH_MS (horloge
    murale, pas de dépendance à dt) — vérifié via un dessin après expiration."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("trading")
    wm = desk.wm
    wm.maximize_toggle(w)
    w._dock_flash_until = pygame.time.get_ticks() - 1   # déjà expiré
    surf = pygame.Surface((w.rect.right + 10, w.rect.bottom + 10))
    w.draw(surf, focused=True)   # ne doit pas lever d'exception une fois expiré


# ============================== réactivité des graphes + flash vert/rouge ======
def test_watchlist_uses_animated_live_price(app):
    """La Watchlist affiche le prix ANIMÉ (core/intraday.py), pas juste la
    clôture figée du dernier pas — cohérent avec le reste du bureau (research,
    graphe)."""
    from apps.app_watchlist import WatchlistApp
    tk = app.market.top_companies(n=1)[0]["ticker"]
    w = WatchlistApp(app)
    w.on_open()
    hist = w._live_hist(tk)
    assert hist and hist[-1] == pytest.approx(app.market.price_of(tk), rel=0.05)


def test_watchlist_price_flashes_on_change(app):
    from apps.app_watchlist import WatchlistApp
    tk = app.market.top_companies(n=1)[0]["ticker"]
    app.gs.player.watchlist = [tk]
    w = WatchlistApp(app)
    w.desktop = None
    w.on_open()
    rect = pygame.Rect(40, 40, 420, 460)
    w.draw(app.screen, rect)          # 1er point : pas encore de flash (référence)
    app.pending_market_steps = 1
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.update(0.016)                # avance le marché d'un pas -> le prix bouge
    w.draw(app.screen, rect)          # doit pouvoir flasher sans lever d'erreur


def test_sheet_live_price_cell_flashes(app):
    """Une cellule =PRICE(...) clignote vert/rouge au mouvement (flash), pas
    juste blanc statique — cf. _LIVE_FN_NAMES."""
    from apps.app_sheet import _LIVE_FN_NAMES, SheetApp
    assert "PRICE" in _LIVE_FN_NAMES
    tk = app.market.top_companies(n=1)[0]["ticker"]
    s = SheetApp(app)
    s.on_open()
    s.sheet.set("A1", f'=PRICE("{tk}")')
    rect = pygame.Rect(40, 40, 760, 520)
    s.draw(app.screen, rect)          # ne doit pas lever ; alimente le flash
    assert "A1" in s._flash._last


def test_sim_clock_pace_leaves_a_day_slower_than_before():
    """Régression de rythme : un jour de jeu à x1 doit durer plus longtemps
    qu'avec l'ancienne cadence (120 min de jeu/s réelle -> 12s/jour)."""
    from core.sim_clock import GAME_MINUTES_PER_REAL_SECOND_AT_X1, MINUTES_PER_DAY
    seconds_per_day = MINUTES_PER_DAY / GAME_MINUTES_PER_REAL_SECOND_AT_X1
    assert seconds_per_day > 12.0


def test_intraday_refreshes_more_than_once_per_day():
    from core import intraday
    assert intraday.MINUTES_PER_DAY // intraday.QUANTIZE_MINUTES >= 2


# ==================================== Tableur avancé (VLOOKUP UI, CF, CSV, ====
# ==================================== copier/coller, annuler/rétablir) =======
def test_sheet_app_vlookup_catalog_entry_present(app):
    from apps.app_sheet import FUNCTION_CATALOG
    names = {name for _cat, funcs in FUNCTION_CATALOG for name, _hint in funcs}
    assert "VLOOKUP" in names


def test_sheet_app_vlookup_formula_resolves(app):
    sa = SheetApp(app)
    sa.on_open()
    sa.sheet.set("A1", "MVC"); sa.sheet.set("B1", "42")
    sa.sheet.set("C1", '=VLOOKUP("MVC",A1:B1,2)')
    assert sa.sheet.get_value("C1") == 42.0


# ------------------------------------------------------- copier/coller (Ctrl+C/V)
def _ctrl_key(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=pygame.KMOD_CTRL, unicode="")


def test_sheet_app_copy_paste_range(app):
    sa = SheetApp(app)
    sa.on_open()
    sa.sheet.set("A1", "10"); sa.sheet.set("A2", "20")
    sa.range_anchor, sa.range_end = "A1", "A2"
    rect = pygame.Rect(0, 0, 900, 600)
    sa.handle_event(_ctrl_key(pygame.K_c), rect)
    assert sa._clipboard == [["10"], ["20"]]
    sa.sel = "C1"
    sa.handle_event(_ctrl_key(pygame.K_v), rect)
    assert sa.sheet.get_raw("C1") == "10"
    assert sa.sheet.get_raw("C2") == "20"


def test_sheet_app_paste_without_copy_shows_message(app):
    sa = SheetApp(app)
    sa.on_open()
    rect = pygame.Rect(0, 0, 900, 600)
    sa.handle_event(_ctrl_key(pygame.K_v), rect)
    assert "presse-papiers" in sa.msg.lower() or "vide" in sa.msg.lower()


def test_sheet_app_paste_clipped_to_sheet_bounds(app):
    """Coller près du bord de la feuille ne doit pas planter : les cellules
    hors bornes sont silencieusement ignorées."""
    from apps.app_sheet import N_COLS, N_ROWS
    sa = SheetApp(app)
    sa.on_open()
    sa.sheet.set("A1", "x"); sa.sheet.set("B1", "y")
    sa.range_anchor, sa.range_end = "A1", "B1"
    sa._copy_range()
    sa.sel = f"{chr(ord('A') + N_COLS - 1)}{N_ROWS}"   # coin bas-droit de la feuille
    sa._paste_range()   # ne doit pas lever malgré le débordement


# ------------------------------------------------------------ annuler/rétablir
def test_sheet_app_undo_redo_single_edit(app):
    sa = SheetApp(app)
    sa.on_open()
    sa.sel = "A1"
    sa.editing = True
    sa.edit_buf = "=1+1"
    sa._commit()
    assert sa.sheet.get_raw("A1") == "=1+1"
    sa._undo_action()
    assert sa.sheet.get_raw("A1") == ""
    sa._redo_action()
    assert sa.sheet.get_raw("A1") == "=1+1"


def test_sheet_app_undo_empty_stack_shows_message(app):
    sa = SheetApp(app)
    sa.on_open()
    sa._undo_action()
    assert "annuler" in sa.msg.lower()


def test_sheet_app_new_edit_clears_redo_stack(app):
    sa = SheetApp(app)
    sa.on_open()
    sa.sel = "A1"
    sa.editing = True
    sa.edit_buf = "1"
    sa._commit()
    sa._undo_action()
    assert sa._redo    # un rétablissement est possible
    sa.sel = "B1"
    sa.editing = True
    sa.edit_buf = "2"
    sa._commit()
    assert sa._redo == []   # une nouvelle action a invalidé le rétablissement


def test_sheet_app_undo_covers_paste_as_one_action(app):
    """Un collage multi-cellules s'annule en UN SEUL Ctrl+Z (comme un vrai
    tableur), pas cellule par cellule."""
    sa = SheetApp(app)
    sa.on_open()
    sa.sheet.set("A1", "1"); sa.sheet.set("A2", "2")
    sa.range_anchor, sa.range_end = "A1", "A2"
    sa._copy_range()
    sa.sel = "C1"
    sa._paste_range()
    assert sa.sheet.get_raw("C1") == "1" and sa.sheet.get_raw("C2") == "2"
    sa._undo_action()
    assert sa.sheet.get_raw("C1") == "" and sa.sheet.get_raw("C2") == ""


def test_sheet_app_backspace_delete_is_undoable(app):
    sa = SheetApp(app)
    sa.on_open()
    sa.sheet.set("A1", "hello")
    sa.sel = "A1"
    rect = pygame.Rect(0, 0, 900, 600)
    sa.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, mod=0, unicode=""), rect)
    assert sa.sheet.get_raw("A1") == ""
    sa._undo_action()
    assert sa.sheet.get_raw("A1") == "hello"


# ------------------------------------------------------- mise en forme conditionnelle
def test_sheet_app_cf_rule_applies_to_selected_range(app):
    sa = SheetApp(app)
    sa.on_open()
    sa.sheet.set("A1", "150")
    sa.range_anchor, sa.range_end = "A1", "A1"
    sa._cf_op, sa._cf_value_str, sa._cf_color = ">", "100", "up"
    sa._apply_cf_rule()
    assert len(sa.workbook.active.cf_rules) == 1
    rule = sa.workbook.active.cf_rules[0]
    assert rule.range_str == "A1:A1"
    assert sa.workbook.active.cf_color_for("A1", 150.0) == "up"


def test_sheet_app_cf_invalid_threshold_shows_message(app):
    sa = SheetApp(app)
    sa.on_open()
    sa._cf_value_str = "not a number"
    sa._apply_cf_rule()
    assert sa.workbook.active.cf_rules == []
    assert "seuil" in sa.msg.lower() or "invalide" in sa.msg.lower()


def test_sheet_app_cf_panel_toggle_and_remove_rule(app):
    from core.workbook import ConditionalFormat
    sa = SheetApp(app)
    sa.on_open()
    rect = pygame.Rect(0, 0, 900, 600)
    sa.draw(app.screen, rect)          # peuple self._cf_rect
    sa.handle_event(_click(sa._cf_rect.centerx, sa._cf_rect.centery), rect)
    assert sa.cf_open is True
    sa.workbook.active.cf_rules.append(ConditionalFormat("A1:A1", ">", 0.0, "up"))
    sa.draw(app.screen, rect)          # peuple self._cf_remove_rects
    rid = sa.workbook.active.cf_rules[0].id
    rm_rect = sa._cf_remove_rects[rid]
    sa.handle_event(_click(rm_rect.centerx, rm_rect.centery), rect)
    assert sa.workbook.active.cf_rules == []


# ------------------------------------------------------------------- export CSV
def test_sheet_app_export_csv_writes_file(app, tmp_path, monkeypatch):
    monkeypatch.setattr(os.path, "expanduser", lambda p: str(tmp_path))
    sa = SheetApp(app)
    sa.on_open()
    sa.sheet.set("A1", "10")
    sa.sheet.set("B1", "20")
    sa.sheet.set("A2", "=A1+B1")
    sa._export_csv()
    files = list(tmp_path.glob("*.csv"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "10" in content and "20" in content and "30" in content
    assert "Exporté" in sa.msg


def test_sheet_app_export_csv_empty_sheet_shows_message(app):
    sa = SheetApp(app)
    sa.on_open()
    sa._export_csv()
    assert "vide" in sa.msg.lower()


# ================================= Ordres conditionnels (stop-loss/take-profit) ==
def test_trading_app_order_button_appears_only_for_held_positions(app):
    tk = app.market.companies[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    rect = pygame.Rect(0, 0, 840, 520)
    ta.draw(app.screen, rect)
    assert tk not in ta._order_rects       # pas détenu -> pas de bouton ORD
    ta.qty_text = "5"
    ta._do_buy(tk)
    ta.draw(app.screen, rect)
    assert tk in ta._order_rects


def test_trading_app_order_button_opens_prompt(app):
    tk = app.market.companies[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_text = "5"
    ta._do_buy(tk)
    rect = pygame.Rect(0, 0, 840, 520)
    ta.draw(app.screen, rect)
    r = ta._order_rects[tk]
    ta.handle_event(_click(r.centerx, r.centery), rect)
    assert ta._order_prompt == {"ticker": tk}
    assert ta._order_kind == "stop"
    assert ta._order_price_str          # pré-rempli au cours courant


def test_trading_app_place_stop_loss_via_prompt(app):
    tk = app.market.companies[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_text = "5"
    ta._do_buy(tk)
    ta._open_order_prompt(tk)
    ta._order_kind = "stop"
    ta._order_price_str = "1.00"
    ta._confirm_order()
    assert ta._order_prompt is None
    assert len(app.gs.player.conditional_orders) == 1
    order = app.gs.player.conditional_orders[0]
    assert order["ticker"] == tk and order["kind"] == "stop" and order["trigger"] == 1.0


def test_trading_app_place_take_profit_switch_kind(app):
    tk = app.market.companies[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_text = "5"
    ta._do_buy(tk)
    rect = pygame.Rect(0, 0, 840, 520)
    ta._open_order_prompt(tk)
    ta.draw(app.screen, rect)          # peuple _order_kind_rects
    target_r = ta._order_kind_rects["target"]
    ta.handle_event(_click(target_r.centerx, target_r.centery), rect)
    assert ta._order_kind == "target"
    ta._order_price_str = "999999.00"
    ta._confirm_order()
    order = app.gs.player.conditional_orders[0]
    assert order["kind"] == "target"


def test_trading_app_order_prompt_invalid_price_keeps_prompt_open(app):
    tk = app.market.companies[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_text = "5"
    ta._do_buy(tk)
    ta._open_order_prompt(tk)
    ta._order_price_str = "not a number"
    ta._confirm_order()
    assert ta._order_prompt is not None
    assert app.gs.player.conditional_orders == []


def test_trading_app_order_prompt_escape_cancels(app):
    tk = app.market.companies[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_text = "5"
    ta._do_buy(tk)
    ta._open_order_prompt(tk)
    rect = pygame.Rect(0, 0, 840, 520)
    ta.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""), rect)
    assert ta._order_prompt is None
    assert app.gs.player.conditional_orders == []


def test_trading_app_cancel_conditional_order_via_list(app):
    from core import conditional_orders as CO
    tk = app.market.companies[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_text = "5"
    ta._do_buy(tk)
    r = CO.place(app.gs.player, app.market, tk, "stop", 1.0)
    oid = r["order"]["id"]
    rect = pygame.Rect(0, 0, 840, 520)
    ta.draw(app.screen, rect)          # peuple _cond_cancel_rects
    cr = ta._cond_cancel_rects[oid]
    ta.handle_event(_click(cr.centerx, cr.centery), rect)
    assert app.gs.player.conditional_orders == []


def test_conditional_order_executes_on_market_step_via_desktop(app):
    """Bout en bout : un stop-loss posé depuis l'app se déclenche au pas de
    marché suivant (via GameState.advance_step, câblé dans le terminal)."""
    from core import conditional_orders as CO
    tk = app.market.companies[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_text = "5"
    ta._do_buy(tk)
    price = app.market.price_of(tk)
    CO.place(app.gs.player, app.market, tk, "stop", price * 10)   # seuil très haut -> déclenche à coup sûr
    summary = app.gs.advance_step(app.market)
    assert summary["conditional_orders_executed"]
    assert tk not in app.gs.player.portfolio


# ====================================== Recherche globale (Ctrl+/) ===============
def _ctrl_slash():
    return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SLASH, mod=pygame.KMOD_CTRL, unicode="")


def test_ctrl_slash_opens_global_search(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.handle_event(_ctrl_slash())
    assert desk._search_open is True
    assert desk._search_query == ""


def test_search_escape_closes(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk._open_search()
    desk.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
    assert desk._search_open is False


def test_search_finds_held_position_and_opens_trading(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    app.gs.player.portfolio[tk] = {"shares": 10.0, "avg": 100.0}
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk._open_search()
    desk._search_query = tk
    results = desk._search_results()
    assert len(results) == 1
    desk._search_navigate(results[0])
    assert desk._search_open is False
    tw = next((win for win in desk.wm.windows if win.key == "trading"), None)
    assert tw is not None
    assert tw.app_obj.search == tk.upper()


def test_search_finds_inbox_message_and_opens_inbox(app):
    app.gs.player.inbox = [{"id": 1, "subject": "Alerte importante", "sender": "Manager",
                            "body": "", "read": False}]
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk._open_search()
    desk._search_query = "importante"
    results = desk._search_results()
    assert len(results) == 1
    desk._search_navigate(results[0])
    assert any(w.key == "scene:inbox" for w in desk.wm.windows)


def test_search_typing_and_backspace(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk._open_search()
    desk.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode="a"))
    desk.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0, unicode="b"))
    assert desk._search_query == "ab"
    desk.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, mod=0, unicode=""))
    assert desk._search_query == "a"


def test_search_enter_navigates_to_selected_result(app):
    tk = app.market.top_companies(n=1)[0]["ticker"]
    app.gs.player.watchlist = [tk]
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk._open_search()
    desk._search_query = tk
    desk.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode=""))
    assert desk._search_open is False
    assert any(w.key == "trading" for w in desk.wm.windows)


def test_search_click_outside_box_closes(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk._open_search()
    desk.draw(app.screen)
    desk.handle_event(_click(5, 5))
    assert desk._search_open is False


def test_search_draw_does_not_raise_with_no_results(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk._open_search()
    desk._search_query = "zzz_no_match_zzz"
    desk.draw(app.screen)   # ne doit pas lever


# ------------------------------------------------ clic ne traverse pas les fenêtres
class _DeadApp:
    """Appli factice dont handle_event ne réagit jamais (comme une zone morte
    du tableur) — utilisée pour vérifier que WindowManager absorbe quand même
    le clic plutôt que de le laisser retomber sur ce qu'il y a derrière."""
    default_size = (400, 300)
    min_size = (200, 150)
    icon_kind = "generic"

    def __init__(self, app):
        pass

    def on_open(self):
        pass

    def update(self, dt):
        pass

    def draw(self, surf, rect):
        pass

    def handle_event(self, event, rect):
        return False


def test_dead_click_inside_window_content_is_still_consumed(app):
    wm = WindowManager(app)
    w = wm.open("dead", lambda: _DeadApp(app), x=50, y=50)
    inside = (w.content_rect.centerx, w.content_rect.centery)
    consumed = wm.handle_event(_click(*inside))
    assert consumed is True


def test_dead_scroll_inside_window_content_is_still_consumed(app):
    wm = WindowManager(app)
    w = wm.open("dead", lambda: _DeadApp(app), x=50, y=50)
    inside = (w.content_rect.centerx, w.content_rect.centery)
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=4, pos=inside)
    assert wm.handle_event(ev) is True


def test_click_outside_all_windows_not_consumed(app):
    wm = WindowManager(app)
    wm.open("dead", lambda: _DeadApp(app), x=50, y=50)
    consumed = wm.handle_event(_click(1, 1))
    assert consumed is False


def test_click_on_dead_window_does_not_reach_desktop_behind(app):
    """Reproduction directe du bug rapporté : une fenêtre (ex. Tableur) posée
    par-dessus une icône du bureau — cliquer dans une zone morte de la fenêtre
    ne doit JAMAIS déclencher l'icône du bureau située dessous."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)   # peuple desk._icon_rects
    icon_key = desk._icon_list()[0][0]
    icon_rect = desk._icon_rects[icon_key][0]
    w = desk.wm.open("dead", lambda: _DeadApp(app), x=icon_rect.x, y=icon_rect.y)
    before = len(desk.wm.windows)
    inside = (w.content_rect.centerx, w.content_rect.centery)
    desk.handle_event(_click(*inside))
    # aucune nouvelle fenêtre n'a été ouverte par un double-déclenchement de l'icône
    assert len(desk.wm.windows) == before


def test_scene_host_default_size_close_to_full_resolution():
    """Le facteur de réduction (smoothscale) doit rester modéré pour éviter le
    flou signalé : la fenêtre par défaut ne doit pas être ridiculement petite
    par rapport à la résolution logique (1280x720)."""
    from apps.scene_host import SceneHostApp
    from core import config
    dw, dh = SceneHostApp.default_size
    assert dw >= config.SCREEN_WIDTH * 0.8
    assert dh >= 600
