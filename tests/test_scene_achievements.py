"""
tests/test_scene_achievements.py — Écran dédié Succès (scenes/scene_achievements.py) :
liste TOUS les badges (obtenus en couleur, verrouillés grisés), avec une jauge
de progression pour ceux à seuil numérique. Distinct de la galerie inline de
scene_career.py (qui ne montre que les badges déjà obtenus).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main
from core import badges as badges_mod


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    a.gs.player.grade_index = 5
    return a


def _click(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y))


def test_lists_every_badge_including_streaks(app):
    app.scenes.go("achievements", return_to="terminal")
    scene = app.scenes.current
    scene.draw(app.screen)
    total = len(badges_mod.all_badges()) + len(badges_mod.all_streak_badges())
    assert len(scene.rows) == total


def test_obtained_badges_marked_and_sorted_first(app):
    app.gs.player.badges = ["first_deal"]
    app.scenes.go("achievements", return_to="terminal")
    scene = app.scenes.current
    obtained_rows = [r for r in scene.rows if r["obtained"]]
    assert len(obtained_rows) == 1
    assert obtained_rows[0]["name"] == badges_mod.badge_name(badges_mod.get("first_deal"))
    # tri : obtenus en premier
    assert scene.rows[0]["obtained"] is True


def test_locked_badge_with_numeric_target_has_progress(app):
    app.gs.player.deals_won = 4
    app.scenes.go("achievements", return_to="terminal")
    scene = app.scenes.current
    row = next(r for r in scene.rows
              if r["name"] == badges_mod.badge_name(badges_mod.get("dealmaker")))
    assert row["obtained"] is False
    assert row["progress"] == (4.0, 10.0)


def test_obtained_badge_has_no_progress_bar(app):
    app.gs.player.badges = ["first_deal"]
    app.scenes.go("achievements", return_to="terminal")
    scene = app.scenes.current
    row = next(r for r in scene.rows
              if r["name"] == badges_mod.badge_name(badges_mod.get("first_deal")))
    assert row["progress"] is None


def test_streak_badge_progress_uses_flag_value(app):
    app.gs.player.flags["clean_quarter_streak"] = 3
    app.scenes.go("achievements", return_to="terminal")
    scene = app.scenes.current
    untouchable = badges_mod.get_streak("untouchable")
    row = next(r for r in scene.rows
              if r["streak"] and r["name"] == badges_mod.streak_badge_name(untouchable))
    assert row["progress"] is not None
    cur, target = row["progress"]
    assert cur == 3.0
    assert target == 8.0


def test_draw_and_scroll_do_not_raise(app):
    app.scenes.go("achievements", return_to="terminal")
    scene = app.scenes.current
    scene.update(0.016)
    scene.draw(app.screen)
    assert scene._list_rect is not None
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=5,
                                          pos=scene._list_rect.center))


def test_back_button_returns_to_return_to_scene(app):
    app.scenes.go("achievements", return_to="career")
    scene = app.scenes.current
    scene.draw(app.screen)
    scene.handle_event(_click(scene.back_btn.rect.centerx, scene.back_btn.rect.centery))
    assert app.scenes.current_name == "career"


def test_escape_returns_to_return_to_scene(app):
    app.scenes.go("achievements", return_to="terminal")
    scene = app.scenes.current
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert app.scenes.current_name == "terminal"


def test_filter_defaults_to_all_categories(app):
    app.scenes.go("achievements", return_to="terminal")
    scene = app.scenes.current
    assert scene._cat_filter is None
    assert scene._visible_rows() == scene.rows


def test_draw_builds_chip_rects_for_present_categories(app):
    app.scenes.go("achievements", return_to="terminal")
    scene = app.scenes.current
    scene.draw(app.screen)
    present = {r["cat"] for r in scene.rows if r["cat"]}
    assert set(scene._chip_rects) == present | {None}


def test_clicking_a_chip_filters_rows_by_category(app):
    app.scenes.go("achievements", return_to="terminal")
    scene = app.scenes.current
    scene.draw(app.screen)
    career_rect = scene._chip_rects["career"]
    scene.handle_event(_click(career_rect.centerx, career_rect.centery))
    assert scene._cat_filter == "career"
    assert scene._visible_rows()
    assert all(r["cat"] == "career" for r in scene._visible_rows())


def test_clicking_all_chip_clears_filter(app):
    app.scenes.go("achievements", return_to="terminal")
    scene = app.scenes.current
    scene.draw(app.screen)
    scene._cat_filter = "career"
    all_rect = scene._chip_rects[None]
    scene.handle_event(_click(all_rect.centerx, all_rect.centery))
    assert scene._cat_filter is None
    assert scene._visible_rows() == scene.rows


def test_every_badge_has_a_known_category():
    valid = {cid for cid, _fr, _en in badges_mod.CATEGORIES}
    for b in badges_mod.all_badges() + badges_mod.all_streak_badges():
        assert b.get("cat") in valid, b["id"]


def test_terminal_command_opens_achievements_scene(app):
    app.scenes.go("desktop")
    desk = app.scenes.current
    term = desk._terminal_host.scene
    term.app.scenes.go("achievements", return_to="terminal")
    assert app.scenes.current_name == "desktop"
    assert any(w.key == "scene:achievements" for w in desk.wm.windows)


def test_more_hub_lists_achievements_entry(app):
    from core.app_catalog import SECTIONS
    scenes = {scene for _title, items in SECTIONS for _label, scene, _kw, _desc in items}
    assert "achievements" in scenes


def test_career_screen_has_achievements_button(app):
    app.scenes.go("career", return_to="terminal")
    scene = app.scenes.current
    scene.draw(app.screen)
    scene.handle_event(_click(scene.achievements_btn.rect.centerx, scene.achievements_btn.rect.centery))
    assert app.scenes.current_name == "achievements"
