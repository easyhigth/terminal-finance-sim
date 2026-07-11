"""
strategic_allocation.py — Allocation STRATÉGIQUE multi-classes d'actifs
(voie Portfolio, logique pure).

Distinct de la frontière efficiente (core/quant_tools.py, qui optimise les
POIDS entre actions individuelles) : ici, le niveau est plus haut — combien
du patrimoine total va en actions / obligations / matières premières /
crypto / cash, façon allocation stratégique d'un gérant multi-actifs (le
choix qui, empiriquement, explique l'essentiel de la performance d'un
portefeuille à long terme, bien avant la sélection de titres).

`current_allocation` lit l'état RÉEL du joueur (mêmes fonctions
`holdings_value` que `core/portfolio_margin.py::net_worth`, cf. ce module
pour la liste). `drift` compare à des cibles (un des `PROFILES` prédéfinis,
ou des cibles personnalisées) et signale les buckets hors de la bande de
tolérance. `rebalance_plan`/`apply_plan` ne savent RÉÉQUILIBRER
automatiquement QUE le bucket actions (redimensionner les positions
longues existantes au prorata, via core/portfolio.py) — les autres classes
(obligations/commodities/crypto) exigent un choix d'instrument spécifique
que ce module ne peut pas deviner ; il indique alors le montant à
déplacer et renvoie vers le desk concerné.
"""
from core import portfolio as PF

BUCKETS = ["cash", "equity", "bonds", "commodities", "crypto"]

BUCKET_LABEL = {
    "cash": "Trésorerie", "equity": "Actions", "bonds": "Obligations",
    "commodities": "Matières premières", "crypto": "Crypto",
}

DRIFT_BAND = 0.05   # 5 points de pourcentage : au-delà, bucket signalé

PROFILES = {
    "prudent": {"label": "Prudent",
                "targets": {"cash": 0.20, "equity": 0.30, "bonds": 0.40,
                            "commodities": 0.05, "crypto": 0.05}},
    "equilibre": {"label": "Équilibré",
                  "targets": {"cash": 0.10, "equity": 0.45, "bonds": 0.30,
                              "commodities": 0.10, "crypto": 0.05}},
    "dynamique": {"label": "Dynamique",
                  "targets": {"cash": 0.05, "equity": 0.65, "bonds": 0.15,
                              "commodities": 0.10, "crypto": 0.05}},
}


def _equity_long_value(player, market):
    total = 0.0
    for t, pos in player.portfolio.items():
        if pos["shares"] <= 0:
            continue
        price = market.price_of(t)
        if price is not None:
            total += price * pos["shares"]
    return total


def current_allocation(player, market):
    """{"values": {bucket: montant}, "pct": {bucket: part 0..1}, "total": ...}."""
    values = {"cash": max(0.0, player.cash), "equity": _equity_long_value(player, market),
               "bonds": 0.0, "commodities": 0.0, "crypto": 0.0}
    if getattr(player, "bonds", None):
        from core import bonds
        values["bonds"] = bonds.holdings_value(player, market)
    if getattr(player, "commodities", None):
        from core import commodities
        values["commodities"] = commodities.holdings_value(player, market)
    if getattr(player, "crypto", None):
        from core import crypto as crypto_mod
        values["crypto"] = crypto_mod.holdings_value(player, market)
    total = sum(values.values())
    pct = {b: (v / total if total > 0 else 0.0) for b, v in values.items()}
    return {"values": values, "pct": pct, "total": total}


def drift(alloc, targets):
    """{bucket: (pct_courant - pct_cible)}, signé — positif = surpondéré."""
    return {b: alloc["pct"].get(b, 0.0) - targets.get(b, 0.0) for b in BUCKETS}


def out_of_band(alloc, targets, band=DRIFT_BAND):
    d = drift(alloc, targets)
    return {b: dv for b, dv in d.items() if abs(dv) > band}


def rebalance_plan(player, market, targets):
    """Plan de rééquilibrage. Pour le bucket "equity" détenu, redimensionne
    PROPORTIONNELLEMENT les positions longues existantes vers la valeur
    cible (jamais de sélection de nouveaux titres — ce module ne choisit pas
    d'actions). Pour les autres buckets hors bande, indique le montant à
    déplacer (le joueur choisit lui-même l'instrument via le desk adapté)."""
    alloc = current_allocation(player, market)
    total = alloc["total"]
    trades = []
    notes = []
    if total <= 0:
        return {"trades": [], "notes": ["Aucun patrimoine à allouer."], "alloc": alloc}

    target_equity_value = targets.get("equity", 0.0) * total
    cur_equity_value = alloc["values"]["equity"]
    if cur_equity_value > 0 and abs(target_equity_value - cur_equity_value) > total * 0.005:
        scale = target_equity_value / cur_equity_value
        for t, pos in player.portfolio.items():
            if pos["shares"] <= 0:
                continue
            price = market.price_of(t)
            if price is None:
                continue
            target_shares = pos["shares"] * scale
            delta_shares = round(target_shares - pos["shares"])
            if delta_shares == 0:
                continue
            trades.append({"ticker": t, "delta_qty": float(delta_shares),
                           "delta_value": delta_shares * price})
    elif target_equity_value > 0 and cur_equity_value <= 0:
        notes.append("Aucune position action existante à redimensionner — "
                     "achetez d'abord via l'Explorateur ou la Boutique.")

    for b in BUCKETS:
        if b in ("cash", "equity"):
            continue
        cur_v = alloc["values"][b]
        target_v = targets.get(b, 0.0) * total
        delta = target_v - cur_v
        if abs(delta) > total * DRIFT_BAND * 0.5:
            verb = "Ajoutez" if delta > 0 else "Réduisez"
            notes.append(f"{verb} ~{abs(delta):,.0f} de {BUCKET_LABEL[b]} "
                        f"(via le desk correspondant).")
    return {"trades": trades, "notes": notes, "alloc": alloc}


def apply_plan(player, market, plan):
    """Exécute les trades ACTIONS du plan (ventes d'abord, pour libérer du
    cash avant les achats). Les autres classes restent manuelles (cf. notes
    du plan). Renvoie la liste des résultats d'exécution."""
    trades = sorted(plan.get("trades", []), key=lambda t: t["delta_qty"])
    results = []
    for tr in trades:
        qty = abs(tr["delta_qty"])
        if qty < 1e-6:
            continue
        if tr["delta_qty"] < 0:
            res = PF.sell(player, market, tr["ticker"], qty)
        else:
            res = PF.buy(player, market, tr["ticker"], qty)
        results.append({"ticker": tr["ticker"], "qty": qty,
                        "side": "sell" if tr["delta_qty"] < 0 else "buy", **res})
    return results
