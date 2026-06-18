"""
indicators.py — Indicateurs techniques pour superposition sur les graphiques
de cours (outil d'analyse purement visuel, sans impact sur le cash/portefeuille).

Logique pure et testable (numpy autorisé, pas de pygame). Toutes les fonctions
prennent une liste/array de prix en entrée et retournent une **liste Python**
(jamais un array numpy brut), de même longueur que l'entrée, pour rester
simples à consommer côté UI (alignement direct avec l'axe des x du graphique).
Les points sans historique suffisant valent `None`.
"""
import numpy as np


def sma(prices, period):
    """Moyenne mobile simple sur `period` points. Même longueur que `prices`,
    `None` pour les indices où l'historique est insuffisant."""
    n = len(prices)
    out = [None] * n
    if period <= 0 or n == 0:
        return out
    s = 0.0
    for i, v in enumerate(prices):
        s += v
        if i >= period:
            s -= prices[i - period]
        if i >= period - 1:
            out[i] = s / period
    return out


def ema(prices, period):
    """Moyenne mobile exponentielle sur `period` points. Même contrat de
    longueur/alignement que `sma` : `None` tant que l'historique est
    insuffisant, puis amorcée par la SMA des `period` premiers points."""
    n = len(prices)
    out = [None] * n
    if period <= 0 or n == 0:
        return out
    if n < period:
        return out
    alpha = 2.0 / (period + 1.0)
    seed = sum(prices[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, n):
        prev = prices[i] * alpha + prev * (1.0 - alpha)
        out[i] = prev
    return out


def bollinger_bands(prices, period=20, num_std=2.0):
    """Bandes de Bollinger : (lower, mid, upper), trois listes de même longueur
    que `prices`. `mid` = SMA(period), `lower`/`upper` = mid ± num_std * écart-type
    glissant (population, calculé sur la même fenêtre que la SMA)."""
    n = len(prices)
    mid = sma(prices, period)
    lower = [None] * n
    upper = [None] * n
    if period <= 0 or n == 0:
        return lower, mid, upper
    arr = np.asarray(prices, dtype=float)
    for i in range(n):
        if mid[i] is None:
            continue
        window = arr[i - period + 1:i + 1]
        std = float(np.std(window))
        lower[i] = mid[i] - num_std * std
        upper[i] = mid[i] + num_std * std
    return lower, mid, upper


def rsi(prices, period=14):
    """RSI standard (0-100) : moyenne des gains/pertes lissée (méthode de Wilder).
    Même longueur que `prices`, `None` tant que l'historique est insuffisant."""
    n = len(prices)
    out = [None] * n
    if period <= 0 or n <= period:
        return out
    gains = [0.0] * n
    losses = [0.0] * n
    for i in range(1, n):
        diff = prices[i] - prices[i - 1]
        gains[i] = max(diff, 0.0)
        losses[i] = max(-diff, 0.0)
    avg_gain = sum(gains[1:period + 1]) / period
    avg_loss = sum(losses[1:period + 1]) / period

    def _rsi_value(ag, al):
        if al == 0.0:
            return 100.0 if ag > 0.0 else 50.0
        rs = ag / al
        return 100.0 - 100.0 / (1.0 + rs)

    out[period] = _rsi_value(avg_gain, avg_loss)
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out
