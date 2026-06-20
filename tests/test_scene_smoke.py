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
_NO_PLAYER_SCENES = {"menu", "splash", "intro", "continent", "runsetup", "saves", "sandbox"}


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
    "menu", "continent", "runsetup", "sandbox", "terminal", "glossary", "evaluation", "portfolio",
    "ma", "ma_target", "mandates", "deals", "track", "risk", "quant",
    "spreadsheet", "saves", "gameover", "company", "commands", "mission",
    "career", "book", "inbox", "dilemma", "intro", "academy", "cert", "deal",
    "financials", "bonds", "governments", "commodities", "crypto", "etfs",
    "news", "more", "structured", "credit", "alm", "swaps", "hedge",
    "options", "ipo", "fx", "review", "calendar", "graph", "rivals",
    "analytics", "performance", "explorer", "tutorials", "splash", "markethub", "shop",
    "examcert", "stresstest", "history", "team", "alerts",
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


# --------------------------------------------------------- export vers le tableur
# Couvre l'option "→ TABLEUR" ajoutée sur les écrans d'états financiers
# (scene_financials.py / scene_ma_target.py) : ouverture de scene_spreadsheet
# avec les données importées, et retour vers l'écran d'origine avec le bon
# contexte (ticker conservé).

def test_financials_open_spreadsheet_income(app):
    ticker = app.market.companies[0]["ticker"]
    app.scenes.go("financials", ticker=ticker, return_to="terminal")
    scene = app.scenes.current
    scene.update(0.016)
    scene._open_spreadsheet("income")
    assert app.scenes.current_name == "spreadsheet"
    sheet = app.scenes.current
    assert sheet.import_title == f"{ticker} — Compte de résultat"
    # libellé de la première ligne importée (Chiffre d'affaires) en A3
    assert sheet.sheet.get_raw("A3") == "Chiffre d'affaires"
    # valeur numérique importée et lisible par le moteur de formules
    assert isinstance(sheet.sheet.get_value("B3"), float)
    # le retour ramène bien sur la fiche financière du même ticker
    sheet.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=sheet.back_btn.rect.center))
    assert app.scenes.current_name == "financials"
    assert app.scenes.current.ticker == ticker


def test_financials_open_spreadsheet_balance_fits_grid(app):
    """Le bilan (~14 lignes) doit tenir entièrement dans la grille du tableur
    (régression : la grille était trop petite -> lignes tronquées silencieusement)."""
    from scenes.scene_spreadsheet import N_ROWS
    ticker = app.market.companies[0]["ticker"]
    app.scenes.go("financials", ticker=ticker, return_to="terminal")
    scene = app.scenes.current
    scene.update(0.016)
    n_bal_rows = (len(scene.block[0]["balance"]["assets_lines"])
                  + len(scene.block[0]["balance"]["liab_lines"]))
    scene._open_spreadsheet("balance")
    sheet = app.scenes.current
    assert n_bal_rows + 2 <= N_ROWS   # +2 lignes d'en-tête (titre, années)
    last_row = 2 + n_bal_rows
    assert sheet.sheet.get_raw(f"A{last_row}") != ""


def test_ma_target_open_spreadsheet_roundtrip(app):
    from data.ma_targets import all_targets
    target = all_targets()[0]
    app.scenes.go("ma_target", ticker=target["ticker"], return_to="ma")
    scene = app.scenes.current
    scene.tab = "ÉTATS FINANCIERS"
    scene.update(0.016)
    scene._open_spreadsheet("balance")
    assert app.scenes.current_name == "spreadsheet"
    sheet = app.scenes.current
    assert sheet.import_title == f"{target['ticker']} — Bilan"
    sheet.handle_event(pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=sheet.back_btn.rect.center))
    assert app.scenes.current_name == "ma_target"
    assert app.scenes.current.ticker == target["ticker"]
