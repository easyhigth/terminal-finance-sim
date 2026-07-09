"""
quant_tools.py — Boîte à outils QUANT partagée par les applications d'analyse
du bureau (Sharpe, Z-Score, Couverture, Frontière efficiente interactive) —
logique PURE, sans pygame, testable directement.

Conventions :
- 1 pas de marché = ``config.DAYS_PER_STEP`` (5) jours → ``STEPS_PER_YEAR``
  (73) pas par an (réutilisé depuis core.market, comme core/analytics).
  Les périodes d'analyse utilisent le MÊME barème que l'atelier de graphes
  (``scenes/scene_graph.STEP_PERIODS``) : 1M=6, 3M=18, 1A=73, 3A=219, 5A=365.
- Les rendements sont PAR PAS ; les chiffres affichés (rendement, volatilité,
  Sharpe) sont ANNUALISÉS (× STEPS_PER_YEAR, × √STEPS_PER_YEAR).
- Le benchmark « marché » est le VRAI indice régional du joueur
  (``market.index_history``) — pas un proxy inventé.
- Aucun aléa : tout est calculé depuis l'historique déterministe du moteur
  (la « projection 1 an » utilise les quantiles ANALYTIQUES d'une lognormale,
  pas un Monte-Carlo tiré au hasard — même résultat à chaque frame).
"""
import math

import numpy as np

from core import finmath
from core import portfolio as pf
from core.market import STEPS_PER_YEAR

# Mêmes horizons que scenes/scene_graph.STEP_PERIODS (1 pas = 5 jours).
PERIOD_STEPS = {"1M": 6, "3M": 18, "1A": 73, "3A": 219, "5A": 365, "MAX": None}
PERIOD_ORDER = ["1M", "3M", "1A", "3A", "5A", "MAX"]

DEFAULT_LOOKBACK = 73          # 1 an de pas — défaut des estimations mean/cov
MIN_POINTS = 8                 # points de rendement minimum pour une stat


# ===========================================================================
# Rendements / annualisation
# ===========================================================================
def simple_returns(series):
    """Rendements simples d'une série de prix (liste/array) → np.array."""
    if series is None:
        return np.zeros(0)
    s = np.asarray(series, dtype=float)
    s = s[np.isfinite(s) & (s != 0)]
    if len(s) < 2:
        return np.zeros(0)
    return s[1:] / s[:-1] - 1.0


def returns_of(market, ticker, steps=None):
    """Rendements PAR PAS d'une action sur les `steps` derniers pas."""
    hist = market.history_of(ticker, steps or DEFAULT_LOOKBACK)
    return simple_returns(hist)


def index_returns(market, name=None, steps=None):
    """Rendements PAR PAS d'un indice (le premier du marché par défaut)."""
    if name is None:
        name = main_index(market)
        if name is None:
            return np.zeros(0)
    hist = market.index_history(name)
    if steps:
        hist = hist[-(steps + 1):]
    return simple_returns(hist)


def main_index(market, player=None):
    """Nom de l'indice de référence : celui de la région du joueur si connue,
    sinon le premier indice du marché. None si aucun indice."""
    if not getattr(market, "index_region", None):
        return None
    if player is not None:
        region = getattr(player, "continent", None)
        for name, reg in market.index_region.items():
            if reg == region:
                return name
    return next(iter(market.index_region))


def ann_return(step_returns):
    """Rendement moyen annualisé (arithmétique × pas/an)."""
    r = np.asarray(step_returns, dtype=float)
    return float(r.mean()) * STEPS_PER_YEAR if len(r) else 0.0


def ann_vol(step_returns):
    """Volatilité annualisée (écart-type par pas × √pas/an)."""
    r = np.asarray(step_returns, dtype=float)
    return float(r.std()) * math.sqrt(STEPS_PER_YEAR) if len(r) >= 2 else 0.0


def sharpe(step_returns, rf_annual=0.02):
    """Ratio de Sharpe ANNUALISÉ : (rendement ann. − rf) / vol ann.
    Une vol quasi nulle (série constante, bruit flottant) renvoie 0 plutôt
    qu'un ratio astronomique dénué de sens."""
    vol = ann_vol(step_returns)
    if vol <= 1e-9:
        return 0.0
    return (ann_return(step_returns) - rf_annual) / vol


def rolling_sharpe(step_returns, window=18, rf_annual=0.02):
    """Sharpe annualisé sur fenêtre glissante — série pour la courbe.
    `window` = 18 pas ≈ un trimestre. Renvoie np.array (peut être vide)."""
    r = np.asarray(step_returns, dtype=float)
    if len(r) < window:
        return np.zeros(0)
    out = []
    rf_step = rf_annual / STEPS_PER_YEAR
    for i in range(window, len(r) + 1):
        w = r[i - window:i]
        sd = w.std()
        out.append(((w.mean() - rf_step) / sd * math.sqrt(STEPS_PER_YEAR))
                   if sd > 0 else 0.0)
    return np.asarray(out)


def beta(asset_returns, bench_returns):
    """Bêta de l'actif vs le benchmark (cov/var), sur la fenêtre commune."""
    a = np.asarray(asset_returns, dtype=float)
    b = np.asarray(bench_returns, dtype=float)
    n = min(len(a), len(b))
    if n < MIN_POINTS:
        return 0.0
    a, b = a[-n:], b[-n:]
    cm = np.cov(a, b)               # ddof=1 partout (cov ET var de la même matrice)
    if cm[1, 1] <= 0:
        return 0.0
    return float(cm[0, 1] / cm[1, 1])


# ===========================================================================
# Portefeuille du joueur
# ===========================================================================
def portfolio_step_returns(player, market, steps=None):
    """Rendements PAR PAS du panier d'actions LONGUES du joueur, reconstruits
    avec les quantités ACTUELLES sur les clôtures passées (approximation
    honnête : mesure le comportement du panier tel qu'il est composé
    aujourd'hui, pas le P&L historique réel — celui-là vit dans le Journal)."""
    held = [h for h in pf.holdings(player, market) if not h["short"]]
    if not held:
        return np.zeros(0), []
    steps = steps or DEFAULT_LOOKBACK
    series = []
    for h in held:
        hist = market.history_of(h["ticker"], steps)
        series.append((h["shares"], np.asarray(hist, dtype=float)))
    n = min(len(s) for _q, s in series)
    if n < 2:
        return np.zeros(0), [h["ticker"] for h in held]
    values = sum(q * s[-n:] for q, s in series)
    return simple_returns(values), [h["ticker"] for h in held]


def current_weights(player, market, tickers):
    """Poids ACTUELS (valeur longue / total) du joueur sur cet univers —
    0.0 pour un ticker non détenu. Renvoie (np.array poids, valeur totale)."""
    vals = []
    for tk in tickers:
        pos = player.portfolio.get(tk)
        shares = pos["shares"] if pos else 0.0
        price = market.price_of(tk) or 0.0
        vals.append(max(0.0, shares) * price)
    vals = np.asarray(vals, dtype=float)
    total = float(vals.sum())
    if total <= 0:
        return np.zeros(len(tickers)), 0.0
    return vals / total, total


# ===========================================================================
# Frontière efficiente (avec POIDS par point — pour trader vers une cible)
# ===========================================================================
def frontier(market, tickers, n_points=30, lookback=None, rf_annual=0.02):
    """Frontière efficiente ANNUALISÉE sur un univers d'actions, AVEC les
    poids de chaque point (contrairement à analytics.frontier_for_universe,
    pensé pour l'affichage seul) — c'est ce qui permet ensuite de calculer
    les ordres qui mènent à un point choisi de la courbe.

    Retourne None si < 2 tickers ou historique insuffisant, sinon :
    {tickers, mean, cov, vols, rets, weights (liste np.array),
     i_min_var, i_max_sharpe} — vols/rets en DÉCIMAL annualisé."""
    tickers = [tk for tk in tickers if tk]
    if len(tickers) < 2:
        return None
    lookback = lookback or DEFAULT_LOOKBACK
    rets = [returns_of(market, tk, lookback) for tk in tickers]
    n = min((len(r) for r in rets), default=0)
    if n < MIN_POINTS:
        return None
    R = np.array([r[-n:] for r in rets])
    mean = R.mean(axis=1) * STEPS_PER_YEAR
    cov = np.cov(R) * STEPS_PER_YEAR
    try:
        vols, frets, ws = finmath.efficient_frontier(mean, cov, n_points)
    except Exception:
        return None
    if len(vols) < 2:
        return None
    sharpes = [(r - rf_annual) / v if v > 0 else 0.0 for v, r in zip(vols, frets)]
    return {
        "tickers": list(tickers), "mean": mean, "cov": cov,
        "vols": np.asarray(vols), "rets": np.asarray(frets),
        "weights": [np.asarray(w) for w in ws],
        "i_min_var": int(np.argmin(vols)),
        "i_max_sharpe": int(np.argmax(sharpes)),
    }


def point_stats(weights, mean, cov, rf_annual=0.02):
    """(rendement, volatilité, sharpe) annualisés d'un jeu de poids."""
    w = np.asarray(weights, dtype=float)
    ret = finmath.portfolio_return(w, mean)
    vol = finmath.portfolio_volatility(w, cov)
    return ret, vol, ((ret - rf_annual) / vol if vol > 0 else 0.0)


def target_trades(player, market, tickers, target_weights, budget=None):
    """Ordres (entiers) pour amener les positions du joueur sur cet univers
    aux poids cibles. `budget` = valeur totale visée (défaut : valeur longue
    ACTUELLE de l'univers — rééquilibrage auto-financé ; si le joueur ne
    détient rien, 80 % du cash pour laisser les frais passer).

    Renvoie {"budget", "trades": [{"ticker","side","qty","value"}]} — ventes
    d'abord (elles financent les achats), poussières ignorées (< 1 titre ou
    < 0,5 % du budget)."""
    w = np.asarray(target_weights, dtype=float)
    tot = w.sum()
    if tot <= 0:
        return {"budget": 0.0, "trades": []}
    w = w / tot
    _cur_w, held_value = current_weights(player, market, tickers)
    if budget is None:
        budget = held_value if held_value > 0 else max(0.0, player.cash * 0.8)
    sells, buys = [], []
    for tk, wi in zip(tickers, w):
        price = market.price_of(tk)
        if not price or price <= 0:
            continue
        pos = player.portfolio.get(tk)
        cur_shares = max(0.0, pos["shares"]) if pos else 0.0
        delta_val = wi * budget - cur_shares * price
        qty = int(round(abs(delta_val) / price))
        if qty < 1 or abs(delta_val) < 0.005 * budget:
            continue
        entry = {"ticker": tk, "qty": qty, "value": qty * price}
        if delta_val < 0:
            entry["side"] = "sell"
            entry["qty"] = min(qty, int(cur_shares))
            if entry["qty"] < 1:
                continue
            entry["value"] = entry["qty"] * price
            sells.append(entry)
        else:
            entry["side"] = "buy"
            buys.append(entry)
    return {"budget": float(budget), "trades": sells + buys}


def apply_trades(player, market, trades):
    """Exécute une liste d'ordres de `target_trades` via core.portfolio
    (ventes PUIS achats — les ventes libèrent le cash). Best-effort : un
    ordre refusé (levier, secteur exclu…) est collecté, pas bloquant.
    Renvoie {"done", "failed": [(ticker, raison)], "realized"}."""
    done, failed, realized = 0, [], 0.0
    for t in [t for t in trades if t["side"] == "sell"]:
        r = pf.sell(player, market, t["ticker"], t["qty"])
        if r.get("ok"):
            done += 1
            realized += r.get("realized", 0.0)
        else:
            failed.append((t["ticker"], r.get("reason", "?")))
    for t in [t for t in trades if t["side"] == "buy"]:
        r = pf.buy(player, market, t["ticker"], t["qty"])
        if r.get("ok"):
            done += 1
        else:
            failed.append((t["ticker"], r.get("reason", "?")))
    return {"done": done, "failed": failed, "realized": realized}


def projection(value, ret_annual, vol_annual, years=1.0):
    """Quantiles ANALYTIQUES (lognormale) de la valeur à l'horizon donné —
    la « simulation » déterministe affichée sous un point de frontière.
    Renvoie {"p5","p50","p95"}."""
    if value <= 0:
        return {"p5": 0.0, "p50": 0.0, "p95": 0.0}
    mu = (ret_annual - 0.5 * vol_annual ** 2) * years
    sd = vol_annual * math.sqrt(years)
    z95 = 1.6449  # quantile 95 % de la normale standard
    return {
        "p5": value * math.exp(mu - z95 * sd),
        "p50": value * math.exp(mu),
        "p95": value * math.exp(mu + z95 * sd),
    }


# ===========================================================================
# Z-scores
# ===========================================================================
def rolling_zscore(values, window=18):
    """Z-score glissant : z_t = (x_t − moyenne_fenêtre) / écart-type_fenêtre.
    Renvoie np.array de longueur len(values) − window + 1 (vide si trop court)."""
    x = np.asarray(values, dtype=float)
    if len(x) < window or window < 3:
        return np.zeros(0)
    out = []
    for i in range(window, len(x) + 1):
        w = x[i - window:i]
        sd = w.std()
        out.append((w[-1] - w.mean()) / sd if sd > 0 else 0.0)
    return np.asarray(out)


def zscore_last(values, window=None):
    """Z-score de la DERNIÈRE valeur vs la fenêtre (toute la série par défaut)."""
    x = np.asarray(values, dtype=float)
    if window:
        x = x[-window:]
    if len(x) < 3:
        return 0.0
    sd = x.std()
    return float((x[-1] - x.mean()) / sd) if sd > 0 else 0.0


def rolling_volatility(step_returns, window=18):
    """Volatilité annualisée sur fenêtre glissante (série pour z-score de vol)."""
    r = np.asarray(step_returns, dtype=float)
    if len(r) < window:
        return np.zeros(0)
    out = [r[i - window:i].std() * math.sqrt(STEPS_PER_YEAR)
           for i in range(window, len(r) + 1)]
    return np.asarray(out)


def rolling_correlation(asset_returns, bench_returns, window=18):
    """Corrélation glissante actif/benchmark (série pour z-score de corrélation)."""
    a = np.asarray(asset_returns, dtype=float)
    b = np.asarray(bench_returns, dtype=float)
    n = min(len(a), len(b))
    if n < window:
        return np.zeros(0)
    a, b = a[-n:], b[-n:]
    out = []
    for i in range(window, n + 1):
        wa, wb = a[i - window:i], b[i - window:i]
        if wa.std() > 0 and wb.std() > 0:
            c = float(np.corrcoef(wa, wb)[0, 1])
            out.append(c if not np.isnan(c) else 0.0)
        else:
            out.append(0.0)
    return np.asarray(out)


# ===========================================================================
# Couverture (paire corrélée)
# ===========================================================================
def hedge_ratio(asset_returns, hedge_returns):
    """Ratio de couverture à variance minimale h = cov/var(hedge), avec la
    qualité attendue : R² (part de variance neutralisable) et corrélation.
    Renvoie {"ratio","corr","r2","resid_vol_pct"} (resid = vol résiduelle en
    % de la vol de l'actif : √(1−R²))."""
    a = np.asarray(asset_returns, dtype=float)
    h = np.asarray(hedge_returns, dtype=float)
    n = min(len(a), len(h))
    if n < MIN_POINTS:
        return {"ratio": 0.0, "corr": 0.0, "r2": 0.0, "resid_vol_pct": 100.0}
    a, h = a[-n:], h[-n:]
    cm = np.cov(a, h)               # ddof=1 partout (cov ET var de la même matrice)
    if cm[1, 1] <= 0 or a.std() <= 0:
        return {"ratio": 0.0, "corr": 0.0, "r2": 0.0, "resid_vol_pct": 100.0}
    ratio = float(cm[0, 1] / cm[1, 1])
    corr = float(np.corrcoef(a, h)[0, 1])
    corr = 0.0 if np.isnan(corr) else corr
    r2 = corr ** 2
    return {"ratio": ratio, "corr": corr, "r2": r2,
            "resid_vol_pct": math.sqrt(max(0.0, 1.0 - r2)) * 100.0}


def hedge_candidates(market, ticker, n=5, lookback=None):
    """Les `n` actions les PLUS corrélées à `ticker` (candidats naturels pour
    une couverture en paire) — [(ticker, corr)] triés décroissant."""
    base = returns_of(market, ticker, lookback or DEFAULT_LOOKBACK)
    if len(base) < MIN_POINTS:
        return []
    scored = []
    for c in market.companies:
        tk = c["ticker"]
        if tk == ticker:
            continue
        r = returns_of(market, tk, lookback or DEFAULT_LOOKBACK)
        m = min(len(base), len(r))
        if m < MIN_POINTS:
            continue
        with np.errstate(invalid="ignore", divide="ignore"):
            cm = np.corrcoef(base[-m:], r[-m:])
        v = float(cm[0, 1])
        if not np.isnan(v):
            scored.append((tk, v))
    scored.sort(key=lambda kv: kv[1], reverse=True)
    return scored[:n]
