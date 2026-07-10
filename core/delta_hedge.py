"""
delta_hedge.py — Couverture dynamique en delta / gamma scalping (logique pure).

LA leçon vécue du trading d'options, en deux morceaux :

- **Aplatir le delta** (`flatten_plan`/`execute_flatten`) : le book
  d'options a un delta par sous-jacent (Σ Δ×contrats, en titres) ; on le
  neutralise en détenant −Δ actions (vendre si on en a, shorter sinon).
  Une fois plat, le P&L ne dépend plus de la DIRECTION — il ne reste que
  gamma (le marché bouge) contre theta (le temps passe).

- **Décomposition ex-post du P&L** (`pnl_decomposition`) : pour chaque
  option du book, on REJOUE le chemin de prix réellement observé depuis
  l'achat et on découpe le P&L par les grecques de chaque pas :
      P&L ≈ Σ Δ_t·ΔS  (directionnel — ce que le hedge aurait annulé)
          + Σ ½·Γ_t·ΔS² (le GAIN DU SCALPEUR — toujours ≥ 0 en gamma long)
          + Σ Θ_t·Δjours (le COÛT DU TEMPS — toujours ≤ 0 en gamma long)
          + résidu (ordres supérieurs, saut de vol)
  Déterministe (chemin de clôtures du moteur, grecques Black-Scholes).
"""
import math

from core import finmath as fm
from core import options as opt
from core import portfolio as pf

DAYS_PER_OPT_STEP = 365.0 / opt.STEPS_PER_YEAR    # convention 52 pas/an du desk


def book_delta_by_underlying(player, market):
    """Delta agrégé du book d'options PAR sous-jacent, en TITRES (Σ Δ×n).
    [{ticker, delta_shares, stock_shares, net_shares}]."""
    agg = {}
    for pos in getattr(player, "options", []) or []:
        spot = market.price_of(pos["ticker"])
        if spot is None:
            continue
        steps_left = max(0, pos["maturity_step"] - market.step_count)
        t_left = steps_left / opt.STEPS_PER_YEAR
        if t_left <= 0:
            continue
        sigma = opt._stock_vol(market, pos["ticker"])
        r = opt.risk_free_rate(market)
        g = fm.bs_greeks(spot, pos["strike"], t_left, r, sigma,
                         option=pos["option_type"])
        agg[pos["ticker"]] = agg.get(pos["ticker"], 0.0) + g["delta"] * pos["contracts"]
    out = []
    for tk, d in agg.items():
        p_pos = player.portfolio.get(tk)
        stock = p_pos["shares"] if p_pos else 0.0
        out.append({"ticker": tk, "delta_shares": d, "stock_shares": stock,
                    "net_shares": d + stock})
    out.sort(key=lambda x: abs(x["net_shares"]), reverse=True)
    return out


def flatten_plan(player, market):
    """Ordres ACTIONS qui neutralisent le delta net de chaque sous-jacent
    (position action cible = −Δ options, arrondi au titre).
    [{ticker, trade (signé : >0 acheter, <0 vendre/shorter)}]."""
    plan = []
    for row in book_delta_by_underlying(player, market):
        target_stock = -round(row["delta_shares"])
        trade = int(target_stock - row["stock_shares"])
        if trade != 0:
            plan.append({"ticker": row["ticker"], "trade": trade})
    return plan


def execute_flatten(player, market, plan):
    """Exécute le plan (achats/ventes/shorts réels via core/portfolio).
    Best-effort : {done, failed:[(ticker, raison)]}."""
    done, failed = 0, []
    for t in plan:
        tk, qty = t["ticker"], t["trade"]
        if qty > 0:
            pos = player.portfolio.get(tk)
            if pos and pos["shares"] < 0:            # racheter le short d'abord
                r = pf.cover(player, market, tk, min(qty, -pos["shares"]))
                if not r.get("ok"):
                    failed.append((tk, r.get("reason", "?")))
                    continue
                qty -= r["qty"] if "qty" in r else 0
                done += 1
            if qty > 0:
                r = pf.buy(player, market, tk, qty)
                (failed.append((tk, r.get("reason", "?")))
                 if not r.get("ok") else None)
                done += 1 if r.get("ok") else 0
        else:
            qty = -qty
            pos = player.portfolio.get(tk)
            held = pos["shares"] if pos and pos["shares"] > 0 else 0
            if held > 0:
                r = pf.sell(player, market, tk, min(qty, held))
                if not r.get("ok"):
                    failed.append((tk, r.get("reason", "?")))
                    continue
                done += 1
                qty -= min(qty, held)
            if qty > 0:
                r = pf.short(player, market, tk, qty)
                (failed.append((tk, r.get("reason", "?")))
                 if not r.get("ok") else None)
                done += 1 if r.get("ok") else 0
    return {"done": done, "failed": failed}


def pnl_decomposition(player, market, pos):
    """Décompose le P&L d'UNE position d'options depuis l'achat en
    delta / gamma / theta / résidu, en rejouant le chemin de clôtures réel
    (cf. docstring du module). Renvoie None si historique insuffisant,
    sinon {delta, gamma, theta, residual, actual, steps}."""
    entry_step = pos["maturity_step"] - int(round(pos["years"] * opt.STEPS_PER_YEAR))
    held_steps = market.step_count - entry_step
    if held_steps < 1:
        return None
    hist = market.history_of(pos["ticker"], held_steps + 1)
    s = [v for v in hist if v]
    if len(s) < 2:
        return None
    r = opt.risk_free_rate(market)
    sigma = opt._stock_vol(market, pos["ticker"])
    n = pos["contracts"]
    d_pnl = g_pnl = t_pnl = 0.0
    for i in range(1, len(s)):
        steps_left = pos["maturity_step"] - (entry_step + i - 1)
        t_left = max(1e-6, steps_left / opt.STEPS_PER_YEAR)
        g = fm.bs_greeks(s[i - 1], pos["strike"], t_left, r, sigma,
                         option=pos["option_type"])
        ds = s[i] - s[i - 1]
        d_pnl += g["delta"] * ds * n
        g_pnl += 0.5 * g["gamma"] * ds * ds * n
        t_pnl += g["theta"] * DAYS_PER_OPT_STEP * n   # theta déjà par JOUR
    # valeur courante mark-to-model vs prime payée
    steps_left = max(0, pos["maturity_step"] - market.step_count)
    t_left = steps_left / opt.STEPS_PER_YEAR
    spot = market.price_of(pos["ticker"])
    if t_left > 0:
        value = fm.black_scholes(spot, pos["strike"], t_left, r, sigma,
                                 option=pos["option_type"]) * n
    else:
        intrinsic = (max(0.0, spot - pos["strike"]) if pos["option_type"] == "call"
                     else max(0.0, pos["strike"] - spot))
        value = intrinsic * n
    actual = value - pos["premium"]
    return {"delta": d_pnl, "gamma": g_pnl, "theta": t_pnl,
            "residual": actual - (d_pnl + g_pnl + t_pnl),
            "actual": actual, "steps": len(s) - 1}
