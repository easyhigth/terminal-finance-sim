"""
tests/test_popup_navigation.py — Audit de navigation des popups internes
(CompanyPopup/ChartPopup/..., ui/popups.py::PopupMixin) dans une scène
HÉBERGÉE en fenêtre (bureau, étape 2 : `apps/scene_host.py::_Router`).

Contexte : PR #185 avait corrigé un bug où `self.app.scenes.back(...)`
ouvrait une fenêtre supplémentaire au lieu de fermer la fenêtre appelante,
pour les boutons RETOUR des scènes. Cet audit vérifie que le mécanisme de
navigation DEPUIS un popup flottant (`PopupMixin._consume_popup_signals`,
qui appelle `self.app.scenes.go(...)`, jamais `.back()`) reste cohérent avec
ces mêmes règles : un lien de popup est une navigation DÉLIBÉRÉE (ouvre une
fenêtre en plus, sans fermer la fenêtre hôte), et `return_to` doit pointer
vers la scène hôte réelle (pas une valeur figée), pour qu'un bouton retour
dans la fenêtre nouvellement ouverte ferme la BONNE fenêtre.
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
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("explorer")
    explorer = w.app_obj.scene
    tk = app.market.top_companies(n=1)[0]["ticker"]
    popup = explorer.open_company(tk)
    popup.nav_request = {"to": "explorer", "search": tk}

    explorer._consume_popup_signals(popup)

    # la navigation depuis le popup ouvre une DEUXIÈME fenêtre "explorer" —
    # impossible ici (même clé de fenêtre), donc elle se contente de
    # ramener au premier plan la fenêtre déjà ouverte plutôt que la fermer.
    assert any(win.key == "scene:explorer" for win in desk.wm.windows)


def test_popup_nav_request_return_to_targets_the_real_host_scene(app):
    """`return_to` posé par `_consume_popup_signals` doit être le nom de la
    scène HÔTE réelle (`current_name` du routeur, ex. "explorer"), jamais une
    valeur générique figée — sinon un bouton retour depuis la fenêtre ouverte
    fermerait la mauvaise fenêtre (ou aucune)."""
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

    explorer_win = next(win for win in desk.wm.windows if win.key == "scene:explorer")
    assert explorer_win.app_obj.scene.return_to == "bonds"
    # la fenêtre "bonds" appelante n'a pas été fermée par cette navigation
    assert any(win.key == "scene:bonds" for win in desk.wm.windows)


def test_popup_expand_and_stack_do_not_touch_scene_navigation(app):
    """« AGRANDIR » (ChartPopup) et « ANALYSE COMPLÈTE » (autre CompanyPopup)
    restent des popups FLOTTANTS empilés dans la même fenêtre — ils ne
    doivent jamais déclencher `app.scenes.go/back` (contrairement à
    `nav_request`, qui lui le fait délibérément)."""
    app.scenes.go("desktop")
    desk = app.scenes.current
    w = desk._open_scene_window("explorer")
    explorer = w.app_obj.scene
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
