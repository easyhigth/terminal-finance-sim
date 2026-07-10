"""Tests des tutoriels illustrés (data/tutorials.py + scenes/scene_tutorials.py) :
intégrité du contenu (ids uniques, images présentes sur disque, étapes non
vides) et rendu headless de CHAQUE tutoriel sans exception ni image manquante
silencieusement remplacée par un cadre vide."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

pytest.importorskip("pygame")

import main
from data import tutorials as T

pygame.font.init()

_IMG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "assets", "tutorials")

# tutoriels ajoutés pour les desks avancés (Lot intégration A/B et lots
# précédents) — verrou explicite pour ne pas en oublier un futur ajout.
_NEW_DESK_TUTORIAL_IDS = {
    "sharpe", "zscore", "frontier", "greeks", "vardesk", "rates", "attribution",
    "pairs", "creditdesk", "crisislab", "valuation", "fxdesk", "vollab",
    "funding", "pnlexplain", "backtester",
}


def test_tutorial_ids_are_unique():
    ids = [t["id"] for t in T.TUTORIALS]
    assert len(ids) == len(set(ids))


def test_new_desk_tutorials_are_present():
    ids = {t["id"] for t in T.TUTORIALS}
    missing = _NEW_DESK_TUTORIAL_IDS - ids
    assert not missing, f"Tutoriels manquants : {sorted(missing)}"


def test_every_tutorial_has_well_formed_content():
    for t in T.TUTORIALS:
        assert t["title"].strip()
        assert t["intro"].strip()
        assert isinstance(t["steps"], list) and len(t["steps"]) >= 1
        assert all(s.strip() for s in t["steps"])
        assert t["concept"].strip()


def test_every_tutorial_image_exists_on_disk():
    for t in T.TUTORIALS:
        path = os.path.join(_IMG_DIR, t["image"])
        assert os.path.isfile(path), f"Image manquante : {t['image']} ({t['id']})"


def test_every_tutorial_image_loads_as_a_valid_surface():
    for t in T.TUTORIALS:
        path = os.path.join(_IMG_DIR, t["image"])
        img = pygame.image.load(path)
        assert img.get_width() > 0 and img.get_height() > 0


def test_get_returns_none_for_unknown_id():
    assert T.get("does-not-exist") is None


def test_get_returns_the_matching_entry():
    for tid in _NEW_DESK_TUTORIAL_IDS:
        assert T.get(tid)["id"] == tid


@pytest.fixture(scope="module")
def app():
    a = main.App()
    a.ensure_market()
    return a


@pytest.mark.parametrize("tid", [t["id"] for t in T.TUTORIALS])
def test_tutorial_scene_draws_without_crash(app, tid):
    app.scenes.go("tutorials", tid=tid, return_to="terminal")
    scene = app.scenes.current
    scene.update(0.05)
    scene.draw(app.screen)
