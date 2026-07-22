"""
profile_scenes.py — Profilage HEADLESS du coût de rendu des scènes/apps.

Complète l'overlay live FINSIM_DEBUG (ui/perf_overlay.py, mesure en jeu) par
une mesure REPRODUCTIBLE hors écran : boote l'app avec le driver SDL factice,
avance le marché d'un nombre fixe de pas (historique réel pour les graphes),
puis chronomètre update()+draw() de chaque scène sur N frames. Sert à
RÉPONDRE « quelle scène est la plus lourde, et où passe le temps ? » sans
supposer — au-delà du cache de texte déjà en place (cf. CLAUDE.md).

    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python scripts/profile_scenes.py
    ... --frames 120 --top 20            # plus de frames, tableau plus long
    ... --profile graph                  # cProfile fonction-par-fonction d'UNE scène
    ... --json out.json                  # tableau brut pour comparer deux commits

Déterministe : graine fixe + nombre de pas fixe → deux exécutions sur le même
commit rendent des chiffres comparables (le bruit machine près, d'où la
moyenne sur N frames et l'exclusion du pire échantillon).
"""
import argparse
import cProfile
import os
import pstats
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402

SEED = 20260401
STEPS = 60          # assez d'historique pour exercer le rendu des graphes réels

# Scènes qui exigent des kwargs pour s'afficher dans leur état normal
# (aligné sur tests/test_scene_smoke.py::_SPECIAL_KWARGS).
_SPECIAL_KWARGS = {
    "ma_target": lambda app: {"ticker": app.market.companies[0]["ticker"]},
    "company": lambda app: {"ticker": app.market.companies[0]["ticker"]},
    "financials": lambda app: {"ticker": app.market.companies[0]["ticker"]},
    "graph": lambda app: {"tickers": [app.market.companies[0]["ticker"]]},
    "compare": lambda app: {"tickers": [app.market.companies[0]["ticker"],
                                        app.market.companies[1]["ticker"]]},
}

# Écrans de flux hors-partie : pas représentatifs de la boucle de jeu, exclus
# du classement par défaut (mesurables avec --all).
_FLOW_SCENES = {"menu", "splash", "intro", "continent", "runsetup", "sandbox",
                "saves", "gameover"}

# Scènes alias qui redirigent au 1er update (rien de stationnaire à mesurer).
_REDIRECT_SCENES = {"spreadsheet"}


def build_app():
    """App headless dans un état de milieu de partie (features débloquées,
    petit portefeuille, marché avancé) — mêmes hypothèses que make_screenshots."""
    app = main.App()
    p = app.gs.player
    p.name = "A. Moreau"
    p.grade_index = 9              # débloque la quasi-totalité des features
    p.cash = 3_000_000.0
    p.reputation = 78
    p.heat = 10
    p.market_seed = SEED
    p.onboarding_done = True
    p.flags["machine_welcome_seen"] = True
    app.ensure_market()
    for _ in range(STEPS):
        app.market.step()
        app.gs.advance_step(market=app.market)
    p.market_step = app.market.step_count
    from core import portfolio as pf
    for j, qty in ((0, 120), (10, 60), (25, 90), (60, 40)):
        pf.buy(p, app.market, app.market.companies[j]["ticker"], qty)
    p.watchlist = [app.market.companies[j]["ticker"] for j in (0, 10, 25)]
    return app


def _scene_names(app, include_flow):
    names = [n for n in app.scenes.scenes if n not in _REDIRECT_SCENES]
    if not include_flow:
        names = [n for n in names if n not in _FLOW_SCENES]
    return names


def _enter(app, name):
    kwargs = _SPECIAL_KWARGS.get(name, lambda _a: {})(app)
    app.scenes.go(name, **kwargs)
    scene = app.scenes.current
    # deux cycles de chauffe : certaines scènes bâtissent leur état au 1er update
    for _ in range(2):
        scene.update(0.016)
        scene.draw(app.screen)
    return scene


def _time_scene(app, name, frames):
    """Retourne (update_ms, draw_ms) MOYENS par frame, pire échantillon exclu
    pour amortir un hoquet ponctuel du GC/OS."""
    scene = _enter(app, name)
    ups, draws = [], []
    for _ in range(frames):
        t0 = time.perf_counter()
        scene.update(0.016)
        t1 = time.perf_counter()
        scene.draw(app.screen)
        t2 = time.perf_counter()
        ups.append((t1 - t0) * 1000.0)
        draws.append((t2 - t1) * 1000.0)

    def _trimmed_mean(xs):
        if len(xs) <= 2:
            return sum(xs) / len(xs)
        xs = sorted(xs)[:-1]            # exclut le pire
        return sum(xs) / len(xs)

    return _trimmed_mean(ups), _trimmed_mean(draws)


def measure(app, frames, include_flow):
    rows = []
    for name in _scene_names(app, include_flow):
        try:
            up, draw = _time_scene(app, name, frames)
            rows.append({"scene": name, "update_ms": round(up, 3),
                         "draw_ms": round(draw, 3),
                         "frame_ms": round(up + draw, 3),
                         "est_fps": round(1000.0 / (up + draw), 1) if (up + draw) > 0 else 0.0})
        except Exception as exc:       # une scène qui plante ne doit pas tout arrêter
            rows.append({"scene": name, "error": f"{type(exc).__name__}: {exc}"})
    ok = [r for r in rows if "error" not in r]
    ok.sort(key=lambda r: r["frame_ms"], reverse=True)
    errs = [r for r in rows if "error" in r]
    return ok, errs


def _print_table(rows, errs, top):
    print(f"\n{'scène':<20} {'update':>9} {'draw':>9} {'frame':>9} {'~FPS':>7}")
    print("-" * 58)
    for r in rows[:top]:
        print(f"{r['scene']:<20} {r['update_ms']:>8.2f} {r['draw_ms']:>8.2f} "
              f"{r['frame_ms']:>8.2f} {r['est_fps']:>7.0f}")
    if len(rows) > top:
        print(f"... ({len(rows) - top} scènes plus légères non affichées, --top pour tout voir)")
    if errs:
        print("\nScènes en erreur (rendu impossible dans ce harnais) :")
        for r in errs:
            print(f"  {r['scene']:<20} {r['error']}")
    if rows:
        heaviest = rows[0]
        print(f"\nPlus lourde : {heaviest['scene']} "
              f"({heaviest['frame_ms']:.2f} ms/frame ≈ {heaviest['est_fps']:.0f} FPS). "
              f"Profil fonction-par-fonction : --profile {heaviest['scene']}")


def profile_one(app, name, frames):
    """cProfile de update()+draw() d'UNE scène : révèle les fonctions qui
    dominent le temps cumulé (le vrai goulot, pas la supposition)."""
    scene = _enter(app, name)

    def _run():
        for _ in range(frames):
            scene.update(0.016)
            scene.draw(app.screen)

    prof = cProfile.Profile()
    prof.enable()
    _run()
    prof.disable()
    print(f"\ncProfile — scène « {name} » sur {frames} frames "
          f"(tri par temps cumulé, top 25) :\n")
    stats = pstats.Stats(prof)
    stats.sort_stats("cumulative")
    stats.print_stats(25)


def main_cli():
    ap = argparse.ArgumentParser(description="Profilage headless des scènes.")
    ap.add_argument("--frames", type=int, default=60, help="frames chronométrées par scène")
    ap.add_argument("--top", type=int, default=15, help="lignes affichées dans le classement")
    ap.add_argument("--all", action="store_true", help="inclure les écrans de flux hors-partie")
    ap.add_argument("--profile", metavar="SCENE", help="cProfile fonction-par-fonction d'une scène")
    ap.add_argument("--json", metavar="PATH", help="écrit le tableau brut en JSON")
    args = ap.parse_args()

    app = build_app()
    if args.profile:
        if args.profile not in app.scenes.scenes:
            print(f"scène inconnue : {args.profile!r} "
                  f"(voir la liste avec une exécution normale)")
            return 2
        profile_one(app, args.profile, args.frames)
        return 0

    rows, errs = measure(app, args.frames, include_flow=args.all)
    _print_table(rows, errs, args.top)
    if args.json:
        import json
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        print(f"\nJSON écrit : {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main_cli())
