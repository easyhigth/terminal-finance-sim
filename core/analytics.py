"""
analytics.py — Synthèse COMPLÈTE et testable du portefeuille (toutes classes).

Agrège actions, obligations, matières premières et crypto en une vue unifiée :
poids, P&L, répartition (classe / secteur / région), risque (bêta, levier, vol
annualisée estimée, drawdown), concentration (HHI), corrélations et frontière
efficiente estimées sur l'historique réel. Logique pure (numpy), sans pygame.
"""
import numpy as np

from core import charts, finmath
from core import market as _market
from core import portfolio as pf

STEPS_PER_YEAR = _market.STEPS_PER_YEAR
_HIST = 120          # fenêtre d'historique pour vol / corrélation / frontière


def holdings_table(player, market):
    """Positions unifiées de toutes les classes d'actifs, avec poids (% du brut
    investi). Chaque ligne : {label, name, cls, qty, price, value, pnl, pnl_pct,
    short, weight}."""
    comp = {c["ticker"]: c for c in market.companies}
    rows = []
    for h in pf.holdings(player, market):
        c = comp.get(h["ticker"], {})
        rows.append({"label": h["ticker"], "name": c.get("name", h["ticker"]),
                     "cls": "Actions", "qty": h["shares"], "price": h["price"],
                     "value": h["value"], "pnl": h["pnl"], "pnl_pct": h["pnl_pct"],
                     "short": h["short"]})
    if getattr(player, "bonds", None):
        from core import bonds
        for h in bonds.holdings(player, market):
            base = h["avg"] * h["qty"]
            rows.append({"label": h["id"], "name": h["name"], "cls": "Obligations",
                         "qty": h["qty"], "price": h["price"], "value": h["value"],
                         "pnl": h["pnl"], "pnl_pct": (h["pnl"] / base * 100) if base else 0.0,
                         "short": False})
    if getattr(player, "commodities", None):
        from core import commodities
        for h in commodities.holdings(player, market):
            base = h["avg"] * h["qty"]
            rows.append({"label": h["id"], "name": h["name"], "cls": "Matières",
                         "qty": h["qty"], "price": h["price"], "value": h["value"],
                         "pnl": h["pnl"], "pnl_pct": (h["pnl"] / base * 100) if base else 0.0,
                         "short": h["qty"] < 0})
    if getattr(player, "crypto", None):
        from core import crypto
        for h in crypto.holdings(player, market):
            base = h.get("avg", 0) * h.get("qty", 0)
            rows.append({"label": h.get("id", "?"), "name": h.get("name", "?"),
                         "cls": "Crypto", "qty": h.get("qty", 0), "price": h.get("price", 0),
                         "value": h["value"], "pnl": h.get("pnl", 0.0),
                         "pnl_pct": (h.get("pnl", 0) / base * 100) if base else 0.0,
                         "short": False})
    gross = sum(abs(r["value"]) for r in rows) or 1.0
    for r in rows:
        r["weight"] = abs(r["value"]) / gross * 100.0
    rows.sort(key=lambda r: abs(r["value"]), reverse=True)
    return rows


def max_drawdown(history):
    """Drawdown maximal (%) d'une série de valeur nette."""
    if not history or len(history) < 2:
        return 0.0
    peak, mdd = history[0], 0.0
    for v in history:
        peak = max(peak, v)
        if peak > 0:
            mdd = max(mdd, (peak - v) / peak)
    return mdd * 100.0


def recovery_time(history):
    """Temps de récupération (en pas) après le drawdown le plus profond de la
    série : nombre de pas entre le creux le plus bas (sous le pic le plus
    pénalisant) et le retour au-dessus de ce même pic. 0 si aucun drawdown.
    None si le portefeuille n'a pas encore récupéré."""
    if not history or len(history) < 2:
        return 0
    peak, peak_i = history[0], 0
    worst_dd, worst_peak_i, worst_trough_i = 0.0, 0, 0
    for i, v in enumerate(history):
        if v > peak:
            peak, peak_i = v, i
        dd = (peak - v) / peak if peak > 0 else 0.0
        if dd > worst_dd:
            worst_dd, worst_peak_i, worst_trough_i = dd, peak_i, i
    if worst_dd <= 0:
        return 0
    recovery_level = history[worst_peak_i]
    for i in range(worst_trough_i + 1, len(history)):
        if history[i] >= recovery_level:
            return i - worst_trough_i
    return None


def tracking_error(player, market):
    """Tracking error (%) du portefeuille vs l'indice régional du joueur, sur
    l'historique commun le plus long disponible (cf. finmath.tracking_error).
    0.0 si l'historique est trop court pour être significatif."""
    hist = getattr(player, "cash_history", [])
    idx = {n: r for n, r, *_ in market.index_defs}
    ref = next((n for n, r in idx.items() if r == player.continent), None)
    if ref is None or len(hist) < 3:
        return 0.0
    bench_hist = market.index_history(ref)
    n = min(len(hist), len(bench_hist))
    if n < 3:
        return 0.0
    port_rets = charts.simple_returns(hist[-n:])
    bench_rets = charts.simple_returns(bench_hist[-n:])
    m = min(len(port_rets), len(bench_rets))
    if m < 2:
        return 0.0
    return finmath.tracking_error(port_rets[-m:], bench_rets[-m:]) * 100.0


def equity_volatility(player, market):
    """Volatilité annualisée (%) du sous-portefeuille ACTIONS, estimée par la
    covariance des rendements d'historique, pondérée par les poids signés."""
    eq = pf.holdings(player, market)
    if len(eq) < 1:
        return 0.0
    series = [market.history_of(h["ticker"], _HIST) for h in eq]
    rets = [charts.simple_returns(s) for s in series]
    n = min((len(r) for r in rets), default=0)
    if n < 5:
        return 0.0
    R = np.array([r[-n:] for r in rets])
    tot = sum(h["value"] for h in eq)
    if abs(tot) < 1e-9:
        return 0.0
    w = np.array([h["value"] / tot for h in eq])
    cov = np.cov(R) if len(eq) > 1 else np.array([[float(np.var(R[0]))]])
    var = float(w @ np.atleast_2d(cov) @ w)
    return float(np.sqrt(max(0.0, var)) * np.sqrt(STEPS_PER_YEAR) * 100.0)


def correlation(player, market):
    """Matrice de corrélation des rendements des actions détenues.
    Retourne (labels, matrice np) ; labels vide si < 2 actions."""
    eq = pf.holdings(player, market)
    if len(eq) < 2:
        return [], np.zeros((0, 0))
    smap = {h["ticker"]: market.history_of(h["ticker"], _HIST) for h in eq}
    return charts.correlation_matrix(smap)


def equity_frontier(player, market, n_points=30):
    """Frontière efficiente estimée sur les actions LONGUES détenues (≥ 2).
    Retourne {vols, rets, cur:(vol,ret), labels} (en %), ou None."""
    eq = [h for h in pf.holdings(player, market) if not h["short"]]
    if len(eq) < 2:
        return None
    series = [market.history_of(h["ticker"], _HIST) for h in eq]
    rets = [charts.simple_returns(s) for s in series]
    n = min((len(r) for r in rets), default=0)
    if n < 10:
        return None
    R = np.array([r[-n:] for r in rets])
    mean = R.mean(axis=1) * STEPS_PER_YEAR
    cov = np.cov(R) * STEPS_PER_YEAR
    try:
        vols, frets, _ = finmath.efficient_frontier(mean, cov, n_points)
    except Exception:
        return None
    tot = sum(h["value"] for h in eq) or 1.0
    w = np.array([h["value"] / tot for h in eq])
    cur_vol = finmath.portfolio_volatility(w, cov)
    cur_ret = finmath.portfolio_return(w, mean)
    return {"vols": np.asarray(vols) * 100, "rets": np.asarray(frets) * 100,
            "cur": (cur_vol * 100, cur_ret * 100),
            "labels": [h["ticker"] for h in eq]}


def summary(player, market):
    """Synthèse chiffrée complète du portefeuille (pour le tableau de bord)."""
    rows = holdings_table(player, market)
    nw = pf.net_worth(player, market)
    cash = player.cash
    invested = sum(abs(r["value"]) for r in rows)
    upnl = sum(r["pnl"] for r in rows)
    by_class, by_sector, by_region = {}, {}, {}
    for r in rows:
        by_class[r["cls"]] = by_class.get(r["cls"], 0.0) + abs(r["value"])
    by_sector = pf.allocation_by(player, market, "sector")
    by_region = pf.allocation_by(player, market, "region")
    # concentration (HHI sur les poids du brut investi)
    weights = [abs(r["value"]) / invested for r in rows] if invested else []
    hhi = sum(w * w for w in weights)
    eff_n = (1.0 / hhi) if hhi else 0.0           # nombre effectif de lignes
    ms = pf.margin_status(player, market)
    return {
        "rows": rows,
        "net_worth": nw, "cash": cash, "invested": invested,
        "unrealized_pnl": upnl, "realized_pnl": getattr(player, "realized_pnl", 0.0),
        "beta": pf.portfolio_beta(player, market),
        "leverage": ms["leverage"], "gross": ms["gross"],
        "buying_power": ms["buying_power"], "margin_call": ms["margin_call"],
        "volatility": equity_volatility(player, market),
        "max_drawdown": max_drawdown(getattr(player, "cash_history", [])),
        "recovery_time": recovery_time(getattr(player, "cash_history", [])),
        "tracking_error": tracking_error(player, market),
        "by_class": by_class, "by_sector": by_sector, "by_region": by_region,
        "top_weight": (max(weights) * 100 if weights else 0.0),
        "hhi": hhi, "effective_positions": eff_n, "n_positions": len(rows),
    }
