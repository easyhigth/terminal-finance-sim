"""
tests/test_popup_navigation.py — Audit de navigation des popups internes
(CompanyPopup/ChartPopup/..., ui/popups.py::PopupMixin) sur le bureau.

Contexte : PR #185 avait corrigé un bug où `self.app.scenes.back(...)`
ouvrait une fenêtre supplémentaire au lieu de fermer la fenêtre appelante,
pour les boutons RETOUR des scènes. Cet audit vérifie que le mécanisme de
navigation DEPUIS un popup flottant (`PopupMixin._consume_popup_signals`)
reste cohérent : un lien de popup est une navigation DÉLIBÉRÉE (ouvre une
fenêtre en plus, sans fermer la fenêtre hôte). Deux hôtes possibles :
une scène HÉBERGÉE (routeur `apps/scene_host.py::_Router` → le `return_to`
transite par `_open_scene_window`) et une app NATIVE (back-ref `desktop`
→ `_open_scene_window` direct, jamais `app.scenes.go` qui basculerait tout
l'écran hors du bureau).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

import main


@pytest.fixture()
def app():
    from core import desktop_onboarding
    desktop_onboarding.mark_seen()
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.reputation = 80
    return a


def test_popup_nav_request_opens_a_new_window_without_closing_the_host(app):
    """Nav depuis le popup d'une scène HÉBERGÉE (bonds) vers l'Explorateur :
    ouvre la fenêtre NATIVE de l'Explorateur, sans fermer la fenêtre hôte."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("bonds")
    bonds = w.app_obj.scene
    from core.bonds import BONDS
    bond_id = BONDS[0]["id"]
    popup = bonds.open_bond(bond_id)
    assert popup is not None
    popup.nav_request = {"to": "explorer", "search": bond_id}

    bonds._consume_popup_signals(popup)

    # l'Explorateur est désormais une app NATIVE : clé "explorer" (sans
    # préfixe "scene:"), reconfigurée avec la recherche demandée.
    explorer_win = next(win for win in desk.wm.windows if win.key == "explorer")
    assert explorer_win.app_obj.search == bond_id
    # la fenêtre "bonds" appelante n'a pas été fermée par cette navigation
    assert any(win.key == "scene:bonds" for win in desk.wm.windows)


def test_popup_nav_request_from_native_app_stays_on_the_desktop(app):
    """Nav depuis le popup d'une app NATIVE (Explorateur) : `self.app` étant
    le VRAI App global, `_consume_popup_signals` doit router via la back-ref
    `desktop` (fenêtre) et JAMAIS via `app.scenes.go` (qui basculerait tout
    l'écran hors du bureau)."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("explorer")
    explorer = w.app_obj
    tk = app.market.top_companies(n=1)[0]["ticker"]
    popup = explorer.open_company(tk)
    popup.nav_request = {"to": "company", "ticker": tk}

    explorer._consume_popup_signals(popup)

    assert app.scenes.current_name == "desktop"          # jamais quitté
    assert any(win.key == "company" for win in desk.wm.windows)


def test_popup_expand_and_stack_do_not_touch_scene_navigation(app):
    """« AGRANDIR » (ChartPopup) et « ANALYSE COMPLÈTE » (autre CompanyPopup)
    restent des popups FLOTTANTS empilés dans la même fenêtre — ils ne
    doivent jamais déclencher `app.scenes.go/back` (contrairement à
    `nav_request`, qui lui le fait délibérément)."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("explorer")
    explorer = w.app_obj
    tk = app.market.top_companies(n=1)[0]["ticker"]
    popup = explorer.open_company(tk)
    n_windows_before = len(desk.wm.windows)

    popup.expand_requested = True
    explorer._consume_popup_signals(popup)
    assert len(desk.wm.windows) == n_windows_before   # graphe agrandi = popup en plus, pas de fenêtre
    assert len(explorer.popups) == 2                  # CompanyPopup + ChartPopup empilés

    tk2 = app.market.top_companies(n=2)[1]["ticker"]
    popup.open_ticker = tk2
    explorer._consume_popup_signals(popup)
    assert len(desk.wm.windows) == n_windows_before
    assert len(explorer.popups) == 3
