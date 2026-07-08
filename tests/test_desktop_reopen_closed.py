"""Tests pour le raccourci « Rouvrir la dernière fenêtre fermée »
(CTRL+MAJ+Z, scene_desktop.py)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main
from core import desktop_onboarding


@pytest.fixture()
def desktop():
    desktop_onboarding.mark_seen()
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.reputation = 80
    a.scenes.go("desktop")
    sc = a.scenes.current
    sc.update(0.016)
    sc.draw(a.screen)
    return sc


def _reopen_key():
    return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z,
                              mod=pygame.KMOD_CTRL | pygame.KMOD_SHIFT, unicode="")


def test_reopens_a_closed_scene_window_with_its_context(desktop):
    # "financials" reste une scène HÉBERGÉE (contrairement à "company",
    # devenue une app native sans contexte de fenêtre à restaurer — la
    # rouvrir retombe sur le ticker par défaut, cf. test dédié plus bas)
    tk = desktop.app.market.top_companies(n=1)[0]["ticker"]
    w = desktop._open_scene_window("financials", ticker=tk, return_to="markethub")
    desktop.wm.close(w)
    assert not any(win.key == "scene:financials" for win in desktop.wm.windows)

    desktop.handle_event(_reopen_key())

    reopened = next(win for win in desktop.wm.windows if win.key == "scene:financials")
    assert reopened.app_obj.scene.ticker == tk


def test_reopens_a_closed_company_window_native(desktop):
    """"company" est une app NATIVE : la rouvrir via CTRL+MAJ+Z ne perd
    jamais la fenêtre (retombe sur le ticker par défaut, sans contexte
    précis à restaurer — cf. apps/app_company.py)."""
    w = desktop._launch("company")
    desktop.wm.close(w)
    assert not any(win.key == "company" for win in desktop.wm.windows)

    desktop.handle_event(_reopen_key())

    assert any(win.key == "company" for win in desktop.wm.windows)


def test_reopens_a_closed_native_app(desktop):
    w = desktop._launch("research")
    desktop.wm.close(w)
    assert not any(win.key == "research" for win in desktop.wm.windows)

    desktop.handle_event(_reopen_key())

    assert any(win.key == "research" for win in desktop.wm.windows)


def test_closing_terminal_is_never_tracked_for_reopen(desktop):
    tk = desktop.app.market.top_companies(n=1)[0]["ticker"]
    w = desktop._open_scene_window("financials", ticker=tk)
    desktop.wm.close(w)   # dernier fermé = "financials"

    term = next(win for win in desktop.wm.windows if win.key == "scene:terminal")
    desktop.wm.close(term)   # ne doit PAS s'empiler sur _closed_stack

    assert desktop._closed_stack[-1] == ("scene", "financials", {"ticker": tk})


def test_reopen_is_a_noop_when_nothing_was_closed(desktop):
    n_before = len(desktop.wm.windows)
    desktop.handle_event(_reopen_key())
    assert len(desktop.wm.windows) == n_before


def test_reopen_consumes_the_record_only_once(desktop):
    w = desktop._launch("research")
    desktop.wm.close(w)
    desktop.handle_event(_reopen_key())
    assert desktop._closed_stack == []
    n_after_first = len(desktop.wm.windows)
    desktop.handle_event(_reopen_key())   # rien à rouvrir la 2e fois
    assert len(desktop.wm.windows) == n_after_first


# ============================== pile multi-niveaux (rang > 1) =================
def test_closing_two_windows_stacks_both_entries(desktop):
    w1 = desktop._launch("research")
    w2 = desktop._launch("calculator")
    desktop.wm.close(w1)
    desktop.wm.close(w2)
    assert desktop._closed_stack == [("app", "research", {}), ("app", "calculator", {})]


def test_ctrl_shift_z_reopens_most_recent_first_then_the_one_before(desktop):
    w1 = desktop._launch("research")
    w2 = desktop._launch("calculator")
    desktop.wm.close(w1)
    desktop.wm.close(w2)

    desktop.handle_event(_reopen_key())
    assert any(win.key == "calculator" for win in desktop.wm.windows)
    assert desktop._closed_stack == [("app", "research", {})]

    desktop.handle_event(_reopen_key())   # rang suivant : research
    assert any(win.key == "research" for win in desktop.wm.windows)
    assert desktop._closed_stack == []


def test_closed_stack_is_capped(desktop):
    from scenes.scene_desktop import _CLOSED_STACK_MAX
    for _ in range(_CLOSED_STACK_MAX + 3):
        w = desktop._launch("research")
        desktop.wm.close(w)
    assert len(desktop._closed_stack) == _CLOSED_STACK_MAX


def test_context_menu_lists_recently_closed_windows_and_reopens_a_specific_one(desktop):
    """Le menu contextuel du fond du bureau liste les dernières fenêtres
    fermées (pas seulement la toute dernière comme CTRL+MAJ+Z) et permet
    d'en rouvrir une PRÉCISE, même si ce n'est pas la plus récente."""
    w1 = desktop._launch("research")
    w2 = desktop._launch("calculator")
    desktop.wm.close(w1)
    desktop.wm.close(w2)

    items = desktop._desktop_menu_items()
    labels = [lbl for lbl, _cb in items]
    assert any("Recherche" in lbl for lbl in labels)
    assert any("Calculatrice" in lbl for lbl in labels)

    # rouvre spécifiquement "Recherche", pas le plus récent (calculatrice)
    _label, cb = next((lbl, cb) for lbl, cb in items if "Recherche" in lbl)
    cb()
    assert any(win.key == "research" for win in desktop.wm.windows)
    assert ("app", "research", {}) not in desktop._closed_stack
    assert ("app", "calculator", {}) in desktop._closed_stack
