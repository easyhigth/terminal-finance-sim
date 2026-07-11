"""Tests des sections repliables du bureau (façon dossiers) :
scenes/scene_desktop.py::_grouped_icon_sections / _toggle_section, et
scenes/scene_desktop_common.py::ICON_CATEGORY. Une icône nouvellement
débloquée doit atterrir automatiquement dans la bonne section (catégorie
fixe par clé), et une section repliée doit disparaître du hit-testing
(_icon_rects) sans planter le rendu."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main
from scenes.scene_desktop_common import (
    APPS,
    DEFAULT_ICON_CATEGORY,
    ICON_CATEGORY,
    ICON_CATEGORY_ORDER,
    QUICK_APPS,
    icon_category,
)

pygame.font.init()


def _click(x, y, button=1):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=(x, y))


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
    p.flags["desktop_seeded"] = True
    a.scenes.go("desktop")
    return a


# --------------------------------------------------------------- catalogue
def test_every_app_and_quick_app_key_has_a_category():
    keys = {k for k, *_r in APPS} | {k for k, *_r in QUICK_APPS} | {"terminal", "track"}
    for key in keys:
        assert icon_category(key) in ICON_CATEGORY_ORDER


def test_unknown_key_falls_back_to_default_category():
    assert icon_category("some_future_app_nobody_categorized_yet") == DEFAULT_ICON_CATEGORY


def test_category_order_has_no_duplicates_and_covers_the_map():
    assert len(ICON_CATEGORY_ORDER) == len(set(ICON_CATEGORY_ORDER))
    assert set(ICON_CATEGORY.values()) <= set(ICON_CATEGORY_ORDER)


# --------------------------------------------------------------- regroupement
def test_grouped_sections_cover_every_visible_icon_exactly_once(app):
    desk = app.scenes.current
    desk.draw(app.screen)
    flat = {item[0] for item in desk._icon_list()}
    grouped = []
    for _label, items in desk._grouped_icon_sections():
        grouped.extend(item[0] for item in items)
    assert set(grouped) == flat
    assert len(grouped) == len(flat)  # pas de doublon entre sections


def test_grouped_sections_are_non_empty_and_ordered(app):
    desk = app.scenes.current
    desk.draw(app.screen)
    labels = [label for label, _items in desk._grouped_icon_sections()]
    assert all(labels[i] in ICON_CATEGORY_ORDER for i in range(len(labels)))
    order_index = [ICON_CATEGORY_ORDER.index(l) for l in labels]
    assert order_index == sorted(order_index)


def test_new_unlock_lands_in_its_declared_category(app):
    """Un joueur qui débloque une app (montée de grade) la retrouve dans SA
    catégorie fixe — pas de tri manuel nécessaire."""
    p = app.gs.player
    p.grade_index = 0
    desk = app.scenes.current
    desk.draw(app.screen)
    sections_low = dict(desk._grouped_icon_sections())
    assert not any("greeks" == it[0] for items in sections_low.values() for it in items)
    p.grade_index = 9
    desk.draw(app.screen)
    sections_high = dict(desk._grouped_icon_sections())
    cat = icon_category("greeks")
    assert any(it[0] == "greeks" for it in sections_high[cat])


# ---------------------------------------------------------------- repli/dépli
def test_toggle_section_persists_in_player_flags(app):
    desk = app.scenes.current
    desk.draw(app.screen)
    label = next(iter(desk._section_header_rects))
    assert not desk._is_section_collapsed(label)
    desk._toggle_section(label)
    assert desk._is_section_collapsed(label)
    assert label in app.gs.player.flags["desktop_collapsed_sections"]
    desk._toggle_section(label)
    assert not desk._is_section_collapsed(label)


def test_collapsed_section_icons_are_not_hit_testable(app):
    desk = app.scenes.current
    desk.draw(app.screen)
    label, items = desk._grouped_icon_sections()[0]
    keys_in_section = {it[0] for it in items}
    desk._toggle_section(label)
    desk.draw(app.screen)
    assert not (keys_in_section & set(desk._icon_rects))


def test_clicking_section_header_toggles_collapse(app):
    desk = app.scenes.current
    desk.draw(app.screen)
    label, r = next(iter(desk._section_header_rects.items()))
    desk.handle_event(_click(r.centerx, r.centery))
    assert desk._is_section_collapsed(label)
    desk.draw(app.screen)
    r2 = desk._section_header_rects[label]
    desk.handle_event(_click(r2.centerx, r2.centery))
    assert not desk._is_section_collapsed(label)


def test_all_icon_rects_stay_within_screen_bounds(app):
    """Régression : le flux en colonnes de sections ne doit jamais dessiner
    une icône hors de l'écran (bug trouvé lors de la première implémentation
    — mélange colonne-majeure/ligne-majeure faussant le calcul de hauteur)."""
    from core import config
    p = app.gs.player
    p.track = "M&A"
    desk = app.scenes.current
    desk.draw(app.screen)
    for key, (r, _kind, _label) in desk._icon_rects.items():
        assert r.x >= 0 and r.y >= 0
        assert r.right <= config.SCREEN_WIDTH, key
        assert r.bottom <= config.SCREEN_HEIGHT, key


def test_no_two_sections_overlap(app):
    desk = app.scenes.current
    p = app.gs.player
    p.track = "M&A"
    desk.draw(app.screen)
    rects = list(desk._section_header_rects.values())
    for i, r1 in enumerate(rects):
        for r2 in rects[i + 1:]:
            assert not r1.colliderect(r2)
