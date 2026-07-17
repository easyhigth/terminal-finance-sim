"""
credit_risk.py — Risque de crédit structurel, modèle de Merton (logique pure).

LA passerelle théorique du crédit : dans le modèle de Merton (1974), les
ACTIONS d'une entreprise sont un CALL sur ses actifs (strike = la dette) —
la même formule de Black-Scholes price une option ET un défaut :

- Valeur des actifs V = capitalisation boursière E + dette totale D
  (approximation compta : la dette vient du bilan simulé de la société,
  core/financials.balance_sheet) ;
- Vol des actifs σ_V ≈ σ_E · E/V (l'effet de levier amplifie la vol des
  actions par rapport à celle des actifs) ;
- **Distance au défaut** DD = [ln(V/D) + (μ − σ_V²/2)·T] / (σ_V·√T) —
  à combien d'écarts-types les actifs sont-ils du point de défaut ;
- **Probabilité de défaut** PD = N(−DD) ;
- **Spread de crédit implicite** s ≈ −ln(1 − PD·LGD)/T (LGD = 60 %,
  convention marché) — le supplément de rendement qu'exigerait un prêteur.

`market_scan` classe les sociétés du roster par PD décroissante — la
watchlist du desk crédit. Tout bouge avec le cours de bourse : une action
qui chute rapproche mécaniquement la société du défaut (c'est exactement
le lien actions ↔ spreads observé en vrai).
"""
import math

from core import financials
from core import quant_tools as QT

LGD = 0.60                  # perte en cas de défaut (convention marché)
DEFAULT_HORIZON = 1.0       # horizon d'analyse (années)
_VOL_LOOKBACK = 73


def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def merton_credit(market, ticker, horizon=DEFAULT_HORIZON, mu=0.0):
    """Analyse de crédit structurelle d'une société. Renvoie None si les
    données manquent, sinon {ticker, name, equity, debt, assets, leverage,
    sigma_e, sigma_v, dd, pd, spread_bps, rating_view}."""
    mt = market.metrics(ticker)
    if not mt:
        return None
    try:
        bs = financials.balance_sheet(market, ticker)
    except Exception:
        return None
    debt = float(bs.get("total_debt", 0.0))
    equity = float(mt["mktcap"])                     # même unité que le bilan (M)
    if equity <= 0:
        return None
    if debt <= 0:
        # société sans dette : pas de point de défaut — PD nulle par
        # construction (on renvoie quand même la fiche, DD infinie).
        return {"ticker": ticker, "name": mt["name"], "equity": equity,
                "debt": 0.0, "assets": equity, "leverage": 0.0,
                "sigma_e": 0.0, "sigma_v": 0.0, "dd": float("inf"),
                "pd": 0.0, "spread_bps": 0.0}
    rets = QT.returns_of(market, ticker, _VOL_LOOKBACK)
    sigma_e = QT.ann_vol(rets)
    if sigma_e <= 0:
        return None
    assets = equity + debt
    sigma_v = sigma_e * equity / assets              # dé-levier de la vol
    sig_sqrt = sigma_v * math.sqrt(horizon)
    if sig_sqrt <= 0:
        return None
    dd = (math.log(assets / debt) + (mu - 0.5 * sigma_v ** 2) * horizon) / sig_sqrt
    pd = _norm_cdf(-dd)
    el = min(0.999, pd * LGD)
    spread = -math.log(1.0 - el) / horizon           # spread implicite (décimal)
    return {"ticker": ticker, "name": mt["name"], "equity": equity,
            "debt": debt, "assets": assets, "leverage": debt / equity,
            "sigma_e": sigma_e, "sigma_v": sigma_v, "dd": dd, "pd": pd,
            "spread_bps": spread * 10_000.0}


def pd_vs_equity_curve(market, ticker, shocks=(-0.6, -0.4, -0.2, 0.0, 0.2),
                       horizon=DEFAULT_HORIZON):
    """PD recalculée pour des chocs sur le cours de l'action — le lien
    actions ↔ crédit rendu visible : [(choc_pct, pd)]."""
    base = merton_credit(market, ticker, horizon)
    if base is None or base["debt"] <= 0:
        return []
    out = []
    for shock in shocks:
        equity = base["equity"] * (1.0 + shock)
        if equity <= 0:
            out.append((shock, 1.0))
            continue
        assets = equity + base["debt"]
        sigma_v = base["sigma_e"] * equity / assets
        sig_sqrt = sigma_v * math.sqrt(horizon)
        if sig_sqrt <= 0:
            out.append((shock, 0.0))
            continue
        dd = (math.log(assets / base["debt"]) - 0.5 * sigma_v ** 2 * horizon) / sig_sqrt
        out.append((shock, _norm_cdf(-dd)))
    return out


def market_scan(market, n=10, horizon=DEFAULT_HORIZON):
    """Les `n` sociétés du roster les PLUS risquées (PD décroissante) —
    la watchlist du desk crédit. [{... fiche merton_credit ...}]."""
    rows = []
    for c in market.companies:
        r = merton_credit(market, c["ticker"], horizon)
        if r is not None and r["debt"] > 0:
            rows.append(r)
    rows.sort(key=lambda x: x["pd"], reverse=True)
    return rows[:n]
