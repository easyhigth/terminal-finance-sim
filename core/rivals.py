"""
rivals.py — Concurrents et classement (logique pure, sans pygame).

Des banquiers rivaux nommés progressent au fil du temps (corrélés au marché).
Ils raflent les deals que le joueur laisse expirer, créant une pression
concurrentielle tangible. Un classement situe le joueur face à eux.

Le « score » d'un acteur est exprimé dans la même unité (monétaire) que la
valeur nette du joueur, pour permettre la comparaison.
"""
import random
from core import config

RIVAL_PROFILES = [
    {"name": "Marcus Vale", "firm": "Vale & Co.", "track": "M&A"},
    {"name": "Lena Ortega", "firm": "Ortega Capital", "track": "Risk"},
    {"name": "Kenji Sato", "firm": "Sato Quant", "track": "Quant"},
    {"name": "Sophia Brandt", "firm": "Brandt AM", "track": "Portfolio"},
    {"name": "Idris Cole", "firm": "Cole Advisory", "track": "Advisory"},
]


def ensure(player, rng=None):
    """Initialise les rivaux si nécessaire (scores proches du capital de départ)."""
    rng = rng or random
    if player.rivals:
        return
    player.rivals = []
    for prof in RIVAL_PROFILES:
        player.rivals.append({
            "name": prof["name"], "firm": prof["firm"], "track": prof["track"],
            "score": round(config.START_CASH * rng.uniform(0.7, 1.7), 2),
        })


def step(player, market, rng=None):
    """Fait évoluer le score des rivaux (dérive + couplage marché + bruit)."""
    rng = rng or random
    ensure(player, rng)
    world = getattr(market, "last_world", 0.0)
    for r in player.rivals:
        # dérive modérée + couplage marché atténué + bruit borné (anti-emballement)
        growth = 0.003 + 0.6 * world + rng.gauss(0.0, 0.018)
        growth = max(-0.12, min(0.12, growth))
        r["score"] = max(1000.0, r["score"] * (1 + growth))


def player_score(player, market):
    """Score composite du joueur : valeur nette + réputation + prestige."""
    from core import portfolio
    nw = portfolio.net_worth(player, market)
    return nw + player.reputation * 4000 + len(player.titles) * 40000


def leaderboard(player, market):
    """Classement décroissant joueur + rivaux. Retourne [{name, firm, score, is_player}]."""
    ensure(player)
    rows = [{"name": r["name"], "firm": r["firm"], "score": r["score"],
             "is_player": False} for r in player.rivals]
    rows.append({"name": player.name + " (vous)", "firm": player.firm_name or "vous",
                 "score": player_score(player, market), "is_player": True})
    rows.sort(key=lambda x: x["score"], reverse=True)
    for i, row in enumerate(rows):
        row["rank"] = i + 1
    return rows


def player_rank(player, market):
    for row in leaderboard(player, market):
        if row["is_player"]:
            return row["rank"], len(player.rivals) + 1
    return 0, 0


def snipe(player, deal, rng=None):
    """Un rival rafle un deal expiré : son score grimpe. Retourne son nom."""
    rng = rng or random
    ensure(player, rng)
    # de préférence un rival de la même voie que le deal
    same = [r for r in player.rivals if r["track"] == deal.get("kind")]
    rival = rng.choice(same) if same else rng.choice(player.rivals)
    # un deal raflé profite au rival, mais sans le faire exploser (fraction)
    rival["score"] += deal.get("reward_cash", 0) * 0.3
    return rival["name"]
