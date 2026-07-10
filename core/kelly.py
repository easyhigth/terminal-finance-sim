"""
kelly.py — Critère de Kelly / dimensionnement de position (logique pure).

Combien risquer par trade ? Le critère de Kelly maximise la croissance
GÉOMÉTRIQUE du capital : pour un pari gagné avec probabilité p (gain b×mise)
et perdu avec probabilité 1−p (mise perdue),

    f* = p − (1 − p)/b        (fraction de Kelly)

Appliqué aux STATS RÉELLES du Journal de trading du joueur (taux de
réussite p et ratio gain moyen/perte moyenne b observés). La courbe de
croissance g(f) = p·ln(1 + f·b) + (1 − p)·ln(1 − f) montre les deux leçons
du sizing : (1) au-delà de f*, plus de risque = MOINS de croissance ;
(2) au double de Kelly, la croissance retombe à zéro — sur-risquer un
edge positif suffit à ruiner. Le demi-Kelly (f*/2) est la pratique
prudente (≈ 75 % de la croissance pour bien moins de variance).

Garde-fous : avec moins de `MIN_TRADES` trades réalisés, l'estimation de p
et b est du bruit — on l'affiche mais on le DIT.
"""
import math

MIN_TRADES = 10


def stats_from_journal(player):
    """Stats de pari du Journal (trades RÉALISÉS uniquement). Renvoie None
    sans trade réalisé, sinon {n, p, avg_win, avg_loss, b, expectancy,
    reliable}."""
    entries = [e for e in getattr(player, "trade_journal", []) or []
               if e.get("realized") is not None]
    if not entries:
        return None
    wins = [e["realized"] for e in entries if e["realized"] > 0]
    losses = [-e["realized"] for e in entries if e["realized"] < 0]
    n = len(entries)
    p = len(wins) / n
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    b = (avg_win / avg_loss) if avg_loss > 0 else 0.0
    expectancy = p * avg_win - (1.0 - p) * avg_loss
    return {"n": n, "p": p, "avg_win": avg_win, "avg_loss": avg_loss,
            "b": b, "expectancy": expectancy, "reliable": n >= MIN_TRADES}


def kelly_fraction(p, b):
    """f* = p − (1−p)/b, borné à [0, 1]. 0 si le pari n'a pas d'edge
    (espérance ≤ 0) ou si b n'est pas exploitable."""
    if b <= 0:
        return 0.0
    f = p - (1.0 - p) / b
    return max(0.0, min(1.0, f))


def growth_rate(f, p, b):
    """Croissance géométrique attendue par pari, à la fraction f :
    g(f) = p·ln(1 + f·b) + (1−p)·ln(1 − f). −inf si f ≥ 1 (ruine)."""
    if f >= 1.0 or f < 0.0:
        return float("-inf")
    if f == 0.0:
        return 0.0
    return p * math.log(1.0 + f * b) + (1.0 - p) * math.log(1.0 - f)


def growth_curve(p, b, n_points=40):
    """Courbe (f, g(f)) de 0 à min(1, 2·f*) — on VOIT le sommet à f* et la
    chute au-delà. [(f, g)]."""
    f_star = kelly_fraction(p, b)
    fmax = min(0.99, max(0.20, 2.0 * f_star))
    out = []
    for i in range(n_points + 1):
        f = fmax * i / n_points
        out.append((f, growth_rate(f, p, b)))
    return out


def recommendation(player, net_worth):
    """Recommandation de sizing complète depuis le Journal. Renvoie None
    sans historique, sinon {stats, f_star, f_half, stake_full, stake_half,
    curve, warning}."""
    stats = stats_from_journal(player)
    if stats is None:
        return None
    f_star = kelly_fraction(stats["p"], stats["b"])
    warning = None
    if not stats["reliable"]:
        warning = (f"Seulement {stats['n']} trades réalisés — p et b sont "
                   "encore du bruit, pas une loi.")
    elif stats["expectancy"] <= 0:
        warning = ("Espérance NÉGATIVE : aucun sizing ne rend gagnant un "
                   "système perdant — Kelly dit : ne pariez pas.")
    return {"stats": stats, "f_star": f_star, "f_half": f_star / 2.0,
            "stake_full": f_star * max(0.0, net_worth),
            "stake_half": f_star / 2.0 * max(0.0, net_worth),
            "curve": growth_curve(stats["p"], stats["b"]),
            "warning": warning}
