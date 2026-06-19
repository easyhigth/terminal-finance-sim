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

RATE_VOL_WEEKLY = 0.0010      # écart-type hebdo du taux (≈ 16 bps/an annualisé √52)

# Stress tests appliqués au portefeuille RÉEL : (choc F_monde actions, Δtaux),
# avec en option un choc pétrole (% spot, sur les positions commodities Énergie)
# et des chocs additionnels par secteur/région (sur les positions actions
# concernées, en plus du choc monde commun). Les 4 premiers scénarios sont les
# scénarios génériques historiques (krach 2008-like, choc de taux, choc de vol,
# récession) ; les 5 suivants couvrent les scénarios hypothétiques nommés
# attendus par le module de stress test (inflation, Europe, énergie, crédit,
# liquidité).
STRESS = {
    "Krach actions":      {"world": -0.12, "dy": -0.004},
    "Choc de taux +200bps": {"world": -0.03, "dy": 0.020},
    "Choc de volatilité": {"world": -0.07, "dy": 0.0},
    "Récession":          {"world": -0.09, "dy": -0.010},
    "Choc d'inflation":   {"world": -0.04, "dy": 0.030, "oil": 0.15},
    "Crise Europe":       {"world": -0.05, "dy": 0.010, "region_extra": {"Europe": -0.10}},
    "Choc énergie":       {"world": -0.03, "dy": 0.005, "oil": 0.35,
                            "sector_extra": {"Energie": 0.08}},
    "Crise de crédit":    {"world": -0.08, "dy": 0.015},
    "Crise de liquidité": {"world": -0.06, "dy": 0.008},
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
    sector_extra = sh.get("sector_extra", {})
    region_extra = sh.get("region_extra", {})
    equity_pnl = 0.0
    for i, v in eq:
        shock = sh["world"]
        if sector_extra:
            shock += sector_extra.get(market.sectors[market.sec_id[i]], 0.0)
        if region_extra:
            shock += region_extra.get(market.regions[market.reg_id[i]], 0.0)
        equity_pnl += v * market.beta[i] * shock
    equity_pnl /= 1e6
    bond_pnl = sum(-(v * d) * sh["dy"] for v, d in bonds) / 1e6
    oil_pnl = 0.0
    oil_shock = sh.get("oil")
    if oil_shock:
        from core import commodities as commodities_mod
        for cid, pos in getattr(player, "commodities", {}).items():
            c = commodities_mod._BY_ID.get(cid)
            if c and c[6] == "Énergie":
                val = commodities_mod.futures_price(market, cid, 1) * commodities_mod.MULTIPLIER * pos["qty"]
                oil_pnl += val * oil_shock
    oil_pnl /= 1e6
    return {"total": equity_pnl + bond_pnl + oil_pnl, "equity": equity_pnl,
            "bond": bond_pnl, "oil": oil_pnl}


def _fx_pnl(player, shock_pct):
    """P&L (en M) d'un choc `shock_pct` (fraction signée) appliqué à toutes
    les paires FX détenues (spot + forward), notionnel × choc × sens."""
    total = 0.0
    for pos in (getattr(player, "fx_positions", None) or []):
        sign = 1.0 if pos["direction"] == "long" else -1.0
        total += pos["notional"] * shock_pct * sign
    for pos in (getattr(player, "fx_forwards", None) or []):
        sign = 1.0 if pos["direction"] == "long" else -1.0
        total += pos["notional"] * shock_pct * sign
    return total / 1e6


def sensitivity(player, market):
    """Analyse de sensibilité facteur par facteur du book réel (en M) : taux,
    spread de crédit, FX, pétrole, actions, volatilité. Chaque valeur est le
    P&L pour un choc unitaire calibré par facteur (utile pour comparer leur
    poids relatif, pas pour les sommer — les chocs ne sont pas simultanés)."""
    bonds = _bond_positions(player, market)
    dv01 = sum(v * d * 0.01 for v, d in bonds) / 1e6 if bonds else 0.0  # M par +100bps
    rate_sens = -dv01
    credit_sens = -dv01 * 0.5     # même mécanique de duration, choc spread +100bps
    fx_sens = _fx_pnl(player, -0.10)
    eq = _equity_positions(player, market)
    equity_sens = sum(v * market.beta[i] for i, v in eq) / 1e6 * -0.10
    from core import commodities as commodities_mod
    oil_value = 0.0
    for cid, pos in (getattr(player, "commodities", None) or {}).items():
        c = commodities_mod._BY_ID.get(cid)
        if c and c[6] == "Énergie":
            oil_value += commodities_mod.futures_price(market, cid, 1) * commodities_mod.MULTIPLIER * pos["qty"]
    oil_sens = oil_value / 1e6 * -0.10
    vol_sens = stress(player, market, "Choc de volatilité")["total"]
    return {
        "Taux (+100bps)": rate_sens,
        "Spread de crédit (+100bps)": credit_sens,
        "FX (-10%)": fx_sens,
        "Pétrole (-10%)": oil_sens,
        "Actions (-10% monde)": equity_sens,
        "Volatilité": vol_sens,
    }


def reverse_stress(player, market, target_loss_pct, scenario="Krach actions"):
    """Reverse stress test (item 22) : cherche le facteur d'échelle `k` à
    appliquer au `scenario` donné pour atteindre une perte de
    `target_loss_pct` % de la valeur nette. Le P&L de stress étant LINÉAIRE
    dans l'amplitude du choc (cf. stress()), la résolution est en forme close
    plutôt qu'itérative : k = perte_visée / perte_à_choc_unitaire."""
    from core import portfolio as pf
    net_worth = pf.net_worth(player, market)
    if net_worth <= 0:
        return {"ok": False, "reason": "net_worth"}
    base = stress(player, market, scenario)
    base_loss = -base["total"] * 1e6  # valeur monétaire, positif = perte
    if abs(base_loss) < 1e-9:
        return {"ok": False, "reason": "no_exposure"}
    target_loss = abs(target_loss_pct) / 100.0 * net_worth
    k = target_loss / base_loss
    shocked = {key: (val * k if isinstance(val, (int, float)) else
                      {kk: vv * k for kk, vv in val.items()})
               for key, val in STRESS[scenario].items()}
    return {"ok": True, "scenario": scenario, "scale": k,
            "base_loss_pct": base_loss / net_worth * 100.0,
            "target_loss_pct": abs(target_loss_pct), "shocked": shocked}


def net_worth_drawdown(player):
    """Max drawdown de la valeur nette d'après l'historique (cash_history)."""
    hist = getattr(player, "cash_history", [])
    return finmath.max_drawdown(hist) if len(hist) >= 2 else 0.0
