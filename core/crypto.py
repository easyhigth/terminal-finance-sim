"""
crypto.py — Crypto-actifs & stablecoin (classe d'actifs distincte, logique pure).

Quelques crypto-actifs fictifs TRÈS volatils + un stablecoin arrimé au dollar
mais exposé au risque de DEPEG (décrochage). Prix déterministes (reconstruits via
graine+pas). Pas de dividende ni de coupon : du pur spot, volatil.

Contagion : quand le stablecoin DEPEG, un facteur de stress partagé ("F_contagion",
même esprit que les chocs de facteurs du moteur de marché — cf. core/market.py)
augmente la probabilité/magnitude de stress des autres crypto-actifs corrélés
(actuellement le groupe "non-stable, non-CBDC" : BITC/ETHR/SOLR/DOGY). Tout passe
par le rng seedé par (market.seed, cid) : aucun aléa non reproductible.

Holdings : PlayerState.crypto = { id : {"qty","avg"} }.
"""
import numpy as np

from core import liquidity as liq_mod

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
STABLE_IDS = {c[0] for c in COINS if c[5]}
# Groupe corrélé exposé à la contagion d'un depeg de stablecoin (ni stable, ni CBDC :
# la CBDC est garantie par la banque centrale, jamais affectée).
CONTAGION_GROUP = {c[0] for c in COINS if not c[5] and c[0] not in CBDC_IDS}

CONTAGION_VOL_MULT = 1.8     # multiplicateur de vol hebdo sur un pas sous stress
CONTAGION_DRIFT = -0.12      # choc de drift hebdo additionnel (négatif) sous stress
CONTAGION_DECAY = 0.6        # le facteur de stress se résorbe d'un pas à l'autre


def is_cbdc(cid):
    return cid in CBDC_IDS
COMMISSION = 0.0015        # frais plus élevés (15 bps)
_path_cache = {}
_stress_cache = {}


def _hash(cid):
    h = 0
    for ch in cid:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h


def _stress_factor(market, n_steps):
    """Facteur de stress de contagion F_contagion[t], dérivé déterministement des
    pas de DEPEG de chaque stablecoin (boucle de rétroaction comme les chocs de
    facteurs du marché). Reconstruit à partir de (seed, n_steps) ; mis en cache."""
    seed = int(getattr(market, "seed", 12345)) & 0xFFFFFFFF
    key = (seed, n_steps)
    cached = _stress_cache.get(key)
    if cached is not None and len(cached) > n_steps:
        return cached
    n = n_steps + 1
    stress = np.zeros(n)
    for sid in STABLE_IDS:
        path = _path(market, sid, n_steps)
        lvl = np.asarray(path[:n])
        depeg_mask = lvl < 0.95
        for t in range(1, n):
            # le stress décroît puis est relevé par un depeg actif à ce pas
            stress[t] = max(stress[t] * CONTAGION_DECAY, stress[t - 1] * CONTAGION_DECAY)
            if depeg_mask[t]:
                stress[t] = max(stress[t], 1.0 - lvl[t])    # plus le decrochage est fort, plus le stress est haut
    _stress_cache[key] = stress
    return stress


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
            if cid in CONTAGION_GROUP:
                # contagion : un facteur de stress partagé (issu des depegs de
                # stablecoin) augmente la vol et tire le drift à la baisse sur les
                # pas concernés — toujours via le même rng seedé (déterministe).
                stress = _stress_factor(market, n_steps)[:n_steps + 1]
                rets = np.empty(n_steps + 1)
                for t in range(n_steps + 1):
                    s = stress[t] if t < len(stress) else 0.0
                    rets[t] = rng.normal(mu + CONTAGION_DRIFT * s,
                                          sig * (1.0 + CONTAGION_VOL_MULT * s))
            else:
                rets = rng.normal(mu, sig, n_steps + 1)
            spots = (base * np.exp(np.cumsum(rets))).tolist()
            spots[0] = base
        path = spots
        _path_cache[key] = path
    return path


def contagion_risk(market, cid):
    """Niveau de stress de contagion [0..1] affectant cid au pas courant (0 si
    hors du groupe corrélé ou si aucun depeg n'est actif)."""
    if cid not in CONTAGION_GROUP:
        return 0.0
    step = int(getattr(market, "step_count", 0))
    stress = _stress_factor(market, step)
    t = min(step, len(stress) - 1)
    return float(stress[t])


def active_depegs(market):
    """Liste des stablecoins actuellement décrochés (spot < 0.95)."""
    out = []
    for sid in STABLE_IDS:
        if spot(market, sid) < 0.95:
            out.append(sid)
    return out


def name(cid):
    """Nom affichable d'un actif (pour l'UI, sans exposer _BY_ID)."""
    c = _BY_ID.get(cid)
    return c[1] if c else cid


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


def history(market, cid, n=None):
    """Historique de spot complet (depuis l'origine) d'un crypto-actif.
    `n` borne au dernier n points si fourni. Retourne une liste de floats."""
    if cid not in _BY_ID:
        return []
    step = int(getattr(market, "step_count", 0))
    if is_cbdc(cid):
        path = [1.0] * (step + 1)
        return path[-n:] if n else path
    c = _BY_ID[cid]
    raw = _path(market, cid, step)[:step + 1]
    factor = c[2] if c[5] else 1.0   # stable: niveau×base ; sinon le path est déjà au prix
    path = [v * factor for v in raw]
    return path[-n:] if n else path


def quote(market, cid):
    c = _BY_ID.get(cid)
    if not c:
        return None
    sp = spot(market, cid)
    return {"id": cid, "name": c[1], "spot": sp, "vol": c[4], "stable": c[5],
            "cbdc": is_cbdc(cid), "yield": policy_rate(market) if is_cbdc(cid) else 0.0,
            "liquidity": liq_mod.crypto_tier(cid)}


def all_quotes(market):
    return [quote(market, c[0]) for c in COINS]


# ---------------------------------------------------------------- trading
def fill_price(market, cid, qty, side):
    """Prix d'exécution réel = spot ± (demi-spread + impact), calibrés par tier de
    liquidité (cf. core/liquidity.py) et par le stress de marché courant
    (market.last_stress_level, 0..1) — même mécanique que les actions/obligations/
    matières premières. La CBDC (monnaie banque centrale, garantie, rémunérée) est
    exécutée au pair sans spread ni impact : ce n'est pas un actif de marché, c'est
    un dépôt. Le stablecoin et les crypto-actifs volatils, eux, ont un carnet bien
    plus mince que les grandes capi actions ou les souverains notés (cf.
    core/liquidity.crypto_tier) : un même ordre y coûte plus cher."""
    if is_cbdc(cid):
        return spot(market, cid)
    mid = spot(market, cid)
    if mid is None:
        return None
    order_value = mid * abs(qty)
    stress_level = getattr(market, "last_stress_level", 0.0)
    return liq_mod.fill_price(mid, order_value, liq_mod.crypto_depth(cid),
                               liq_mod.crypto_tier(cid), side, stress_level)


def buy(player, market, cid, qty):
    if cid not in _BY_ID:
        return {"ok": False, "reason": "id"}
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    price = fill_price(market, cid, qty, "buy")
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
    if qty == "ALL" or qty >= pos["qty"]:
        qty = pos["qty"]
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    price = fill_price(market, cid, qty, "sell")
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
