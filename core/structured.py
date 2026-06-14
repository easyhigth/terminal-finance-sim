"""
structured.py — Produits structurés (logique pure, sans pygame).

Instruments à payoff NON LINÉAIRE sur un sous-jacent (l'indice phare de la
région du joueur), évalués à l'échéance :
  - Capital garanti : capital protégé + participation à la hausse.
  - Reverse convertible : coupon élevé, mais si le sous-jacent casse une barrière
    à la baisse, l'investisseur subit la perte.
  - Autocallable : coupon conditionnel ; remboursé si le sous-jacent tient, perte
    en capital sous la barrière à l'échéance.

Risque émetteur implicite. Détenu jusqu'à l'échéance (mark-to-model = notionnel).
Holdings : PlayerState.structured = [ {dict produit} ].
"""
STEPS_PER_YEAR = 52

# Catalogue : type, libellé, params, maturité (années).
TEMPLATES = [
    {"type": "capital_guaranteed", "name": "Capital garanti 100% + 60% hausse",
     "participation": 0.60, "years": 3,
     "desc": "Capital protégé à l'échéance + 60% de la hausse de l'indice."},
    {"type": "reverse_convertible", "name": "Reverse convertible 10% / barrière 70%",
     "coupon": 0.10, "barrier": 0.70, "years": 2,
     "desc": "Coupon 10%/an. Si l'indice finit sous 70% du niveau initial, "
             "vous subissez la baisse."},
    {"type": "autocallable", "name": "Autocallable 8% / barrière 60%",
     "coupon": 0.08, "barrier": 0.60, "years": 3,
     "desc": "Coupon 8%/an si l'indice tient. Perte en capital sous 60% à l'échéance."},
]


def _index_for_region(market, region):
    for name, reg, *_ in market.index_defs:
        if reg == region:
            return name
    return market.index_defs[0][0]


def payoff(product, final_level):
    """Cash total restitué à l'échéance (coupons inclus) pour un notionnel donné."""
    notional = product["notional"]
    start = product["start_level"]
    years = product["years"]
    perf = (final_level / start - 1.0) if start else 0.0
    t = product["type"]
    if t == "capital_guaranteed":
        return notional * (1.0 + product["participation"] * max(0.0, perf))
    if t == "reverse_convertible":
        coupons = notional * product["coupon"] * years
        breached = final_level < product["barrier"] * start
        principal = notional if not breached else notional * (1.0 + perf)
        return coupons + principal
    if t == "autocallable":
        if perf >= 0.0:                                   # rappelé : capital + coupons
            return notional * (1.0 + product["coupon"] * years)
        if final_level >= product["barrier"] * start:     # au-dessus barrière : capital
            return notional
        return notional * (1.0 + perf)                    # sous barrière : perte
    return notional


def invest(player, market, template_index, notional):
    """Souscrit un produit structuré pour `notional` (débité du cash)."""
    if not (0 <= template_index < len(TEMPLATES)):
        return {"ok": False, "reason": "id"}
    if notional <= 0 or notional > player.cash:
        return {"ok": False, "reason": "cash"}
    tpl = TEMPLATES[template_index]
    region = player.continent
    idx = _index_for_region(market, region)
    prod = dict(tpl)
    prod["notional"] = float(notional)
    prod["underlying"] = idx
    prod["start_level"] = market.index_value(idx)
    prod["maturity_step"] = market.step_count + int(tpl["years"] * STEPS_PER_YEAR)
    player.cash -= notional
    player.structured.append(prod)
    return {"ok": True, "product": prod}


def evaluate_due(player, market):
    """Évalue et dénoue les produits arrivés à échéance. Retourne les résultats."""
    results, still = [], []
    for prod in getattr(player, "structured", []):
        if market.step_count >= prod["maturity_step"]:
            final = market.index_value(prod["underlying"])
            pay = payoff(prod, final)
            player.cash += pay
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + (pay - prod["notional"])
            results.append({"product": prod, "payoff": pay,
                            "pnl": pay - prod["notional"], "final": final})
        else:
            still.append(prod)
    player.structured = still
    return results


def holdings_value(player, market):
    """Mark-to-model simple : notionnel (détenu jusqu'à l'échéance)."""
    return sum(p["notional"] for p in getattr(player, "structured", []))


def holdings(player, market):
    out = []
    for p in getattr(player, "structured", []):
        cur = market.index_value(p["underlying"])
        perf = (cur / p["start_level"] - 1.0) * 100 if p["start_level"] else 0.0
        steps_left = max(0, p["maturity_step"] - market.step_count)
        out.append({"name": p["name"], "notional": p["notional"], "underlying": p["underlying"],
                    "perf": perf, "steps_left": steps_left,
                    "years_left": steps_left / STEPS_PER_YEAR})
    return out
