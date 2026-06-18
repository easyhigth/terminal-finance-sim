"""
hedging.py — Couverture du portefeuille via PUT PROTECTEUR sur l'indice
régional (logique pure, sans pygame).

Le joueur a un portefeuille actions exposé au marché (bêta net, cf.
core/portfolio.portfolio_beta). Pour réduire ce risque sans liquider ses
positions, il peut acheter un PUT sur l'indice phare de sa région : si
l'indice baisse sous le strike à l'échéance, le put paie la différence
(notionnel proportionnel), compensant une partie des pertes du book.

Prime calculée par Black-Scholes (core.finmath.black_scholes), volatilité
estimée depuis l'historique récent de l'indice — cohérent avec le reste du
jeu (aucun nouveau modèle de pricing, on réutilise l'existant).

Détenu jusqu'à l'échéance (mark-to-model = valeur Black-Scholes courante).
Holdings : PlayerState.hedges = [ {dict position} ].
"""
import math

import numpy as np

from core import finmath as fm
from core import portfolio as pf

STEPS_PER_YEAR = 52
MIN_VOL = 0.08             # plancher de volatilité (évite une prime nulle)
MATURITY_CHOICES = [0.25, 0.5, 1.0]      # années proposées au joueur
STRIKE_CHOICES = [1.00, 0.95, 0.90]      # % du niveau courant (ATM, -5%, -10%)


def _index_for_region(market, region):
    for name, reg, *_ in market.index_defs:
        if reg == region:
            return name
    return market.index_defs[0][0]


def _index_vol(market, idx, lookback=26):
    """Volatilité hebdo récente de l'indice, annualisée (proxy pour le pricing)."""
    hist = market.index_history(idx)
    if len(hist) < 3:
        return MIN_VOL
    h = np.asarray(hist[-lookback:], dtype=float)
    rets = np.diff(h) / h[:-1]
    if len(rets) < 2:
        return MIN_VOL
    sigma = float(np.std(rets, ddof=1)) * math.sqrt(STEPS_PER_YEAR)
    return max(MIN_VOL, sigma)


def risk_free_rate(market):
    return market.macro["rate"]["v"] / 100.0 if hasattr(market, "macro") else 0.03


def quote(player, market, strike_pct, years):
    """Cote du put : niveau de l'indice, strike, vol, prime par unité de notionnel
    (= prime Black-Scholes / niveau spot, payée en proportion du notionnel couvert)."""
    region = player.continent
    idx = _index_for_region(market, region)
    spot = market.index_value(idx)
    strike = spot * strike_pct
    sigma = _index_vol(market, idx)
    r = risk_free_rate(market)
    premium_per_unit = fm.black_scholes(spot, strike, years, r, sigma, option="put") / spot
    return {"underlying": idx, "spot": spot, "strike": strike, "sigma": sigma,
            "rate": r, "premium_rate": premium_per_unit}


def buy_put(player, market, notional, strike_pct, years):
    """Souscrit un put protecteur pour `notional` de couverture (prime débitée
    du cash, proportionnelle au notionnel et à la cote courante)."""
    if notional <= 0:
        return {"ok": False, "reason": "notional"}
    q = quote(player, market, strike_pct, years)
    premium = notional * q["premium_rate"]
    if premium <= 0 or premium > player.cash:
        return {"ok": False, "reason": "cash"}
    player.cash -= premium
    pos = {
        "underlying": q["underlying"], "notional": float(notional),
        "start_level": q["spot"], "strike": q["strike"], "strike_pct": strike_pct,
        "premium": premium, "years": years,
        "maturity_step": market.step_count + int(round(years * STEPS_PER_YEAR)),
    }
    player.hedges = getattr(player, "hedges", [])
    player.hedges.append(pos)
    return {"ok": True, "position": pos, "premium": premium}


def evaluate_due(player, market):
    """Dénoue les puts arrivés à échéance. Retourne les résultats (payoff, pnl)."""
    results, still = [], []
    for pos in getattr(player, "hedges", []) or []:
        if market.step_count >= pos["maturity_step"]:
            final = market.index_value(pos["underlying"])
            payoff = max(0.0, (pos["strike"] - final) / pos["start_level"]) * pos["notional"]
            if payoff:
                player.cash += payoff
            pnl = payoff - pos["premium"]
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + pnl
            results.append({"position": pos, "payoff": payoff, "pnl": pnl, "final": final})
        else:
            still.append(pos)
    player.hedges = still
    return results


def holdings_value(player, market):
    """Valeur de marché courante (mark-to-model Black-Scholes) des puts en cours."""
    total = 0.0
    for pos in getattr(player, "hedges", []) or []:
        steps_left = max(0, pos["maturity_step"] - market.step_count)
        years_left = steps_left / STEPS_PER_YEAR
        final = market.index_value(pos["underlying"])
        sigma = _index_vol(market, pos["underlying"])
        r = risk_free_rate(market)
        price_per_unit = fm.black_scholes(final, pos["strike"], years_left, r, sigma,
                                          option="put") / pos["start_level"]
        total += price_per_unit * pos["notional"]
    return total


def holdings(player, market):
    """Détail des couvertures en cours, pour affichage."""
    out = []
    for pos in getattr(player, "hedges", []) or []:
        cur = market.index_value(pos["underlying"])
        perf = (cur / pos["start_level"] - 1.0) * 100 if pos["start_level"] else 0.0
        steps_left = max(0, pos["maturity_step"] - market.step_count)
        out.append({"underlying": pos["underlying"], "notional": pos["notional"],
                     "strike_pct": pos["strike_pct"], "premium": pos["premium"],
                     "perf": perf, "steps_left": steps_left,
                     "years_left": steps_left / STEPS_PER_YEAR,
                     "in_money": cur < pos["strike"]})
    return out


def coverage_ratio(player, market):
    """Part de l'exposition brute couverte par des puts en cours (0-1+)."""
    gross = pf.gross_exposure(player, market)
    if gross <= 0:
        return 0.0
    covered = sum(pos["notional"] for pos in getattr(player, "hedges", []) or [])
    return covered / gross
