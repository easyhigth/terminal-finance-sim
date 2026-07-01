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
    windows_by_key = {w.key: w for w in desk.wm.windows}
    focused_before = desk.wm.focused
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=pygame.KMOD_ALT)
    desk.handle_event(ev)
    assert desk.wm.focused is not focused_before
    # un second Alt+Tab avance encore (round-robin, pas juste un aller-retour)
    focused_mid = desk.wm.focused
    desk.handle_event(ev)
    assert desk.wm.focused is not focused_mid


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
