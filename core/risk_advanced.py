"""
risk_advanced.py — Risque avancé du portefeuille réel (logique pure).

Complète core/risk.py (VaR/CVaR/stress sur le book réel) avec deux outils
de salle des marchés qui « s'étudient » :

- **VaR par position (allocation d'Euler)** : la VaR totale est répartie
  entre les lignes par contribution marginale — contrib_i =
  cov(P&L_i, P&L_total)/var(P&L_total) × VaR_total. Les contributions
  SOMMENT à la VaR totale (propriété d'Euler pour une mesure homogène de
  degré 1) : on voit quelle ligne PORTE le risque, ce qui n'a rien à voir
  avec sa taille (une petite ligne très corrélée au reste peut contribuer
  plus qu'une grosse ligne diversifiante — une contribution NÉGATIVE est
  une couverture). Simulation sur le PROPRE modèle à facteurs du jeu
  (mêmes betas monde/secteur/région que core/risk.simulate).

- **Backtest de VaR (test de couverture de Kupiec, 1995)** : on rejoue la
  VaR parametrique sur l'historique du panier (quantités actuelles ×
  clôtures passées) et on compte les EXCEPTIONS (jours où la perte a
  dépassé la VaR). Sous H0 (le modèle est bien calibré), le nombre
  d'exceptions suit une binomiale (n, 1−confiance). La statistique du
  rapport de vraisemblance LR_POF = −2·ln[(1−p)^{n−x} p^x] +
  2·ln[(1−x/n)^{n−x} (x/n)^x] suit un χ²(1) : LR > 3,84 ⇒ modèle rejeté
  à 95 % (trop OU trop peu d'exceptions — un modèle trop prudent est
  aussi faux qu'un modèle laxiste).
"""
import math

import numpy as np

from core import finmath
from core import market as market_mod
from core import quant_tools as QT
from core.risk import RATE_VOL_WEEKLY, _bond_positions, _equity_positions

KUPIEC_CHI2_95 = 3.841        # quantile 95 % du χ² à 1 degré de liberté
_Z_TABLE = {0.90: 1.2816, 0.95: 1.6449, 0.975: 1.9600, 0.99: 2.3263}


def _z_score(confidence):
    """Quantile de la normale standard (scipy si dispo, table sinon)."""
    try:
        from scipy.stats import norm
        return float(norm.ppf(confidence))
    except Exception:
        return _Z_TABLE.get(round(confidence, 3), 1.6449)


def component_var(player, market, confidence=0.95, n=8000, seed=7):
    """VaR totale décomposée par ligne (allocation d'Euler, cf. docstring).
    Renvoie None sans position, sinon {var, cvar, lines: [{label, value,
    contrib, pct}]} — pertes en positif (EN MILLIONS, même convention que
    core/risk.py::simulate), contribs sommant à var (±1 %)."""
    eq = _equity_positions(player, market)
    bonds = _bond_positions(player, market)
    if not eq and not bonds:
        return None
    rng = np.random.default_rng(seed)
    cols, labels, values = [], [], []
    if eq:
        idx = np.array([i for i, _ in eq])
        val = np.array([v for _, v in eq]) / 1e6
        beta = market.beta[idx]
        bsec = market.b_sector[idx]
        breg = market.b_region[idx]
        sig = market.sigma[idx]
        sec_id = market.sec_id[idx]
        reg_id = market.reg_id[idx]
        Fw = rng.normal(0.0, market_mod.VOL_WORLD, n)
        Fs = rng.normal(0.0, market_mod.VOL_SECTOR, (n, len(market.sectors)))
        Fr = rng.normal(0.0, market_mod.VOL_REGION, (n, len(market.regions)))
        eps = rng.normal(0.0, 1.0, (n, len(idx)))
        ret = (beta * Fw[:, None] + bsec * Fs[:, sec_id]
               + breg * Fr[:, reg_id] + sig * eps)
        pnl_eq = ret * val                            # (n, positions)
        for k, (i, v) in enumerate(eq):
            cols.append(pnl_eq[:, k])
            labels.append(market.companies[i]["ticker"])
            values.append(v / 1e6)
    if bonds:
        dy = rng.normal(0.0, RATE_VOL_WEEKLY, n)
        for j, (v, d) in enumerate(bonds):
            v_m = v / 1e6
            cols.append(-(v_m * d) * dy)
            labels.append(f"OBLIG {j + 1}")
            values.append(v_m)
    P = np.column_stack(cols)                         # (n, lignes)
    total = P.sum(axis=1)
    var_total = finmath.value_at_risk(total, confidence)
    cvar_total = finmath.conditional_var(total, confidence)
    var_tot_v = total.var()
    lines = []
    for k, label in enumerate(labels):
        if var_tot_v > 0:
            beta_k = float(np.cov(P[:, k], total)[0, 1] / var_tot_v)
        else:
            beta_k = 0.0
        contrib = beta_k * var_total
        lines.append({"label": label, "value": float(values[k]),
                      "contrib": contrib,
                      "pct": (contrib / var_total * 100.0) if var_total else 0.0})
    lines.sort(key=lambda x: x["contrib"], reverse=True)
    return {"var": var_total, "cvar": cvar_total, "lines": lines,
            "confidence": confidence}


def var_backtest(player, market, confidence=0.95, lookback=73):
    """Backtest de la VaR paramétrique 1 pas sur l'historique du panier
    d'actions (quantités actuelles × clôtures passées — même convention que
    quant_tools.portfolio_step_returns). Renvoie None sans historique,
    sinon {n, exceptions, expected, rate, var_step_pct, lr, reject,
    exception_idx} — `reject` = modèle rejeté par Kupiec à 95 %."""
    rets, _tks = QT.portfolio_step_returns(player, market, lookback)
    n = len(rets)
    if n < 20:
        return None
    sigma = float(np.std(rets))
    if sigma <= 0:
        return None
    z = _z_score(confidence)
    var_step = z * sigma                              # perte-seuil en % du panier
    exceptions = [i for i, r in enumerate(rets) if -r > var_step]
    x = len(exceptions)
    p = 1.0 - confidence
    lr = _kupiec_lr(n, x, p)
    return {"n": n, "exceptions": x, "expected": p * n,
            "rate": x / n, "var_step_pct": var_step * 100.0,
            "lr": lr, "reject": lr > KUPIEC_CHI2_95,
            "exception_idx": exceptions, "returns": rets}


def _kupiec_lr(n, x, p):
    """Statistique LR_POF de Kupiec (χ² à 1 ddl sous H0)."""
    if n <= 0:
        return 0.0
    # log-vraisemblance sous H0 (proba d'exception = p)
    ll0 = (n - x) * math.log(1.0 - p) + (x * math.log(p) if x > 0 else 0.0)
    # log-vraisemblance sous H1 (proba observée x/n)
    phat = x / n
    if 0 < phat < 1:
        ll1 = (n - x) * math.log(1.0 - phat) + x * math.log(phat)
    elif x == 0:
        ll1 = 0.0
    else:                                             # x == n
        ll1 = 0.0
    return max(0.0, -2.0 * (ll0 - ll1))
