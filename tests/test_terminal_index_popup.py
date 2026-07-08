"""Régression : clic sur un indice du panneau INDICES du terminal (bloc
« CAC 40 »/« C&D 500 »/etc.) ouvrant un graphe flottant (DataWindow en mode
`chart`, cf. scenes/scene_terminal_windows.py::_open_index_chart).

Deux bugs couverts ici :
1. `DataWindow.draw()` plantait (AttributeError sur `widgets._hover_sync`,
   absent de la liste de réexport de ui/widgets.py) dès que le graphe avait
   au moins 2 points d'historique — soit dans TOUTE partie ayant dépassé le
   tout premier jour. L'exception n'étant catchée nulle part dans la boucle
   principale, elle fermait le jeu entier au clic : de l'extérieur, « ça se
   ferme immédiatement ».
2. `_open_index_chart` ouvrait toujours à une position FIXE qui recouvrait
   le panneau INDICES lui-même : une fois un graphe ouvert, cliquer sur un
   AUTRE indice retombait dans le corps de cette fenêtre déjà ouverte
   (absorbé, aucun nouveau graphe ne s'ouvrait).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main

pygame.font.init()


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    # historique d'indice réaliste (une vraie partie a des mois de préhistoire
    # de carrière avant que le joueur n'atteigne le terminal) : sans ça, le
    # graphe reste sur la branche "insuffisant" qui NE dessine PAS de série et
    # ne déclenche donc jamais le bug (cf. ui/datawindow.py, len(vals) >= 2).
    for _ in range(40):
        a.market.step()
    return a


def _click(term, rect):
    down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
    up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=rect.center)
    term.handle_event(down)
    term.handle_event(up)


def test_clicking_index_opens_popup_and_does_not_crash_on_draw(app):
    app.scenes.go("terminal")
    term = app.scenes.current
    term.update(0.05)
    surf = pygame.Surface((1280, 720))
    term.draw(surf)
    assert term._index_rects, "le panneau INDICES doit exposer des lignes cliquables"
    name, rect = next(iter(term._index_rects.items()))

    _click(term, rect)
    assert len(term.datawins) == 1
    assert term.datawins[0].closed is False
    assert len(term.datawins[0].chart) >= 2   # la branche qui plantait

    # le dessin (pas seulement l'ouverture) est la vraie régression : c'est
    # DataWindow.draw() qui levait AttributeError sur widgets._hover_sync.
    for _ in range(3):
        term.update(0.05)
        term.draw(surf)
    assert term.datawins[0].closed is False


def test_clicking_several_indices_in_a_row_opens_a_popup_each_time(app):
    """Chaque indice cliqué doit ouvrir SON PROPRE graphe — pas absorbé par
    le corps d'un graphe déjà ouvert qui recouvrirait le panneau."""
    app.scenes.go("terminal")
    term = app.scenes.current
    term.update(0.05)
    surf = pygame.Surface((1280, 720))
    term.draw(surf)
    rows = list(term._index_rects.items())
    assert len(rows) >= 2

    for i, (name, rect) in enumerate(rows):
        _click(term, rect)
        term.update(0.05)
        term.draw(surf)
        assert len(term.datawins) == i + 1, (
            f"clic sur {name} (indice {i}) n'a pas ouvert un nouveau graphe "
            f"— datawins actuels: {[w.title for w in term.datawins]}"
        )
        assert all(not w.closed for w in term.datawins)


def test_datawindow_chart_draw_does_not_crash_with_real_history():
    """Test au niveau du widget lui-même (sans passer par le terminal) :
    verrouille le comportement de ui/datawindow.py::DataWindow.draw() en
    mode graphe avec un historique suffisant."""
    from ui.datawindow import DataWindow
    w = DataWindow("Test — historique", [], [], pos=(10, 10),
                   chart=[100.0, 101.5, 99.0, 103.2, 98.7], resizable=True)
    surf = pygame.Surface((800, 600))
    w.draw(surf)   # ne doit pas lever
    assert w.closed is False
