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
    "compare": lambda app: {"tickers": [app.market.companies[0]["ticker"],
                                        app.market.companies[1]["ticker"]]},
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
    "menu", "continent", "runsetup", "sandbox", "terminal", "desktop", "glossary", "evaluation", "portfolio",
    "portfolio_unified",
    "ma", "ma_target", "mandates", "deals", "track", "risk", "quant",
    "spreadsheet", "saves", "gameover", "company", "commands", "mission",
    "career", "book", "inbox", "dilemma", "intro", "academy", "cert", "deal",
    "financials", "bonds", "governments", "commodities", "crypto", "etfs",
    "news", "notifications", "structured", "credit", "alm", "swaps", "hedge",
    "options", "ipo", "fx", "review", "calendar", "graph", "rivals",
    "analytics", "performance", "explorer", "tutorials", "splash", "markethub", "wall",
    "settings", "shop",
    "examcert", "stresstest", "history", "team", "alerts", "frontier_lab",
    "compare", "achievements", "stats", "tradejournal",
]


# scènes ALIAS qui redirigent ailleurs dès le 1er update (pas de visite
# stationnaire possible) — testées par leurs tests dédiés plus bas.
_REDIRECT_SCENES = {"spreadsheet"}


@pytest.mark.parametrize("name", [n for n in _KNOWN_SCENES if n not in _REDIRECT_SCENES])
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
# Couvre l'option "→ TABLEUR" des écrans d'états financiers
# (scene_financials.py / scene_ma_target.py). Le tableur plein écran
# historique a été retiré : toute navigation vers "spreadsheet" (alias
# scenes/scene_sheet_redirect.py) atterrit désormais sur le BUREAU avec l'app
# Tableur native ouverte (classeur app.workbook) et les données importées.

def _redirected_sheet(app):
    """Suit la redirection "spreadsheet" → bureau et retourne le classeur de
    l'app Tableur ouverte en fenêtre."""
    assert app.scenes.current_name == "spreadsheet"
    app.scenes.current.update(0.016)
    assert app.scenes.current_name == "desktop"
    desk = app.scenes.current
    win = next(w for w in desk.wm.windows if w.key == "sheet")
    return win.app_obj


def test_financials_open_spreadsheet_income(app):
    ticker = app.market.companies[0]["ticker"]
    app.scenes.go("financials", ticker=ticker, return_to="terminal")
    scene = app.scenes.current
    scene.update(0.016)
    scene._open_spreadsheet("income")
    sheet_app = _redirected_sheet(app)
    s = sheet_app.sheet
    assert s.get_raw("A1") == f"{ticker} — Compte de résultat"
    # libellé de la première ligne importée (Chiffre d'affaires) en A3
    assert s.get_raw("A3") == "Chiffre d'affaires"
    # valeur numérique importée et lisible par le moteur de formules
    assert isinstance(s.get_value("B3"), float)


def test_financials_open_spreadsheet_balance_fits_grid(app):
    """Le bilan (~14 lignes) doit tenir entièrement dans la grille du tableur
    (régression : la grille était trop petite -> lignes tronquées silencieusement)."""
    from apps.app_sheet import N_ROWS
    ticker = app.market.companies[0]["ticker"]
    app.scenes.go("financials", ticker=ticker, return_to="terminal")
    scene = app.scenes.current
    scene.update(0.016)
    n_bal_rows = (len(scene.block[0]["balance"]["assets_lines"])
                  + len(scene.block[0]["balance"]["liab_lines"]))
    scene._open_spreadsheet("balance")
    sheet_app = _redirected_sheet(app)
    assert n_bal_rows + 2 <= N_ROWS   # +2 lignes d'en-tête (titre, années)
    last_row = 2 + n_bal_rows
    assert sheet_app.sheet.get_raw(f"A{last_row}") != ""


def test_financials_overview_exposes_earnings_and_relative_value(app):
    """L'écran FA enrichi expose désormais : médianes sectorielles
    (m.sector_medians, réutilisées de la commande RV) et l'attribution
    factorielle du dernier pas (m.factor_attribution, réutilisée du desk
    risque) pour le ticker consulté, en plus des stats déjà existantes."""
    # avance le marché pour qu'au moins un résultat trimestriel soit publié
    for _ in range(20):
        app.market.step()
    ticker = app.market.companies[0]["ticker"]
    app.scenes.go("financials", ticker=ticker, return_to="terminal")
    scene = app.scenes.current
    scene.update(0.016)
    scene.draw(app.screen)
    assert scene.sector_med is not None
    assert scene.sector_med["n"] >= 1
    assert scene.attribution is not None
    assert set(scene.attribution) == {"world", "sector", "region", "specific", "drift", "total"}
    # les métriques sous-jacentes (earnings_log) doivent être cohérentes avec
    # ce que la fiche société affiche déjà (réutilisation, pas de duplication)
    mt = app.market.metrics(ticker)
    assert scene.metrics["last_earnings"] == mt["last_earnings"]


def test_financials_overview_handles_no_earnings_yet(app):
    """Au tout début d'une partie (aucun résultat publié), l'écran ne doit
    pas planter : last_earnings/last_guidance sont None et l'historique de
    cours est court (< 2 points). Couvre la branche 'Aucun résultat publié'
    et 'Historique en constitution'."""
    a2 = main.App()
    a2.ensure_market()
    ticker = a2.market.companies[3]["ticker"]
    a2.scenes.go("financials", ticker=ticker, return_to="terminal")
    scene = a2.scenes.current
    scene.update(0.016)
    scene.draw(a2.screen)   # ne doit pas lever d'exception
    assert scene.metrics["last_earnings"] is None


def test_ma_target_open_spreadsheet_redirects_to_desktop_sheet(app):
    from data.ma_targets import all_targets
    target = all_targets()[0]
    app.scenes.go("ma_target", ticker=target["ticker"], return_to="ma")
    scene = app.scenes.current
    scene.tab = "ÉTATS FINANCIERS"
    scene.update(0.016)
    scene._open_spreadsheet("balance")
    sheet_app = _redirected_sheet(app)
    assert sheet_app.sheet.get_raw("A1") == f"{target['ticker']} — Bilan"
