"""
structured.py — Produits structurés (logique pure, sans pygame).

Instruments à payoff NON LINÉAIRE sur un sous-jacent (l'indice phare de la
région du joueur, ou un panier de 3 indices régionaux pour les « worst-of »),
évalués à l'échéance. Trois familles :

  - Classique : capital garanti, reverse convertible, autocallable, twin-win,
    range accrual — payoffs conditionnels « manuels » classiques de desk.
  - Exotique : note digitale (binaire), knock-out à barrière suivie en
    continu, lookback (sur le plus haut observé), worst-of sur panier —
    payoffs PATH-DEPENDENT, reconstruits depuis l'historique réel de l'indice
    (market.index_history), donc déterministes comme le reste du moteur.
  - Volatilité : swap de variance, note vol courte, note straddle — payoff
    fonction de la VOLATILITÉ RÉALISÉE du sous-jacent sur la durée de vie du
    produit (et non de sa seule performance directionnelle).

Risque émetteur implicite. Détenu jusqu'à l'échéance par défaut (mark-to-model
= notionnel) ; une sortie anticipée est possible via `sell_by_type` à la
valeur mark-to-model courante, minorée d'une décote de sortie (illiquidité
d'un produit OTC sur mesure).

Holdings : PlayerState.structured = [ {dict produit} ].
"""
import numpy as np

STEPS_PER_YEAR = 52
LOT = 50_000.0                 # notionnel souscrit par clic (desk & boutique)
EARLY_EXIT_HAIRCUT = 0.02      # décote de sortie anticipée (illiquidité OTC)

# Catalogue : id, famille, type (clé de payoff), nom, params, maturité (années).
# `regimes` : régimes de marché (core/market_constants.py::REGIMES) où le desk
# met en avant le produit (cohérent avec son profil de risque) — sert à faire
# varier l'offre mise en avant selon le régime courant (cf. `featured_templates`)
# sans jamais retirer un produit du catalogue complet.
TEMPLATES = [
    # ---- Classique : payoff conditionnel simple sur l'indice régional ----
    {"id": "capguard", "family": "Classique", "type": "capital_guaranteed",
     "name": "Capital garanti 100% + 60% hausse", "participation": 0.60, "years": 3,
     "regimes": ["Volatil", "Récession"],
     "desc": "Capital protégé à l'échéance + 60% de la hausse de l'indice."},
    {"id": "revconv", "family": "Classique", "type": "reverse_convertible",
     "name": "Reverse convertible 10% / barrière 70%", "coupon": 0.10, "barrier": 0.70, "years": 2,
     "regimes": ["Calme", "Expansion"],
     "desc": "Coupon 10%/an. Si l'indice finit sous 70% du niveau initial, "
             "vous subissez la baisse."},
    {"id": "autocall", "family": "Classique", "type": "autocallable",
     "name": "Autocallable 8% / barrière 60%", "coupon": 0.08, "barrier": 0.60, "years": 3,
     "regimes": ["Expansion"],
     "desc": "Coupon 8%/an si l'indice tient. Perte en capital sous 60% à l'échéance."},
    {"id": "twinwin", "family": "Classique", "type": "twin_win",
     "name": "Twin-Win 50% / barrière 75%", "barrier": 0.75, "cap": 0.50, "years": 2,
     "regimes": ["Volatil"],
     "desc": "Gagne dans les deux sens (hausse OU baisse, plafonné à 50%) si la barrière "
             "à 75% n'est jamais franchie à l'échéance ; sinon perte directionnelle classique."},
    {"id": "rangeaccrual", "family": "Classique", "type": "range_accrual",
     "name": "Range accrual 12% / [85%-115%]", "low": 0.85, "high": 1.15, "coupon": 0.12, "years": 2,
     "regimes": ["Calme"],
     "desc": "Coupon 12%/an au prorata du temps passé par l'indice dans le couloir [85%, 115%]."},

    # ---- Exotique : payoff path-dependent (barrière continue, lookback, panier) ----
    {"id": "digital", "family": "Exotique", "type": "digital",
     "name": "Note digitale (binaire) 20%", "payout_pct": 0.20, "floor": 0.80, "years": 1,
     "regimes": ["Expansion"],
     "desc": "Pari binaire : +20% si l'indice finit au-dessus de son niveau initial, "
             "sinon capital ramené à 80%."},
    {"id": "koupcoupon", "family": "Exotique", "type": "knockout",
     "name": "Knock-out coupon 9% / barrière 130%", "barrier": 1.30, "coupon": 0.09, "years": 2,
     "regimes": ["Calme", "Récession"],
     "desc": "Coupon 9%/an si l'indice ne dépasse JAMAIS 130% de son niveau initial (suivi en "
             "continu) ; sinon remboursement anticipé au pair, coupons perdus."},
    {"id": "lookback", "family": "Exotique", "type": "lookback",
     "name": "Lookback 50% sur plus haut", "participation": 0.50, "years": 2,
     "regimes": ["Volatil"],
     "desc": "Participation de 50% à la hausse calculée sur le PLUS HAUT niveau observé "
             "pendant la vie du produit (et non le niveau final)."},
    {"id": "worstof", "family": "Exotique", "type": "worst_of",
     "name": "Worst-of panier régional 70%", "participation": 0.70, "years": 2,
     "regimes": ["Expansion"],
     "desc": "Participation de 70% à la performance du PIRE indice d'un panier de 3 régions ; "
             "perte directionnelle si la pire performance est négative."},

    # ---- Volatilité : payoff lié à la volatilité réalisée du sous-jacent ----
    {"id": "varswap", "family": "Volatilité", "type": "var_swap",
     "name": "Swap de variance (strike 18%)", "vol_strike": 0.18, "vol_mult": 1.5, "years": 1,
     "regimes": ["Volatil", "Récession"],
     "desc": "Position longue volatilité : gagne si la volatilité RÉALISÉE annualisée dépasse "
             "18%, perd (jusqu'à 0) si le marché reste calme."},
    {"id": "shortvol", "family": "Volatilité", "type": "short_vol",
     "name": "Note vol courte 18% / cap 25%", "coupon": 0.18, "vol_cap": 0.25,
     "vol_loss_mult": 3.0, "years": 1,
     "regimes": ["Calme", "Expansion"],
     "desc": "Coupon élevé de 18% si la volatilité réalisée reste sous 25% ; perte en capital "
             "amplifiée (x3) au-delà — vend de la volatilité, encaisse la prime, risque de queue."},
    {"id": "straddle", "family": "Volatilité", "type": "straddle_note",
     "name": "Note straddle (long gamma) 80%", "participation": 0.80, "cost": 0.05, "years": 1,
     "regimes": ["Volatil", "Récession"],
     "desc": "Réplique un straddle : gagne 80% de la VARIATION ABSOLUE de l'indice (hausse ou "
             "baisse), net d'une prime de 5% payée d'avance."},
]
_BY_ID = {t["id"]: t for t in TEMPLATES}


def _resolve_template(template_id):
    """Accepte un id (str) ou un index historique (int, pour compat ascendante)."""
    if isinstance(template_id, int):
        return TEMPLATES[template_id] if 0 <= template_id < len(TEMPLATES) else None
    return _BY_ID.get(template_id)


def _index_for_region(market, region):
    for name, reg, *_ in market.index_defs:
        if reg == region:
            return name
    return market.index_defs[0][0]


def _basket_for_region(market, region):
    """Panier déterministe de 3 indices régionaux (le sien + 2 autres) pour
    les produits worst-of."""
    own = _index_for_region(market, region)
    others = [d[0] for d in market.index_defs if d[0] != own]
    return [own] + others[:2]


def _path_since(market, idx, start_step):
    """Historique de l'indice depuis `start_step` jusqu'au pas courant (inclus).
    S'appuie sur la fenêtre glissante `market.index_hist` : valide tant que la
    durée de vie du produit reste sous HIST_LEN pas (cas de tous les TEMPLATES)."""
    hist = market.index_history(idx)
    n = market.step_count - start_step
    if n <= 0 or not hist:
        return [market.index_value(idx)]
    return hist[-(n + 1):]


def _realized_vol(path):
    """Volatilité réalisée annualisée (écart-type des rendements log) sur un chemin."""
    if not path or len(path) < 3:
        return 0.0
    arr = np.clip(np.asarray(path, dtype=float), 1e-9, None)
    rets = np.diff(np.log(arr))
    if rets.size == 0:
        return 0.0
    return float(np.std(rets) * np.sqrt(STEPS_PER_YEAR))


def _range_fraction(path, lo, hi):
    if not path:
        return 1.0
    inside = sum(1 for v in path if lo <= v <= hi)
    return inside / len(path)


def payoff(product, final_level, path=None, market=None):
    """Cash total restitué à l'échéance (coupons inclus) pour un notionnel donné.
    `path` (historique du sous-jacent depuis la souscription) est requis pour les
    payoffs path-dependent (knockout/lookback/range_accrual/vol) ; `market` pour
    le worst-of (relit les autres membres du panier)."""
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
        if final_level >= product["barrier"] * start:      # au-dessus barrière : capital
            return notional
        return notional * (1.0 + perf)                     # sous barrière : perte
    if t == "twin_win":
        if final_level >= product["barrier"] * start:
            gain = min(abs(perf), product["cap"])
            return notional * (1.0 + gain)
        return notional * (1.0 + perf)
    if t == "range_accrual":
        frac = _range_fraction(path, product["low"] * start, product["high"] * start)
        return notional + notional * product["coupon"] * years * frac
    if t == "digital":
        if perf >= 0.0:
            return notional * (1.0 + product["payout_pct"])
        return notional * product.get("floor", 0.80)
    if t == "knockout":
        breached = (max(path) >= product["barrier"] * start) if path \
            else (final_level >= product["barrier"] * start)
        if breached:
            return notional
        return notional * (1.0 + product["coupon"] * years)
    if t == "lookback":
        best = max(path) if path else final_level
        perf_best = (best / start - 1.0) if start else 0.0
        return notional * (1.0 + product["participation"] * max(0.0, perf_best))
    if t == "worst_of":
        if market is not None and "basket" in product:
            perfs = [market.index_value(b) / product["basket_start"][b] - 1.0
                     for b in product["basket"]]
        else:
            perfs = [perf]
        worst = min(perfs)
        return notional * (1.0 + product["participation"] * worst) if worst >= 0.0 \
            else notional * (1.0 + worst)
    if t == "var_swap":
        rv = _realized_vol(path)
        diff = rv - product["vol_strike"]
        return max(0.0, notional + notional * product["vol_mult"] * diff)
    if t == "short_vol":
        rv = _realized_vol(path)
        if rv <= product["vol_cap"]:
            return notional * (1.0 + product["coupon"])
        loss = min(1.0, (rv - product["vol_cap"]) * product.get("vol_loss_mult", 3.0))
        return notional * (1.0 - loss)
    if t == "straddle_note":
        return notional * (1.0 - product["cost"] + product["participation"] * abs(perf))
    return notional


def invest(player, market, template_id, notional):
    """Souscrit un produit structuré pour `notional` (débité du cash)."""
    tpl = _resolve_template(template_id)
    if tpl is None:
        return {"ok": False, "reason": "id"}
    if notional <= 0 or notional > player.cash:
        return {"ok": False, "reason": "cash"}
    region = player.continent
    prod = dict(tpl)
    prod["notional"] = float(notional)
    prod["tpl_id"] = tpl["id"]
    if tpl["type"] == "worst_of":
        basket = _basket_for_region(market, region)
        prod["basket"] = basket
        prod["basket_start"] = {b: market.index_value(b) for b in basket}
        prod["underlying"] = basket[0]
        prod["start_level"] = prod["basket_start"][basket[0]]
    else:
        idx = _index_for_region(market, region)
        prod["underlying"] = idx
        prod["start_level"] = market.index_value(idx)
    prod["start_step"] = market.step_count
    prod["maturity_step"] = market.step_count + int(tpl["years"] * STEPS_PER_YEAR)
    player.cash -= notional
    player.structured.append(prod)
    return {"ok": True, "product": prod, "price": LOT}


def _start_step_of(product):
    return product.get("start_step",
                        product["maturity_step"] - int(product["years"] * STEPS_PER_YEAR))


def evaluate_due(player, market):
    """Évalue et dénoue les produits arrivés à échéance. Retourne les résultats."""
    results, still = [], []
    for prod in getattr(player, "structured", []):
        if market.step_count >= prod["maturity_step"]:
            final = market.index_value(prod["underlying"])
            path = _path_since(market, prod["underlying"], _start_step_of(prod))
            pay = payoff(prod, final, path=path, market=market)
            player.cash += pay
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + (pay - prod["notional"])
            results.append({"product": prod, "payoff": pay,
                            "pnl": pay - prod["notional"], "final": final})
        else:
            still.append(prod)
    player.structured = still
    return results


def mark_to_model(product, market):
    """Valeur de sortie anticipée (avant échéance) : ré-applique le payoff comme si
    la maturité était maintenant (coupons au prorata du temps écoulé), minorée
    d'une décote d'illiquidité OTC."""
    start_step = _start_step_of(product)
    path = _path_since(market, product["underlying"], start_step)
    current_level = path[-1] if path else market.index_value(product["underlying"])
    elapsed_years = max(market.step_count - start_step, 1) / STEPS_PER_YEAR
    tmp = dict(product)
    tmp["years"] = elapsed_years
    val = payoff(tmp, current_level, path=path, market=market)
    return val * (1.0 - EARLY_EXIT_HAIRCUT)


def sell_by_type(player, market, template_id, notional):
    """Dénoue par anticipation jusqu'à `notional` de notionnel souscrit sur le
    template `template_id` (FIFO sur les positions ouvertes), à la valeur
    mark-to-model courante. Retourne un dict compatible avec le format générique
    des autres marchés (qty=lots vendus, price=LOT, realized=P&L)."""
    items = getattr(player, "structured", [])
    remaining = notional
    total_value, total_pnl, sold_any = 0.0, 0.0, False
    i = 0
    while i < len(items) and remaining > 1e-6:
        prod = items[i]
        if prod.get("tpl_id", prod.get("type")) != template_id:
            i += 1
            continue
        sell_amt = min(remaining, prod["notional"])
        frac = sell_amt / prod["notional"] if prod["notional"] else 0.0
        value = mark_to_model(prod, market) * frac
        total_value += value
        total_pnl += value - sell_amt
        player.cash += value
        prod["notional"] -= sell_amt
        remaining -= sell_amt
        sold_any = True
        if prod["notional"] <= 1e-6:
            items.pop(i)
        else:
            i += 1
    if not sold_any:
        return {"ok": False, "reason": "noposition"}
    player.realized_pnl = getattr(player, "realized_pnl", 0.0) + total_pnl
    return {"ok": True, "qty": (notional - remaining) / LOT, "price": LOT,
            "realized": total_pnl, "value": total_value}


def held_notional(player, template_id):
    return sum(p["notional"] for p in getattr(player, "structured", [])
               if p.get("tpl_id", p.get("type")) == template_id)


def is_featured(template_id, market):
    """Le desk met-il ce produit en avant dans le régime de marché courant ?
    `market` peut être None (catalogue hors contexte de marché) -> jamais
    mis en avant."""
    if market is None:
        return False
    t = _BY_ID.get(template_id) if isinstance(template_id, str) else _resolve_template(template_id)
    if t is None:
        return False
    return getattr(market, "regime", None) in t.get("regimes", [])


def featured_templates(market):
    """Ids des templates mis en avant par le desk dans le régime courant."""
    return [t["id"] for t in TEMPLATES if is_featured(t["id"], market)]


def template_quote(template_id, market=None):
    t = _BY_ID[template_id]
    return {"id": t["id"], "name": t["name"], "family": t["family"],
            "type": t["type"], "years": t["years"], "desc": t["desc"],
            "coupon": t.get("coupon"), "vol_strike": t.get("vol_strike"),
            "featured": is_featured(t["id"], market)}


def all_templates(market=None):
    return [template_quote(t["id"], market) for t in TEMPLATES]


def payoff_curve(template_id, n=21):
    """Points (x, ratio_payoff/notionnel) pour une visualisation pédagogique du
    payoff. Pour les produits Volatilité, x = volatilité réalisée annualisée
    (0% à 40%) ; pour les autres, x = performance finale du sous-jacent
    (-50% à +50%). Indicatif : ignore l'effet de chemin exact (barrière suivie
    en continu, plus haut observé...) et n'utilise que le niveau final."""
    tpl = _resolve_template(template_id)
    if tpl is None:
        return []
    t = tpl["type"]
    pts = []
    if t in ("var_swap", "short_vol"):
        for i in range(n):
            rv = i / (n - 1) * 0.40
            if t == "var_swap":
                diff = rv - tpl["vol_strike"]
                ratio = max(0.0, 1.0 + tpl["vol_mult"] * diff)
            else:
                if rv <= tpl["vol_cap"]:
                    ratio = 1.0 + tpl["coupon"]
                else:
                    loss = min(1.0, (rv - tpl["vol_cap"]) * tpl.get("vol_loss_mult", 3.0))
                    ratio = 1.0 - loss
            pts.append((rv, ratio))
        return pts
    for i in range(n):
        perf = -0.5 + i / (n - 1) * 1.0
        final = 1.0 + perf
        prod = dict(tpl)
        prod["notional"] = 1.0
        prod["start_level"] = 1.0
        ratio = payoff(prod, final, path=[final], market=None)
        pts.append((perf, ratio))
    return pts


def payoff_curve_xlabel(template_id):
    tpl = _resolve_template(template_id)
    if tpl is not None and tpl["type"] in ("var_swap", "short_vol"):
        return "Volatilité réalisée"
    return "Performance du sous-jacent"


def holdings_value(player, market):
    """Mark-to-model simple : notionnel (détenu jusqu'à l'échéance)."""
    return sum(p["notional"] for p in getattr(player, "structured", []))


def holdings(player, market):
    out = []
    for p in getattr(player, "structured", []):
        cur = market.index_value(p["underlying"])
        perf = (cur / p["start_level"] - 1.0) * 100 if p["start_level"] else 0.0
        steps_left = max(0, p["maturity_step"] - market.step_count)
        out.append({"name": p["name"], "family": p.get("family", "Classique"),
                    "tpl_id": p.get("tpl_id", p.get("type")), "notional": p["notional"],
                    "underlying": p["underlying"], "perf": perf,
                    "steps_left": steps_left, "years_left": steps_left / STEPS_PER_YEAR})
    return out
