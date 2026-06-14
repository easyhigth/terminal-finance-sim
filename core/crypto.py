"""
crypto.py — Crypto-actifs & stablecoin (classe d'actifs distincte, logique pure).

Quelques crypto-actifs fictifs TRÈS volatils + un stablecoin arrimé au dollar
mais exposé au risque de DEPEG (décrochage). Prix déterministes (reconstruits via
graine+pas). Pas de dividende ni de coupon : du pur spot, volatil.

Holdings : PlayerState.crypto = { id : {"qty","avg"} }.
"""
import numpy as np

# (id, nom, prix de base, dérive annuelle, vol annuelle, stablecoin ?)
COINS = [
    ("BITC", "Bitcorn", 60000.0, 0.10, 0.80, False),
    ("ETHR", "Etherus", 3000.0, 0.12, 0.95, False),
    ("SOLR", "Solaris", 150.0, 0.05, 1.20, False),
    ("DOGY", "Dogycoin", 0.15, -0.05, 1.80, False),   # memecoin, espérance négative
    ("USDX", "USDX (stablecoin)", 1.0, 0.0, 0.02, True),
    ("CBDC", "e-Dollar (CBDC)", 1.0, 0.0, 0.0, False),  # monnaie banque centrale : sûre + rémunérée
]
_BY_ID = {c[0]: c for c in COINS}
CBDC_IDS = {"CBDC"}


def is_cbdc(cid):
    return cid in CBDC_IDS
COMMISSION = 0.0015        # frais plus élevés (15 bps)
_path_cache = {}


def _hash(cid):
    h = 0
    for ch in cid:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h


def _path(market, cid, n_steps):
    c = _BY_ID[cid]
    base, drift, vol, stable = c[2], c[3], c[4], c[5]
    seed = (int(getattr(market, "seed", 12345)) + _hash(cid)) & 0xFFFFFFFF
    key = (seed, cid)
    path = _path_cache.get(key)
    if path is None or len(path) <= n_steps:
        rng = np.random.RandomState(seed)
        if stable:
            # arrimé à 1.0 avec bruit faible + rares DEPEG (chute brutale, repeg lent)
            spots, lvl = [1.0], 1.0
            for _ in range(n_steps + 1):
                if rng.random() < 0.004:                # ~depeg occasionnel
                    lvl *= rng.uniform(0.55, 0.8)
                lvl += 0.05 * (1.0 - lvl) + rng.normal(0, 0.004)   # repeg progressif
                spots.append(max(0.2, lvl))
        else:
            mu = drift / 52.0 - 0.5 * (vol / np.sqrt(52)) ** 2
            sig = vol / np.sqrt(52)
            rets = rng.normal(mu, sig, n_steps + 1)
            spots = (base * np.exp(np.cumsum(rets))).tolist()
            spots[0] = base
        path = spots
        _path_cache[key] = path
    return path


def policy_rate(market):
    if market is not None and hasattr(market, "macro"):
        return market.macro["rate"]["v"] / 100.0
    return 0.03


def spot(market, cid):
    if is_cbdc(cid):
        return 1.0                                   # CBDC arrimée 1:1, jamais de depeg
    step = int(getattr(market, "step_count", 0))
    p = _path(market, cid, step)
    return p[step] * (_BY_ID[cid][2] if _BY_ID[cid][5] else 1.0)  # stable: niveau×base(=1)


def quote(market, cid):
    c = _BY_ID.get(cid)
    if not c:
        return None
    sp = spot(market, cid)
    return {"id": cid, "name": c[1], "spot": sp, "vol": c[4], "stable": c[5],
            "cbdc": is_cbdc(cid), "yield": policy_rate(market) if is_cbdc(cid) else 0.0}


def all_quotes(market):
    return [quote(market, c[0]) for c in COINS]


# ---------------------------------------------------------------- trading
def buy(player, market, cid, qty):
    if cid not in _BY_ID:
        return {"ok": False, "reason": "id"}
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    price = spot(market, cid)
    cost = price * qty
    fee = cost * COMMISSION
    if cost + fee > player.cash:
        return {"ok": False, "reason": "cash"}
    player.cash -= (cost + fee)
    pos = player.crypto.get(cid)
    if pos:
        n = pos["qty"] + qty
        pos["avg"] = (pos["qty"] * pos["avg"] + price * qty) / n
        pos["qty"] = n
    else:
        player.crypto[cid] = {"qty": float(qty), "avg": price}
    return {"ok": True, "price": price, "qty": qty, "total": cost + fee}


def sell(player, market, cid, qty):
    pos = player.crypto.get(cid)
    if not pos:
        return {"ok": False, "reason": "noposition"}
    price = spot(market, cid)
    if qty == "ALL" or qty >= pos["qty"]:
        qty = pos["qty"]
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    proceeds = price * qty
    fee = proceeds * COMMISSION
    realized = (price - pos["avg"]) * qty - fee
    player.cash += proceeds - fee
    player.realized_pnl = getattr(player, "realized_pnl", 0.0) + realized
    pos["qty"] -= qty
    if pos["qty"] <= 1e-9:
        del player.crypto[cid]
    return {"ok": True, "price": price, "qty": qty, "realized": realized}


def holdings_value(player, market):
    total = 0.0
    for cid, pos in getattr(player, "crypto", {}).items():
        if cid in _BY_ID:
            total += spot(market, cid) * pos["qty"]
    return total


def interest(player, market, days):
    """Intérêt versé par la CBDC (rémunérée au taux directeur), au prorata."""
    total = 0.0
    rate = policy_rate(market)
    for cid, pos in getattr(player, "crypto", {}).items():
        if is_cbdc(cid):
            total += spot(market, cid) * pos["qty"] * rate * (days / 365.0)
    return total


def holdings(player, market):
    out = []
    for cid, pos in getattr(player, "crypto", {}).items():
        q = quote(market, cid)
        if not q:
            continue
        value = q["spot"] * pos["qty"]
        out.append({"id": cid, "name": q["name"], "qty": pos["qty"], "avg": pos["avg"],
                    "price": q["spot"], "value": value,
                    "pnl": (q["spot"] - pos["avg"]) * pos["qty"]})
    out.sort(key=lambda h: h["value"], reverse=True)
    return out
