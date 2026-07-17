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
from core import config
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
    # neutralise la disposition de bureau par défaut (cf. DesktopScene._seed_default_layout) :
    # la plupart des tests ci-dessous veulent un bureau "déjà en cours de partie"
    # (icônes cliquables sans fenêtre par-dessus), pas un tout premier atterrissage.
    p.flags["desktop_seeded"] = True
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


# ----------------------------------------------- modèles de tableur prêts à l'emploi
def test_sheet_app_insert_template_fills_blank_sheet(app):
    sa = SheetApp(app)
    sa.on_open()
    sa._insert_template("returns")
    assert sa.tpl_open is False
    assert sa.sheet.get_raw("A1") == "RENDEMENT D'UN INVESTISSEMENT"
    assert "Modèle inséré" in sa.msg


def test_sheet_app_insert_template_cancels_pending_edit(app):
    sa = SheetApp(app)
    sa.on_open()
    sa.editing = True
    sa.edit_buf = "=SUM(A1:A2"
    sa._insert_template("networth")
    assert sa.editing is False
    assert sa.edit_buf == ""


def test_sheet_app_tpl_button_click_toggles_panel(app):
    sa = SheetApp(app)
    sa.on_open()
    rect = pygame.Rect(0, 0, 400, 300)
    sa.draw(app.screen, rect)
    assert sa._tpl_rect is not None
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=sa._tpl_rect.center)
    sa.handle_event(ev, rect)
    assert sa.tpl_open is True


def test_sheet_app_tpl_panel_click_inserts_and_closes(app):
    sa = SheetApp(app)
    sa.on_open()
    rect = pygame.Rect(0, 0, 400, 300)
    sa.tpl_open = True
    sa.draw(app.screen, rect)
    r = sa._tpl_item_rects["loan"]
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=r.center)
    sa.handle_event(ev, rect)
    assert sa.tpl_open is False
    assert sa.sheet.get_raw("A1") == "MENSUALITÉ D'EMPRUNT"


def test_sheet_app_tpl_panel_click_outside_closes_without_inserting(app):
    sa = SheetApp(app)
    sa.on_open()
    rect = pygame.Rect(0, 0, 400, 300)
    sa.tpl_open = True
    sa.draw(app.screen, rect)
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(2, 2))
    sa.handle_event(ev, rect)
    assert sa.tpl_open is False
    assert sa.sheet.get_raw("A1") == ""


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


def test_window_snaps_to_top_left_quarter_on_drag_to_corner(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("research")
    wm = desk.wm
    tr = w.title_rect
    wm.handle_event(_down(tr.centerx, tr.centery))
    wm.handle_event(_motion(wm.work_area.x + 2, wm.work_area.y + 2))
    assert wm._snap_preview == wm._quarter_rect("tl")
    wm.handle_event(_up(wm.work_area.x + 2, wm.work_area.y + 2))
    assert w.rect == wm._quarter_rect("tl")


def test_window_snaps_to_bottom_right_quarter_on_drag_to_corner(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("research")
    wm = desk.wm
    tr = w.title_rect
    wm.handle_event(_down(tr.centerx, tr.centery))
    wm.handle_event(_motion(wm.work_area.right - 2, wm.work_area.bottom - 2))
    assert wm._snap_preview == wm._quarter_rect("br")
    wm.handle_event(_up(wm.work_area.right - 2, wm.work_area.bottom - 2))
    assert w.rect == wm._quarter_rect("br")


def test_quarter_rects_tile_the_work_area_without_gaps_or_overlap(app):
    wm = WindowManager(app)
    wa = wm.work_area
    tl, tr, bl, br = (wm._quarter_rect(s) for s in ("tl", "tr", "bl", "br"))
    assert tl.w + tr.w == wa.w
    assert tl.h + bl.h == wa.h
    assert tl.topleft == wa.topleft
    assert br.bottomright == wa.bottomright
    assert tl.right == tr.x
    assert tl.bottom == bl.y


def test_context_menu_snap_to_quarter_positions_and_docks_window(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("sheet")
    desk._snap_window(w, "tr")
    assert w.rect == desk.wm._quarter_rect("tr")
    assert w._dock_flash_until > pygame.time.get_ticks()


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
    # "markethub" est une app NATIVE (apps/app_markethub.py, plus d'hébergement
    # de la scène plein écran — cf. étape "netteté" du bureau) : clé sans préfixe.
    assert any(w.key == "markethub" for w in desk.wm.windows)


def test_palette_navigate_fullscreen_outside_desktop():
    a = main.App()
    a.ensure_market()
    a.scenes.go("terminal")
    a.scenes._palette_navigate("markethub", {})
    assert a.scenes.current_name == "markethub"


# ------------------------------------- palette Ctrl+K : actions rapides (⚡)
def test_palette_action_matches_lists_held_positions(app):
    tk = app.market.companies[0]["ticker"]
    app.gs.player.portfolio[tk] = {"shares": 10.0, "avg": 100.0}
    hits = app.scenes._palette_action_matches("vendre")
    assert any(scene == "__sell_all__" and kw["ticker"] == tk
              for _label, scene, kw in hits)


def test_palette_action_matches_empty_without_position():
    a = main.App()
    a.ensure_market()
    assert a.scenes._palette_action_matches("vendre") == []


def test_palette_filtered_includes_action_hits_before_scene_hits(app):
    tk = app.market.companies[0]["ticker"]
    app.gs.player.portfolio[tk] = {"shares": 5.0, "avg": 50.0}
    app.scenes.palette_query = tk
    filtered = app.scenes._palette_filtered()
    assert filtered and filtered[0][1] == "__sell_all__"


def test_palette_sell_all_executes_and_clears_position(app):
    tk = app.market.companies[0]["ticker"]
    app.gs.player.cash = 0.0
    app.gs.player.portfolio[tk] = {"shares": 5.0, "avg": 10.0}
    app.scenes.go("desktop")
    app.scenes._palette_execute_sell_all(tk)
    assert tk not in app.gs.player.portfolio
    assert app.gs.player.cash > 0.0


def test_palette_sell_all_high_impact_opens_trading_instead_of_selling(app):
    tk = app.market.companies[0]["ticker"]
    price = app.market.price_of(tk)
    # position qui pèse largement > 30% du patrimoine net -> confirmation requise
    huge_qty = (app.gs.player.cash * 5) / price
    app.gs.player.portfolio[tk] = {"shares": huge_qty, "avg": price}
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.scenes._palette_execute_sell_all(tk)
    assert tk in app.gs.player.portfolio      # pas vendu silencieusement
    assert any(w.key == "trading" for w in desk.wm.windows)


def test_palette_sell_all_noop_on_unknown_ticker(app):
    app.scenes.go("desktop")
    app.scenes._palette_execute_sell_all("NOPE")   # ne doit pas lever


# --------------------------------------- mode débutant/expert (menu Démarrer)
def test_start_menu_beginner_mode_hides_advanced_sections(app, monkeypatch):
    from core import experience_mode as XP
    monkeypatch.setattr(XP, "_mode", "expert")
    app.scenes.go("desktop")
    desk = app.scenes.current
    all_scenes = {it[1] for _title, items in desk._start_visible_sections() for it in items}
    assert "structured" in all_scenes

    XP.set_mode("beginner")
    try:
        beginner_scenes = {it[1] for _title, items in desk._start_visible_sections() for it in items}
        assert "structured" not in beginner_scenes
        assert "markethub" in beginner_scenes   # jamais masquée (pas "avancée")
    finally:
        XP.set_mode("expert")


def test_palette_entries_respect_beginner_mode(app):
    from core import experience_mode as XP
    XP.set_mode("beginner")
    try:
        scenes = {scene for _label, scene, _kw in app.scenes._palette_entries()}
        assert "structured" not in scenes
    finally:
        XP.set_mode("expert")


# --------------------------------------------- routine quotidienne (checklist)
def test_checklist_widget_lists_items_when_enabled(app):
    app.scenes.go("desktop")
    scene = app.scenes.current
    scene.draw(app.screen)
    ids = {i for _r, i in scene._checklist_rects}
    from core import daily_checklist as DC
    assert ids == {it["id"] for it in DC.ITEMS}


def test_checklist_click_toggles_item(app):
    scene = _empty_desktop(app)
    scene.draw(app.screen)
    row, item_id = scene._checklist_rects[0]
    scene.handle_event(_click(*row.center))
    from core import daily_checklist as DC
    items = {it["id"]: it["done"] for it in DC.items_for_today(app.gs.player)}
    assert items[item_id] is True


def test_checklist_hidden_when_all_items_done(app):
    app.scenes.go("desktop")
    scene = app.scenes.current
    from core import daily_checklist as DC
    for it in DC.ITEMS:
        DC.toggle(app.gs.player, it["id"])
    scene.draw(app.screen)
    assert scene._checklist_rects == []


def test_checklist_hidden_when_disabled_in_settings(app):
    from core import daily_checklist as DC
    DC.set_enabled(app.gs.player, False)
    try:
        app.scenes.go("desktop")
        scene = app.scenes.current
        scene.draw(app.screen)
        assert scene._checklist_rects == []
    finally:
        DC.set_enabled(app.gs.player, True)


def test_settings_screen_has_daily_routine_row(app):
    app.scenes.go("settings", return_to="desktop")
    sc = app.scenes.current
    labels = [label for label, _btns in sc.rows]
    assert any("routine" in lbl.lower() for lbl in labels)


def test_changing_daily_routine_setting_persists_via_core_module(app):
    from core import daily_checklist as DC
    DC.set_enabled(app.gs.player, True)
    app.scenes.go("settings", return_to="desktop")
    sc = app.scenes.current
    row = next(btns for label, btns in sc.rows if "routine" in label.lower())
    hide_btn = next(b for b in row if b.action == ("checklist", False))
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=hide_btn.rect.center)
    sc.handle_event(click)
    assert DC.is_enabled(app.gs.player) is False
    DC.set_enabled(app.gs.player, True)   # restaure pour les autres tests


# --------------------------------------------- indicateur de risque unifié
def test_risk_badge_shows_ok_by_default(app):
    app.scenes.go("desktop")
    scene = app.scenes.current
    scene.draw(app.screen)
    assert scene._risk_badge_rect is not None
    assert "contrôle" in scene._risk_badge_reasons or "signaler" in scene._risk_badge_reasons


def test_risk_badge_shows_danger_on_heavy_concentration(app):
    tk = app.market.companies[0]["ticker"]
    app.market.price[app.market.ticker_idx[tk]] = 100.0
    app.gs.player.cash = 5_000.0
    app.gs.player.portfolio[tk] = {"shares": 950.0, "avg": 100.0}
    app.scenes.go("desktop")
    scene = app.scenes.current
    scene.draw(app.screen)
    assert "concentr" in scene._risk_badge_reasons.lower()


def test_risk_badge_click_opens_portfolio(app):
    app.scenes.go("desktop")
    scene = app.scenes.current
    scene.draw(app.screen)
    r = scene._risk_badge_rect
    scene.handle_event(_click(r.centerx, r.centery))
    assert any(w.key == "book" for w in scene.wm.windows)   # app native, cf. apps/app_book.py


def test_settings_screen_has_experience_mode_row(app):
    from core import experience_mode as XP
    XP.set_mode("expert")
    app.scenes.go("settings", return_to="desktop")
    sc = app.scenes.current
    labels = [label for label, _btns in sc.rows]
    assert any("page" in lbl.lower() for lbl in labels)


def test_changing_experience_mode_persists_via_core_module(app):
    from core import experience_mode as XP
    XP.set_mode("expert")
    app.scenes.go("settings", return_to="desktop")
    sc = app.scenes.current
    row = next(btns for label, btns in sc.rows if "page" in label.lower())
    beginner_btn = next(b for b in row if b.action == ("xpmode", "beginner"))
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=beginner_btn.rect.center)
    sc.handle_event(click)
    assert XP.get_mode() == "beginner"
    XP.set_mode("expert")   # restaure pour les autres tests


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
    assert any(win.key == "company" for win in desk.wm.windows)


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
    assert any(w.key == "shop" for w in desk.wm.windows)   # app native, cf. apps/app_shop.py


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
    w = desk._open_scene_window("career")   # scène encore hébergée (mission est native)
    hosted = w.app_obj.scene
    assert hosted.return_to == "terminal"
    assert any(win.key == "scene:career" for win in desk.wm.windows)

    hosted.app.scenes.back(hosted.return_to)

    assert not any(win.key == "scene:career" for win in desk.wm.windows)
    assert app.scenes.current_name == "desktop"   # jamais de bascule plein écran


def test_back_does_not_force_open_a_window_that_was_not_already_open(app):
    """Après le correctif, `back()` ne fait QUE fermer la fenêtre appelante —
    il n'ouvre plus jamais la fenêtre cible (return_to) si elle n'était pas
    déjà ouverte, contrairement à l'ancien comportement basé sur go().
    Utilise "career" (scène encore HÉBERGÉE, pas une app native) pour
    exercer le mécanisme générique SceneHostApp/_Router.back()."""
    app.gs.player.grade_index = 9
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.wm.close(next(w for w in desk.wm.windows if w.key == "scene:terminal"))
    w = desk._open_scene_window("career")
    career = w.app_obj.scene
    career.app.scenes.back(career.return_to)
    assert not any(win.key == "scene:career" for win in desk.wm.windows)
    assert not any(win.key == "scene:terminal" for win in desk.wm.windows)


def test_deliberate_forward_navigation_to_terminal_still_opens_it(app):
    """Contrairement à un bouton retour, une navigation délibérée vers le
    terminal (ex. « Acheter » depuis les états financiers, qui pré-remplit
    une commande BUY) doit continuer à ouvrir/focaliser la fenêtre terminal
    SANS fermer la fenêtre appelante — seul go(self.return_to) est
    requalifié en back(), pas les go() explicites vers un autre nom de
    scène. (États financiers reste hébergé — Fiche société, elle, est
    devenue une app native qui ouvre Trading plutôt que de taper une
    commande, cf. apps/app_company.py::handle_event.)"""
    app.gs.player.grade_index = 9
    app.gs.player.cash = 5_000_000.0
    app.scenes.go("desktop")
    desk = app.scenes.current
    tk = app.market.top_companies(n=1)[0]["ticker"]
    w = desk._open_scene_window("financials", ticker=tk, return_to="markethub")
    fin = w.app_obj.scene
    fin.update(0.016)
    fin.draw(app.screen)
    fin.handle_event(_click(fin.buy_btn.rect.centerx, fin.buy_btn.rect.centery))
    assert any(win.key == "scene:financials" for win in desk.wm.windows)
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
    """"risk" (scène encore HÉBERGÉE, pas une app native comme "markethub"
    désormais) pour exercer le routeur générique SceneHostApp/_Router."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    # ouvre une scène hébergée via le menu Démarrer
    w = desk._open_scene_window("risk")
    assert any(win.key == "scene:risk" for win in desk.wm.windows)
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
    # certaines scènes du catalogue (ex. "markethub") sont redirigées vers une
    # app NATIVE (clé sans préfixe) plutôt qu'hébergées (clé "scene:<nom>") —
    # cf. DesktopScene._open_scene_window.
    assert any(win.key in (f"scene:{scene}", scene) for win in desk.wm.windows)
    assert desk.start_open is False


@pytest.mark.parametrize("key", ["book", "markethub", "inbox", "alerts"])
def test_native_app_redirects_close_the_start_menu(app, key):
    """Régression : les redirections vers les apps NATIVES (Portefeuille,
    Marché, Inbox, Alertes — cf. _open_scene_window) retournaient tôt, AVANT
    la ligne `self.start_open = False` du chemin générique d'hébergement de
    scène — ouvrir l'une de ces apps depuis le menu Démarrer laissait le menu
    ouvert par-dessus la fenêtre nouvellement ouverte."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk._open_start_menu()
    assert desk.start_open is True
    desk._open_scene_window(key)
    assert desk.start_open is False


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
    assert w.app_obj.ticker   # app native : le ticker par défaut est déjà configuré


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
    desk.handle_event(_up(rect.centerx, rect.centery))
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
    assert any(w.key == "dilemma" for w in desk.wm.windows)


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
    # apps NATIVES migrées (netteté) : clé nue, pas "scene:<nom>".
    _NATIVE = {"book", "markethub", "dilemma", "review", "mission", "deals", "shop",
               "explorer"}
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    for key, _label, _kind, scene in QUICK_APPS:
        if scene is None:      # "save" : action instantanée, pas une fenêtre
            continue
        desk._launch(key)
        expected = scene if scene in _NATIVE else f"scene:{scene}"
        assert any(w.key == expected for w in desk.wm.windows), key


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
    desk.handle_event(_up(rect.centerx, rect.centery))
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
    w = next(win for win in desk.wm.windows if win.key == "dilemma")
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
    assert any(win.key == "book" for win in desk.wm.windows)   # app native, cf. apps/app_book.py


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


def test_desktop_marks_onboarding_seen_when_guide_wont_show():
    """L'ex-carte d'accueil machine a été FUSIONNÉE dans le guide de
    démarrage : quand le guide ne s'affichera pas (déjà lu, vétéran,
    sandbox), l'arrivée sur le bureau marque directement l'accueil comme vu
    pour que le tutoriel guidé démarre sans étape fantôme."""
    from core import desktop_onboarding
    desktop_onboarding.reset()
    a = main.App()
    a.ensure_market()
    a.gs.player.flags["intro_guide_done"] = True    # guide déjà lu
    a.scenes.go("desktop")
    assert desktop_onboarding.seen() is True
    desktop_onboarding.mark_seen()                  # laisse l'état propre pour la suite


def test_desktop_keeps_onboarding_unseen_while_guide_is_active():
    """Tant que le guide de démarrage (modal) est affiché, l'accueil n'est
    pas marqué vu à l'arrivée : c'est SA fermeture qui le marque (cf.
    _close_intro_guide) — le tutoriel guidé ne doit pas se superposer."""
    from core import desktop_onboarding
    desktop_onboarding.reset()
    a = main.App()
    a.ensure_market()          # grade 0, jour 1 : guide actif
    a.scenes.go("desktop")
    desk = a.scenes.current
    assert desk._intro_guide_active() is True
    assert desktop_onboarding.seen() is False
    desk._close_intro_guide()
    assert desktop_onboarding.seen() is True
    assert a.gs.player.flags.get("intro_guide_done") is True
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


# ==================================== réorganisation des icônes (glisser) =====
def test_small_click_on_icon_still_launches_without_moving(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    r, _kind, _label = desk._icon_rects["research"]
    desk.handle_event(_click(r.centerx, r.centery))
    assert desk._icon_drag is not None
    desk.handle_event(_up(r.centerx, r.centery))
    assert desk._icon_drag is None
    assert any(w.key == "research" for w in desk.wm.windows)


def test_dragging_an_icon_past_threshold_does_not_launch(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    r, _kind, _label = desk._icon_rects["research"]
    other_key = next(k for k in desk._icon_rects if k != "research")
    other_r, _k2, _l2 = desk._icon_rects[other_key]
    desk.handle_event(_down(r.centerx, r.centery))
    desk.handle_event(_motion(other_r.centerx, other_r.centery))
    desk.handle_event(_up(other_r.centerx, other_r.centery))
    assert not any(w.key == "research" for w in desk.wm.windows)


def test_dragging_an_icon_persists_custom_order(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    default_order = list(desk._icon_rects.keys())
    first_key = default_order[0]
    last_key = default_order[-1]
    first_r, _k, _l = desk._icon_rects[first_key]
    last_r, _k2, _l2 = desk._icon_rects[last_key]
    desk.handle_event(_down(first_r.centerx, first_r.centery))
    desk.handle_event(_motion(last_r.centerx, last_r.centery))
    desk.handle_event(_up(last_r.centerx, last_r.centery))
    order = app.gs.player.flags.get("desktop_icon_order")
    assert order is not None
    # déposée près de la dernière icône : plus du tout en tête, et voisine
    # de sa cible (insérée juste avant, cf. _reorder_icon).
    assert order.index(first_key) != 0
    assert abs(order.index(first_key) - order.index(last_key)) == 1
    # persisté : un nouveau dessin applique bien le nouvel ordre
    desk.draw(app.screen)
    assert list(desk._icon_rects.keys())[0] != first_key


def test_newly_unlocked_icon_appends_to_end_of_custom_order(app):
    """Une icône jamais vue (pas encore dans l'ordre sauvegardé) ne doit ni
    planter ni écraser silencieusement l'ordre choisi par le joueur — elle
    se glisse à la fin."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.draw(app.screen)
    keys_before = list(desk._icon_rects.keys())
    app.gs.player.flags["desktop_icon_order"] = keys_before[:3]   # ordre partiel
    desk.draw(app.screen)
    shown = list(desk._icon_rects.keys())
    assert shown[:3] == keys_before[:3]
    assert set(shown) == set(keys_before)   # rien perdu


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
    assert sa._clipboard["data"] == [["10"], ["20"]]
    assert sa._clipboard["origin"] == (0, 1)   # colonne A, ligne 1
    sa.sel = "C1"
    sa.handle_event(_ctrl_key(pygame.K_v), rect)
    assert sa.sheet.get_raw("C1") == "10"
    assert sa.sheet.get_raw("C2") == "20"


def test_sheet_app_paste_shifts_relative_references(app):
    """Comportement Excel : une formule collée ailleurs voit ses références
    décalées du même vecteur que la copie (sauf ancres $)."""
    sa = SheetApp(app)
    sa.on_open()
    sa.sheet.set("A1", "10"); sa.sheet.set("A2", "20")
    sa.sheet.set("B1", "=A1*2")
    sa.range_anchor = sa.range_end = "B1"
    sa._copy_range()
    sa.sel = "B2"
    sa._paste_range()
    assert sa.sheet.get_raw("B2") == "=A2*2"
    assert sa.sheet.get_value("B2") == 40.0


def test_sheet_app_paste_respects_absolute_anchors(app):
    sa = SheetApp(app)
    sa.on_open()
    sa.sheet.set("A1", "5"); sa.sheet.set("A2", "7")
    sa.sheet.set("B1", "=$A$1+A1")
    sa.range_anchor = sa.range_end = "B1"
    sa._copy_range()
    sa.sel = "B2"
    sa._paste_range()
    assert sa.sheet.get_raw("B2") == "=$A$1+A2"
    assert sa.sheet.get_value("B2") == 12.0


def test_sheet_app_paste_out_of_grid_reference_becomes_ref_error(app):
    """Décaler une référence au-dessus de la ligne 1 donne une erreur (#REF),
    pas un plantage ni une référence silencieusement fausse."""
    sa = SheetApp(app)
    sa.on_open()
    sa.sheet.set("B2", "=B1*2")
    sa.range_anchor = sa.range_end = "B2"
    sa._copy_range()
    sa.sel = "B1"        # colle une ligne PLUS HAUT : B1 -> B0 impossible
    sa._paste_range()
    assert "#REF" in sa.sheet.get_raw("B1")
    assert sa.sheet.get_value("B1") == "#ERR"


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


# ============================== mode "j'investis X€" (app Trading) ============
def test_trading_app_defaults_to_shares_mode(app):
    ta = TradingApp(app)
    ta.on_open()
    assert ta.qty_mode == "shares"
    tk = app.market.companies[0]["ticker"]
    ta.qty_text = "7"
    assert ta._qty_for_ticker(tk) == 7.0


def test_trading_app_amount_mode_converts_to_shares(app):
    tk = app.market.companies[0]["ticker"]
    price = app.market.price_of(tk)
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_mode = "amount"
    ta.qty_text = f"{price * 3:g}"
    assert ta._qty_for_ticker(tk) == pytest.approx(3.0)


def test_trading_app_amount_mode_rounds_down_to_whole_shares(app):
    tk = app.market.companies[0]["ticker"]
    price = app.market.price_of(tk)
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_mode = "amount"
    ta.qty_text = f"{price * 3.9:g}"
    assert ta._qty_for_ticker(tk) == 3.0


def test_trading_app_mode_toggle_click_switches_mode_and_default_amount(app):
    ta = TradingApp(app)
    ta.on_open()
    rect = pygame.Rect(0, 0, 840, 520)
    ta.draw(app.screen, rect)
    r = ta._qty_mode_rects["amount"]
    ta.handle_event(_click(r.centerx, r.centery), rect)
    assert ta.qty_mode == "amount"
    assert ta.qty_text == "1000"
    ta.draw(app.screen, rect)
    r2 = ta._qty_mode_rects["shares"]
    ta.handle_event(_click(r2.centerx, r2.centery), rect)
    assert ta.qty_mode == "shares"
    assert ta.qty_text == "10"


def test_trading_app_buy_in_amount_mode_buys_correct_share_count(app):
    tk = app.market.companies[0]["ticker"]
    price = app.market.price_of(tk)
    app.gs.player.cash = 1_000_000.0
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_mode = "amount"
    ta.qty_text = f"{price * 4:g}"
    ta._do_buy(tk)
    assert app.gs.player.portfolio[tk]["shares"] == pytest.approx(4.0)


def test_trading_app_amount_presets_differ_from_share_presets(app):
    from apps.app_trading import AMOUNT_PRESETS, QTY_PRESETS
    assert AMOUNT_PRESETS != QTY_PRESETS
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_mode = "amount"
    rect = pygame.Rect(0, 0, 840, 520)
    ta.draw(app.screen, rect)
    assert set(ta._preset_rects) == set(AMOUNT_PRESETS)


def test_trading_app_amount_mode_zero_price_yields_zero_qty(app, monkeypatch):
    tk = app.market.companies[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    ta.qty_mode = "amount"
    ta.qty_text = "1000"
    monkeypatch.setattr(ta.market, "price_of", lambda _tk: None)
    assert ta._qty_for_ticker(tk) == 0.0


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
    # l'Inbox est désormais une app NATIVE du bureau (clé "inbox", plus
    # d'hébergement de la scène plein écran — cf. apps/app_inbox.py)
    assert any(w.key == "inbox" for w in desk.wm.windows)


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


# ============================ indicateur discret « sauvegardé » (topbar) ======
def test_saved_ago_label_empty_when_never_saved(app):
    from scenes.scene_desktop import _saved_ago_label
    app.gs.last_saved = 0.0
    assert _saved_ago_label(app.gs) == ""


def test_saved_ago_label_instant_just_after_save(app):
    import time

    from scenes.scene_desktop import _saved_ago_label
    app.gs.last_saved = time.time()
    assert "instant" in _saved_ago_label(app.gs)


def test_saved_ago_label_seconds_and_minutes(app):
    import time

    from scenes.scene_desktop import _saved_ago_label
    app.gs.last_saved = time.time() - 30
    assert _saved_ago_label(app.gs) == "· Sauvegardé il y a 30s"
    app.gs.last_saved = time.time() - 125
    assert _saved_ago_label(app.gs) == "· Sauvegardé il y a 2min"


def test_topbar_draws_without_error_with_and_without_saved_label(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.gs.last_saved = 0.0
    desk.draw(app.screen)   # jamais sauvegardé : ne doit pas lever
    import time
    app.gs.last_saved = time.time()
    desk.draw(app.screen)   # juste sauvegardé : ne doit pas lever


def test_settings_screen_has_autosave_cadence_row(app):
    app.scenes.go("settings", return_to="desktop")
    sc = app.scenes.current
    labels = [label for label, _btns in sc.rows]
    assert any("auto" in lbl.lower() for lbl in labels)


def test_changing_autosave_cadence_persists_via_core_module(app):
    from core import autosave_settings as AS
    app.scenes.go("settings", return_to="desktop")
    sc = app.scenes.current
    row = next(btns for label, btns in sc.rows if "auto" in label.lower())
    disabled_btn = next(b for b in row if b.action == ("autosave", None))
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=disabled_btn.rect.center)
    sc.handle_event(click)
    assert AS.get_interval() is None
    AS.set_interval(0.0)   # restaure la valeur par défaut pour les autres tests


# =========================== widget calendrier macro (bureau) =================
def _macro_event(eid, event_type, resolve_step):
    return {"id": eid, "event_type": event_type, "resolve_step": resolve_step,
            "consensus": "en ligne"}


def test_calendar_widget_hidden_when_no_events(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.gs.player.macro_events = []
    desk.draw(app.screen)
    assert desk._calendar_rect is None


def test_calendar_widget_shows_up_to_three_soonest_events(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    step_now = app.market.step_count
    app.gs.player.macro_events = [
        _macro_event(1, "Inflation (CPI)", step_now + 10),
        _macro_event(2, "Emploi (NFP)", step_now + 2),
        _macro_event(3, "Croissance (PIB)", step_now + 6),
        _macro_event(4, "Indice PMI (manufacturier/services)", step_now + 20),
    ]
    desk.draw(app.screen)
    assert desk._calendar_rect is not None


def test_calendar_widget_click_opens_calendar_window(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    step_now = app.market.step_count
    app.gs.player.macro_events = [_macro_event(1, "Inflation (CPI)", step_now + 4)]
    desk.draw(app.screen)
    r = desk._calendar_rect
    assert r is not None
    desk.handle_event(_click(r.centerx, r.centery))
    assert any(w.key == "scene:calendar" for w in desk.wm.windows)


def test_calendar_widget_stacks_above_todo_widget_when_both_present(app):
    from core import todo as todo_mod
    app.scenes.go("desktop")
    desk = app.scenes.current
    step_now = app.market.step_count
    app.gs.player.macro_events = [_macro_event(1, "Inflation (CPI)", step_now + 4)]
    has_todo = bool(todo_mod.suggestions(app.gs.player, app.market))
    desk.draw(app.screen)
    if has_todo:
        assert desk._calendar_rect.bottom < desk._todo_rects[0][0].top


# ============================== espace de travail (disposition sauvegardée) ===
def test_layout_flag_is_synced_continuously(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk._launch("research")
    desk.update(0.016)
    layout = app.gs.player.flags.get("desktop_layout")
    assert layout is not None
    assert any(e.get("kind") == "app" and e.get("key") == "research" for e in layout)
    assert any(e.get("kind") == "terminal" for e in layout)


def test_layout_snapshot_captures_rect_minimized_pinned(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("watchlist")
    w.rect = pygame.Rect(50, 60, 300, 200)
    w.pinned = True
    desk.update(0.016)
    layout = app.gs.player.flags["desktop_layout"]
    entry = next(e for e in layout if e.get("key") == "watchlist")
    assert entry["rect"] == [50, 60, 300, 200]
    assert entry["pinned"] is True
    assert entry["minimized"] is False


def test_layout_snapshot_captures_scene_window_kwargs(app):
    # "financials" reste une scène HÉBERGÉE (contrairement à "company",
    # devenue une app native sans kwargs de fenêtre à snapshotter — cf.
    # apps/app_company.py) : c'est elle qui exerce ce chemin de sauvegarde.
    app.scenes.go("desktop")
    desk = app.scenes.current
    tk = app.market.top_companies(n=1)[0]["ticker"]
    desk._open_scene_window("financials", ticker=tk, return_to="markethub")
    desk.update(0.016)
    layout = app.gs.player.flags["desktop_layout"]
    entry = next(e for e in layout if e.get("kind") == "scene" and e.get("name") == "financials")
    assert entry["kwargs"].get("ticker") == tk


def test_pinned_layout_save_and_restore_reopens_windows(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk._launch("research")
    desk._launch("calculator")
    desk.update(0.016)
    desk._save_pinned_layout()
    assert app.gs.player.flags.get("desktop_layout_pinned")

    desk._close_all_windows()
    assert not any(w.key == "research" for w in desk.wm.windows)
    assert not any(w.key == "calculator" for w in desk.wm.windows)

    desk._restore_pinned_layout()
    assert any(w.key == "research" for w in desk.wm.windows)
    assert any(w.key == "calculator" for w in desk.wm.windows)


def test_restore_pinned_layout_is_a_noop_without_a_saved_snapshot(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.gs.player.flags.pop("desktop_layout_pinned", None)
    n_before = len(desk.wm.windows)
    desk._restore_pinned_layout()
    assert len(desk.wm.windows) == n_before


def test_pinned_layout_restores_position_and_pin_state(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._launch("sheet")
    w.rect = pygame.Rect(80, 90, 500, 400)
    w.pinned = True
    desk.update(0.016)
    desk._save_pinned_layout()
    w.rect = pygame.Rect(0, 0, 100, 100)
    w.pinned = False

    desk._restore_pinned_layout()
    restored = next(win for win in desk.wm.windows if win.key == "sheet")
    assert restored.rect == pygame.Rect(80, 90, 500, 400)
    assert restored.pinned is True


def test_seeded_default_layout_opens_market_and_portfolio_for_general_track():
    a = main.App()
    a.ensure_market()
    a.gs.player.grade_index = 9
    a.scenes.go("desktop")
    desk = a.scenes.current
    keys = {w.key for w in desk.wm.windows}
    assert "markethub" in keys   # apps NATIVES, cf. apps/app_markethub.py / apps/app_book.py
    assert "book" in keys


def test_seeded_default_layout_includes_track_scene():
    a = main.App()
    a.ensure_market()
    a.gs.player.grade_index = 9
    a.gs.player.track = "Risk"
    a.scenes.go("desktop")
    desk = a.scenes.current
    keys = {w.key for w in desk.wm.windows}
    assert "scene:risk" in keys


def test_seeded_default_layout_only_happens_once_per_career():
    """Une fois `desktop_seeded` posé, fermer toutes les fenêtres et revenir
    au bureau (même App()) ne doit PAS rouvrir la disposition de départ."""
    a = main.App()
    a.ensure_market()
    a.gs.player.grade_index = 9
    a.scenes.go("desktop")
    desk = a.scenes.current
    assert a.gs.player.flags.get("desktop_seeded") is True
    for w in list(desk.wm.windows):
        if w.key != "scene:terminal":
            desk.wm.close(w)
    desk._restore_layout()   # simule un 2e appel (ne devrait rien rouvrir)
    keys = {w.key for w in desk.wm.windows}
    assert "scene:markethub" not in keys


def test_seeded_default_layout_skipped_when_saved_layout_exists():
    """Une carrière REPRISE (disposition déjà sauvegardée) ne doit jamais
    déclencher une 2e disposition de départ par-dessus celle sauvegardée."""
    a1 = main.App()
    a1.ensure_market()
    a1.gs.player.grade_index = 9
    a1.scenes.go("desktop")
    for w in list(a1.scenes.current.wm.windows):
        if w.key != "scene:terminal":
            a1.scenes.current.wm.close(w)
    a1.scenes.current._launch("research")
    a1.scenes.current.update(0.016)
    saved_layout = a1.gs.player.flags["desktop_layout"]
    assert "scene:book" not in {e.get("name") for e in saved_layout if e.get("kind") == "scene"}

    a2 = main.App()
    a2.ensure_market()
    a2.gs.player.flags["desktop_layout"] = saved_layout
    a2.scenes.go("desktop")
    desk2 = a2.scenes.current
    keys = {w.key for w in desk2.wm.windows}
    assert "research" in keys
    assert "scene:book" not in keys   # pas de disposition de départ en plus


def test_layout_auto_restores_on_first_desktop_entry_of_a_fresh_app():
    """Une NOUVELLE instance App() (donc une nouvelle DesktopScene) doit
    rouvrir automatiquement la disposition mémorisée dans le player chargé —
    contrairement au réglage manuel figé (`desktop_layout_pinned`), celui-ci
    reflète la dernière disposition en cours au moment de la sauvegarde."""
    a1 = main.App()
    a1.ensure_market()
    a1.gs.player.grade_index = 9
    a1.scenes.go("desktop")
    desk1 = a1.scenes.current
    desk1._launch("research")
    desk1.update(0.016)
    saved_layout = a1.gs.player.flags["desktop_layout"]

    a2 = main.App()
    a2.ensure_market()
    a2.gs.player.flags["desktop_layout"] = saved_layout
    a2.scenes.go("desktop")
    desk2 = a2.scenes.current
    assert any(w.key == "research" for w in desk2.wm.windows)


# --------------------------------------------- assistant « que faire ? » (F1)
def test_f1_opens_assistant_card(app):
    app.scenes.go("desktop")
    scene = app.scenes.current
    assert scene._assistant_open is False
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, mod=0))
    assert scene._assistant_open is True


def test_f1_does_not_open_over_pending_quarter_card(app):
    """Régression : F1 ouvrait l'Assistant PAR-DESSUS la carte « Bilan du
    trimestre » déjà affichée — deux cartes modales superposées au même
    endroit de l'écran, celle du dessous devenant injoignable."""
    app.scenes.go("desktop")
    scene = app.scenes.current
    app.gs.player.flags["last_quarter_report"] = {"quarter": 1, "total": 3, "done": 2}
    assert scene._quarter_card_pending() is not None
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1, mod=0))
    assert scene._assistant_open is False
    del app.gs.player.flags["last_quarter_report"]




def test_ctrl_slash_does_not_open_search_over_pending_quarter_card(app):
    """Régression (bug pré-existant, même famille que F1) : Ctrl+/ ouvrait la
    recherche globale PAR-DESSUS la carte « Bilan du trimestre »."""
    app.scenes.go("desktop")
    scene = app.scenes.current
    app.gs.player.flags["last_quarter_report"] = {"quarter": 1, "total": 3, "done": 2}
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SLASH, mod=pygame.KMOD_CTRL)
    scene.handle_event(ev)
    assert scene._search_open is False
    del app.gs.player.flags["last_quarter_report"]


def test_quarter_card_suppressed_while_search_open(app):
    app.scenes.go("desktop")
    scene = app.scenes.current
    scene._open_search()
    app.gs.player.flags["last_quarter_report"] = {"quarter": 1, "total": 3, "done": 2}
    scene.draw(app.screen)
    assert scene._qcard_rects == {}
    del app.gs.player.flags["last_quarter_report"]



def test_assistant_escape_closes(app):
    app.scenes.go("desktop")
    scene = app.scenes.current
    scene._assistant_open = True
    scene.update(0.016)
    scene.draw(app.screen)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
    assert scene._assistant_open is False


def test_assistant_shows_top_suggestion_and_go_button(app):
    app.scenes.go("desktop")
    scene = app.scenes.current
    scene.app.gs.player.pending_review = True
    scene._assistant_open = True
    scene.draw(app.screen)
    btn, target_scene = scene._assistant_rects["go"]
    assert target_scene == "review"
    assert btn is not None


def test_assistant_go_button_opens_target_scene_and_closes_card(app):
    app.scenes.go("desktop")
    scene = app.scenes.current
    scene.app.gs.player.pending_review = True
    scene._assistant_open = True
    scene.draw(app.screen)
    btn, _target = scene._assistant_rects["go"]
    scene.handle_event(_click(*btn.center))
    assert scene._assistant_open is False
    assert any(w.key == "review" for w in scene.wm.windows)


def test_assistant_reassures_when_nothing_pending(app):
    app.scenes.go("desktop")
    scene = app.scenes.current
    scene._assistant_open = True
    scene.draw(app.screen)
    assert "go" not in scene._assistant_rects


def test_assistant_click_outside_card_closes_it(app):
    app.scenes.go("desktop")
    scene = app.scenes.current
    scene._assistant_open = True
    scene.draw(app.screen)
    scene.handle_event(_click(2, 2))
    assert scene._assistant_open is False


# ------------------------------------------- résumé « en votre absence »
def _empty_desktop(app):
    app.scenes.go("desktop")
    scene = app.scenes.current
    for w in list(scene.wm.windows):
        if w.key != "scene:terminal":
            scene.wm.close(w)
    return scene





# =========================== audit V1.0 : robustesse & débordements UI ========
def test_scene_host_draw_survives_degenerate_rect(app):
    """Régression : une fenêtre à taille dégénérée (rect restauré d'une
    sauvegarde corrompue) faisait planter smoothscale (taille négative) à
    chaque frame — sauvegarde briquée."""
    from apps.scene_host import SceneHostApp
    host = SceneHostApp(app, "markethub", "Marché", {})
    surf = pygame.Surface((200, 200))
    host.draw(surf, pygame.Rect(10, 10, 0, 0))      # ne doit pas lever
    host.draw(surf, pygame.Rect(10, 10, -5, 12))    # ne doit pas lever


def test_scene_host_redraws_content_every_frame_at_same_size():
    """Régression : SceneHostApp mettait en cache le smoothscale et ne
    rescale que si la taille changeait. L'offscreen est pourtant redessiné
    à chaque frame : l'image affichée restait donc figée tant que la fenêtre
    gardait la même taille — les fenêtres semblaient ne plus réagir au clic
    car le feedback visuel n'était pas mis à jour."""
    import main
    from apps.scene_host import SceneHostApp
    a = main.App()
    a.ensure_market()
    host = SceneHostApp(a, "markethub", "Marché", {})
    host.on_open()
    rect = pygame.Rect(10, 10, 400, 300)

    calls = []
    orig_smoothscale = pygame.transform.smoothscale
    def tracking_smoothscale(surf, size, dest=None):
        # la variante à 3 arguments (dest_surface réutilisée entre les frames)
        # reste un rescale par frame — c'est l'invariant vérifié ici.
        calls.append(size)
        if dest is not None:
            return orig_smoothscale(surf, size, dest)
        return orig_smoothscale(surf, size)
    pygame.transform.smoothscale = tracking_smoothscale
    try:
        host.draw(pygame.Surface((500, 500)), rect)
        host.draw(pygame.Surface((500, 500)), rect)
    finally:
        pygame.transform.smoothscale = orig_smoothscale

    # même taille pour les deux draw : smoothscale doit quand même être appelé
    # deux fois car l'offscreen a été redessiné entre-temps.
    assert len(calls) == 2
    assert calls[0] == (rect.w, rect.h)
    assert calls[1] == (rect.w, rect.h)


def test_apply_layout_clamps_degenerate_rects(app):
    """Un rect de disposition hors bornes (fichier de save édité, autre
    résolution) est ramené à une taille/position jouables. Format
    kind="scene" volontairement ANCIEN (rétrocompatibilité d'une sauvegarde
    d'avant la conversion en app native, cf. apps/app_markethub.py) : la
    redirection de _open_scene_window doit rester transparente."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    layout = [{"kind": "scene", "name": "markethub", "kwargs": {},
               "rect": [5000, -300, 3, 2], "minimized": False, "pinned": False}]
    desk._apply_layout(layout)
    w = next(w for w in desk.wm.windows if w.key == "markethub")
    assert w.rect.w >= 300 and w.rect.h >= 200
    assert 0 <= w.rect.x <= config.SCREEN_WIDTH - 60
    assert w.rect.y >= 0


def test_taskbar_entries_stay_on_screen_with_many_windows(app):
    """Régression : au-delà d'une poignée de fenêtres, les entrées à largeur
    fixe de la barre des tâches débordaient de l'écran — fenêtres
    infocalisables. La largeur est désormais adaptative."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    for sc in ("markethub", "book", "graph", "inbox", "news", "career", "risk",
               "quant", "alerts", "shop", "explorer", "glossary"):
        desk._open_scene_window(sc)
    desk.draw(app.screen)
    assert len(desk._task_rects) >= 13
    assert all(r.right <= config.SCREEN_WIDTH for r in desk._task_rects.values())


def test_settings_all_rows_and_shortcuts_button_fit_on_screen(app):
    """Régression : l'écran Réglages a gagné des lignes au fil des versions
    et les dernières (Routine, Vitesse) + le bouton Raccourcis passaient sous
    le bord de l'écran — injoignables."""
    app.scenes.go("settings", return_to="desktop")
    sc = app.scenes.current
    assert sc.rows[-1][1][0].rect.bottom <= config.footer_y()
    assert sc.shortcuts_btn.rect.bottom <= config.footer_y()


# ==================== audit V1.0 (2e passe) : collisions/débordements =========
def test_achievements_chips_wrap_and_stay_on_screen(app):
    app.scenes.go("achievements")
    sc = app.scenes.current
    sc.update(0.016)
    sc.draw(app.screen)
    assert sc._chip_rects
    assert all(r.right <= config.SCREEN_WIDTH - 20 for r in sc._chip_rects.values())


def test_trading_app_min_width_leaves_room_for_row_buttons():
    """Sous ~640 px, les colonnes COURS/POSSÉDÉ passaient sous le bloc de
    boutons ORD/VENDRE/ACHETER — la largeur mini de l'app l'empêche désormais."""
    assert TradingApp.min_size[0] >= 640


def test_watchlist_app_min_width_prevents_row_collisions():
    from apps.app_watchlist import WatchlistApp
    assert WatchlistApp.min_size[0] >= 360


def test_financials_fiche_button_label_fits_inside_button(app):
    tk = app.market.companies[0]["ticker"]
    app.scenes.go("financials", ticker=tk)
    sc = app.scenes.current
    from ui import fonts as F
    assert F.body(bold=True).size(sc.fiche_btn.label)[0] <= sc.fiche_btn.rect.w - 8


# ==================== audit V1.0 (3e passe) : glyphes non couverts ============
# La police embarquée (JetBrains Mono) ne couvre pas tous les glyphes Unicode
# utilisés par erreur (emoji, symboles rares) : ils s'affichaient en "tofu"
# (glyphe .notdef). cf. ui/desktop_icons.py pour la même limite déjà
# documentée sur les icônes. Ce test vérifie qu'aucun rendu produit un signal
# identique à celui d'un caractère certainement absent (zone d'usage privé).

_UNSUPPORTED_GLYPHS = [
    "✉", "📰", "ℹ", "↺", "⇩", "⏱", "⏳", "⏸", "▦", "▮", "★", "⚑", "⚙",
    "⤢", "⧉", "🎓", "💹", "📌", "📒", "📖", "📘", "🔍", "🔒", "🔔", "🔥",
    "🖥", "🛒", "🛠", "🤝",
]


def test_font_glyph_coverage_still_missing_for_known_unsupported_set(app):
    """Sanity check de la méthode de détection elle-même : ces glyphes sont
    connus pour ne pas être couverts par la police embarquée (vérifié par
    comparaison de signature avec un caractère de zone d'usage privé, garanti
    absent). Si ce test échoue, la police a changé — revoir cette liste."""
    from ui import fonts as F
    f = F.tiny()
    pua = pygame.image.tostring(f.render(chr(0xE000), True, (255, 255, 255)), "RGBA")
    for ch in _UNSUPPORTED_GLYPHS:
        sig = pygame.image.tostring(f.render(ch, True, (255, 255, 255)), "RGBA")
        assert sig == pua, f"{ch!r} semble maintenant couvert — on peut le réutiliser"


def test_no_rendered_ui_string_uses_unsupported_glyphs():
    """Régression : plusieurs écrans (notifications, TUTO, lock badges, SHOP,
    onboarding...) utilisaient des glyphes non couverts (✉ 📰 📘 🔒 🔥 ⏳ ▮
    ★ ⚙ ⇩ ⤢ ⧉ 🎓 📖 🔍 🔔 🛒 🛠 ℹ ↺) qui s'affichaient en boîte vide. On
    parcourt l'AST de chaque module pour n'examiner que les littéraux de
    chaîne RÉELLEMENT utilisés (pas les docstrings de module/classe/fonction,
    qui documentent légitimement la limite — cf. ui/desktop_icons.py)."""
    import ast
    import glob

    def _string_constants(tree):
        docstring_ids = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                body = getattr(node, "body", None)
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    docstring_ids.add(id(body[0].value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and id(node) not in docstring_ids:
                yield node

    offenders = []
    for fn in (glob.glob("scenes/*.py") + glob.glob("apps/*.py")
               + glob.glob("ui/*.py") + glob.glob("core/*.py")):
        with open(fn, encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src, filename=fn)
        for node in _string_constants(tree):
            for ch in _UNSUPPORTED_GLYPHS:
                if ch in node.value:
                    offenders.append(f"{fn}:{node.lineno}: {ch!r} in {node.value!r}")
    assert not offenders, "glyphes non couverts trouvés :\n" + "\n".join(offenders)


def test_notifications_screen_renders_without_glyph_tofu(app):
    """L'écran notifications utilisait ✉/📰 (non couverts) comme préfixes de
    ligne et dans la légende — remplacés par des tags texte (MSG/NEWS/M/N)."""
    p = app.gs.player
    p.inbox.append({"kind": "manager", "subject": "Test", "body": "Corps.",
                     "day": p.day, "read": False})
    app.scenes.go("notifications", return_to="desktop")
    sc = app.scenes.current
    sc.update(0.016)
    sc.draw(app.screen)
    assert sc.row_rects


# ==================== guide de démarrage + nouveautés de promotion ===========
def _fresh_career_desktop(app):
    """Bureau d'un DÉBUT de carrière (grade 0, jour 1) — le guide de
    démarrage doit s'y afficher."""
    p = app.gs.player
    p.grade_index = 0
    p.day = 1
    p.flags.pop("intro_guide_done", None)
    p.flags.pop("veteran", None)
    app.scenes.go("desktop")
    desk = app.scenes.current
    desk.update(0.016)
    desk.draw(app.screen)
    return desk


def test_intro_guide_active_only_for_fresh_careers(app):
    desk = _fresh_career_desktop(app)
    assert desk._intro_guide_active()
    # plus affiché une fois lu
    app.gs.player.flags["intro_guide_done"] = True
    assert not desk._intro_guide_active()
    # jamais pour un vétéran (il connaît la boucle)
    app.gs.player.flags.pop("intro_guide_done")
    app.gs.player.flags["veteran"] = True
    assert not desk._intro_guide_active()
    # jamais après le tout début de carrière (vieille sauvegarde d'avant le guide)
    app.gs.player.flags.pop("veteran")
    app.gs.player.grade_index = 3
    assert not desk._intro_guide_active()


def test_intro_guide_is_modal_and_completes_via_next_clicks(app):
    from core import unlock_briefs
    desk = _fresh_career_desktop(app)
    # modal : un clic sur une icône du bureau est absorbé (aucune fenêtre ouverte)
    n_win = len(desk.wm.windows)
    any_icon = next(iter(desk._icon_rects.values()))[0]
    desk.handle_event(_click(*any_icon.center))
    assert len(desk.wm.windows) == n_win
    # cliquer « Suivant » sur chaque page jusqu'à « Commencer » referme et persiste
    for _ in range(unlock_briefs.intro_page_count()):
        desk.draw(app.screen)
        assert desk._guide_rects.get("next")
        desk.handle_event(_click(*desk._guide_rects["next"].center))
    assert app.gs.player.flags.get("intro_guide_done") is True
    assert not desk._intro_guide_active()


def test_intro_guide_escape_skips_and_marks_done(app):
    desk = _fresh_career_desktop(app)
    desk.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
    assert app.gs.player.flags.get("intro_guide_done") is True


def test_every_unlockable_feature_has_a_brief():
    from core import unlock_briefs, unlocks
    missing = [f for f in unlocks.UNLOCKS if f not in unlock_briefs.FEATURE_BRIEFS]
    assert not missing, f"fiches manquantes : {missing}"


def _features_at_grade(grade):
    """Fonctionnalités dont le grade EFFECTIF requis (voie "General", sans
    vétéran) est exactement `grade` — délègue à core.unlocks.features_at_grade
    plutôt que de recopier un ensemble figé à mettre à jour à la main à
    chaque réglage du calendrier de déblocage."""
    from core import unlocks
    from core.game_state import PlayerState
    p = PlayerState()
    p.track = "General"
    return set(unlocks.features_at_grade(p, grade))


def test_newly_unlocked_diff_between_grades(app):
    from core import unlock_briefs
    p = app.gs.player
    p.flags.pop("veteran", None)
    p.track = "General"
    p.grade_index = 4
    feats = unlock_briefs.newly_unlocked(p, 3)
    assert set(feats) == _features_at_grade(4)
    p.grade_index = 2
    assert set(unlock_briefs.newly_unlocked(p, 1)) == _features_at_grade(2)


def test_promotion_records_pending_unlock_briefs(app):
    """Le _finish d'un examen réussi pose flags['pending_unlock_briefs'] avec
    les fonctionnalités du nouveau grade (diff par grade EFFECTIF)."""
    p = app.gs.player
    p.grade_index = 3
    p.flags.pop("veteran", None)
    p.flags.pop("pending_unlock_briefs", None)
    app.scenes.go("evaluation")
    ev = app.scenes.current
    ev.score = len(ev.items)          # sans-faute
    ev.idx = len(ev.items)
    ev._finish()
    briefs = p.flags.get("pending_unlock_briefs")
    assert briefs and set(briefs["features"]) == _features_at_grade(p.grade_index)
    assert briefs["grade"] == p.grade


def test_unlock_brief_card_pages_then_ack(app):
    desk = _empty_desktop(app)
    p = app.gs.player
    p.flags["pending_unlock_briefs"] = {"grade": p.grade,
                                        "features": ["hedge", "mandates"]}
    desk._brief_page = 0
    desk.draw(app.screen)
    assert desk._brief_rects.get("card")
    # page 1 → « Suivant » avance sans acquitter
    desk.handle_event(_click(*desk._brief_rects["ok"].center))
    assert p.flags.get("pending_unlock_briefs")
    assert desk._brief_page == 1
    # dernière page → « C'est parti » acquitte
    desk.draw(app.screen)
    desk.handle_event(_click(*desk._brief_rects["ok"].center))
    assert p.flags.get("pending_unlock_briefs") is None


def test_unlock_brief_tuto_button_opens_tutorials_window(app):
    desk = _empty_desktop(app)
    p = app.gs.player
    p.flags["pending_unlock_briefs"] = {"grade": p.grade, "features": ["trade"]}
    desk._brief_page = 0
    desk.draw(app.screen)
    assert desk._brief_rects.get("tuto")
    desk.handle_event(_click(*desk._brief_rects["tuto"].center))
    assert p.flags.get("pending_unlock_briefs") is None
    assert any(w.key == "scene:tutorials" for w in desk.wm.windows)


# ==================== auto-pause pendant les activités de carrière ===========
def test_focus_window_auto_pauses_clock(app):
    """Une fenêtre « de travail » (mission, examen…) ouverte gèle le temps ;
    la minimiser ou la fermer le relance — le marché ne bouge pas dans le
    dos du joueur pendant une activité nécessaire à sa carrière."""
    desk = _empty_desktop(app)
    desk.update(0.016)
    assert app.sim_clock.auto_paused is False
    w = desk._open_scene_window("mission")
    desk.update(0.016)
    assert app.sim_clock.auto_paused is True
    desk.wm.toggle_minimize(w)          # mise de côté explicite → le temps reprend
    desk.update(0.016)
    assert app.sim_clock.auto_paused is False
    desk.wm.toggle_minimize(w)
    desk.update(0.016)
    assert app.sim_clock.auto_paused is True
    desk.wm.close(w)
    desk.update(0.016)
    assert app.sim_clock.auto_paused is False


def test_non_focus_window_does_not_pause_clock(app):
    desk = _empty_desktop(app)
    w = desk._open_scene_window("markethub")
    desk.update(0.016)
    assert app.sim_clock.auto_paused is False
    desk.wm.close(w)


def test_intro_guide_auto_pauses_clock(app):
    desk = _fresh_career_desktop(app)
    desk.update(0.016)
    assert app.sim_clock.auto_paused is True
    desk._close_intro_guide()
    desk.update(0.016)
    assert app.sim_clock.auto_paused is False


def test_unlock_brief_card_auto_pauses_clock(app):
    desk = _empty_desktop(app)
    p = app.gs.player
    p.flags["pending_unlock_briefs"] = {"grade": p.grade, "features": ["trade"]}
    desk.update(0.016)
    assert app.sim_clock.auto_paused is True
    desk._ack_unlock_brief()
    desk.update(0.016)
    assert app.sim_clock.auto_paused is False


# ==================== dynamisme : cours en direct dans l'app Trading =========
def test_trading_app_row_price_uses_live_canonical_path(app):
    """La liste de valeurs affichait le cours STATIQUE du pas (gelé entre deux
    pas de marché) — elle doit désormais suivre le même chemin de prix
    canonique que les graphes/tickers (core/intraday.py), donc bouger en
    accord avec le reste du jeu au fil des minutes de jeu."""
    from core import intraday
    tk = app.market.companies[0]["ticker"]
    ta = TradingApp(app)
    ta.on_open()
    app.sim_clock.game_minutes_acc = 0.0
    p0 = ta._live_price(tk)
    assert p0 == pytest.approx(app.market.price_of(tk))   # début de pas == clôture
    app.sim_clock.game_minutes_acc = 3 * intraday.QUANTIZE_MINUTES
    p1 = ta._live_price(tk)
    # le prix affiché bouge désormais AU FIL DU PAS (ne reste plus figé sur
    # la clôture statique jusqu'au prochain pas de marché).
    assert p1 != pytest.approx(p0)
    # et coïncide avec ce que verrait n'importe quel autre écran au même
    # instant (market_query.history_of — même chemin canonique partout).
    expected = app.market.history_of(tk, 1, sim_clock=app.sim_clock, day=app.gs.player.day)[-1]
    assert p1 == pytest.approx(expected)


def test_trading_app_row_price_frozen_when_region_closed(app):
    """Cohérence avec le reste du jeu : si la place de cotation est fermée à
    ce pas, le bruit intraday est coupé (core/intraday.region_open_factor)
    comme partout ailleurs — pas de mouvement erratique pendant la fermeture."""
    from core import market_hours as mh
    tk = next(c["ticker"] for c in app.market.companies
             if not mh.is_region_open(c["region"], app.market.step_count))
    ta = TradingApp(app)
    ta.on_open()
    app.sim_clock.game_minutes_acc = 5 * 90.0
    price = ta._live_price(tk)
    assert isinstance(price, float)   # ne plante pas ; reste un nombre exploitable


# ==================== fiche société : sélecteur de période du graphique =====
def test_company_sheet_chart_period_selector_matches_graph_periods(app):
    """La fiche société (onglet « graphique avancé ») expose le même choix de
    périodes que l'atelier de graphes (1J/1W/1M/3M/1A/3A/5A/MAX)."""
    from scenes.scene_graph_common import PERIODS
    tk = app.market.companies[0]["ticker"]
    app.scenes.go("company", ticker=tk)
    sc = app.scenes.current
    sc.tab = "chart"
    sc.draw(app.screen)
    assert set(sc._chart_period_rects) == {period for _label, period in PERIODS}


def test_company_sheet_chart_series_matches_graph_scene_series(app):
    """La série tracée par la fiche société pour une période donnée doit être
    EXACTEMENT celle de l'atelier de graphes (même fonction partagée,
    scene_graph_common.stock_series) — sinon les deux écrans montreraient
    des variations différentes pour la même société (bug d'origine du
    signalement joueur : « on dirait des sociétés différentes »)."""
    from scenes.scene_graph_common import stock_series
    tk = app.market.companies[0]["ticker"]
    app.scenes.go("company", ticker=tk)
    sc = app.scenes.current
    for period in (-1440, 18, None):
        sc.chart_period = period
        expected = stock_series(app.market, app.sim_clock, app.gs.player.day, tk, period)
        got = stock_series(app.market, app.sim_clock, app.gs.player.day, tk, period)
        assert got == pytest.approx(expected)


def test_company_sheet_switching_period_updates_rects(app):
    tk = app.market.companies[0]["ticker"]
    app.scenes.go("company", ticker=tk)
    sc = app.scenes.current
    sc.tab = "chart"
    sc.draw(app.screen)
    r = sc._chart_period_rects[18]   # 3M
    sc.handle_event(_click(*r.center))
    assert sc.chart_period == 18


# ================== apps natives Inbox / Alertes (ex-scènes hébergées) =======
def test_inbox_window_opens_native_app_and_targets_message(app):
    """Ouvrir « inbox » en fenêtre lance l'app NATIVE (plus d'hébergement flou
    de la scène plein écran) et `select_idx` cible/marque lu le bon message."""
    app.gs.player.inbox = [
        {"id": 1, "kind": "manager", "day": 1, "subject": "Bienvenue",
         "sender": "Boss", "body": "…", "read": True},
        {"id": 2, "kind": "client", "day": 2, "subject": "Mandat",
         "sender": "Client", "body": "…", "read": False},
    ]
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("inbox", select_idx=1)
    assert w is not None and w.key == "inbox"
    assert w.app_obj.sel == 1
    assert app.gs.player.inbox[1]["read"] is True
    w.app_obj.draw(app.screen, w.content_rect)   # dessin natif : ne lève pas


def test_alerts_window_opens_native_app_and_posts_alert(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    tk = app.market.companies[0]["ticker"]
    w = desk._open_scene_window("alerts", ticker=tk)
    assert w is not None and w.key == "alerts"
    a = w.app_obj
    assert a.sel_ticker == tk
    price = app.market.price_of(tk)
    a.price_text = f"{price * 1.1:.2f}"
    a._post_alert()
    assert any(al["ticker"] == tk for al in app.gs.player.alerts)
    a.draw(app.screen, w.content_rect)
    # suppression via l'API (le × passe par le même chemin)
    from core import alerts as ALERTS
    aid = app.gs.player.alerts[-1]["id"]
    assert ALERTS.cancel(app.gs.player, aid) is True


def test_inbox_and_alerts_desktop_icons_launch_native_apps(app):
    """Les icônes Inbox/Alertes du bureau lancent les apps natives (elles ont
    remplacé les accès rapides qinbox/qalerts vers les scènes hébergées)."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    keys = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert "inbox" in keys and "alerts" in keys
    assert "qinbox" not in keys and "qalerts" not in keys
    w = desk._launch("inbox")
    assert w is not None and w.app_obj.__class__.__name__ == "InboxApp"
    w2 = desk._launch("alerts")
    assert w2 is not None and w2.app_obj.__class__.__name__ == "AlertsApp"


def test_desktop_never_shows_two_icons_with_the_same_label(app):
    """Régression : migrer une scène vers une app native (cf. APPS) sans
    retirer son ancien accès rapide de QUICK_APPS affiche deux icônes
    identiques côte à côte (arrivé pour Mission/Deals lors de leur
    migration). Vérifié avec un dilemme EN ATTENTE (qui rend "qdecide"
    visible) pour couvrir aussi ce cas conditionnel."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    app.gs.player.pending_dilemmas = [{"id": "x", "category": "ethique",
                                       "title": "T", "scenario": "S", "options": []}]
    labels = [lbl for _k, lbl, _kind, _acc in desk._icon_list()]
    dupes = {lbl for lbl in labels if labels.count(lbl) > 1}
    assert not dupes, f"icônes en double : {dupes}"


def test_evaluation_and_review_and_dilemma_are_factory_only_not_standing_icons(app):
    """"dilemma"/"review"/"evaluation"/"deals" sont enregistrées dans APPS
    uniquement pour que `_launch` trouve leur classe (popups forcés/liens
    internes) — jamais une icône de bureau permanente : "evaluation" en
    particulier contournerait les critères de promotion vérifiés par
    scene_examcert.py::_go_exam si elle était directement cliquable."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    keys = {k for k, _l, _kind, _acc in desk._icon_list()}
    assert not keys & {"dilemma", "review", "evaluation", "deals"}
