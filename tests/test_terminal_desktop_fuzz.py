"""Fuzz headless PERMANENT (graine fixe, reproductible) du terminal et du
bureau, avec un marché ayant un historique RÉEL (plusieurs dizaines de pas).

Motivation : le smoke test (tests/test_scene_smoke.py) visite chaque scène
une fois avec un marché fraîchement créé (1-2 points d'historique) — il n'a
donc jamais exercé la branche de rendu des graphes avec >= 2 points
(`ui/datawindow.py`), là où vivait le crash `widgets._hover_sync` (cf. PR
« Corrige le crash au clic sur un indice du terminal »). Ce fuzz reproduit
délibérément les conditions d'une VRAIE partie (marché avancé) et matraque
le terminal et le bureau de clics/molette/clavier pseudo-aléatoires pour
attraper toute régression similaire (widget mal alimenté, popup qui plante
au dessin...) avant qu'elle n'atteigne un joueur.

Volontairement borné (peu d'évènements) pour rester rapide en CI ; ce n'est
pas un remplacement du fuzz exploratoire plus long utilisé ponctuellement en
investigation, seulement un filet permanent bon marché.
"""
import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from core import config

pygame.font.init()

N_EVENTS = 150
KEYS = [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
        pygame.K_RETURN, pygame.K_TAB, pygame.K_BACKSPACE, pygame.K_SPACE,
        pygame.K_ESCAPE, pygame.K_a, pygame.K_m, pygame.K_1]
CHARS = "abcMV12.,-"


@pytest.fixture(scope="module")
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.reputation = 80
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    from core import onboarding as onboarding_mod
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    onboarding_mod.skip(p)
    # historique de marché RÉEL : sans ça, les graphes (indices, tickers)
    # restent sur la branche "insuffisant" qui ne dessine pas de série et ne
    # couvre donc jamais le code de rendu réellement exercé en jeu normal.
    for _ in range(40):
        a.market.step()
    return a


def _rand_event(rng):
    r = rng.random()
    W, H = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
    pos = (rng.randrange(0, W), rng.randrange(0, H))
    if r < 0.40:
        return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
    if r < 0.55:
        return pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos)
    if r < 0.65:
        return pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(3, 3), buttons=(0, 0, 0))
    if r < 0.72:
        return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=rng.choice((3, 4, 5)), pos=pos)
    if r < 0.90:
        k = rng.choice(KEYS)
        return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")
    ch = rng.choice(CHARS)
    return pygame.event.Event(pygame.KEYDOWN, key=ord(ch.lower()), mod=0, unicode=ch)


def _fuzz_scene(app, name, seed, n_events=N_EVENTS):
    rng = random.Random(seed)
    app.scenes.go(name)
    sc = app.scenes.current
    for i in range(n_events):
        if app.scenes.current is not sc:
            app.scenes.go(name)   # une navigation a eu lieu : revenir
            sc = app.scenes.current
        sc.handle_event(_rand_event(rng))
        if i % 5 == 0:
            sc.update(0.05)
            app.screen.fill((0, 0, 0))
            sc.draw(app.screen)
    sc.update(0.05)
    app.screen.fill((0, 0, 0))
    sc.draw(app.screen)


def test_fuzz_terminal_with_real_market_history_does_not_crash(app):
    _fuzz_scene(app, "terminal", seed="fuzz-terminal-real-history")


def test_fuzz_desktop_with_real_market_history_does_not_crash(app):
    _fuzz_scene(app, "desktop", seed="fuzz-desktop-real-history")


def test_fuzz_book_with_real_market_history_does_not_crash(app):
    _fuzz_scene(app, "book", seed="fuzz-book-real-history")


def test_fuzz_markethub_with_real_market_history_does_not_crash(app):
    _fuzz_scene(app, "markethub", seed="fuzz-markethub-real-history")


def test_clicking_every_terminal_index_opens_a_distinct_chart(app):
    """Verrou ciblé sur le bug corrigé : chaque ligne du panneau INDICES doit
    ouvrir SON PROPRE graphe (pas absorbé par un popup déjà ouvert qui
    recouvrirait le panneau), et le dessin de chacun (>= 2 points
    d'historique réel) ne doit pas lever."""
    app.scenes.go("terminal")
    term = app.scenes.current
    term.datawins.clear()   # fixture `app` partagée (scope="module") : repartir propre
    term.update(0.05)
    surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    term.draw(surf)
    rows = list(term._index_rects.items())
    assert len(rows) >= 2
    for i, (name, rect) in enumerate(rows):
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=rect.center)
        term.handle_event(down)
        term.handle_event(up)
        term.update(0.05)
        term.draw(surf)
        assert len(term.datawins) == i + 1
        assert all(not w.closed for w in term.datawins)
    # nettoyage pour ne pas polluer les autres tests du même module (fixture
    # `app` partagée, scope="module")
    term.datawins.clear()
