"""
balance_sim.py — Harnais de TÉLÉMÉTRIE D'ÉQUILIBRAGE (headless).

Joue N carrières complètes selon les VRAIES règles de progression du jeu
(core/career.promotion_requirements, GameState.advance_step, missions,
économie salaire/coûts, game-over) et agrège combien de temps de jeu il faut
pour atteindre chaque grade, à différents niveaux de compétence du joueur.
But : repérer les PALIERS trop durs / trop lents SANS deviner — le levier n° 1
pour régler la difficulté d'un jeu au contenu déjà complet (cf. CLAUDE.md,
asymétrie novice/expert).

    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python scripts/balance_sim.py
    ... --skills 0.6,0.75,0.9 --runs 30      # compare novice / moyen / expert
    ... --json balance.json                   # données brutes pour diff entre commits

Politique du bot (ASSUMÉE, et c'est le point) : on ne simule PAS les mini-jeux
(quiz mission, deals) — on paramètre les DÉCISIONS du joueur et on laisse le
jeu appliquer ses propres règles de gate :
  * `skill`  : fraction de bonnes réponses aux missions (→ réputation/cash via
               missions.compute_rewards, la vraie formule) ;
  * `work_prob` : probabilité de faire une mission à un tour donné (assiduité) ;
  * `deals_per_quarter` : deals conclus par trimestre (le gate « deals » des
               grades ≥ 2), modélisé en cadence plutôt qu'en mini-jeu.
La promotion, l'économie et le game-over passent, eux, par le code de jeu réel.
Déterministe par graine : un même (graine, profil) rejoue la même carrière.
"""
import argparse
import os
import statistics
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random  # noqa: E402

import main  # noqa: E402
from core import career, config, missions  # noqa: E402

# Voie de spécialisation choisie par le bot au grade 2 (le gate « TRACK » l'exige).
# Peu importe laquelle pour la PACING ; on en fixe une pour la reproductibilité.
_BOT_TRACK = "Portfolio"
DAYS_PER_YEAR = config.DAYS_PER_QUARTER * 4
TOP_GRADE = len(config.GRADES) - 1


def _new_run(seed):
    """App fraîche (gs + marché) pour un joueur débutant au grade 0."""
    app = main.App()
    p = app.gs.player
    p.market_seed = seed
    p.onboarding_done = True
    p.flags["machine_welcome_seen"] = True
    app.ensure_market()
    p.market_step = app.market.step_count
    return app


def _do_mission(app, rng, skill):
    """Joue une mission au niveau `skill` et applique les récompenses via la
    formule réelle (missions.compute_rewards), comme core/mission_flow mais
    sans le couplage UI."""
    p = app.gs.player
    m = missions.generate(p.grade_index, app.market, rng=rng, track=p.track, player=p)
    total = len(m["items"])
    if total == 0:
        return
    correct = int(round(skill * total))
    rep, cash = missions.compute_rewards(m, correct, total, player=p)
    p.adjust_reputation(rep, reason="sim.mission")
    p.adjust_cash(cash)
    p.missions_done += 1
    p.grade_missions += 1


def simulate_one(seed, skill, work_prob, deals_per_quarter, max_steps):
    """Une carrière. Retourne {reached:{grade:day}, final_grade, final_day,
    years, game_over, reason, cash}."""
    app = _new_run(seed)
    p = app.gs.player
    rng = random.Random(seed ^ 0x5EED)
    reached = {0: 0}
    prev_quarter = p.quarter

    for _ in range(max_steps):
        if p.game_over or p.grade_index >= TOP_GRADE:
            break
        # choisir une voie dès que le gate l'exige (grade ≥ 2)
        if p.grade_index >= 2 and p.track == "General":
            p.track = _BOT_TRACK
        # assiduité : faire (ou non) une mission ce tour
        if rng.random() < work_prob:
            _do_mission(app, rng, skill)
        # promotion si tous les critères réels sont remplis
        if career.promotion_ready(p):
            p.promote()
            reached.setdefault(p.grade_index, p.day)
        # avancer le temps d'un tour (économie, marché, game-over : code réel)
        app.market.step()
        app.gs.advance_step(market=app.market)
        # cadence de deals : créditée au passage de trimestre
        if p.quarter != prev_quarter:
            prev_quarter = p.quarter
            p.grade_deals += deals_per_quarter
            p.deals_won += deals_per_quarter

    return {
        "reached": reached,
        "final_grade": p.grade_index,
        "final_day": p.day,
        "years": round(p.day / DAYS_PER_YEAR, 2),
        "game_over": bool(p.game_over),
        "reason": p.game_over_reason if p.game_over else "",
        "cash": round(p.cash),
    }


def run_profile(skill, runs, work_prob, deals_per_quarter, max_steps, base_seed):
    results = [simulate_one(base_seed + i, skill, work_prob, deals_per_quarter, max_steps)
               for i in range(runs)]
    # jours médians pour atteindre chaque grade (parmi les runs qui l'atteignent)
    per_grade = {}
    for g in range(1, TOP_GRADE + 1):
        days = [r["reached"][g] for r in results if g in r["reached"]]
        per_grade[g] = {
            "reach_pct": round(100.0 * len(days) / runs, 1),
            "median_years": round(statistics.median(days) / DAYS_PER_YEAR, 2) if days else None,
        }
    return {
        "skill": skill,
        "runs": runs,
        "game_over_pct": round(100.0 * sum(r["game_over"] for r in results) / runs, 1),
        "median_final_grade": statistics.median(r["final_grade"] for r in results),
        "per_grade": per_grade,
    }


def _print_report(profiles):
    print("\n=== Pacing de carrière — années de jeu médianes pour atteindre chaque grade ===")
    header = f"{'grade':<22}" + "".join(f"  skill {p['skill']:<5}" for p in profiles)
    print(header)
    print("-" * len(header))
    for g in range(1, TOP_GRADE + 1):
        name = f"{g} {config.GRADES[g]}"
        cells = []
        for prof in profiles:
            pg = prof["per_grade"][g]
            if pg["median_years"] is None:
                cells.append("     —      ")   # aucun run n'atteint ce grade
            elif pg["reach_pct"] < 100.0:
                cells.append(f"{pg['median_years']:>5}y ({pg['reach_pct']:>3.0f}%)")
            else:
                cells.append(f"{pg['median_years']:>5}y      ")
        print(f"{name:<22}" + "".join(f"  {c}" for c in cells))
    print("\nLecture : « — » = palier jamais franchi dans l'horizon ; « (xx%) » = "
          "part des parties qui l'atteignent (< 100% => mur de progression).")
    print(f"{'game-over %':<22}" + "".join(f"  {p['game_over_pct']:>10}%" for p in profiles))
    print(f"{'grade final médian':<22}" + "".join(f"  {p['median_final_grade']:>11}" for p in profiles))


def main_cli():
    ap = argparse.ArgumentParser(description="Télémétrie d'équilibrage de carrière (headless).")
    ap.add_argument("--skills", default="0.6,0.75,0.9",
                    help="niveaux de compétence à comparer (fraction de bonnes réponses)")
    ap.add_argument("--runs", type=int, default=20, help="parties simulées par profil")
    ap.add_argument("--work-prob", type=float, default=0.8,
                    help="probabilité de faire une mission à chaque tour (assiduité)")
    ap.add_argument("--deals-per-quarter", type=int, default=1,
                    help="deals conclus par trimestre (gate deals des grades ≥ 2)")
    ap.add_argument("--max-steps", type=int, default=900,
                    help="tours max par partie (~horizon ; 900 ≈ 12 ans de jeu)")
    ap.add_argument("--seed", type=int, default=1000, help="graine de base")
    ap.add_argument("--json", metavar="PATH", help="écrit les profils bruts en JSON")
    args = ap.parse_args()

    try:
        skills = [float(s) for s in args.skills.split(",") if s.strip()]
    except ValueError:
        print("--skills : liste de flottants séparés par des virgules, ex. 0.6,0.75,0.9")
        return 2

    profiles = []
    for skill in skills:
        print(f"… simulation profil skill={skill} ({args.runs} parties)", file=sys.stderr)
        profiles.append(run_profile(skill, args.runs, args.work_prob,
                                    args.deals_per_quarter, args.max_steps, args.seed))
    _print_report(profiles)
    if args.json:
        import json
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)
        print(f"\nJSON écrit : {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main_cli())
