"""
test_financial_apps_integration.py — Tests d'intégration des apps quantitatives
du bureau (Sharpe / Z-Score / Couverture).

Vérifie l'INSTANCIATION réelle (via un contexte App complet, pas un mock None),
le succès de `on_open`, les valeurs par défaut et un rendu smoke —complément
léger au harnais comportemental de tests/test_quant_apps.py (clics, recalcul
au pas de marché, exécution d'ordres). Verrouille l'API publique de ces apps
(titre, icône, tailles, attributs par défaut) contre les dériveages.

Historique : une version antérieure de ce fichier testait une API disparue
(`SharpeApp(None)`, `_period_to_steps()` renvoyant 365 pour "1Y"…) correspondant
aux apps « PR hors-bande » réécrites depuis sur core/quant_tools (cf. CLAUDE.md,
et tests/test_quant_apps.py qui les remplace).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main

pygame.font.init()

RECT = pygame.Rect(0, 0, 1000, 640)


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    for _ in range(60):
        a.market.step()
    a.scenes.go("desktop")
    return a


def _open(app, key):
    """Ouvre l'app native `key` sur le bureau et renvoie l'objet app."""
    desk = app.scenes.current
    w = desk._open_scene_window(key)
    assert w is not None, f"échec ouverture app {key!r}"
    w.app_obj.on_open()
    return w.app_obj


# ============================================================== Sharpe
def test_sharpe_app_creation_and_defaults(app):
    from core import quant_tools as QT
    sa = _open(app, "sharpe")
    assert sa.title == "Sharpe Ratio"
    assert sa.icon_kind == "graph"
    assert sa.default_size == (980, 620)
    assert sa.min_size == (700, 460)
    assert sa.period == "1A"                         # période par défaut
    assert sa.rf == 0.02                             # taux sans risque par défaut
    # la période par défaut résout sur le barème réel (1A = 73 pas, pas 365)
    assert QT.PERIOD_STEPS[sa.period] == 73
    sa.draw(app.screen, RECT)                         # rendu smoke sans erreur


# ============================================================== Z-Score
def test_zscore_app_creation_and_defaults(app):
    from core import quant_tools as QT
    za = _open(app, "zscore")
    assert za.title == "Z-Score"
    assert za.icon_kind == "graph"
    assert za.default_size == (960, 600)
    assert za.min_size == (700, 460)
    assert za.period == "1A"
    assert za.ticker                                  # ticker par défaut non vide
    assert za.analysis == "price"                     # type d'analyse par défaut
    assert za.msg == ""
    assert QT.PERIOD_STEPS[za.period] == 73
    za.draw(app.screen, RECT)


# ================================================================ Hedge
def test_hedge_app_creation_and_defaults(app):
    ha = _open(app, "hedge")
    assert ha.title == "Couverture"
    assert ha.icon_kind == "shield"
    assert ha.default_size == (980, 620)
    assert ha.min_size == (720, 480)
    assert ha.mode == "put"                           # "put" | "pair"
    assert ha.strike_idx == 1                         # défaut -5 %
    assert ha.msg == ""
    ha.draw(app.screen, RECT)


# ================================================ barème des périodes
def test_period_steps_barème_is_the_graph_standard():
    """Les apps quant partagent le barème de scene_graph.STEP_PERIODS :
    1 pas = 5 jours, donc 1A = 73 pas (≈ 365 j), 5A = 365 pas, MAX = None."""
    from core import quant_tools as QT
    assert QT.PERIOD_STEPS == {"1M": 6, "3M": 18, "1A": 73,
                               "3A": 219, "5A": 365, "MAX": None}
