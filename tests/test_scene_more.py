"""
tests/test_scene_more.py — Smoke-tests headless de scenes/scene_more.py
(page « PLUS »).

Couvre une régression réelle : les boutons masqués par le clip de la zone
défilable restaient enregistrés comme cliquables, ce qui pouvait faire
intercepter leur clic par le bouton retour (rects qui se chevauchent en
coordonnées non défilées). Voir le commit qui a introduit ce test.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main
from scenes.scene_more import SECTIONS


@pytest.fixture(scope="module")
def app():
    # Pas de pygame.quit() : invaliderait les Font mis en cache (ui/fonts.py)
    # pour le reste de la session pytest.
    a = main.App()
    a.ensure_market()
    a.gs.player.grade_index = 9   # tout débloqué, pour atteindre toutes les pages
    yield a


def _all_scene_names():
    return [scene for _, items in SECTIONS for (_, scene, _) in items]


def _enter_more(app):
    app.scenes.go("more", return_to="terminal")
    sc = app.scenes.current
    sc.update(16)
    sc.draw(app.screen)
    return sc


def test_every_section_button_is_reachable_via_scroll(app):
    """Chaque bouton de SECTIONS doit, à un moment du défilement, apparaître
    dans _btn_rects (donc être cliquable). Aucun bouton ne doit rester
    fantôme (jamais activable)."""
    sc = _enter_more(app)
    max_scroll = sc._max_scroll
    found = set()
    step = 16
    s = 0
    while s <= max_scroll:
        sc.scroll = s
        sc.draw(app.screen)
        found.update(scene for _, scene, _ in sc._btn_rects)
        s += step
    sc.scroll = max_scroll
    sc.draw(app.screen)
    found.update(scene for _, scene, _ in sc._btn_rects)

    missing = set(_all_scene_names()) - found
    assert not missing, f"boutons jamais cliquables à aucun défilement : {missing}"


def test_no_button_rect_overlaps_back_button_at_any_scroll(app):
    """Régression : un bouton hors-écran ne doit jamais être enregistré comme
    cliquable, sinon il peut chevaucher le bouton retour et lui voler son
    clic (cf. bug historique sur 'calendar' / 'academy' / 'saves' etc.)."""
    sc = _enter_more(app)
    back_rect = sc.back_btn.rect
    max_scroll = sc._max_scroll
    step = 16
    s = 0
    while s <= max_scroll:
        sc.scroll = s
        sc.draw(app.screen)
        for rect, scene, _ in sc._btn_rects:
            assert not rect.colliderect(back_rect), (
                f"{scene} (scroll={s}) chevauche le bouton retour")
        s += step


def test_clicking_each_button_navigates_to_its_scene(app):
    """Pour chaque bouton, on défile jusqu'à ce qu'il soit visible, on clique,
    et on vérifie que la bonne scène s'ouvre (pas une autre par accident)."""
    for label, scene, kw in [item for _, items in SECTIONS for item in items]:
        sc = _enter_more(app)
        max_scroll = sc._max_scroll
        clicked = False
        s = 0
        while s <= max_scroll and not clicked:
            sc.scroll = s
            sc.draw(app.screen)
            for rect, sc_name, _ in sc._btn_rects:
                if sc_name == scene:
                    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=rect.center, button=1)
                    sc.handle_event(ev)
                    clicked = True
                    break
            s += 16
        assert clicked, f"{label} ({scene}) n'a jamais été cliquable"
        assert app.scenes.current_name == scene, (
            f"clic sur {label} a ouvert {app.scenes.current_name}, attendu {scene}")


def test_search_filters_buttons_by_label(app):
    sc = _enter_more(app)
    for ch in "calend":
        sc.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord(ch), unicode=ch))
    sc.draw(app.screen)
    assert [scene for _, scene, _ in sc._btn_rects] == ["calendar"]


def test_escape_clears_search_before_leaving_scene(app):
    sc = _enter_more(app)
    sc.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="a"))
    assert sc.search == "a"
    sc.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=""))
    assert sc.search == ""
    assert app.scenes.current_name == "more"
    sc.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=""))
    assert app.scenes.current_name == "terminal"


def test_search_with_no_match_shows_empty_state_without_crashing(app):
    sc = _enter_more(app)
    for ch in "zzzzznotfound":
        sc.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord(ch[0]), unicode=ch[0]))
    sc.draw(app.screen)
    assert sc._btn_rects == []
