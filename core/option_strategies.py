"""
option_strategies.py — Stratégies d'options MULTI-JAMBES (logique pure).

Compose les briques du desk d'options existant (core/options.py — achat de
calls/puts réels, primes Black-Scholes, exercice à l'échéance par le moteur)
en STRATÉGIES classiques, avec le profil de P&L à l'échéance, les points
morts (breakevens) et les grecques agrégées du paquet. Le jeu ne permet que
d'ACHETER des options (pas de vente à découvert d'options), donc le
catalogue se limite aux stratégies en prime débitée :

- CALL SEC / PUT SEC : directionnel simple ;
- STRADDLE (call ATM + put ATM) : pari de VOLATILITÉ — gagne si le titre
  bouge FORT dans un sens ou l'autre, perd la double prime s'il stagne ;
- STRANGLE (call OTM + put OTM) : même pari, prime réduite, points morts
  plus éloignés ;
- PUT PROTECTEUR (put −5 % sur des actions DÉTENUES) : assurance de
  position — le P&L combine action + put, plancher garanti.

Le book agrégé (`book_greeks`) réévalue chaque position d'options du joueur
AU PRIX D'AUJOURD'HUI (spot/vol/temps restant courants) et somme les
grecques en termes CASH — l'exposition réelle du book, comme sur un vrai
desk.
"""
import numpy as np

from core import finmath as fm
from core import options as opt

STRATEGIES = {
    "call": {
        "label": "Call sec",
        "legs": [("call", 1.00, 1)],
        "needs_stock": False,
        "view": "Haussier — gain illimité au-dessus du point mort, perte limitée à la prime.",
    },
    "put": {
        "label": "Put sec",
        "legs": [("put", 1.00, 1)],
        "needs_stock": False,
        "view": "Baissier — gagne sous le point mort, perte limitée à la prime.",
    },
    "straddle": {
        "label": "Straddle (vol)",
        "legs": [("call", 1.00, 1), ("put", 1.00, 1)],
        "needs_stock": False,
        "view": "Pari de volatilité — gagne si le titre bouge fort, dans N'IMPORTE quel sens.",
    },
    "strangle": {
        "label": "Strangle (vol, OTM)",
        "legs": [("call", 1.10, 1), ("put", 0.90, 1)],
        "needs_stock": False,
        "view": "Volatilité à moindre prime — points morts plus éloignés que le straddle.",
    },
    "protective_put": {
        "label": "Put protecteur",
        "legs": [("put", 0.95, 1)],
        "needs_stock": True,
        "view": "Assurance d'une position détenue — plancher de perte garanti, coût = la prime.",
    },
}
STRATEGY_ORDER = ["call", "put", "straddle", "strangle", "protective_put"]


def quote_strategy(player, market, ticker, strat_id, years, contracts=1):
    """Cote le paquet : jambes (via core/options.quote), prime totale,
    grecques agrégées (en cash), profil de P&L à l'échéance et points morts.
    Renvoie None si le ticker/la stratégie sont invalides."""
    strat = STRATEGIES.get(strat_id)
    spot = market.price_of(ticker)
    if strat is None or spot is None or contracts < 1:
        return None
    legs = []
    total_premium = 0.0
    greeks = {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0}
    for op_type, strike_pct, qty in strat["legs"]:
        q = opt.quote(player, market, ticker, op_type, strike_pct, years)
        if not q.get("ok"):
            return None
        legs.append({**q, "qty": qty * contracts})
        total_premium += q["premium"] * qty * contracts
        for g in greeks:
            greeks[g] += q["greeks"][g] * qty * contracts
    # grecques CASH : delta en unités de sous-jacent × spot = € d'exposition
    cash = {
        "delta_cash": greeks["delta"] * spot,
        "gamma_cash": greeks["gamma"] * spot * spot / 100.0,   # pour 1 % de spot
        "vega": greeks["vega"],                                # par point de vol
        "theta_day": greeks["theta"],                          # par jour
    }
    # profil de P&L à l'échéance sur une grille de spots ±40 %
    spots = np.linspace(spot * 0.6, spot * 1.4, 121)
    pnl = np.full_like(spots, -total_premium)
    for leg in legs:
        if leg["option_type"] == "call":
            pnl = pnl + np.maximum(spots - leg["strike"], 0.0) * leg["qty"]
        else:
            pnl = pnl + np.maximum(leg["strike"] - spots, 0.0) * leg["qty"]
    if strat["needs_stock"]:
        pnl = pnl + (spots - spot) * contracts        # la position action sous-jacente
    breakevens = _zero_crossings(spots, pnl)
    return {
        "strategy": strat_id, "label": strat["label"], "view": strat["view"],
        "ticker": ticker, "spot": spot, "years": years, "contracts": contracts,
        "legs": legs, "premium": total_premium, "greeks": greeks, "cash": cash,
        "spots": spots, "pnl": pnl, "breakevens": breakevens,
        "max_loss": float(pnl.min()), "needs_stock": strat["needs_stock"],
    }


def _zero_crossings(xs, ys):
    """Points morts : passages par zéro du P&L (interpolation linéaire)."""
    out = []
    for i in range(1, len(xs)):
        if ys[i - 1] == 0.0:
            out.append(float(xs[i - 1]))
        elif ys[i - 1] * ys[i] < 0:
            t = ys[i - 1] / (ys[i - 1] - ys[i])
            out.append(float(xs[i - 1] + t * (xs[i] - xs[i - 1])))
    return out


def execute_strategy(player, market, ticker, strat_id, years, contracts=1):
    """Achète toutes les jambes (core/options.buy). Vérifie AVANT le premier
    ordre que la prime TOTALE tient dans le cash et, pour un put protecteur,
    que le joueur détient au moins `contracts` actions du titre — pas de
    paquet à moitié exécuté pour une raison prévisible."""
    q = quote_strategy(player, market, ticker, strat_id, years, contracts)
    if q is None:
        return {"ok": False, "reason": "quote"}
    if q["needs_stock"]:
        pos = player.portfolio.get(ticker)
        held = pos["shares"] if pos else 0.0
        if held < contracts:
            return {"ok": False, "reason": "needs_stock", "held": held}
    if q["premium"] > player.cash:
        return {"ok": False, "reason": "cash", "premium": q["premium"]}
    bought = []
    for op_type, strike_pct, qty in STRATEGIES[strat_id]["legs"]:
        r = opt.buy(player, market, ticker, op_type, strike_pct, years,
                    qty * contracts)
        if not r.get("ok"):
            return {"ok": False, "reason": r.get("reason", "?"), "bought": bought}
        bought.append(r["position"])
    return {"ok": True, "positions": bought, "premium": q["premium"],
            "label": q["label"]}


def book_greeks(player, market):
    """Grecques AGRÉGÉES du book d'options du joueur, réévaluées aujourd'hui
    (spot, vol et temps restant courants). Renvoie {rows, totals} — rows par
    position ({ticker, type, contracts, steps_left, value, delta, ...}),
    totals en cash (delta_cash = € d'exposition équivalente action)."""
    rows = []
    totals = {"delta_cash": 0.0, "gamma_cash": 0.0, "vega": 0.0,
              "theta_day": 0.0, "value": 0.0}
    for pos in getattr(player, "options", []) or []:
        spot = market.price_of(pos["ticker"])
        if spot is None:
            continue
        steps_left = max(0, pos["maturity_step"] - market.step_count)
        t_left = steps_left / opt.STEPS_PER_YEAR
        sigma = opt._stock_vol(market, pos["ticker"])
        r = opt.risk_free_rate(market)
        if t_left > 0:
            g = fm.bs_greeks(spot, pos["strike"], t_left, r, sigma,
                             option=pos["option_type"])
            value = fm.black_scholes(spot, pos["strike"], t_left, r, sigma,
                                     option=pos["option_type"]) * pos["contracts"]
        else:
            g = {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0}
            intrinsic = (max(0.0, spot - pos["strike"])
                         if pos["option_type"] == "call"
                         else max(0.0, pos["strike"] - spot))
            value = intrinsic * pos["contracts"]
        n = pos["contracts"]
        rows.append({
            "ticker": pos["ticker"], "type": pos["option_type"],
            "contracts": n, "strike": pos["strike"], "steps_left": steps_left,
            "value": value, "premium": pos["premium"],
            "delta": g["delta"], "gamma": g["gamma"],
            "vega": g["vega"], "theta": g["theta"],
        })
        totals["delta_cash"] += g["delta"] * n * spot
        totals["gamma_cash"] += g["gamma"] * n * spot * spot / 100.0
        totals["vega"] += g["vega"] * n
        totals["theta_day"] += g["theta"] * n
        totals["value"] += value
    return {"rows": rows, "totals": totals}
