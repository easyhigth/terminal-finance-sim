"""Tests de l'écran « Historique des déblocages »
(core/unlocks.features_at_grade + scenes/scene_unlock_history.py) : chaque
fonctionnalité doit apparaître dans EXACTEMENT un groupe de grade, le groupe
courant/atteint est correctement marqué, et le rendu headless ne plante pas
pour un joueur à n'importe quel grade/voie."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main
from core import unlocks
from core.game_state import PlayerState

pygame.font.init()


def _player(grade=0, track="General"):
    p = PlayerState()
    p.grade_index = grade
    p.track = track
    return p


# --------------------------------------------------------- core.unlocks.features_at_grade
def test_features_at_grade_covers_every_feature_exactly_once():
    p = _player(track="General")
    grades = {unlocks.effective_required_grade(p, f) for f in unlocks.UNLOCKS}
    seen = []
    for g in grades:
        seen.extend(unlocks.features_at_grade(p, g))
    assert sorted(seen) == sorted(unlocks.UNLOCKS)
    assert len(seen) == len(set(seen))


def test_features_at_grade_is_sorted_by_label():
    p = _player(track="General")
    feats = unlocks.features_at_grade(p, 0)
    labels = [unlocks.feature_label(f) for f in feats]
    assert labels == sorted(labels)


def test_features_at_grade_reflects_track_lock():
    """Un module d'affinité Portfolio doit migrer du groupe de son grade de
    base vers TRACK_LOCK_GRADE si le joueur a choisi une AUTRE voie."""
    general = _player(track="General")
    base_grade = unlocks.required_grade("attribution")
    assert "attribution" in unlocks.features_at_grade(general, base_grade)

    mismatched = _player(track="M&A")
    assert "attribution" not in unlocks.features_at_grade(mismatched, base_grade)
    assert "attribution" in unlocks.features_at_grade(mismatched, unlocks.TRACK_LOCK_GRADE)


def test_features_at_grade_empty_for_grade_with_nothing():
    p = _player(track="General")
    # aucun feature n'est requis au-delà du plus haut palier utilisé
    highest = max(unlocks.effective_required_grade(p, f) for f in unlocks.UNLOCKS)
    assert unlocks.features_at_grade(p, highest + 1) == []


# ------------------------------------------------------------------------ scène
@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    return a


def _open(app, grade=5, track="General"):
    p = app.gs.player
    p.grade_index = grade
    p.track = track
    app.scenes.go("unlockhistory", return_to="career")
    return app.scenes.current


def test_scene_registered_and_reachable_from_career():
    assert "unlockhistory" in main.App().scenes.scenes


@pytest.mark.parametrize("grade,track", [
    (0, "General"), (1, "General"), (5, "M&A"), (7, "Advisory"),
    (9, "Risk"), (11, "Quant"),
])
def test_scene_draws_without_crash(app, grade, track):
    scene = _open(app, grade, track)
    scene.update(0.05)
    scene.draw(app.screen)
    # défile jusqu'en bas : exerce le rendu de TOUS les groupes, pas
    # seulement ceux visibles sans défilement
    scene.scroll = scene._max_scroll
    scene.draw(app.screen)


def test_current_grade_group_is_flagged(app):
    scene = _open(app, grade=4, track="General")
    scene.update(0.05)
    scene.draw(app.screen)
    current_groups = [g for g in scene.groups if g["current"]]
    assert len(current_groups) == 1
    assert current_groups[0]["grade"] == 4


def test_reached_groups_precede_grade_index(app):
    scene = _open(app, grade=6, track="General")
    scene.update(0.05)
    scene.draw(app.screen)
    for g in scene.groups:
        if g["reached"]:
            assert g["grade"] <= 6


def test_track_mismatch_rows_carry_a_note(app):
    scene = _open(app, grade=5, track="M&A")
    scene.update(0.05)
    scene.draw(app.screen)
    lock_group = next((g for g in scene.groups if g["grade"] == unlocks.TRACK_LOCK_GRADE), None)
    assert lock_group is not None
    # le groupe du grade max mélange désormais les VRAIS déblocages de ce grade
    # ("founding", sans note) et les modules repoussés là par un choix de voie
    # incompatible (avec note) — chaque module verrouillé par la voie doit
    # porter sa note, les déblocages natifs du grade n'en ont pas.
    for r in lock_group["rows"]:
        if unlocks.required_grade(r["feature"]) < unlocks.TRACK_LOCK_GRADE:
            assert r["note"], r["feature"]     # repoussé par la voie -> note explicative
        else:
            assert not r["note"], r["feature"]  # déblocage natif du grade max
    assert any(r["note"] for r in lock_group["rows"])   # le cas voie existe bien


def test_back_button_returns_to_career(app):
    scene = _open(app, grade=3)
    r = scene.back_btn.rect
    scene.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=r.center))
    assert app.scenes.current is not scene


def test_catalog_entry_exists():
    from core.app_catalog import SECTIONS
    scenes = {s for _t, items in SECTIONS for _l, s, _kw, _d in items}
    assert "unlockhistory" in scenes
