"""
options.py — Desk d'options sur actions individuelles (CALL / PUT), logique
pure (sans pygame).

Le joueur peut acheter un CALL ou un PUT sur une action du roster
(data/companies.py) plutôt que sur l'indice régional (cf. core/hedging.py
pour la version indice). Prime calculée par Black-Scholes
(core.finmath.black_scholes), volatilité estimée depuis l'historique récent
du titre (proxy cohérent avec le reste du jeu, aucun nouveau modèle de
pricing).

Détenu jusqu'à l'échéance (mark-to-model = valeur Black-Scholes courante).
Holdings : PlayerState.options = [ {dict position} ].
"""
import math

import numpy as np

from core import finmath as fm

STEPS_PER_YEAR = 52
MIN_VOL = 0.10              # plancher de volatilité (évite une prime nulle)
MATURITY_CHOICES = [0.25, 0.5, 1.0]      # années proposées au joueur
STRIKE_CHOICES = [0.90, 1.00, 1.10]      # % du spot courant (ITM call/OTM put, ATM, OTM call/ITM put


EARNINGS_VOL_BUMP = 0.35     # +35 % de vol implicite la veille des résultats
EARNINGS_WINDOW = 3          # pas avant publication où la vol commence à gonfler


def earnings_vol_mult(market, ticker):
    """GONFLEMENT DE VOL PRÉ-EARNINGS : la vol implicite monte à l'approche
    d'une publication de résultats (l'incertitude de l'évènement se price),
    puis s'effondre juste après — le « vol crush ». Multiplicateur ∈
    [1, 1+EARNINGS_VOL_BUMP], linéaire sur les EARNINGS_WINDOW derniers pas.
    Acheter un straddle la veille des résultats, c'est payer cette prime —
    le marché bouge souvent MOINS que ce que la vol gonflée impliquait."""
    try:
        mt = market.metrics(ticker)
        steps = mt.get("steps_to_earnings") if mt else None
    except Exception:
        return 1.0
    if steps is None or steps >= EARNINGS_WINDOW:
        return 1.0
    return 1.0 + EARNINGS_VOL_BUMP * (EARNINGS_WINDOW - steps) / EARNINGS_WINDOW


def _stock_vol(market, ticker, lookback=26):
    """Volatilité hebdo récente de l'action, annualisée (proxy pour le pricing),
    × le gonflement pré-earnings (cf. earnings_vol_mult — le smile d'évènement).
    Repli sur la vol idiosyncratique statique (data/companies.py) si l'historique
    est insuffisant."""
    mult = earnings_vol_mult(market, ticker)
    hist = market.history_of(ticker, lookback + 1)
    if len(hist) >= 3:
        h = np.asarray(hist, dtype=float)
        rets = np.diff(h) / h[:-1]
        if len(rets) >= 2:
            sigma = float(np.std(rets, ddof=1)) * math.sqrt(STEPS_PER_YEAR)
            return max(MIN_VOL, sigma) * mult
    i = market.ticker_idx.get(ticker)
    if i is not None:
        sigma_step = float(market.companies[i]["sigma"])
        return max(MIN_VOL, sigma_step * math.sqrt(STEPS_PER_YEAR)) * mult
    return MIN_VOL * mult


def risk_free_rate(market):
    return market.macro["rate"]["v"] / 100.0 if hasattr(market, "macro") else 0.03


def quote(player, market, ticker, option_type, strike_pct, years):
    """Cote l'option : spot, strike, vol, prime par unité (= prix Black-Scholes
    par action sous-jacente)."""
    spot = market.price_of(ticker)
    if spot is None:
        return {"ok": False, "reason": "ticker"}
    strike = spot * strike_pct
    sigma = _stock_vol(market, ticker)
    r = risk_free_rate(market)
    premium = fm.black_scholes(spot, strike, years, r, sigma, option=option_type)
    greeks = fm.bs_greeks(spot, strike, years, r, sigma, option=option_type)
    return {"ok": True, "ticker": ticker, "option_type": option_type, "spot": spot,
            "strike": strike, "sigma": sigma, "rate": r, "premium": premium, "greeks": greeks}


def buy(player, market, ticker, option_type, strike_pct, years, contracts):
    """Achète `contracts` options (1 contrat = 1 action sous-jacente). Débite
    la prime totale du cash et ajoute la position à player.options."""
    if option_type not in ("call", "put"):
        return {"ok": False, "reason": "option_type"}
    if contracts <= 0:
        return {"ok": False, "reason": "contracts"}
    q = quote(player, market, ticker, option_type, strike_pct, years)
    if not q.get("ok"):
        return q
    total_premium = q["premium"] * contracts
    if total_premium <= 0 or total_premium > player.cash:
        return {"ok": False, "reason": "cash"}
    player.cash -= total_premium
    pos = {
        "ticker": ticker, "option_type": option_type, "contracts": float(contracts),
        "start_spot": q["spot"], "strike": q["strike"], "strike_pct": strike_pct,
        "premium": total_premium, "premium_per_unit": q["premium"], "years": years,
        "maturity_step": market.step_count + int(round(years * STEPS_PER_YEAR)),
    }
    player.options = getattr(player, "options", [])
    player.options.append(pos)
    return {"ok": True, "position": pos, "premium": total_premium}


def evaluate_due(player, market):
    """Dénoue les options arrivées à échéance (exercice automatique : payoff
    intrinsèque). Crédite le cash, retire les positions échues. Retourne les
    résultats (payoff, pnl)."""
    results, still = [], []
    for pos in getattr(player, "options", []) or []:
        if market.step_count >= pos["maturity_step"]:
            final = market.price_of(pos["ticker"])
            final = final if final is not None else pos["strike"]
            if pos["option_type"] == "call":
                payoff_per_unit = max(0.0, final - pos["strike"])
            else:
                payoff_per_unit = max(0.0, pos["strike"] - final)
            payoff = payoff_per_unit * pos["contracts"]
            if payoff:
                player.cash += payoff
            pnl = payoff - pos["premium"]
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + pnl
            results.append({"position": pos, "payoff": payoff, "pnl": pnl, "final": final})
        else:
            still.append(pos)
    player.options = still
    return results


def holdings_value(player, market):
    """Valeur de marché courante (mark-to-model Black-Scholes) des options
    en cours."""
    total = 0.0
    for pos in getattr(player, "options", []) or []:
        steps_left = max(0, pos["maturity_step"] - market.step_count)
        years_left = steps_left / STEPS_PER_YEAR
        final = market.price_of(pos["ticker"])
        if final is None:
            continue
        sigma = _stock_vol(market, pos["ticker"])
        r = risk_free_rate(market)
        price_per_unit = fm.black_scholes(final, pos["strike"], years_left, r, sigma,
                                          option=pos["option_type"])
        total += price_per_unit * pos["contracts"]
    return total


def holdings(player, market):
    """Détail des positions d'options en cours, pour affichage."""
    out = []
    r = risk_free_rate(market)
    for pos in getattr(player, "options", []) or []:
        cur = market.price_of(pos["ticker"])
        cur = cur if cur is not None else pos["start_spot"]
        perf = (cur / pos["start_spot"] - 1.0) * 100 if pos["start_spot"] else 0.0
        steps_left = max(0, pos["maturity_step"] - market.step_count)
        years_left = steps_left / STEPS_PER_YEAR
        if pos["option_type"] == "call":
            in_money = cur > pos["strike"]
        else:
            in_money = cur < pos["strike"]
        sigma = _stock_vol(market, pos["ticker"])
        greeks = fm.bs_greeks(cur, pos["strike"], years_left, r, sigma,
                              option=pos["option_type"])
        out.append({"ticker": pos["ticker"], "option_type": pos["option_type"],
                     "contracts": pos["contracts"], "strike_pct": pos["strike_pct"],
                     "strike": pos["strike"], "premium": pos["premium"],
                     "spot": cur, "perf": perf, "steps_left": steps_left,
                     "years_left": years_left, "in_money": in_money, "greeks": greeks})
    return out
