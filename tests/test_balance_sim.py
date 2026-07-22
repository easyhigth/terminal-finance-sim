"""
tests/test_balance_sim.py — Fume-test du harnais de télémétrie d'équilibrage
(scripts/balance_sim.py) : garde l'outil vivant (comme make_screenshots /
profile_scenes) et vérifie ses INVARIANTS de sortie, pas des chiffres précis
(ils bougeront à chaque rééquilibrage). Deux propriétés qui doivent tenir quoi
qu'il arrive : (1) une carrière simulée reste dans les bornes du jeu ;
(2) un meilleur `skill` ne progresse jamais MOINS loin en médiane qu'un pire —
si un jour cette monotonie casse, c'est un signal d'équilibrage à regarder.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from core import config
from scripts import balance_sim


def test_simulate_one_stays_within_game_bounds():
    r = balance_sim.simulate_one(seed=42, skill=0.8, work_prob=0.8,
                                 deals_per_quarter=1, max_steps=120)
    assert 0 <= r["final_grade"] <= len(config.GRADES) - 1
    assert r["final_day"] >= 1
    assert r["years"] >= 0
    assert 0 in r["reached"]                      # on démarre toujours au grade 0
    # tout grade atteint l'est à un jour croissant avec le grade
    days = [r["reached"][g] for g in sorted(r["reached"])]
    assert days == sorted(days)
    assert isinstance(r["game_over"], bool)


def test_run_profile_shape_and_grade_coverage():
    prof = balance_sim.run_profile(skill=0.85, runs=3, work_prob=0.9,
                                   deals_per_quarter=1, max_steps=200, base_seed=7)
    assert prof["runs"] == 3
    assert 0.0 <= prof["game_over_pct"] <= 100.0
    # une entrée par grade promouvable (1..TOP)
    assert set(prof["per_grade"]) == set(range(1, len(config.GRADES)))
    for g, cell in prof["per_grade"].items():
        assert 0.0 <= cell["reach_pct"] <= 100.0


def test_higher_skill_reaches_at_least_as_far():
    """Monotonie du design : à assiduité égale, l'expert ne doit pas finir plus
    BAS que le novice en médiane (sinon un palier récompense mal la compétence)."""
    common = dict(runs=6, work_prob=0.8, deals_per_quarter=1, max_steps=500, base_seed=100)
    low = balance_sim.run_profile(skill=0.55, **common)
    high = balance_sim.run_profile(skill=0.95, **common)
    assert high["median_final_grade"] >= low["median_final_grade"]
