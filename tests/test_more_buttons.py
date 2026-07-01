"""
tests/test_more_buttons.py — Garde-fou : CHAQUE scène jouable enregistrée dans
main.py doit être accessible par un BOUTON dans le hub « PLUS » (scene_more),
pas seulement via une commande ou un raccourci clavier. Si une scène est
ajoutée sans bouton PLUS, ce test échoue (comme _KNOWN_SCENES pour le smoke).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import main
from scenes.scene_more import SECTIONS

# Scènes volontairement SANS bouton PLUS :
#  - flux pré-partie / fin de partie (menu, création de run, game over…) ;
#  - le terminal (hub d'où l'on ouvre PLUS) et PLUS lui-même ;
#  - vues de détail qui exigent une entité passée par une scène parente
#    (fiche d'une cible M&A, mini-jeu d'un deal précis) — leur parent, lui,
#    a bien un bouton PLUS.
_EXCLUDED = {
    "menu", "continent", "runsetup", "sandbox", "intro", "splash", "gameover",
    "terminal", "desktop", "more", "ma_target", "deal",
}


def _more_scenes():
    return {scene for _title, items in SECTIONS for _label, scene, _kw in items}


def test_every_playable_scene_has_a_more_button():
    app = main.App()
    registered = set(app.scenes.scenes.keys())
    missing = registered - _more_scenes() - _EXCLUDED
    assert not missing, f"Scènes sans bouton dans PLUS : {sorted(missing)}"


def test_more_buttons_only_reference_registered_scenes():
    app = main.App()
    registered = set(app.scenes.scenes.keys())
    unknown = _more_scenes() - registered
    assert not unknown, f"Boutons PLUS pointant vers des scènes inconnues : {sorted(unknown)}"
