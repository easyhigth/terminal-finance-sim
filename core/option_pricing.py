"""
option_pricing.py — MODÈLES DE PRICING D'OPTIONS (logique pure, déterministe).

Le desk Options du bureau (apps/app_greeks.py, onglet MODÈLES) price la MÊME
option sous plusieurs modèles classiques et montre où — et pourquoi — leurs
prix divergent. Chaque modèle est réellement implémenté (pas des chiffres
décoratifs) :

- **Black-Scholes-Merton** : formule fermée (core.finmath.black_scholes) —
  la référence, options européennes, vol constante.
- **Arbre binomial (Cox-Ross-Rubinstein)** : u = e^{σ√Δt}, d = 1/u,
  probabilité risque-neutre q = (e^{rΔt} − d)/(u − d), induction arrière.
  En mode AMÉRICAIN, on compare à chaque nœud la valeur de continuation à
  la valeur d'exercice immédiat — la différence avec l'européen est la
  PRIME D'EXERCICE ANTICIPÉ (nulle pour un call sans dividende, positive
  pour un put : résultat de cours de M2).
- **Monte-Carlo** : S_T = S·exp((r − σ²/2)T + σ√T·Z), payoff actualisé,
  variables ANTITHÉTIQUES (Z et −Z) pour réduire la variance, graine fixe
  (déterministe, comme tout aléa du jeu) ; renvoie aussi l'erreur-type —
  on VOIT la convergence vers Black-Scholes.
- **Merton à sauts (1976)** : série fermée Σ e^{−λ'T}(λ'T)^k/k! · BS_k où
  chaque terme re-price BS avec une vol et un taux ajustés du k-ième saut.
  Les sauts sont calibrés sur le régime de crise du jeu — un marché qui
  peut sauter vaut une prime sur les ailes (smile).
- **Vol implicite** : inversion de Black-Scholes par bissection — le
  chiffre que cotent les vrais marchés.

Convention : tous les prix par UNITÉ de sous-jacent, mêmes entrées
(S, K, T, r, σ) partout.
"""
import math

import numpy as np

from core import finmath as fm

# Paramètres de sauts « crise » (calibrage jeu : ~2 crises/an, saut moyen
# −8 %, dispersion 10 % — cohérent avec les chocs de core/market.py)
JUMP_INTENSITY = 2.0       # λ : sauts par an
JUMP_MEAN = -0.08          # moyenne du log-saut
JUMP_VOL = 0.10            # écart-type du log-saut

MC_PATHS = 20_000
MC_SEED = 12345


def bs_price(S, K, T, r, sigma, option="call"):
    """Black-Scholes-Merton (référence, formule fermée)."""
    return fm.black_scholes(S, K, T, r, sigma, option=option)


def binomial_price(S, K, T, r, sigma, option="call", steps=200, american=False):
    """Arbre binomial Cox-Ross-Rubinstein, induction arrière.
    `american=True` autorise l'exercice anticipé à chaque nœud."""
    if T <= 0:
        return max(0.0, (S - K) if option == "call" else (K - S))
    steps = max(1, int(steps))
    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    disc = math.exp(-r * dt)
    q = (math.exp(r * dt) - d) / (u - d)
    q = min(1.0, max(0.0, q))
    # prix terminaux S·u^j·d^(n-j), j = 0..n
    j = np.arange(steps + 1)
    ST = S * (u ** j) * (d ** (steps - j))
    if option == "call":
        vals = np.maximum(ST - K, 0.0)
    else:
        vals = np.maximum(K - ST, 0.0)
    for step in range(steps - 1, -1, -1):
        vals = disc * (q * vals[1:] + (1.0 - q) * vals[:-1])
        if american:
            jj = np.arange(step + 1)
            Snode = S * (u ** jj) * (d ** (step - jj))
            exercise = (Snode - K) if option == "call" else (K - Snode)
            vals = np.maximum(vals, np.maximum(exercise, 0.0))
    return float(vals[0])


def monte_carlo_price(S, K, T, r, sigma, option="call",
                      n=MC_PATHS, seed=MC_SEED):
    """Monte-Carlo GBM avec variables antithétiques. Renvoie
    {"price", "stderr"} — l'erreur-type montre la convergence vers BS."""
    if T <= 0:
        v = max(0.0, (S - K) if option == "call" else (K - S))
        return {"price": v, "stderr": 0.0}
    rng = np.random.default_rng(seed)
    half = max(1, n // 2)
    z = rng.standard_normal(half)
    z = np.concatenate([z, -z])                       # antithétiques
    ST = S * np.exp((r - 0.5 * sigma ** 2) * T + sigma * math.sqrt(T) * z)
    payoff = np.maximum(ST - K, 0.0) if option == "call" else np.maximum(K - ST, 0.0)
    disc = math.exp(-r * T)
    price = disc * float(payoff.mean())
    stderr = disc * float(payoff.std(ddof=1)) / math.sqrt(len(payoff))
    return {"price": price, "stderr": stderr}


def merton_jump_price(S, K, T, r, sigma, option="call",
                      lam=JUMP_INTENSITY, mu_j=JUMP_MEAN, sigma_j=JUMP_VOL,
                      n_terms=25):
    """Diffusion à sauts de Merton (1976), série fermée : conditionnellement
    à k sauts, le prix est un Black-Scholes à vol et taux ajustés ; on somme
    pondéré par la loi de Poisson. Les ailes (OTM) valent PLUS que sous BS —
    c'est le smile de volatilité."""
    if T <= 0:
        return max(0.0, (S - K) if option == "call" else (K - S))
    kappa = math.exp(mu_j + 0.5 * sigma_j ** 2) - 1.0     # E[saut] − 1
    lam_p = lam * (1.0 + kappa)
    total = 0.0
    for k in range(n_terms):
        weight = math.exp(-lam_p * T) * (lam_p * T) ** k / math.factorial(k)
        if weight < 1e-12 and k > lam_p * T:
            break
        sigma_k = math.sqrt(sigma ** 2 + k * sigma_j ** 2 / T)
        r_k = r - lam * kappa + k * (mu_j + 0.5 * sigma_j ** 2) / T
        total += weight * fm.black_scholes(S, K, T, r_k, sigma_k, option=option)
    return total


def implied_vol(price, S, K, T, r, option="call", lo=1e-4, hi=4.0, tol=1e-6):
    """Volatilité implicite par bissection (inversion de Black-Scholes).
    None si le prix est hors des bornes d'arbitrage."""
    if T <= 0 or price <= 0:
        return None
    if fm.black_scholes(S, K, T, r, lo, option=option) > price:
        return None
    if fm.black_scholes(S, K, T, r, hi, option=option) < price:
        return None
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        v = fm.black_scholes(S, K, T, r, mid, option=option)
        if abs(v - price) < tol:
            return mid
        if v < price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


SURFACE_STRIKES = (0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20)
SURFACE_MATURITIES = (0.25, 0.5, 1.0)


def vol_surface(S, r, sigma, strikes_pct=SURFACE_STRIKES,
                maturities=SURFACE_MATURITIES,
                lam=JUMP_INTENSITY, mu_j=JUMP_MEAN, sigma_j=JUMP_VOL):
    """SURFACE DE VOLATILITÉ IMPLICITE : pour chaque (strike, maturité), on
    price l'option sous Merton à sauts (le « vrai » modèle avec crises) puis
    on INVERSE Black-Scholes — la vol implicite obtenue n'est PAS plate :
    c'est le smile/skew (ailes plus chères, surtout le put OTM avec des
    sauts négatifs), qui s'atténue avec la maturité (term structure).
    Renvoie {strikes_pct, maturities, iv: grille [maturité][strike] en
    décimal (None si inversion impossible)}."""
    grid = []
    for T in maturities:
        row = []
        for k in strikes_pct:
            K = S * k
            # put pour les strikes bas, call pour les hauts (OTM des deux
            # côtés : plus liquide et mieux conditionné pour l'inversion)
            option = "put" if k <= 1.0 else "call"
            price = merton_jump_price(S, K, T, r, sigma, option,
                                      lam=lam, mu_j=mu_j, sigma_j=sigma_j)
            row.append(implied_vol(price, S, K, T, r, option))
        grid.append(row)
    return {"strikes_pct": list(strikes_pct), "maturities": list(maturities),
            "iv": grid}


def compare_models(S, K, T, r, sigma, option="call"):
    """Price la même option sous chaque modèle. Renvoie une liste ordonnée de
    lignes {id, label, price, note} + extras (stderr MC, prime d'exercice
    anticipé, vol implicite du prix à sauts = lecture du smile)."""
    bs = bs_price(S, K, T, r, sigma, option)
    bin_eu = binomial_price(S, K, T, r, sigma, option, american=False)
    bin_us = binomial_price(S, K, T, r, sigma, option, american=True)
    mc = monte_carlo_price(S, K, T, r, sigma, option)
    jump = merton_jump_price(S, K, T, r, sigma, option)
    early = max(0.0, bin_us - bin_eu)
    iv_jump = implied_vol(jump, S, K, T, r, option)
    rows = [
        {"id": "bs", "label": "Black-Scholes-Merton", "price": bs,
         "note": "formule fermée — européen, vol constante"},
        {"id": "binom_eu", "label": "Binomial CRR (européen)", "price": bin_eu,
         "note": "arbre 200 pas — converge vers BS"},
        {"id": "binom_us", "label": "Binomial CRR (américain)", "price": bin_us,
         "note": f"prime d'exercice anticipé {early:.2f}"},
        {"id": "mc", "label": "Monte-Carlo (antithétique)", "price": mc["price"],
         "note": f"± {mc['stderr']:.2f} (erreur-type, 20 000 tirages)"},
        {"id": "jump", "label": "Merton à sauts (crises)", "price": jump,
         "note": (f"vol implicite {iv_jump * 100:.1f}% vs {sigma * 100:.1f}% — le smile"
                  if iv_jump else "prime de saut sur les ailes")},
    ]
    return {"rows": rows, "early_exercise": early, "mc_stderr": mc["stderr"],
            "iv_jump": iv_jump}
