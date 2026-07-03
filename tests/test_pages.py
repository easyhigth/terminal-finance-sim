"""Tests de core/pages.py (système d'onglets, cœur de la boucle de jeu) —
ouverture/fermeture d'onglets, largeur compressée, anti-triche pendant un
examen. Headless (SDL_VIDEODRIVER=dummy)."""
import pygame
import pytest

import main


@pytest.fixture
def app():
    return main.App()


def test_initial_state_has_one_page_on_splash(app):
    assert len(app.pages.pages) == 1
    assert app.pages.active == 0
    assert app.pages.current_page.scene_name == "splash"
    assert app.scenes.current_name == "splash"


def test_open_page_appends_and_activates(app):
    page = app.pages.open_page("desktop")
    assert page is not None
    assert len(app.pages.pages) == 2
    assert app.pages.active == 1
    assert app.scenes.current_name == "desktop"


def test_open_new_tab_always_lands_on_desktop(app):
    app.pages.open_page("menu")
    page = app.pages.open_new_tab()
    assert page.scene_name == "desktop"
    assert app.scenes.current_name == "desktop"


def test_close_page_adjusts_active_index(app):
    app.pages.open_page("desktop")
    app.pages.open_page("menu")
    assert len(app.pages.pages) == 3
    app.pages.close_page(1)
    assert len(app.pages.pages) == 2
    assert app.pages.active == 1   # ramené dans les bornes


def test_close_page_is_noop_with_a_single_page(app):
    assert len(app.pages.pages) == 1
    app.pages.close_page()
    assert len(app.pages.pages) == 1


def test_close_other_pages_keeps_only_active(app):
    app.pages.open_page("desktop")
    app.pages.open_page("menu")
    app.pages.close_other_pages()
    assert len(app.pages.pages) == 1
    assert app.scenes.current_name == "menu"


def test_next_prev_page_cycle(app):
    app.pages.open_page("desktop")
    app.pages.open_page("menu")
    assert app.pages.active == 2
    app.pages.next_page()
    assert app.pages.active == 0   # boucle
    app.pages.prev_page()
    assert app.pages.active == 2


def test_toggle_popup_marks_page_and_assigns_rect(app):
    app.pages.open_page("desktop")
    app.pages.switch_to(0)
    app.pages.toggle_popup(1)
    page = app.pages.pages[1]
    assert page.popup is True
    assert page.popup_rect is not None
    app.pages.toggle_popup(1)
    assert page.popup is False


def test_can_switch_blocked_during_exam(app):
    app.pages.open_page("examcert")
    assert app.pages.can_switch() is False
    app.pages.switch_to(0)   # doit être ignoré (verrouillé)
    assert app.pages.active == 1
    app.pages.close_page(0)   # aucune fermeture possible non plus
    assert len(app.pages.pages) == 2


def test_can_switch_true_outside_exam(app):
    app.pages.open_page("desktop")
    assert app.pages.can_switch() is True


def test_tab_metrics_full_width_when_few_tabs(app):
    from core.pages import TAB_W
    w, max_scroll = app.pages._tab_metrics()
    assert w == TAB_W
    assert max_scroll == 0


def test_tab_metrics_compress_and_scroll_with_many_tabs(app):
    from core.pages import MIN_TAB_W
    for _ in range(25):
        app.pages.open_page("menu")
    w, max_scroll = app.pages._tab_metrics()
    assert w == MIN_TAB_W
    assert max_scroll > 0


def test_clock_visible_only_once_a_run_is_active(app):
    assert app.pages._clock_visible() is False
    app.ensure_market()
    assert app.pages._clock_visible() is True


def test_ctrl_t_opens_new_tab_via_handle_event(app):
    n = len(app.pages.pages)
    ev = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_t,
                                             "mod": pygame.KMOD_CTRL, "unicode": ""})
    app.pages.handle_event(ev)
    assert len(app.pages.pages) == n + 1
    assert app.pages.current_page.scene_name == "desktop"


def test_ctrl_w_closes_current_tab(app):
    app.pages.open_page("desktop")
    n = len(app.pages.pages)
    ev = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_w,
                                             "mod": pygame.KMOD_CTRL, "unicode": ""})
    app.pages.handle_event(ev)
    assert len(app.pages.pages) == n - 1


def test_draw_and_update_do_not_raise(app):
    app.pages.open_page("desktop")
    app.pages.toggle_popup(0)
    app.pages.update(0.016)
    app.pages.draw(app.screen)
