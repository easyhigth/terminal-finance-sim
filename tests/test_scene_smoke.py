"""
tests/test_scene_smoke.py — Test de fumée headless : instancie l'app et visite
CHAQUE scène enregistrée (cf. main.py::App._register_scenes), pour attraper les
régressions de rendu (AttributeError, KeyError...) qu'un simple py_compile ne
voit pas. Ne vérifie pas le contenu visuel, seulement l'absence d'exception
lors de on_enter()/update()/draw().
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main

# Scènes nécessitant des kwargs spécifiques pour s'afficher dans leur état
# "normal" (les autres se contentent de return_to="terminal" ou rien).
_SPECIAL_KWARGS = {
    "ma_target": lambda app: {"ticker": app.market.companies[0]["ticker"]},
    "company": lambda app: {"ticker": app.market.companies[0]["ticker"]},
    "financials": lambda app: {"ticker": app.market.companies[0]["ticker"]},
    "graph": lambda app: {"tickers": [app.market.companies[0]["ticker"]]},
    "saves": lambda app: {"return_to": "menu"},
}

# Scènes qui ne dépendent pas du joueur/marché en cours (écrans hors run).
_NO_PLAYER_SCENES = {"menu", "splash", "intro", "continent", "saves"}


@pytest.fixture(scope="module")
def app():
    # Pas de pygame.quit() : invaliderait les Font mis en cache (ui/fonts.py).
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9                  # débloque la quasi-totalité des features
    p.cash = 5_000_000.0
    p.reputation = 80
    p.heat = 10
    yield a


def _scene_names(app):
    return list(app.scenes.scenes.keys())


def test_all_registered_scenes_are_visited(app):
    """Garde-fou : si une scène est ajoutée à main.py sans être listée ici,
    ce test échoue plutôt que de la laisser passer sous le radar."""
    names = set(_scene_names(app))
    assert names == set(_KNOWN_SCENES)


def _visit(app, name):
    kwargs = {}
    factory = _SPECIAL_KWARGS.get(name)
    if factory:
        kwargs = factory(app)
    app.scenes.go(name, **kwargs)
    scene = app.scenes.current
    scene.update(0.016)
    scene.draw(app.screen)
    # un second cycle pour les scènes qui mettent à jour leur état au 1er update
    scene.update(0.016)
    scene.draw(app.screen)


# Un test par scène enregistrée dans main.py, afin que l'échec pointe
# directement sur la scène fautive plutôt qu'un test générique.
_KNOWN_SCENES = [
    "menu", "continent", "terminal", "glossary", "evaluation", "portfolio",
    "ma", "ma_target", "mandates", "deals", "track", "risk", "quant",
    "spreadsheet", "saves", "gameover", "company", "commands", "mission",
    "career", "book", "inbox", "dilemma", "intro", "academy", "cert", "deal",
    "financials", "bonds", "governments", "commodities", "crypto", "etfs",
    "news", "more", "structured", "credit", "alm", "swaps", "hedge",
    "options", "ipo", "fx", "review", "calendar", "graph", "rivals",
    "analytics", "explorer", "tutorials", "splash", "markethub", "shop",
    "examcert", "stresstest", "history", "team",
]


@pytest.mark.parametrize("name", _KNOWN_SCENES)
def test_scene_smoke(app, name):
    """Visite une scène (on_enter via go(), puis update()+draw() x2) et
    s'assure qu'aucune exception n'est levée."""
    _visit(app, name)
    assert app.scenes.current_name == name


def test_terminal_after_every_scene_still_works(app):
    """Vérifie qu'on peut toujours revenir au terminal après avoir traversé
    toutes les scènes (pas de pollution d'état globale genre app.sheet, fonts)."""
    app.scenes.go("terminal")
    app.scenes.current.update(0.016)
    app.scenes.current.draw(app.screen)
    assert app.scenes.current_name == "terminal"
