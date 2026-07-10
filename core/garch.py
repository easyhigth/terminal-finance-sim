"""
garch.py — GARCH(1,1) : estimation et prévision de volatilité (logique pure).

Le fait stylisé n°1 des rendements financiers : la volatilité fait des
GRAPPES (un jour agité est suivi de jours agités). Le GARCH(1,1) le
modélise :

    σ²_t = ω + α·r²_{t−1} + β·σ²_{t−1}

- α (réaction) : combien un choc d'hier gonfle la vol d'aujourd'hui ;
- β (mémoire) : combien la vol d'hier persiste ;
- α + β (persistance) : la demi-vie des grappes ;
- variance de long terme = ω/(1 − α − β), vers laquelle la prévision
  CONVERGE : σ²_{t+h} = LR + (α+β)^h·(σ²_t − LR).

Estimation par MAXIMUM DE VRAISEMBLANCE sur grille (α, β) avec variance
ciblée (ω calé sur la variance empirique) — déterministe, sans dépendance
d'optimiseur. La prévision annualisée se compare à la vol UTILISÉE PAR LE
DESK D'OPTIONS (fenêtre historique plate, core/options._stock_vol) : si le
GARCH voit la vol MONTER au-delà de ce que price le desk, les options sont
« bon marché » en vol (acheter du straddle) — et inversement.
"""
import math

import numpy as np

ALPHA_GRID = [round(0.02 + 0.02 * i, 2) for i in range(15)]   # 0,02 → 0,30
BETA_GRID = [round(0.50 + 0.02 * i, 2) for i in range(24)]    # 0,50 → 0,96
MIN_OBS = 30


def fit(returns):
    """Estime GARCH(1,1) par vraisemblance maximale sur grille (variance
    ciblée). Renvoie None si historique court ou dégénéré, sinon
    {alpha, beta, omega, persistence, lr_var, sigma2_last, loglik}."""
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < MIN_OBS:
        return None
    r = r - r.mean()
    var = float(r.var())
    if var <= 0:
        return None
    best = None
    r2 = r * r
    for a in ALPHA_GRID:
        for b in BETA_GRID:
            if a + b >= 0.999:
                continue
            omega = var * (1.0 - a - b)              # variance ciblée
            sig2 = var
            ll = 0.0
            ok = True
            for t in range(1, len(r)):
                sig2 = omega + a * r2[t - 1] + b * sig2
                if sig2 <= 0:
                    ok = False
                    break
                ll += -0.5 * (math.log(sig2) + r2[t] / sig2)
            if ok and (best is None or ll > best["loglik"]):
                best = {"alpha": a, "beta": b, "omega": omega,
                        "persistence": a + b, "lr_var": var,
                        "sigma2_last": sig2, "loglik": ll}
    return best


def forecast(model, horizon=12):
    """Prévision de variance à h pas : σ²_{t+h} = LR + (α+β)^h·(σ²_t − LR).
    Renvoie [(h, σ²_h)] pour h = 1..horizon."""
    lr = model["lr_var"]
    p = model["persistence"]
    s2 = model["sigma2_last"]
    return [(h, lr + (p ** h) * (s2 - lr)) for h in range(1, horizon + 1)]


def analyze(market, ticker, lookback=104, steps_per_year=52):
    """Analyse complète d'un titre : fit + prévision annualisée + verdict
    vs la vol utilisée par le desk d'options. Renvoie None si historique
    court, sinon {model, vol_now_ann, vol_forecast_ann (h=12), vol_lr_ann,
    vol_desk_ann, verdict, forecast_curve:[(h, vol_ann)]}."""
    hist = market.history_of(ticker, lookback + 1)
    s = np.asarray([v for v in hist if v], dtype=float)
    if len(s) < MIN_OBS + 1:
        return None
    rets = s[1:] / s[:-1] - 1.0
    model = fit(rets)
    if model is None:
        return None
    ann = math.sqrt(steps_per_year)
    fc = forecast(model, horizon=12)
    curve = [(h, math.sqrt(v) * ann) for h, v in fc]
    vol_now = math.sqrt(model["sigma2_last"]) * ann
    vol_12 = curve[-1][1]
    vol_lr = math.sqrt(model["lr_var"]) * ann
    from core import options as opt
    vol_desk = opt._stock_vol(market, ticker)
    # verdict : la vol que le GARCH prévoit vs celle que price le desk
    edge = vol_12 - vol_desk
    if edge > 0.03:
        verdict = "VOL BON MARCHÉ — le GARCH prévoit plus haut que le desk (acheter de la vol : straddle)"
    elif edge < -0.03:
        verdict = "VOL CHÈRE — le GARCH prévoit plus bas que ce que price le desk"
    else:
        verdict = "Vol correctement pricée (écart < 3 pts)"
    return {"model": model, "vol_now_ann": vol_now, "vol_forecast_ann": vol_12,
            "vol_lr_ann": vol_lr, "vol_desk_ann": vol_desk,
            "edge": edge, "verdict": verdict, "forecast_curve": curve}
