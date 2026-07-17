"""
make_screenshots.py — Captures d'écran AUTOMATISÉES du jeu, en headless.

Rend quelques écrans représentatifs dans docs/screenshots/*.png via le driver
SDL factice (aucun affichage requis) : sert d'illustrations au README et, au
passage, de test de fumée manuel (un écran qui plante au rendu se voit ici).

    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python scripts/make_screenshots.py

Déterministe : graine fixe, marché avancé d'un nombre fixe de pas — relancer
le script régénère des images stables (diffs git lisibles).
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

import main  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "screenshots")
SEED = 20260401
STEPS = 60          # assez d'historique pour des graphes réels


def _snap(app, name):
    path = os.path.join(OUT, name + ".png")
    pygame.image.save(app.screen, path)
    print("écrit", path)


def build_app():
    app = main.App()
    p = app.gs.player
    p.name = "A. Moreau"
    p.grade_index = 6
    p.cash = 2_400_000.0
    p.reputation = 72
    p.market_seed = SEED
    p.onboarding_done = True
    p.flags["machine_welcome_seen"] = True
    app.ensure_market()
    for _ in range(STEPS):
        app.market.step()
        app.gs.advance_step(market=app.market)
    p.market_step = app.market.step_count
    # un petit portefeuille pour des écrans vivants
    from core import portfolio as pf
    for j, qty in ((0, 120), (10, 60), (25, 90), (60, 40)):
        pf.buy(p, app.market, app.market.companies[j]["ticker"], qty)
    p.watchlist = [app.market.companies[j]["ticker"] for j in (0, 10, 25)]
    return app


def shot_desktop(app):
    """Bureau avec quelques fenêtres ouvertes (le plan d'ensemble du jeu)."""
    app.gs.player.flags.pop("last_quarter_report", None)   # pas de carte modale sur la capture
    app.scenes.go("desktop")
    d = app.scenes.scenes["desktop"]
    d.on_enter()
    for w in list(d.wm.windows):
        d.wm.close(w)
    w1 = d._launch("markethub")
    if w1:
        w1.rect = pygame.Rect(340, 60, 620, 420)
        w1.first_open_brief = None
    w2 = d._launch("book")
    if w2:
        w2.rect = pygame.Rect(700, 250, 540, 400)
        w2.first_open_brief = None
    for _ in range(30):     # laisse finir l'animation d'ouverture des fenêtres
        d.update(0.033)
    d.draw(app.screen)
    _snap(app, "desktop")


def shot_trading(app):
    d = app.scenes.scenes["desktop"]
    for w in list(d.wm.windows):
        d.wm.close(w)
    w = d._launch("trading")
    if w:
        w.rect = pygame.Rect(120, 50, 1040, 620)
        w.first_open_brief = None
    for _ in range(30):
        d.update(0.033)
    d.draw(app.screen)
    _snap(app, "trading")


def shot_gameover(app):
    p = app.gs.player
    p.game_over = True
    p.game_over_reason = ("Réputation anéantie : vous êtes écarté "
                          "de la profession.")
    p.decisions_log = [
        {"day": 42, "title": "Un tuyau d'initié", "choice": "Refuser net"},
        {"day": 130, "title": "Maquiller une perte", "choice": "Tout déclarer"},
    ]
    p.badges = ["first_deal"]
    app.scenes.go("gameover")
    sc = app.scenes.scenes["gameover"]
    sc.update(0.016)
    sc.draw(app.screen)
    _snap(app, "gameover")
    p.game_over = False


def run():
    os.makedirs(OUT, exist_ok=True)
    app = build_app()
    shot_desktop(app)
    shot_trading(app)
    shot_gameover(app)
    print("terminé :", OUT)


if __name__ == "__main__":
    run()
