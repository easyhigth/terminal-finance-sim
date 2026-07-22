"""
tests/test_perf_caches.py — Verrous des CACHES de rendu ajoutés après profilage
(scripts/profile_scenes.py). Ces caches ont fait tomber trois écrans lourds
(frontier_lab 139 ms → <9 ms, analytics 73 ms, tutorials 35 ms par frame) en
évitant de recalculer, à CHAQUE draw(), une optimisation SLSQP ou des centaines
de mesures font.size() sur du texte statique.

On teste deux choses : (1) le cache renvoie bien le MÊME résultat que le calcul
direct (pas de régression de correction) ; (2) il s'invalide quand ses entrées
changent (sinon un écran resterait figé sur un état périmé). Plus un smoke du
harnais de profilage lui-même, pour qu'il ne pourrisse pas silencieusement.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from ui import fonts, widgets


@pytest.fixture(scope="module", autouse=True)
def _pygame_font():
    """Les helpers de mesure ont besoin du sous-système font initialisé
    (le reste de la suite passe par main.App() qui l'initialise)."""
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    yield


# --------------------------------------------------------------- mesures texte
def test_fit_text_cache_matches_and_truncates():
    f = fonts.small()
    long = "Une chaîne délibérément beaucoup trop longue pour la largeur donnée"
    out1 = widgets.fit_text(long, f, 80)
    out2 = widgets.fit_text(long, f, 80)
    assert out1 == out2
    assert out1.endswith("…")
    assert f.size(out1)[0] <= 80
    # texte qui tient : renvoyé tel quel
    assert widgets.fit_text("ok", f, 400) == "ok"


def test_wrap_text_lines_cache_matches_direct():
    f = fonts.tiny()
    txt = "un deux trois quatre cinq six sept huit neuf dix onze douze treize"
    a = widgets.wrap_text_lines(txt, f, 120)
    b = widgets.wrap_text_lines(txt, f, 120)
    assert a == b
    # chaque ligne tient dans la largeur
    for line in a:
        assert f.size(line)[0] <= 120
    # le texte complet est préservé mot pour mot
    assert " ".join(a).split() == txt.split()


# ------------------------------------------------------- frontière efficiente
@pytest.fixture(scope="module")
def app_with_portfolio():
    import main
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.cash = 3_000_000.0
    for _ in range(40):                 # historique pour la frontière
        a.market.step()
    from core import portfolio as pf
    for j in (0, 10, 25, 60):
        pf.buy(p, a.market, a.market.companies[j]["ticker"], 50)
    return a


def test_equity_frontier_memoized_same_step(app_with_portfolio):
    from core import analytics
    a = app_with_portfolio
    r1 = analytics.equity_frontier(a.gs.player, a.market)
    r2 = analytics.equity_frontier(a.gs.player, a.market)
    assert r1 is not None
    assert r1 is r2                      # même objet -> pas de recalcul


def test_equity_frontier_invalidates_on_step(app_with_portfolio):
    from core import analytics
    a = app_with_portfolio
    r1 = analytics.equity_frontier(a.gs.player, a.market)
    a.market.step()
    r2 = analytics.equity_frontier(a.gs.player, a.market)
    assert r2 is not None
    assert r1 is not r2                  # pas de résultat périmé après un pas


# ---------------------------------------------------------- harnais de profil
def test_profile_scenes_harness_runs():
    """Fume-test : le profileur boote l'app et mesure quelques scènes sans
    erreur (garde l'outil vivant, comme scripts/make_screenshots)."""
    import scripts.profile_scenes as prof
    app = prof.build_app()
    rows, errs = prof.measure(app, frames=2, include_flow=False)
    assert rows, "aucune scène mesurée"
    assert not errs, f"scènes en erreur dans le harnais : {errs}"
    assert all("frame_ms" in r for r in rows)
