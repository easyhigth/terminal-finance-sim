"""
charts.py — Calculs purs pour les graphes analytiques (style Bloomberg).

Logique pure et testable (numpy autorisé, pas de pygame). Sert les écrans de
graphes : variations relatives, volatilité historique, corrélations, bêta/
régression, spreads/ratios, courbe des taux. Toutes les fonctions travaillent
sur des listes de prix/valeurs déjà fournies par le moteur de marché.
"""
import math

import numpy as np

from core import market as _market

PERIODS_PER_YEAR = _market.STEPS_PER_YEAR    # pas de marché par an (annualisation)


def normalize(series, ref=None):
    """Variation cumulée en % vs `ref` (ou le 1er point) — base 0 % au départ."""
    if not series:
        return []
    base = ref if ref is not None else series[0]
    if not base:
        return [0.0] * len(series)
    return [(v / base - 1.0) * 100.0 for v in series]


def simple_returns(series):
    """Rendements simples pas-à-pas (longueur n-1)."""
    out = []
    for i in range(1, len(series)):
        prev = series[i - 1]
        out.append((series[i] / prev - 1.0) if prev else 0.0)
    return out


def sma(series, window):
    """Moyenne mobile simple, alignée sur `series` (None tant qu'incomplet)."""
    out, s = [], 0.0
    for i, v in enumerate(series):
        s += v
        if i >= window:
            s -= series[i - window]
        out.append(s / window if i >= window - 1 else None)
    return out


def rolling_vol(series, window, periods_per_year=PERIODS_PER_YEAR):
    """Volatilité annualisée glissante (écart-type des rendements simples), en %.
    Retourne une liste alignée sur `series` (None tant que la fenêtre est incomplète)."""
    rets = simple_returns(series)
    out = [None] * len(series)
    ann = math.sqrt(periods_per_year)
    for i in range(window, len(rets) + 1):
        w = rets[i - window:i]
        if len(w) > 1:
            mean = sum(w) / len(w)
            var = sum((x - mean) ** 2 for x in w) / (len(w) - 1)
            out[i] = math.sqrt(var) * ann * 100.0      # aligné : rets[i-1] -> series[i]
    return out


def spread(a, b, mode="ratio"):
    """Écart ou ratio entre deux séries de même longueur (tronqué au plus court)."""
    n = min(len(a), len(b))
    out = []
    for i in range(n):
        if mode == "ratio":
            out.append(a[i] / b[i] if b[i] else 0.0)
        else:
            out.append(a[i] - b[i])
    return out


def ols_beta(y_returns, x_returns):
    """Régression MCO de y sur x. Retourne (beta, alpha, r2).
    y = actif, x = marché/indice. Beta = sensibilité systémique."""
    n = min(len(y_returns), len(x_returns))
    if n < 3:
        return 0.0, 0.0, 0.0
    x = np.asarray(x_returns[:n], dtype=float)
    y = np.asarray(y_returns[:n], dtype=float)
    vx = float(np.var(x))
    if vx == 0:
        return 0.0, float(np.mean(y)), 0.0
    cov = float(np.cov(x, y, bias=True)[0, 1])
    beta = cov / vx
    alpha = float(np.mean(y) - beta * np.mean(x))
    # R²
    yhat = alpha + beta * x
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = (1.0 - ss_res / ss_tot) if ss_tot else 0.0
    return beta, alpha, r2


def correlation_matrix(series_map):
    """Matrice de corrélation des rendements entre plusieurs séries.
    `series_map` : dict label -> série de prix. Retourne (labels, matrice np)."""
    labels = list(series_map.keys())
    rets = [simple_returns(series_map[k]) for k in labels]
    n = min((len(r) for r in rets), default=0)
    if n < 2 or len(labels) < 2:
        return labels, np.eye(max(1, len(labels)))
    mat = np.array([r[-n:] for r in rets], dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.corrcoef(mat)
    return labels, np.nan_to_num(corr, nan=0.0)


def yield_curve(market, rating="AAA", maturities=(1, 2, 3, 5, 7, 10, 20, 30)):
    """Courbe des taux : (maturité en années, rendement en %) pour un rating donné.
    Reconstruite depuis le niveau de courbe du marché + prime de terme + spread."""
    from core import bonds as _bonds
    base = _bonds.base_yield_level(market)
    spr = _bonds._RATING_SPREAD.get(rating, 0.02)
    return [(m, (base + _bonds.TERM_PREMIUM * m + spr) * 100.0) for m in maturities]
