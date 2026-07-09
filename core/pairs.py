"""
pairs.py — Pairs trading / arbitrage statistique (logique pure).

La boucle COMPLÈTE d'une stratégie market-neutral, celle qu'on étudie en
cours de stat arb :

1. **Cointégration (Engle-Granger)** : régression des LOG-prix
   ln(A) = α + β·ln(B) + u, puis test de racine unitaire sur le résidu u
   (régression Δu_t = ρ·u_{t−1} + e ; statistique t de ρ). Si t < −3,0
   (approximation de la valeur critique 5 % d'Engle-Granger, ≈ −3,34 pour
   des paramètres estimés — documenté), le SPREAD est stationnaire : les
   deux titres sont attachés par un élastique.
2. **Half-life** : vitesse du retour à la moyenne, −ln(2)/ln(1+ρ) — un
   spread qui met 2 ans à revenir ne se trade pas.
3. **Signal** : z-score du spread — ±2σ = entrée (short le spread quand il
   est trop haut : short A / long β·B ; long quand trop bas), retour vers
   0 = sortie.
4. **Exécution** : ordres réels via core/portfolio (long + short
   dimensionné par β en VALEUR), soumis au déblocage « leverage » côté
   app, frais/slippage du jeu.

`best_pairs` scanne les plus grosses capitalisations et classe les paires
par qualité de cointégration — le travail de recherche d'un desk de stat
arb, en un clic.
"""
import math

import numpy as np

from core import portfolio as pf

DEFAULT_LOOKBACK = 73
ADF_CRITICAL = -3.0       # approx. valeur critique 5 % Engle-Granger (≈ −3,34)
ENTRY_Z = 2.0
EXIT_Z = 0.25


def _log_prices(market, ticker, lookback):
    hist = market.history_of(ticker, lookback + 1)
    s = np.asarray([v for v in hist if v and v > 0], dtype=float)
    return np.log(s) if len(s) >= 12 else None


def engle_granger(market, ticker_a, ticker_b, lookback=DEFAULT_LOOKBACK):
    """Test de cointégration d'Engle-Granger sur les log-prix. Renvoie None
    si l'historique manque, sinon {beta, alpha, adf_t, cointegrated,
    half_life, spread (array u), z (array), z_last, corr}."""
    la = _log_prices(market, ticker_a, lookback)
    lb = _log_prices(market, ticker_b, lookback)
    if la is None or lb is None or ticker_a == ticker_b:
        return None
    n = min(len(la), len(lb))
    la, lb = la[-n:], lb[-n:]
    # étape 1 : OLS ln(A) = alpha + beta·ln(B) + u
    X = np.column_stack([np.ones(n), lb])
    coef, *_ = np.linalg.lstsq(X, la, rcond=None)
    alpha, beta = float(coef[0]), float(coef[1])
    u = la - (alpha + beta * lb)
    # étape 2 : test ADF (sans retards) sur u : Δu_t = rho·u_{t−1} + e
    du = np.diff(u)
    ul = u[:-1]
    denom = float((ul * ul).sum())
    if denom <= 0 or len(du) < 10:
        return None
    rho = float((ul * du).sum() / denom)
    resid = du - rho * ul
    dof = max(1, len(du) - 1)
    se = math.sqrt(float((resid * resid).sum()) / dof / denom)
    adf_t = rho / se if se > 0 else 0.0
    # half-life du retour à la moyenne (processus AR(1) : u_t = (1+rho)·u_{t−1})
    if -1.0 < rho < 0.0:
        half_life = -math.log(2.0) / math.log(1.0 + rho)
    else:
        half_life = float("inf")
    sd = float(u.std())
    z = (u - float(u.mean())) / sd if sd > 0 else np.zeros_like(u)
    ra = np.diff(la)
    rb = np.diff(lb)
    corr = float(np.corrcoef(ra, rb)[0, 1]) if len(ra) >= 3 else 0.0
    return {"beta": beta, "alpha": alpha, "adf_t": adf_t,
            "cointegrated": adf_t < ADF_CRITICAL,
            "half_life": half_life, "spread": u, "z": z,
            "z_last": float(z[-1]), "corr": 0.0 if np.isnan(corr) else corr}


def signal(z_last):
    """Signal de trading du spread : 'short_spread' (z ≥ +2 : short A /
    long B), 'long_spread' (z ≤ −2 : long A / short B), 'exit' (|z| ≤ 0,25 :
    déboucler), 'hold' sinon."""
    if z_last >= ENTRY_Z:
        return "short_spread"
    if z_last <= -ENTRY_Z:
        return "long_spread"
    if abs(z_last) <= EXIT_Z:
        return "exit"
    return "hold"


def best_pairs(market, n_universe=18, n_pairs=5, lookback=DEFAULT_LOOKBACK):
    """Scanne les paires des `n_universe` plus grosses capitalisations et
    renvoie les `n_pairs` meilleures par statistique ADF (les plus
    cointégrées d'abord) : [(ticker_a, ticker_b, adf_t, z_last)]."""
    tks = [c["ticker"] for c in market.top_companies(n=n_universe)]
    logs = {tk: _log_prices(market, tk, lookback) for tk in tks}
    tks = [tk for tk in tks if logs[tk] is not None]
    out = []
    for i in range(len(tks)):
        for j in range(i + 1, len(tks)):
            r = engle_granger(market, tks[i], tks[j], lookback)
            if r is not None and math.isfinite(r["half_life"]):
                out.append((tks[i], tks[j], r["adf_t"], r["z_last"]))
    out.sort(key=lambda x: x[2])
    return out[:n_pairs]


def execute_pair(player, market, ticker_a, ticker_b, direction, notional,
                 lookback=DEFAULT_LOOKBACK):
    """Exécute le trade de paire : `direction` = 'long_spread' (ACHETER A,
    SHORTER B) ou 'short_spread' (SHORTER A, ACHETER B). La jambe short est
    dimensionnée par β en VALEUR (couverture du ratio de cointégration).
    Renvoie {ok, legs:[...]} ou {ok: False, reason}."""
    if direction not in ("long_spread", "short_spread"):
        return {"ok": False, "reason": "direction"}
    r = engle_granger(market, ticker_a, ticker_b, lookback)
    if r is None:
        return {"ok": False, "reason": "history"}
    pa = market.price_of(ticker_a)
    pb = market.price_of(ticker_b)
    if not pa or not pb or notional <= 0:
        return {"ok": False, "reason": "price"}
    qty_a = max(1, int(notional / pa))
    qty_b = max(1, int(abs(r["beta"]) * notional / pb))
    if direction == "long_spread":
        legs = [("buy", ticker_a, qty_a), ("short", ticker_b, qty_b)]
    else:
        legs = [("short", ticker_a, qty_a), ("buy", ticker_b, qty_b)]
    done = []
    for side, tk, qty in legs:
        fn = pf.buy if side == "buy" else pf.short
        res = fn(player, market, tk, qty)
        if not res.get("ok"):
            return {"ok": False, "reason": res.get("reason", "?"),
                    "failed_leg": tk, "done": done}
        done.append({"side": side, "ticker": tk, "qty": qty,
                     "price": res["price"]})
    return {"ok": True, "legs": done, "beta": r["beta"]}
