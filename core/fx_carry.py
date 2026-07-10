"""
fx_carry.py — Carry trade FX et parité des taux couverte (logique pure).

Le module FX du jeu (core/fx.py) traite les paires comme des prix purs ;
ici on leur donne leur dimension de TAUX — le cœur du marché des changes :

- **Taux par devise** : taux directeur macro du jeu + écart structurel par
  devise (le yen et le franc suisse financent, le rand et le réal
  rémunèrent — mêmes ordres de grandeur que le monde réel). Déterministe.
- **Parité des taux couverte** : le forward THÉORIQUE
  F = S·(1+r_cotée·τ)/(1+r_base·τ) — les « points de terme ». Une devise à
  haut taux cote FORWARD DÉCOTÉ : le marché « rembourse » le carry, on ne
  gagne rien sans risque (c'est le théorème).
- **Carry annuel** d'une position : LONG la paire = long la devise de BASE
  → on touche r_base − r_cotée (négatif si on est long la devise à bas
  taux). `accrue` crédite ce portage au prorata des jours écoulés sur les
  positions spot OUVERTES (câblé dans GameState.advance_step, comme les
  dividendes) — le carry devient un vrai revenu… et la leçon complète est
  dans le Labo de crise : le carry gagne petit souvent et perd gros quand
  la paire décroche.
- `carry_table` : le tableau du desk — paires triées par carry, taux des
  deux jambes, forward théorique 3 mois, points de terme.
"""
from core import fx

# Écarts structurels de taux par devise (annuels, ajoutés au taux directeur
# macro du jeu) — hiérarchie réaliste : JPY/CHF financent, ZAR/BRL portent.
CURRENCY_SPREAD = {
    "USD": 0.000, "EUR": -0.005, "GBP": 0.002, "JPY": -0.028,
    "CHF": -0.022, "AUD": 0.008, "CAD": 0.001, "ZAR": 0.045, "BRL": 0.055,
}


def base_rate(market):
    """Taux directeur macro du jeu (décimal)."""
    try:
        return market.macro["rate"]["v"] / 100.0
    except Exception:
        return 0.03


def currency_rate(market, ccy):
    """Taux annuel d'une devise = taux directeur + écart structurel."""
    return max(0.0, base_rate(market) + CURRENCY_SPREAD.get(ccy, 0.0))


def pair_rates(market, pair):
    """(r_base, r_cotée) de la paire BASE/COTÉE."""
    base, quote = pair.split("/")
    return currency_rate(market, base), currency_rate(market, quote)


def carry_annual(market, pair, direction="long"):
    """Portage annuel (décimal, signé) d'une position sur la paire :
    LONG = long la devise de base → r_base − r_cotée ; SHORT inverse."""
    r_base, r_quote = pair_rates(market, pair)
    diff = r_base - r_quote
    return diff if direction == "long" else -diff


def parity_forward(market, pair, tenor_months):
    """Forward THÉORIQUE par parité des taux couverte :
    F = S·(1 + r_cotée·τ)/(1 + r_base·τ) (cotation BASE/COTÉE : une unité
    de base vaut S unités cotées — la devise au taux le plus HAUT cote
    forward décoté). Renvoie None si paire inconnue."""
    sp = fx.spot(market, pair)
    if sp is None:
        return None
    r_base, r_quote = pair_rates(market, pair)
    tau = tenor_months / 12.0
    return sp * (1.0 + r_quote * tau) / (1.0 + r_base * tau)


def carry_table(market, tenor_months=3):
    """Le tableau du desk : chaque paire avec spot, taux des deux jambes,
    carry annuel (long), forward théorique et points de terme (F − S, en %
    du spot). Trié par |carry| décroissant."""
    rows = []
    for pair in fx.PAIRS:
        sp = fx.spot(market, pair)
        if sp is None:
            continue
        r_base, r_quote = pair_rates(market, pair)
        fwd = parity_forward(market, pair, tenor_months)
        rows.append({
            "pair": pair, "spot": sp, "r_base": r_base, "r_quote": r_quote,
            "carry_long": r_base - r_quote,
            "forward": fwd, "points_pct": (fwd / sp - 1.0) * 100.0,
            "vol": fx.pair_vol(pair),
        })
    rows.sort(key=lambda x: abs(x["carry_long"]), reverse=True)
    return rows


def accrue(player, market, days):
    """Portage couru sur les positions FX SPOT ouvertes, au prorata des
    jours écoulés — crédité/débité du cash par l'appelant (advance_step).
    Renvoie le montant total (peut être négatif)."""
    total = 0.0
    for pos in getattr(player, "fx_positions", []) or []:
        c = carry_annual(market, pos["pair"],
                         "long" if pos.get("direction") == "long" else "short")
        total += pos["notional"] * c * (days / 365.0)
    return total
