"""
commodities.py — Matières premières avec courbe de futures (logique pure).

Chaque commodity a un SPOT déterministe (reconstruit via graine+pas, comme le
reste du moteur) et une COURBE DE FUTURES : F(échéance) = spot·e^(slope·t).
  slope > 0 -> contango (futures > spot), roll yield négatif au roulement ;
  slope < 0 -> backwardation, roll yield positif.
Le joueur trade le contrat de premier mois ; un coût/gain de roulement (roll
yield) est prélevé à chaque tour, proportionnel à la pente de la courbe.

Holdings : PlayerState.commodities = { id : {"qty": nb de contrats, "avg": prix} }.
"""
import numpy as np

# (id, nom, spot de base, dérive annuelle, vol annuelle, pente de courbe annuelle)
COMMODITIES = [
    ("GOLD", "Or (once)", 2000.0, 0.03, 0.15, -0.01),     # léger backwardation
    ("OIL",  "Pétrole (baril)", 80.0, 0.01, 0.35, 0.06),  # contango marqué
    ("GAS",  "Gaz naturel", 3.0, 0.0, 0.55, 0.10),        # fort contango, très volatil
    ("COPP", "Cuivre (tonne)", 8500.0, 0.02, 0.25, 0.03),
    ("WHEAT", "Blé (boisseau)", 6.0, 0.0, 0.30, 0.04),
]
_BY_ID = {c[0]: c for c in COMMODITIES}
MULTIPLIER = 100.0          # 1 contrat = 100 unités
COMMISSION = 0.001

_path_cache = {}            # (seed, id) -> liste de spots (étendue à la demande)


def _hash(cid):
    h = 0
    for ch in cid:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h


def _path(market, cid, n_steps):
    """Trajectoire de spot déterministe jusqu'à n_steps (cache + extension)."""
    c = _BY_ID[cid]
    base, drift, vol = c[2], c[3], c[4]
    seed = (int(getattr(market, "seed", 12345)) + _hash(cid)) & 0xFFFFFFFF
    key = (seed, cid)
    path = _path_cache.get(key)
    if path is None or len(path) <= n_steps:
        rng = np.random.RandomState(seed)
        mu = drift / 52.0 - 0.5 * (vol / np.sqrt(52)) ** 2
        sig = vol / np.sqrt(52)
        rets = rng.normal(mu, sig, n_steps + 1)
        spots = base * np.exp(np.cumsum(rets))
        spots[0] = base
        path = spots.tolist()
        _path_cache[key] = path
    return path


def spot(market, cid):
    step = int(getattr(market, "step_count", 0))
    return _path(market, cid, step)[step]


def futures_price(market, cid, months):
    """Prix du future à échéance `months` mois (cost of carry de courbe)."""
    slope = _BY_ID[cid][5]
    return spot(market, cid) * np.exp(slope * months / 12.0)


def curve(market, cid, maturities=(1, 3, 6, 12)):
    return [(mo, futures_price(market, cid, mo)) for mo in maturities]


def roll_yield(market, cid):
    """Roll yield indicatif (par an) : −pente (négatif en contango)."""
    return -_BY_ID[cid][5]


def quote(market, cid):
    c = _BY_ID.get(cid)
    if not c:
        return None
    sp = spot(market, cid)
    front = futures_price(market, cid, 1)
    structure = "Contango" if c[5] > 0 else "Backwardation" if c[5] < 0 else "Plate"
    return {"id": cid, "name": c[1], "spot": sp, "front": front,
            "slope": c[5], "structure": structure, "roll_yield": roll_yield(market, cid),
            "vol": c[4]}


def all_quotes(market):
    return [quote(market, c[0]) for c in COMMODITIES]


# ---------------------------------------------------------------- trading
def _contract_value(market, cid, qty):
    return futures_price(market, cid, 1) * MULTIPLIER * qty


def buy(player, market, cid, qty):
    if cid not in _BY_ID:
        return {"ok": False, "reason": "id"}
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    price = futures_price(market, cid, 1)
    cost = price * MULTIPLIER * qty
    fee = cost * COMMISSION
    if cost + fee > player.cash:
        return {"ok": False, "reason": "cash"}
    player.cash -= (cost + fee)
    pos = player.commodities.get(cid)
    if pos:
        n = pos["qty"] + qty
        pos["avg"] = (pos["qty"] * pos["avg"] + price * qty) / n
        pos["qty"] = n
    else:
        player.commodities[cid] = {"qty": float(qty), "avg": price}
    return {"ok": True, "price": price, "qty": qty, "total": cost + fee}


def sell(player, market, cid, qty):
    pos = player.commodities.get(cid)
    if not pos:
        return {"ok": False, "reason": "noposition"}
    price = futures_price(market, cid, 1)
    if qty == "ALL" or qty >= pos["qty"]:
        qty = pos["qty"]
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    proceeds = price * MULTIPLIER * qty
    fee = proceeds * COMMISSION
    realized = (price - pos["avg"]) * MULTIPLIER * qty - fee
    player.cash += proceeds - fee
    player.realized_pnl = getattr(player, "realized_pnl", 0.0) + realized
    pos["qty"] -= qty
    if pos["qty"] <= 1e-9:
        del player.commodities[cid]
    return {"ok": True, "price": price, "qty": qty, "realized": realized}


def holdings_value(player, market):
    total = 0.0
    for cid, pos in getattr(player, "commodities", {}).items():
        if cid in _BY_ID:
            total += futures_price(market, cid, 1) * MULTIPLIER * pos["qty"]
    return total


def roll_cost(player, market, days):
    """Coût/gain de roulement du tour : roll yield prorata sur la valeur détenue.
    En contango (roll yield < 0), détenir le future coûte."""
    total = 0.0
    for cid, pos in getattr(player, "commodities", {}).items():
        if cid in _BY_ID:
            val = futures_price(market, cid, 1) * MULTIPLIER * pos["qty"]
            total += val * roll_yield(market, cid) * (days / 365.0)
    return total


def holdings(player, market):
    out = []
    for cid, pos in getattr(player, "commodities", {}).items():
        q = quote(market, cid)
        if not q:
            continue
        value = q["front"] * MULTIPLIER * pos["qty"]
        out.append({"id": cid, "name": q["name"], "qty": pos["qty"], "avg": pos["avg"],
                    "price": q["front"], "value": value,
                    "pnl": (q["front"] - pos["avg"]) * MULTIPLIER * pos["qty"]})
    out.sort(key=lambda h: h["value"], reverse=True)
    return out
