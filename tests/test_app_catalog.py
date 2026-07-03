"""
tests/test_app_catalog.py — Garde-fou : CHAQUE scène jouable enregistrée dans
main.py doit apparaître dans core/app_catalog.SECTIONS (donc être accessible
via le menu Démarrer du bureau), pas seulement via une commande ou un
raccourci clavier. Si une scène est ajoutée sans entrée de catalogue, ce test
échoue (comme _KNOWN_SCENES pour le smoke). Couvre aussi l'intégrité des
données du catalogue (descriptions, verrous) consommées par le menu Démarrer
(scenes/scene_desktop_menus.py).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import main
from core.app_catalog import SCENE_FEATURE, SECTIONS

# Scènes volontairement SANS entrée de catalogue :
#  - flux pré-partie / fin de partie (menu, création de run, game over…) ;
#  - le terminal (hub d'où l'on ouvre le menu Démarrer) ;
#  - vues de détail qui exigent une entité passée par une scène parente
#    (fiche d'une cible M&A, mini-jeu d'un deal précis) — leur parent, lui,
#    a bien une entrée de catalogue.
_EXCLUDED = {
    "menu", "continent", "runsetup", "sandbox", "intro", "splash", "gameover",
    "terminal", "desktop", "ma_target", "deal",
}


def _catalog_scenes():
    return {scene for _title, items in SECTIONS for _label, scene, _kw, _desc in items}


def test_every_playable_scene_is_in_the_catalog():
    app = main.App()
    registered = set(app.scenes.scenes.keys())
    missing = registered - _catalog_scenes() - _EXCLUDED
    assert not missing, f"Scènes sans entrée de catalogue : {sorted(missing)}"


def test_catalog_entries_only_reference_registered_scenes():
    app = main.App()
    registered = set(app.scenes.scenes.keys())
    unknown = _catalog_scenes() - registered
    assert not unknown, f"Entrées de catalogue pointant vers des scènes inconnues : {sorted(unknown)}"


def test_every_entry_has_a_non_empty_description():
    for title, items in SECTIONS:
        for label, scene, _kw, desc in items:
            assert isinstance(desc, str) and desc.strip(), (title, label, scene)


def test_scene_feature_keys_are_all_present_in_some_section():
    scenes = _catalog_scenes()
    for scene in SCENE_FEATURE:
        assert scene in scenes, f"SCENE_FEATURE référence une scène absente du catalogue : {scene}"


def test_no_duplicate_scene_across_sections():
    scenes = [scene for _title, items in SECTIONS for _label, scene, _kw, _desc in items]
    assert len(scenes) == len(set(scenes)), "Une scène apparaît deux fois dans le catalogue"
