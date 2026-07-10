"""
valuation.py — Valorisation fondamentale (logique pure).

Trois outils d'investisseur fondamental, sur les états financiers SIMULÉS
du jeu (core/financials — les mêmes qui alimentent la fiche société) :

- **DCF** (`dcf`, `dcf_sensitivity`) : flux de trésorerie disponibles
  projetés (proxy NOPAT = EBIT×(1−taux d'impôt) — hypothèse documentée :
  capex ≈ dotations, ΔBFR négligé), croissance explicite sur N années puis
  valeur terminale de Gordon (g_terminal < WACC), actualisés au WACC.
  EV → valeur des fonds propres (− dette nette) → par action vs le COURS :
  le verdict sous/surévalué. La table de sensibilité WACC × g_terminal est
  LE réflexe du métier : une valorisation n'est jamais un chiffre, c'est
  une plage.

- **Security Market Line** (`sml`) : le CAPM testé sur tout le roster —
  bêta de chaque société vs le facteur monde observable (rendement pondéré
  capi, cf. core/brinson.factor_returns) et rendement réalisé annualisé ;
  la droite de marché r = rf + β·(r_m − rf) sépare les titres « bon
  marché » (au-dessus : alpha CAPM positif) des « chers ».

- **Pont d'IRR LBO** (`lbo_bridge`) : décomposition EXACTE de la création
  de valeur d'un LBO en trois effets — DÉSENDETTEMENT (le cash sweep
  rembourse la dette), CROISSANCE (ΔEBITDA au multiple d'entrée) et
  EXPANSION DE MULTIPLE ((multiple sortie − entrée) × EBITDA de sortie) —
  la somme des trois retombe exactement sur le gain de fonds propres
  (invariant testé). MOIC et IRR inclus.
"""
import numpy as np

from core import brinson as BR
from core import financials
from core.market import STEPS_PER_YEAR

DEFAULT_WACC = 0.09
DEFAULT_G_TERM = 0.02
DCF_YEARS = 5
WACC_GRID = (0.07, 0.08, 0.09, 0.10, 0.11)
GTERM_GRID = (0.01, 0.02, 0.03)


def dcf(market, ticker, wacc=DEFAULT_WACC, g_term=DEFAULT_G_TERM,
        years=DCF_YEARS, growth=None):
    """Valorisation DCF d'une société cotée. None si données manquantes ou
    WACC ≤ g_terminal (Gordon diverge). Renvoie {fcf0, growth, pv_explicit,
    pv_terminal, ev, net_debt, equity, per_share, price, upside}."""
    if wacc <= g_term:
        return None
    mt = market.metrics(ticker)
    if not mt or not mt.get("shares"):
        return None
    try:
        inc = financials.income_statement(market, ticker)
        bs = financials.balance_sheet(market, ticker)
    except Exception:
        return None
    tax = max(0.0, min(0.50, inc["effective_tax"]))
    fcf0 = inc["ebit"] * (1.0 - tax)                 # NOPAT ≈ FCF (cf. docstring)
    if fcf0 <= 0:
        return None
    if growth is None:
        growth = max(-0.05, min(0.15, financials.annual_growth(market, ticker)))
    pv_explicit = 0.0
    fcf_t = fcf0
    for t in range(1, years + 1):
        fcf_t = fcf0 * (1.0 + growth) ** t
        pv_explicit += fcf_t / (1.0 + wacc) ** t
    tv = fcf_t * (1.0 + g_term) / (wacc - g_term)
    pv_terminal = tv / (1.0 + wacc) ** years
    ev = pv_explicit + pv_terminal
    net_debt = float(bs.get("total_debt", 0.0)) - float(bs.get("cash", 0.0))
    equity = ev - net_debt
    per_share = equity / mt["shares"]
    price = mt["price"]
    return {"ticker": ticker, "name": mt["name"], "fcf0": fcf0,
            "growth": growth, "pv_explicit": pv_explicit,
            "pv_terminal": pv_terminal, "ev": ev, "net_debt": net_debt,
            "equity": equity, "per_share": per_share, "price": price,
            "upside": (per_share / price - 1.0) if price else 0.0}


def dcf_sensitivity(market, ticker, waccs=WACC_GRID, g_terms=GTERM_GRID,
                    growth=None):
    """Table de sensibilité : valeur par action pour chaque (g_term, wacc).
    Renvoie {waccs, g_terms, grid: [g_term][wacc] (None si invalide)}."""
    grid = []
    for g_term in g_terms:
        row = []
        for wacc in waccs:
            r = dcf(market, ticker, wacc=wacc, g_term=g_term, growth=growth)
            row.append(r["per_share"] if r else None)
        grid.append(row)
    return {"waccs": list(waccs), "g_terms": list(g_terms), "grid": grid}


def sml(market, rf=0.02, lookback=73):
    """Security Market Line sur le roster : bêta vs le facteur monde
    observable, rendement réalisé annualisé, alpha CAPM = r − [rf + β(r_m −
    rf)]. Renvoie None si historique court, sinon {r_market, rf, rows:
    [{ticker, beta, ret, expected, alpha}] triés par alpha décroissant}."""
    P = BR._price_matrix(market, lookback)
    if P is None:
        return None
    with np.errstate(divide="ignore", invalid="ignore"):
        R = P[1:] / P[:-1] - 1.0
    R = np.nan_to_num(R)
    w = BR._bench_weights(market)
    rm = R @ w                                       # facteur monde par pas
    var_m = rm.var()
    if var_m <= 0:
        return None
    r_market = float(rm.mean()) * STEPS_PER_YEAR
    rows = []
    for i, c in enumerate(market.companies):
        ri = R[:, i]
        beta = float(np.cov(ri, rm)[0, 1] / var_m)
        ret = float(ri.mean()) * STEPS_PER_YEAR
        expected = rf + beta * (r_market - rf)
        rows.append({"ticker": c["ticker"], "beta": beta, "ret": ret,
                     "expected": expected, "alpha": ret - expected})
    rows.sort(key=lambda x: x["alpha"], reverse=True)
    return {"r_market": r_market, "rf": rf, "rows": rows}


def lbo_bridge(entry_ebitda, entry_mult, debt_pct, ebitda_growth,
               exit_mult, years, sweep_pct=0.35):
    """Pont de création de valeur d'un LBO. La décomposition est EXACTE :
    gain de fonds propres = croissance + expansion de multiple +
    désendettement (invariant testé). `sweep_pct` = part de l'EBITDA
    annuel affectée au remboursement de la dette (cash sweep)."""
    if entry_ebitda <= 0 or entry_mult <= 0 or years <= 0:
        return None
    entry_ev = entry_ebitda * entry_mult
    debt0 = entry_ev * max(0.0, min(0.95, debt_pct))
    equity0 = entry_ev - debt0
    exit_ebitda = entry_ebitda * (1.0 + ebitda_growth) ** years
    # cash sweep : Σ EBITDA_t × sweep, plafonné à la dette d'entrée
    paid = 0.0
    for t in range(1, years + 1):
        paid += entry_ebitda * (1.0 + ebitda_growth) ** t * sweep_pct
    paydown = min(debt0, paid)
    debt_end = debt0 - paydown
    exit_ev = exit_ebitda * exit_mult
    equity_end = exit_ev - debt_end
    # décomposition exacte : ΔEq = ΔEV + paydown ;
    # ΔEV = entry_mult·ΔEBITDA (croissance) + (exit_mult−entry_mult)·EBITDA_sortie
    growth_effect = entry_mult * (exit_ebitda - entry_ebitda)
    multiple_effect = (exit_mult - entry_mult) * exit_ebitda
    gain = equity_end - equity0
    moic = equity_end / equity0 if equity0 > 0 else 0.0
    irr = (moic ** (1.0 / years) - 1.0) if moic > 0 else -1.0
    return {"entry_ev": entry_ev, "debt0": debt0, "equity0": equity0,
            "exit_ebitda": exit_ebitda, "exit_ev": exit_ev,
            "debt_end": debt_end, "equity_end": equity_end, "gain": gain,
            "growth_effect": growth_effect, "multiple_effect": multiple_effect,
            "paydown_effect": paydown, "moic": moic, "irr": irr}
