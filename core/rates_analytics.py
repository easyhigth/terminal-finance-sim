"""
rates_analytics.py — Analytique de taux du book obligataire (logique pure).

Le desk Taux du bureau s'appuie dessus pour trois lectures de cours de
fixed income, calculées sur le VRAI univers obligataire du jeu
(core/bonds.py — YTM, duration modifiée, convexité par titre) :

- **Courbe des taux** : structure par terme des rendements SOUVERAINS
  (YTM moyen par maturité) — celle que déforme la macro du jeu (taux
  directeur, prime de terme, spreads).
- **Book** : chaque ligne du joueur avec sa duration modifiée, sa
  convexité et son **DV01** (= valeur × duration × 0,0001 : le P&L d'un
  déplacement de 1 point de base — l'unité de compte d'un desk de taux).
  Agrégats pondérés par la valeur.
- **Chocs de courbe** : P&L du book sous des scénarios de déplacement,
  au 2e ordre — ΔP ≈ V·(−D·Δy + ½·C·Δy²). Les scénarios non parallèles
  (pentification/aplatissement) interpolent Δy selon la maturité de
  chaque ligne : c'est la convexité et la RÉPARTITION par maturité qui
  font la différence entre deux books de même duration (immunisation).
"""
import numpy as np

from core import bonds as B

# (nom, Δy court terme, Δy long terme) — interpolation par maturité entre
# les deux (pivot : 2 ans → court, 10 ans+ → long).
CURVE_SCENARIOS = [
    ("+50 bp parallèle", 0.005, 0.005),
    ("+100 bp parallèle", 0.010, 0.010),
    ("+200 bp parallèle", 0.020, 0.020),
    ("−100 bp parallèle", -0.010, -0.010),
    ("Pentification (+25/+150)", 0.0025, 0.015),
    ("Aplatissement (+150/+25)", 0.015, 0.0025),
]
_SHORT_Y, _LONG_Y = 2.0, 10.0


def yield_curve(market):
    """Points (maturité en années, YTM moyen) des souverains, triés par
    maturité — la structure par terme observable du jeu."""
    buckets = {}
    for q in B.sovereign_quotes(market):
        buckets.setdefault(q["years"], []).append(q["ytm"])
    return sorted((y, sum(v) / len(v)) for y, v in buckets.items())


def book_lines(player, market):
    """Lignes du book obligataire du joueur : valeur, YTM, duration
    modifiée, convexité, DV01. Triées par valeur décroissante."""
    out = []
    for bond_id, pos in getattr(player, "bonds", {}).items():
        q = B.quote(market, bond_id)
        if not q:
            continue
        value = q["price"] * pos["qty"]
        out.append({
            "id": bond_id, "name": q["name"], "kind": q["kind"],
            "years": q["years"], "qty": pos["qty"], "value": value,
            "ytm": q["ytm"], "duration": q["mod_duration"],
            "convexity": q["convexity"],
            "dv01": value * q["mod_duration"] * 1e-4,
        })
    out.sort(key=lambda x: x["value"], reverse=True)
    return out


def book_totals(lines):
    """Agrégats du book : valeur, duration et convexité PONDÉRÉES par la
    valeur, DV01 total."""
    total = sum(x["value"] for x in lines)
    if total <= 0:
        return {"value": 0.0, "duration": 0.0, "convexity": 0.0, "dv01": 0.0}
    return {
        "value": total,
        "duration": sum(x["duration"] * x["value"] for x in lines) / total,
        "convexity": sum(x["convexity"] * x["value"] for x in lines) / total,
        "dv01": sum(x["dv01"] for x in lines),
    }


def _dy_for_maturity(years, dy_short, dy_long):
    """Δy d'une maturité donnée sous un choc (interpolation court→long)."""
    if years <= _SHORT_Y:
        return dy_short
    if years >= _LONG_Y:
        return dy_long
    t = (years - _SHORT_Y) / (_LONG_Y - _SHORT_Y)
    return dy_short + t * (dy_long - dy_short)


def shock_pnl(lines, dy_short, dy_long):
    """P&L du book sous un choc de courbe, au 2e ordre (duration +
    convexité) : ΔP = Σ V_i·(−D_i·Δy_i + ½·C_i·Δy_i²)."""
    pnl = 0.0
    for x in lines:
        dy = _dy_for_maturity(x["years"], dy_short, dy_long)
        pnl += x["value"] * (-x["duration"] * dy + 0.5 * x["convexity"] * dy * dy)
    return pnl


def forward_rates(curve):
    """Taux FORWARDS implicites entre points consécutifs de la courbe :
    f(t1,t2) = (y2·t2 − y1·t1)/(t2 − t1) — « ce que le marché price » pour
    la période future [t1, t2] (le taux qui rend indifférent entre placer
    long ou rouler court). [(t1, t2, fwd)]."""
    out = []
    for (t1, y1), (t2, y2) in zip(curve, curve[1:]):
        if t2 > t1:
            out.append((t1, t2, (y2 * t2 - y1 * t1) / (t2 - t1)))
    return out


def dv01_rotation_plan(player, market, direction, fraction=0.25):
    """Plan de ROTATION de courbe du book (le jeu ne permet pas de shorter
    une obligation, on fait donc tourner le book) : `direction` =
    "shorten" (vendre du long terme, acheter du court — parier sur la
    pentification / se protéger d'une hausse des taux longs) ou "lengthen"
    (l'inverse). Les quantités sont appariées en DV01 (le risque de taux
    déplacé est le même des deux côtés). Renvoie None si rien à tourner,
    sinon {sell: {id, name, qty, dv01}, buy: {id, name, qty, dv01}}."""
    from core import bonds as B
    lines = book_lines(player, market)
    if not lines:
        return None
    lines_sorted = sorted(lines, key=lambda x: x["years"])
    sell_line = lines_sorted[-1] if direction == "shorten" else lines_sorted[0]
    quotes = sorted(B.sovereign_quotes(market), key=lambda q: q["years"])
    buy_q = quotes[0] if direction == "shorten" else quotes[-1]
    if buy_q["id"] == sell_line["id"]:
        return None
    dv01_unit_sell = sell_line["dv01"] / sell_line["qty"]
    qty_sell = max(1, int(round(sell_line["qty"] * fraction)))
    dv01_moved = qty_sell * dv01_unit_sell
    dv01_unit_buy = buy_q["price"] * buy_q["mod_duration"] * 1e-4
    if dv01_unit_buy <= 0:
        return None
    qty_buy = max(1, int(round(dv01_moved / dv01_unit_buy)))
    return {"sell": {"id": sell_line["id"], "name": sell_line["name"],
                     "qty": qty_sell, "dv01": dv01_moved},
            "buy": {"id": buy_q["id"], "name": buy_q["name"],
                    "qty": qty_buy, "dv01": qty_buy * dv01_unit_buy}}


def execute_rotation(player, market, plan):
    """Exécute un plan de rotation (vente puis achat, core/bonds)."""
    from core import bonds as B
    r1 = B.sell_bond(player, market, plan["sell"]["id"], plan["sell"]["qty"])
    if not r1.get("ok"):
        return {"ok": False, "reason": r1.get("reason", "?"), "leg": "sell"}
    r2 = B.buy_bond(player, market, plan["buy"]["id"], plan["buy"]["qty"])
    if not r2.get("ok"):
        return {"ok": False, "reason": r2.get("reason", "?"), "leg": "buy"}
    return {"ok": True}


def immunize_plan(player, market, liability, horizon_years):
    """IMMUNISATION classique : financer un passif de `liability` (valeur à
    l'échéance) dû dans `horizon_years`, avec un BARBELL de deux souverains
    encadrant l'horizon, pondérés pour que la DURATION des actifs égale
    l'horizon — au 1er ordre, un choc de taux laisse la couverture intacte
    (le prix perd ce que le réinvestissement gagne, et réciproquement).
    Renvoie None si l'univers n'encadre pas l'horizon, sinon
    {pv, y_h, short:{id,name,qty,weight,dur}, long:{...}, dur_target}."""
    from core import bonds as B
    quotes = sorted(B.sovereign_quotes(market), key=lambda q: q["years"])
    shorts = [q for q in quotes if q["mod_duration"] < horizon_years]
    longs = [q for q in quotes if q["mod_duration"] > horizon_years]
    if not shorts or not longs or liability <= 0:
        return None
    qs = shorts[-1]                                   # le plus proche en-dessous
    ql = longs[0]                                     # le plus proche au-dessus
    # taux à l'horizon (interpolation de la courbe) → valeur actuelle du passif
    curve = yield_curve(market)
    y_h = curve[0][1]
    for (t1, y1), (t2, y2) in zip(curve, curve[1:]):
        if t1 <= horizon_years <= t2:
            w = (horizon_years - t1) / (t2 - t1) if t2 > t1 else 0.0
            y_h = y1 + w * (y2 - y1)
            break
    else:
        y_h = curve[-1][1]
    pv = liability / (1.0 + y_h) ** horizon_years
    # barbell : w_s·D_s + w_l·D_l = horizon, w_s + w_l = 1
    d_s, d_l = qs["mod_duration"], ql["mod_duration"]
    w_s = (d_l - horizon_years) / (d_l - d_s)
    w_l = 1.0 - w_s
    qty_s = max(1, int(round(pv * w_s / qs["price"])))
    qty_l = max(1, int(round(pv * w_l / ql["price"])))
    return {"pv": pv, "y_h": y_h, "dur_target": horizon_years,
            "short": {"id": qs["id"], "name": qs["name"], "qty": qty_s,
                      "weight": w_s, "dur": d_s, "price": qs["price"]},
            "long": {"id": ql["id"], "name": ql["name"], "qty": qty_l,
                     "weight": w_l, "dur": d_l, "price": ql["price"]}}


def execute_immunization(player, market, plan):
    """Achète les deux jambes du barbell (core/bonds.buy_bond)."""
    from core import bonds as B
    for leg in (plan["short"], plan["long"]):
        r = B.buy_bond(player, market, leg["id"], leg["qty"])
        if not r.get("ok"):
            return {"ok": False, "reason": r.get("reason", "?"),
                    "leg": leg["id"]}
    return {"ok": True}


def immunization_check(plan, dy=0.01):
    """Vérification pédagogique : sous un choc parallèle ±dy, la variation
    des ACTIFS (duration) vs celle du PASSIF actualisé — l'écart résiduel
    doit être petit devant le choc. {d_assets, d_liability, mismatch}."""
    pv = plan["pv"]
    h = plan["dur_target"]
    d_assets = -(plan["short"]["weight"] * plan["short"]["dur"]
                 + plan["long"]["weight"] * plan["long"]["dur"]) * dy * pv
    d_liability = -h * dy * pv                        # même sensibilité visée
    return {"d_assets": d_assets, "d_liability": d_liability,
            "mismatch": d_assets - d_liability}


def scenario_table(player, market):
    """Table des scénarios de courbe appliqués au book du joueur.
    Renvoie {lines, totals, scenarios: [{name, pnl, pnl_pct}]}."""
    lines = book_lines(player, market)
    totals = book_totals(lines)
    scenarios = []
    for name, dys, dyl in CURVE_SCENARIOS:
        pnl = shock_pnl(lines, dys, dyl)
        pct = (pnl / totals["value"] * 100.0) if totals["value"] else 0.0
        scenarios.append({"name": name, "pnl": pnl, "pnl_pct": pct})
    return {"lines": lines, "totals": totals, "scenarios": scenarios}
