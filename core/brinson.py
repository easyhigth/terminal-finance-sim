"""
brinson.py — Attribution Brinson et régression factorielle (logique pure).

Distinct de core/attribution.py (ventilation du P&L du DERNIER pas pour
l'écran Performance) : ici on juge la GESTION sur une fenêtre entière —
LA question du gérant, « suis-je bon ou chanceux ? » :

- **Brinson-Fachler** (`brinson`) : l'écart de performance vs le marché,
  décomposé par SECTEUR en effet d'ALLOCATION (avoir surpondéré les bons
  secteurs : (w_p − w_b)·(r_b,s − r_b)), effet de SÉLECTION (avoir choisi
  les bons titres DANS chaque secteur : w_b·(r_p,s − r_b,s)) et effet
  d'INTERACTION. La somme des trois retombe EXACTEMENT sur l'écart total
  (r_p − r_b) — invariant verrouillé par test. Le benchmark est le marché
  ENTIER pondéré par capitalisation (les 320 sociétés du roster).

- **Régression factorielle** (`factor_regression`) : le marché du jeu EST
  un modèle à facteurs (monde/secteur/région, cf. core/market.py) — on
  reconstruit les facteurs OBSERVABLES depuis la coupe transversale des
  rendements (facteur monde = rendement pondéré capi du marché ; facteur
  secteur = rendement du secteur − monde ; idem régions), puis on régresse
  les rendements du portefeuille dessus (moindres carrés). Sortie : bêtas
  par facteur, ALPHA annualisé (ce qui reste une fois les paris factoriels
  retirés) et R² (part du P&L expliquée par les facteurs — un « stock
  picker » à R² de 95 % ne fait en réalité que des paris sectoriels).

Convention : mêmes fenêtres que le reste des outils quantitatifs
(core/quant_tools.PERIOD_STEPS), poids du portefeuille = valeur longue
actuelle (approximation cohérente avec quant_tools).
"""
import numpy as np

from core import portfolio as pf
from core import quant_tools as QT
from core.market import STEPS_PER_YEAR

DEFAULT_LOOKBACK = 73


def _price_matrix(market, lookback):
    """Matrice (pas, sociétés) des clôtures des `lookback`+1 derniers pas."""
    snaps = list(market.price_hist_all)[-(lookback + 1):]
    if len(snaps) < 3:
        return None
    return np.asarray(snaps, dtype=float)


def _bench_weights(market):
    """Poids capi du marché entier (le benchmark)."""
    caps = np.array([market.metrics(c["ticker"])["mktcap"]
                     for c in market.companies], dtype=float)
    tot = caps.sum()
    return caps / tot if tot > 0 else np.full(len(caps), 1.0 / len(caps))


# ================================================================ Brinson
def brinson(player, market, lookback=DEFAULT_LOOKBACK):
    """Attribution Brinson-Fachler par secteur sur la fenêtre (une période,
    rendements cumulés). Renvoie None sans position action longue, sinon
    {rows: [{sector, w_p, w_b, r_p, r_b, allocation, selection,
    interaction}], totals, r_p, r_b, excess}."""
    held = {h["ticker"]: h["value"] for h in pf.holdings(player, market)
            if not h["short"]}
    if not held:
        return None
    P = _price_matrix(market, lookback)
    if P is None:
        return None
    with np.errstate(divide="ignore", invalid="ignore"):
        cum = P[-1] / P[0] - 1.0                     # rendement cumulé par société
    cum = np.nan_to_num(cum)
    w_b = _bench_weights(market)
    sec_id = market.sec_id
    idx_of = market.ticker_idx
    tot_p = sum(held.values())
    r_b = float((w_b * cum).sum())                   # rendement du benchmark
    r_p = sum(v / tot_p * cum[idx_of[tk]] for tk, v in held.items()
              if tk in idx_of)
    rows = []
    tot_alloc = tot_sel = tot_inter = 0.0
    for s, sector in enumerate(market.sectors):
        mask = sec_id == s
        wbs = float(w_b[mask].sum())
        rbs = float((w_b[mask] * cum[mask]).sum() / wbs) if wbs > 0 else 0.0
        p_vals = {tk: v for tk, v in held.items()
                  if tk in idx_of and sec_id[idx_of[tk]] == s}
        wps = sum(p_vals.values()) / tot_p
        if p_vals:
            vs = sum(p_vals.values())
            rps = sum(v / vs * cum[idx_of[tk]] for tk, v in p_vals.items())
        else:
            rps = rbs                                # pas de position → pas de sélection
        alloc = (wps - wbs) * (rbs - r_b)
        sel = wbs * (rps - rbs)
        inter = (wps - wbs) * (rps - rbs)
        tot_alloc += alloc
        tot_sel += sel
        tot_inter += inter
        if wps > 0.001 or wbs > 0.01:
            rows.append({"sector": sector, "w_p": wps, "w_b": wbs,
                         "r_p": rps, "r_b": rbs, "allocation": alloc,
                         "selection": sel, "interaction": inter})
    rows.sort(key=lambda x: abs(x["allocation"] + x["selection"]), reverse=True)
    return {"rows": rows, "r_p": r_p, "r_b": r_b, "excess": r_p - r_b,
            "totals": {"allocation": tot_alloc, "selection": tot_sel,
                       "interaction": tot_inter}}


# ================================================== régression factorielle
def factor_returns(market, lookback=DEFAULT_LOOKBACK):
    """Facteurs OBSERVABLES par pas, reconstruits de la coupe transversale :
    monde (rendement pondéré capi), secteurs et régions (rendement du groupe
    − monde). Renvoie (X (pas, k), labels) ou None si historique court."""
    P = _price_matrix(market, lookback)
    if P is None:
        return None
    with np.errstate(divide="ignore", invalid="ignore"):
        R = P[1:] / P[:-1] - 1.0                     # (pas, sociétés)
    R = np.nan_to_num(R)
    w = _bench_weights(market)
    world = R @ w                                    # facteur monde
    cols = [world]
    labels = ["Monde"]
    for gid, names, group in (("sec_id", market.sectors, "Secteur"),
                              ("reg_id", market.regions, "Région")):
        ids = getattr(market, gid)
        for g, name in enumerate(names):
            mask = ids == g
            wg = w[mask]
            tot = wg.sum()
            if tot <= 0:
                continue
            grp = R[:, mask] @ (wg / tot)
            cols.append(grp - world)
            labels.append(f"{group} : {name}")
    return np.column_stack(cols), labels


def factor_regression(player, market, lookback=DEFAULT_LOOKBACK):
    """Régresse les rendements du portefeuille sur les facteurs observables.
    Renvoie None sans historique, sinon {alpha_ann, r2, rows:
    [{label, beta}] triés par |beta| décroissant, n}."""
    rp, _tks = QT.portfolio_step_returns(player, market, lookback)
    fx = factor_returns(market, lookback)
    if fx is None or len(rp) < 12:
        return None
    X, labels = fx
    n = min(len(rp), X.shape[0])
    rp = np.asarray(rp[-n:], dtype=float)
    X = X[-n:]
    A = np.column_stack([np.ones(n), X])             # constante = alpha
    coef, *_ = np.linalg.lstsq(A, rp, rcond=None)
    fitted = A @ coef
    ss_res = float(((rp - fitted) ** 2).sum())
    ss_tot = float(((rp - rp.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    rows = [{"label": lbl, "beta": float(b)}
            for lbl, b in zip(labels, coef[1:])]
    rows.sort(key=lambda x: abs(x["beta"]), reverse=True)
    return {"alpha_ann": float(coef[0]) * STEPS_PER_YEAR, "r2": r2,
            "rows": rows, "n": n}
