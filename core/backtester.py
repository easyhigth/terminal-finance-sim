"""
backtester.py — Backtesteur de stratégies simples (logique pure, sans pygame).

Rejoue une règle de trading MÉCANIQUE (pas d'IA, pas de triche) sur
l'historique de prix RÉEL d'un titre — y compris la préhistoire de carrière
(5 ans avant le jour 1, cf. `Market.history_of`), donnant assez de données
pour juger une stratégie avant même de risquer du cash réel en jeu.

Chaque stratégie renvoie un signal de POSITION (0 = flat, 1 = long à 100 %
du capital) par pas, décidé avec les données disponibles JUSQU'À ce pas
(aucun regard vers le futur) ; `run_backtest` applique ce signal au
RENDEMENT SUIVANT (position déterminée en t, appliquée au rendement t→t+1),
comme un ordre qui ne peut s'exécuter qu'après avoir été décidé.
"""
import numpy as np

STEPS_PER_YEAR = 73  # convention core/market.py (1 pas = 5 jours)


def _prices(prices):
    return np.asarray(prices, dtype=float)


def buy_hold_signal(prices):
    return np.ones(len(_prices(prices)))


def sma_crossover_signal(prices, fast=5, slow=20):
    """Long tant que la moyenne mobile rapide est au-dessus de la lente."""
    p = _prices(prices)
    n = len(p)
    sig = np.zeros(n)
    for t in range(slow - 1, n):
        fast_avg = p[t - fast + 1:t + 1].mean()
        slow_avg = p[t - slow + 1:t + 1].mean()
        sig[t] = 1.0 if fast_avg > slow_avg else 0.0
    return sig


def momentum_signal(prices, lookback=10):
    """Long si le prix a progressé sur les `lookback` derniers pas."""
    p = _prices(prices)
    n = len(p)
    sig = np.zeros(n)
    for t in range(lookback, n):
        sig[t] = 1.0 if p[t] > p[t - lookback] else 0.0
    return sig


def mean_reversion_signal(prices, z_lookback=20, entry_z=-1.0):
    """Long quand le z-score du prix (fenêtre glissante) tombe sous `entry_z` —
    achète le creux, parie sur le retour à la moyenne."""
    p = _prices(prices)
    n = len(p)
    sig = np.zeros(n)
    for t in range(z_lookback - 1, n):
        window = p[t - z_lookback + 1:t + 1]
        mu, sd = window.mean(), window.std()
        z = (p[t] - mu) / sd if sd > 1e-12 else 0.0
        sig[t] = 1.0 if z < entry_z else 0.0
    return sig


STRATEGIES = {
    "buy_hold": buy_hold_signal,
    "sma_crossover": sma_crossover_signal,
    "momentum": momentum_signal,
    "mean_reversion": mean_reversion_signal,
}

STRATEGY_LABELS = {
    "buy_hold": "Buy & hold",
    "sma_crossover": "Croisement de moyennes mobiles",
    "momentum": "Momentum",
    "mean_reversion": "Retour à la moyenne",
}


def run_backtest(prices, strategy="sma_crossover", **kwargs):
    """Rejoue `strategy` sur `prices` (liste/array). Renvoie None si
    l'historique est trop court, sinon {equity, positions, total_return,
    benchmark_return, sharpe, max_drawdown, exposure, n}."""
    p = _prices(prices)
    if len(p) < 3:
        return None
    fn = STRATEGIES.get(strategy)
    if fn is None:
        return None
    sig = np.asarray(fn(p, **kwargs), dtype=float)
    rets = np.diff(p) / p[:-1]              # rets[t] = rendement de t vers t+1
    positions = sig[:-1]                     # décidée en t (données jusqu'à t incluses)
    strat_rets = positions * rets
    equity = np.cumprod(1.0 + strat_rets)
    bh_equity = np.cumprod(1.0 + rets)
    total_return = float(equity[-1] - 1.0) if len(equity) else 0.0
    bh_return = float(bh_equity[-1] - 1.0) if len(bh_equity) else 0.0
    mean = float(strat_rets.mean()) if len(strat_rets) else 0.0
    std = float(strat_rets.std(ddof=1)) if len(strat_rets) > 1 else 0.0
    sharpe = (mean / std * np.sqrt(STEPS_PER_YEAR)) if std > 1e-12 else 0.0
    running_max = np.maximum.accumulate(equity) if len(equity) else np.array([1.0])
    drawdown = (equity - running_max) / running_max if len(equity) else np.array([0.0])
    max_dd = float(drawdown.min()) if len(drawdown) else 0.0
    exposure = float(positions.mean()) if len(positions) else 0.0
    return {
        "equity": equity.tolist(), "positions": positions.tolist(),
        "total_return": total_return, "benchmark_return": bh_return,
        "sharpe": sharpe, "max_drawdown": max_dd, "exposure": exposure,
        "n": len(p),
    }


def backtest_ticker(market, ticker, strategy="sma_crossover", **kwargs):
    """Rejoue `strategy` sur l'historique complet (préhistoire incluse) d'un
    titre du roster. None si le ticker est inconnu ou l'historique trop court."""
    hist = market.history_of(ticker)
    if not hist:
        return None
    return run_backtest(hist, strategy=strategy, **kwargs)
