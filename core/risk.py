"""
risk.py — Risque du PORTEFEUILLE RÉEL (logique pure, sans pygame).

Au lieu d'un bac à sable d'expositions, on mesure le risque sur les positions
effectives du joueur, avec le PROPRE modèle à facteurs du marché (cohérence
totale avec le moteur de jeu) :
  rendement_i = beta_i·F_monde + b_secteur_i·F_secteur + b_region_i·F_region + sigma_i·bruit
Le P&L action = Σ valeur_i · rendement_i. On y ajoute le risque de taux des
obligations (P&L ≈ −valeur·duration·Δy). On en tire VaR/CVaR (historique simulée
et paramétrique) et des stress tests appliqués au book réel.
"""
import numpy as np

from core import finmath
from core import market as market_mod
from core import portfolio as pf

RATE_VOL_WEEKLY = 0.0010      # écart-type hebdo du taux (≈ 16 bps/an annualisé √52)

# Stress tests appliqués au portefeuille RÉEL : (choc F_monde actions, Δtaux).
STRESS = {
    "Krach actions":      {"world": -0.12, "dy": -0.004},
    "Choc de taux +200bps": {"world": -0.03, "dy": 0.020},
    "Choc de volatilité": {"world": -0.07, "dy": 0.0},
    "Récession":          {"world": -0.09, "dy": -0.010},
}


def _equity_positions(player, market):
    """Liste (index, valeur signée) des positions actions."""
    out = []
    for tk, pos in player.portfolio.items():
        i = market.ticker_idx.get(tk)
        price = market.price_of(tk)
        if i is None or price is None:
            continue
        out.append((i, price * pos["shares"]))
    return out


def _bond_positions(player, market):
    """Liste (valeur, duration modifiée) des positions obligataires."""
    out = []
    if not getattr(player, "bonds", None):
        return out
    from core import bonds as bonds_mod
    for bid, pos in player.bonds.items():
        q = bonds_mod.quote(market, bid)
        if q:
            out.append((q["price"] * pos["qty"], q["mod_duration"]))
    return out


def exposures(player, market):
    """Expositions agrégées du book réel (en M de devise)."""
    eq = _equity_positions(player, market)
    bonds = _bond_positions(player, market)
    equities_net = sum(v for _, v in eq) / 1e6
    bond_value = sum(v for v, _ in bonds) / 1e6
    rates_dv01 = sum(v * d * 0.01 for v, d in bonds) / 1e6   # M par +100 bps
    return {"Actions (net)": equities_net, "Obligations": bond_value,
            "Taux (DV01/100bps)": rates_dv01}


def simulate(player, market, confidence=0.95, n=20000, seed=7):
    """Simule la distribution de P&L 1 pas du portefeuille réel. Renvoie un dict
    {pnl (array, en M), var, cvar, param_var, sigma} — pertes en valeurs positives."""
    eq = _equity_positions(player, market)
    bonds = _bond_positions(player, market)
    rng = np.random.default_rng(seed)

    pnl = np.zeros(n)
    if eq:
        idx = np.array([i for i, _ in eq])
        val = np.array([v for _, v in eq])
        beta = market.beta[idx]
        bsec = market.b_sector[idx]
        breg = market.b_region[idx]
        sig = market.sigma[idx]
        sec_id = market.sec_id[idx]
        reg_id = market.reg_id[idx]
        n_sec = len(market.sectors)
        n_reg = len(market.regions)
        Fw = rng.normal(0.0, market_mod.VOL_WORLD, n)
        Fs = rng.normal(0.0, market_mod.VOL_SECTOR, (n, n_sec))
        Fr = rng.normal(0.0, market_mod.VOL_REGION, (n, n_reg))
        eps = rng.normal(0.0, 1.0, (n, len(idx)))
        ret = (beta * Fw[:, None]
               + bsec * Fs[:, sec_id]
               + breg * Fr[:, reg_id]
               + sig * eps)                       # (n, positions)
        pnl += (ret * val).sum(axis=1)
    if bonds:
        bval = np.array([v for v, _ in bonds])
        bdur = np.array([d for _, d in bonds])
        dy = rng.normal(0.0, RATE_VOL_WEEKLY, n)
        pnl += (-(bval * bdur)[None, :] * dy[:, None]).sum(axis=1)

    pnl_m = pnl / 1e6
    var = finmath.value_at_risk(pnl_m, confidence)
    cvar = finmath.conditional_var(pnl_m, confidence)
    sigma = float(pnl_m.std())
    param = finmath.parametric_var(1.0, 0.0, sigma, confidence)
    return {"pnl": pnl_m, "var": var, "cvar": cvar, "param_var": param, "sigma": sigma}


def stress(player, market, scenario):
    """Perte instantanée (en M) d'un scénario de stress sur le book réel."""
    sh = STRESS[scenario]
    eq = _equity_positions(player, market)
    bonds = _bond_positions(player, market)
    equity_pnl = sum(v * market.beta[i] * sh["world"] for i, v in eq) / 1e6
    bond_pnl = sum(-(v * d) * sh["dy"] for v, d in bonds) / 1e6
    return {"total": equity_pnl + bond_pnl, "equity": equity_pnl, "bond": bond_pnl}


def net_worth_drawdown(player):
    """Max drawdown de la valeur nette d'après l'historique (cash_history)."""
    hist = getattr(player, "cash_history", [])
    return finmath.max_drawdown(hist) if len(hist) >= 2 else 0.0
