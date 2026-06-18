"""
finmath.py — Moteur de calcul financier (formules réelles).
Toutes les fonctions sont pures (entrées -> sorties), testables sans pygame.
Couvre : valeur temps de l'argent, obligations, DCF, options (Black-Scholes),
portefeuille (Markowitz / efficient frontier), risque (VaR, Sharpe), LBO.

Dépendances : numpy, scipy.
"""
import math

import numpy as np

try:
    from scipy.optimize import minimize
    from scipy.stats import norm
    _HAS_SCIPY = True
except Exception:  # pragma: no cover
    _HAS_SCIPY = False


# ===========================================================================
# 1. VALEUR TEMPS DE L'ARGENT
# ===========================================================================
def present_value(fv, rate, periods):
    """Valeur actuelle d'un flux futur unique."""
    return fv / ((1 + rate) ** periods)


def future_value(pv, rate, periods):
    """Valeur future d'un montant actuel."""
    return pv * ((1 + rate) ** periods)


def npv(rate, cashflows):
    """Valeur actuelle nette. cashflows[0] = t0 (souvent négatif)."""
    return sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cashflows))


def irr(cashflows, guess=0.1, tol=1e-7, max_iter=200):
    """Taux de rentabilité interne (Newton-Raphson, fallback bisection)."""
    rate = guess
    for _ in range(max_iter):
        f = npv(rate, cashflows)
        # dérivée numérique
        d = (npv(rate + 1e-6, cashflows) - f) / 1e-6
        if abs(d) < 1e-12:
            break
        new = rate - f / d
        if abs(new - rate) < tol:
            return new
        rate = new
    # fallback : bissection sur [-0.99, 10]
    lo, hi = -0.99, 10.0
    flo = npv(lo, cashflows)
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = npv(mid, cashflows)
        if abs(fm) < tol:
            return mid
        if (flo < 0) == (fm < 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return rate


# ===========================================================================
# 2. OBLIGATIONS
# ===========================================================================
def bond_price(face, coupon_rate, ytm, years, freq=2):
    """Prix d'une obligation à coupons. freq = paiements/an."""
    n = int(years * freq)
    c = face * coupon_rate / freq
    r = ytm / freq
    price = sum(c / ((1 + r) ** t) for t in range(1, n + 1))
    price += face / ((1 + r) ** n)
    return price


def bond_duration(face, coupon_rate, ytm, years, freq=2):
    """Duration de Macaulay (en années)."""
    n = int(years * freq)
    c = face * coupon_rate / freq
    r = ytm / freq
    price = bond_price(face, coupon_rate, ytm, years, freq)
    weighted = 0.0
    for t in range(1, n + 1):
        cf = c + (face if t == n else 0)
        pv = cf / ((1 + r) ** t)
        weighted += (t / freq) * pv
    return weighted / price


def bond_modified_duration(face, coupon_rate, ytm, years, freq=2):
    """Duration modifiée = sensibilité du prix au taux."""
    mac = bond_duration(face, coupon_rate, ytm, years, freq)
    return mac / (1 + ytm / freq)


# ===========================================================================
# 3. DCF / VALORISATION D'ENTREPRISE
# ===========================================================================
def wacc(equity, debt, cost_equity, cost_debt, tax_rate):
    """Coût moyen pondéré du capital."""
    v = equity + debt
    return (equity / v) * cost_equity + (debt / v) * cost_debt * (1 - tax_rate)


def dcf_enterprise_value(fcf_list, discount_rate, terminal_growth):
    """
    Valeur d'entreprise par DCF.
    fcf_list : free cash flows projetés (années 1..N).
    Valeur terminale par Gordon Growth sur la dernière FCF.
    """
    pv_explicit = sum(fcf / ((1 + discount_rate) ** (t + 1))
                      for t, fcf in enumerate(fcf_list))
    last = fcf_list[-1] * (1 + terminal_growth)
    terminal = last / (discount_rate - terminal_growth)
    pv_terminal = terminal / ((1 + discount_rate) ** len(fcf_list))
    return pv_explicit + pv_terminal


# ===========================================================================
# 4. OPTIONS — BLACK-SCHOLES
# ===========================================================================
def _norm_cdf(x):
    if _HAS_SCIPY:
        return float(norm.cdf(x))
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def black_scholes(S, K, T, r, sigma, option="call", q=0.0):
    """
    Prix Black-Scholes-Merton.
    S spot, K strike, T maturité (ans), r taux sans risque,
    sigma volatilité, q dividende continu.
    """
    if T <= 0 or sigma <= 0:
        intrinsic = max(0.0, (S - K) if option == "call" else (K - S))
        return intrinsic
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option == "call":
        return S * math.exp(-q * T) * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * _norm_cdf(-d2) - S * math.exp(-q * T) * _norm_cdf(-d1)


def bs_greeks(S, K, T, r, sigma, option="call", q=0.0):
    """Greeks principaux : delta, gamma, vega, theta, rho."""
    if T <= 0 or sigma <= 0:
        return {"delta": 0, "gamma": 0, "vega": 0, "theta": 0, "rho": 0}
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    pdf = math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi)
    if option == "call":
        delta = math.exp(-q * T) * _norm_cdf(d1)
        theta = (-S * pdf * sigma * math.exp(-q * T) / (2 * math.sqrt(T))
                 - r * K * math.exp(-r * T) * _norm_cdf(d2)
                 + q * S * math.exp(-q * T) * _norm_cdf(d1))
        rho = K * T * math.exp(-r * T) * _norm_cdf(d2)
    else:
        delta = -math.exp(-q * T) * _norm_cdf(-d1)
        theta = (-S * pdf * sigma * math.exp(-q * T) / (2 * math.sqrt(T))
                 + r * K * math.exp(-r * T) * _norm_cdf(-d2)
                 - q * S * math.exp(-q * T) * _norm_cdf(-d1))
        rho = -K * T * math.exp(-r * T) * _norm_cdf(-d2)
    gamma = math.exp(-q * T) * pdf / (S * sigma * math.sqrt(T))
    vega = S * math.exp(-q * T) * pdf * math.sqrt(T)
    return {"delta": delta, "gamma": gamma, "vega": vega / 100,
            "theta": theta / 365, "rho": rho / 100}


# ===========================================================================
# 5. PORTEFEUILLE — MARKOWITZ / EFFICIENT FRONTIER
# ===========================================================================
def portfolio_return(weights, mean_returns):
    return float(np.dot(weights, mean_returns))


def portfolio_volatility(weights, cov_matrix):
    return float(np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))))


def sharpe_ratio(weights, mean_returns, cov_matrix, rf=0.02):
    ret = portfolio_return(weights, mean_returns)
    vol = portfolio_volatility(weights, cov_matrix)
    return (ret - rf) / vol if vol > 0 else 0.0


def min_variance_portfolio(mean_returns, cov_matrix):
    """Portefeuille à variance minimale (poids sommant à 1, long-only)."""
    n = len(mean_returns)
    if not _HAS_SCIPY:
        w = np.ones(n) / n
        return w
    cons = ({"type": "eq", "fun": lambda w: np.sum(w) - 1},)
    bounds = tuple((0, 1) for _ in range(n))
    res = minimize(lambda w: portfolio_volatility(w, cov_matrix),
                   np.ones(n) / n, method="SLSQP", bounds=bounds, constraints=cons)
    return res.x


def max_sharpe_portfolio(mean_returns, cov_matrix, rf=0.02):
    """Portefeuille tangent (Sharpe max)."""
    n = len(mean_returns)
    if not _HAS_SCIPY:
        return np.ones(n) / n
    cons = ({"type": "eq", "fun": lambda w: np.sum(w) - 1},)
    bounds = tuple((0, 1) for _ in range(n))
    res = minimize(lambda w: -sharpe_ratio(w, mean_returns, cov_matrix, rf),
                   np.ones(n) / n, method="SLSQP", bounds=bounds, constraints=cons)
    return res.x


def efficient_frontier(mean_returns, cov_matrix, n_points=40):
    """
    Calcule la frontière efficiente.
    Retourne (vols, rets, weights_list) le long de la frontière.
    """
    mean_returns = np.asarray(mean_returns, dtype=float)
    n = len(mean_returns)
    targets = np.linspace(mean_returns.min(), mean_returns.max(), n_points)
    vols, rets, ws = [], [], []
    for target in targets:
        if _HAS_SCIPY:
            cons = (
                {"type": "eq", "fun": lambda w: np.sum(w) - 1},
                {"type": "eq", "fun": lambda w, t=target: portfolio_return(w, mean_returns) - t},
            )
            bounds = tuple((0, 1) for _ in range(n))
            res = minimize(lambda w: portfolio_volatility(w, cov_matrix),
                           np.ones(n) / n, method="SLSQP",
                           bounds=bounds, constraints=cons)
            if res.success:
                vols.append(portfolio_volatility(res.x, cov_matrix))
                rets.append(target)
                ws.append(res.x)
        else:
            w = np.ones(n) / n
            vols.append(portfolio_volatility(w, cov_matrix))
            rets.append(portfolio_return(w, mean_returns))
            ws.append(w)
    return np.array(vols), np.array(rets), ws


# ===========================================================================
# 6. RISQUE — VaR / CVaR
# ===========================================================================
def value_at_risk(returns, confidence=0.95):
    """VaR historique (perte au quantile). returns = série de rendements."""
    returns = np.asarray(returns, dtype=float)
    return -np.percentile(returns, (1 - confidence) * 100)


def conditional_var(returns, confidence=0.95):
    """CVaR / Expected Shortfall : perte moyenne au-delà de la VaR."""
    returns = np.asarray(returns, dtype=float)
    var = value_at_risk(returns, confidence)
    tail = returns[returns <= -var]
    return -tail.mean() if len(tail) else var


def parametric_var(value, mean, sigma, confidence=0.95, horizon=1):
    """VaR paramétrique (gaussienne) sur un horizon donné."""
    z = _inv_norm(confidence)
    return value * (z * sigma * math.sqrt(horizon) - mean * horizon)


def _inv_norm(p):
    if _HAS_SCIPY:
        return float(norm.ppf(p))
    # approximation de Acklam
    a = [-39.6968302866538, 220.946098424521, -275.928510446969,
         138.357751867269, -30.6647980661472, 2.50662827745924]
    b = [-54.4760987982241, 161.585836858041, -155.698979859887,
         66.8013118877197, -13.2806815528857]
    if p < 0.5:
        q = math.sqrt(-2 * math.log(p))
    else:
        q = math.sqrt(-2 * math.log(1 - p))
    num = ((((a[0]*q+a[1])*q+a[2])*q+a[3])*q+a[4])*q+a[5]
    den = (((b[0]*q+b[1])*q+b[2])*q+b[3])*q+b[4]
    val = num / (den + 1) if den != -1 else 0
    return val if p >= 0.5 else -val


# ===========================================================================
# 7. M&A / LBO
# ===========================================================================
def accretion_dilution(acq_eps, acq_shares, target_net_income,
                       new_shares_issued, synergies=0.0):
    """
    Analyse relutif/dilutif d'une acquisition payée en actions.
    Retourne (eps_pro_forma, variation_pct).
    """
    acq_net_income = acq_eps * acq_shares
    combined_ni = acq_net_income + target_net_income + synergies
    combined_shares = acq_shares + new_shares_issued
    pf_eps = combined_ni / combined_shares
    delta = (pf_eps - acq_eps) / acq_eps * 100
    return pf_eps, delta


def lbo_returns(entry_ev, entry_ebitda, debt_pct, exit_multiple,
                years, ebitda_cagr, debt_paydown_pct=0.5, interest_rate=0.07):
    """
    Modèle LBO simplifié. Retourne (MOIC, IRR, exit_equity).
    """
    debt = entry_ev * debt_pct
    equity_in = entry_ev - debt
    exit_ebitda = entry_ebitda * ((1 + ebitda_cagr) ** years)
    exit_ev = exit_ebitda * exit_multiple
    remaining_debt = debt * (1 - debt_paydown_pct)
    exit_equity = exit_ev - remaining_debt
    moic = exit_equity / equity_in if equity_in > 0 else 0
    irr_val = (moic ** (1 / years) - 1) if moic > 0 and years > 0 else -1
    return moic, irr_val, exit_equity


# ===========================================================================
# 8. RATIOS FINANCIERS
# ===========================================================================
def financial_ratios(financials):
    """
    Calcule les ratios clés depuis un dict de données financières.
    Champs attendus (optionnels) : revenue, net_income, total_assets,
    total_equity, total_debt, current_assets, current_liabilities,
    ebit, interest_expense, cogs, inventory.
    """
    f = financials
    r = {}
    def safe(a, b):
        return a / b if b else float("nan")
    if "net_income" in f and "total_equity" in f:
        r["ROE"] = safe(f["net_income"], f["total_equity"])
    if "net_income" in f and "total_assets" in f:
        r["ROA"] = safe(f["net_income"], f["total_assets"])
    if "net_income" in f and "revenue" in f:
        r["Net Margin"] = safe(f["net_income"], f["revenue"])
    if "total_debt" in f and "total_equity" in f:
        r["D/E"] = safe(f["total_debt"], f["total_equity"])
    if "current_assets" in f and "current_liabilities" in f:
        r["Current Ratio"] = safe(f["current_assets"], f["current_liabilities"])
    if "ebit" in f and "interest_expense" in f:
        r["Interest Coverage"] = safe(f["ebit"], f["interest_expense"])
    if "cogs" in f and "inventory" in f:
        r["Inventory Turnover"] = safe(f["cogs"], f["inventory"])
    return r


# ===========================================================================
# 9. VALORISATION ACTIONS (Gordon) & OBLIGATIONS (convexité)
# ===========================================================================
def gordon_growth(d1, cost_equity, growth):
    """Modèle de Gordon : P0 = D1 / (re - g). Exige re > g."""
    if cost_equity <= growth:
        raise ValueError("cost_equity doit être > growth pour Gordon")
    return d1 / (cost_equity - growth)


def terminal_value(last_fcf, discount_rate, growth):
    """Valeur terminale (Gordon) à partir du dernier FCF : FCF·(1+g)/(r-g)."""
    if discount_rate <= growth:
        raise ValueError("discount_rate doit être > growth")
    return last_fcf * (1 + growth) / (discount_rate - growth)


def bond_convexity(face, coupon_rate, ytm, years, freq=2):
    """Convexité d'une obligation à coupons (annualisée)."""
    n = int(years * freq)
    c = face * coupon_rate / freq
    r = ytm / freq
    price = bond_price(face, coupon_rate, ytm, years, freq)
    s = 0.0
    for t in range(1, n + 1):
        cf = c + (face if t == n else 0)
        s += cf * t * (t + 1) / ((1 + r) ** (t + 2))
    return s / (price * freq ** 2)


# ===========================================================================
# 10. DÉRIVÉS : prix forward (cost of carry) & roll yield
# ===========================================================================
def forward_price(spot, rate, T, income_yield=0.0, storage_yield=0.0):
    """Prix forward par coût de portage (discret) :
    F = S·(1 + r - income + storage)^T."""
    return spot * ((1 + rate - income_yield + storage_yield) ** T)


def roll_yield(near_price, far_price):
    """Roll yield d'une courbe de futures. > 0 = backwardation (near > far),
    < 0 = contango (near < far)."""
    if far_price == 0:
        return 0.0
    return (near_price - far_price) / far_price


# ===========================================================================
# 11. MACRO : taux réel (Fisher)
# ===========================================================================
def real_rate(nominal_rate, inflation):
    """Taux réel exact (Fisher) : (1 + nominal)/(1 + inflation) - 1."""
    return (1 + nominal_rate) / (1 + inflation) - 1


# ===========================================================================
# 12. CRÉDIT : perte attendue
# ===========================================================================
def expected_loss(pd, lgd, ead):
    """Expected Loss = PD × LGD × EAD."""
    return pd * lgd * ead


# ===========================================================================
# 13. PERFORMANCE AVANCÉE : Treynor, IR, drawdown, Sortino, Calmar, TWR
# ===========================================================================
def treynor_ratio(portfolio_return, beta, rf=0.02):
    """Rendement excédentaire par unité de risque de marché (bêta)."""
    return (portfolio_return - rf) / beta if beta else 0.0


def tracking_error(portfolio_returns, benchmark_returns):
    """Écart-type de la différence de rendement vs benchmark (active return)."""
    diff = np.asarray(portfolio_returns, float) - np.asarray(benchmark_returns, float)
    return float(np.std(diff, ddof=1)) if len(diff) > 1 else 0.0


def information_ratio(portfolio_returns, benchmark_returns):
    """Surperformance moyenne rapportée à la tracking error."""
    diff = np.asarray(portfolio_returns, float) - np.asarray(benchmark_returns, float)
    te = float(np.std(diff, ddof=1)) if len(diff) > 1 else 0.0
    return float(np.mean(diff)) / te if te > 0 else 0.0


def max_drawdown(equity_curve):
    """Drawdown maximal (magnitude positive) d'une courbe de valeur nette."""
    arr = np.asarray(equity_curve, float)
    if len(arr) < 2:
        return 0.0
    peak = np.maximum.accumulate(arr)
    dd = (arr - peak) / peak
    return float(-dd.min())


def downside_deviation(returns, target=0.0):
    """Écart-type des seuls rendements sous un seuil cible (risque baissier)."""
    arr = np.asarray(returns, float)
    shortfall = np.minimum(0.0, arr - target)
    return float(np.sqrt(np.mean(shortfall ** 2)))


def sortino_ratio(returns, target=0.0, rf=0.0):
    """Comme le Sharpe mais avec la downside deviation au dénominateur."""
    arr = np.asarray(returns, float)
    dd = downside_deviation(arr, target)
    return (float(np.mean(arr)) - rf) / dd if dd > 0 else 0.0


def calmar_ratio(annual_return, max_dd):
    """Rendement annuel rapporté au max drawdown."""
    return annual_return / max_dd if max_dd > 0 else 0.0


def time_weighted_return(period_returns):
    """TWR : rendement composé des sous-périodes, neutralise les flux."""
    prod = 1.0
    for r in period_returns:
        prod *= (1 + r)
    return prod - 1


# ===========================================================================
# 14. FINANCE DE PROJET & BANQUE (ratios de couverture / capital)
# ===========================================================================
def dscr(cash_flow_available, debt_service):
    """Debt Service Coverage Ratio = cash flow disponible / service de la dette."""
    return cash_flow_available / debt_service if debt_service else float("inf")


def cet1_ratio(cet1_capital, rwa):
    """Ratio CET1 = fonds propres durs / actifs pondérés du risque."""
    return cet1_capital / rwa if rwa else float("inf")
