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

from core import liquidity as liq_mod

# (id, nom, spot de base, dérive annuelle, vol annuelle, pente de courbe annuelle, catégorie)
COMMODITIES = [
    # ---- Métaux précieux (7) ----
    ("GOLD", "Or (once)", 2000.0, 0.03, 0.15, -0.01, "Métaux précieux"),     # léger backwardation
    ("SILV", "Argent (once)", 24.0, 0.02, 0.30, -0.005, "Métaux précieux"),
    ("PLAT", "Platine (once)", 950.0, 0.01, 0.25, 0.01, "Métaux précieux"),
    ("PALL", "Palladium (once)", 1100.0, -0.02, 0.35, 0.02, "Métaux précieux"),
    ("RHOD", "Rhodium (once)", 4500.0, 0.0, 0.55, 0.03, "Métaux précieux"),
    ("IRID", "Iridium (once)", 4800.0, 0.01, 0.40, 0.02, "Métaux précieux"),
    ("RUTH", "Ruthénium (once)", 450.0, 0.0, 0.45, 0.02, "Métaux précieux"),

    # ---- Énergie (17) ----
    ("OIL",  "Pétrole WTI (baril)", 80.0, 0.01, 0.35, 0.06, "Énergie"),  # contango marqué
    ("BRENT", "Pétrole Brent (baril)", 84.0, 0.01, 0.33, 0.05, "Énergie"),
    ("GAS",  "Gaz naturel Henry Hub (MMBtu)", 3.0, 0.0, 0.55, 0.10, "Énergie"),  # fort contango, très volatil
    ("TTF",  "Gaz naturel TTF Europe (MWh)", 35.0, 0.0, 0.50, 0.08, "Énergie"),
    ("JKM",  "GNL Asie JKM (MMBtu)", 12.0, 0.0, 0.45, 0.07, "Énergie"),
    ("HEAT", "Fioul domestique (gallon)", 2.8, 0.01, 0.32, 0.05, "Énergie"),
    ("GASO", "Essence RBOB (gallon)", 2.5, 0.01, 0.34, 0.05, "Énergie"),
    ("DIES", "Diesel (gallon)", 3.0, 0.01, 0.30, 0.04, "Énergie"),
    ("PROP", "Propane (gallon)", 0.9, 0.0, 0.40, 0.06, "Énergie"),
    ("URAN", "Uranium (livre U3O8)", 75.0, 0.04, 0.30, -0.02, "Énergie"),
    ("COAL", "Charbon thermique (tonne)", 130.0, 0.0, 0.35, 0.02, "Énergie"),
    ("COKE", "Charbon à coke (tonne)", 220.0, 0.0, 0.33, 0.02, "Énergie"),
    ("ETOH", "Éthanol (gallon)", 2.1, 0.0, 0.25, 0.03, "Énergie"),
    ("BIOD", "Biodiesel (gallon)", 4.2, 0.0, 0.28, 0.03, "Énergie"),
    ("CARB", "Crédits carbone EUA (tonne CO2)", 65.0, 0.05, 0.40, -0.03, "Énergie"),
    ("RIN",  "Crédits RIN biocarburant", 1.2, 0.0, 0.45, 0.0, "Énergie"),
    ("PETC", "Coke de pétrole (tonne)", 95.0, 0.0, 0.30, 0.02, "Énergie"),

    # ---- Métaux industriels (21) ----
    ("COPP", "Cuivre (tonne)", 8500.0, 0.02, 0.25, 0.03, "Métaux industriels"),
    ("ALUM", "Aluminium (tonne)", 2300.0, 0.01, 0.22, 0.02, "Métaux industriels"),
    ("ZINC", "Zinc (tonne)", 2700.0, 0.01, 0.28, 0.02, "Métaux industriels"),
    ("NICK", "Nickel (tonne)", 17000.0, 0.0, 0.40, 0.03, "Métaux industriels"),
    ("LEAD", "Plomb (tonne)", 2100.0, 0.0, 0.24, 0.01, "Métaux industriels"),
    ("TIN",  "Étain (tonne)", 26000.0, 0.0, 0.35, 0.02, "Métaux industriels"),
    ("STEEL", "Acier (tonne)", 700.0, 0.0, 0.20, 0.01, "Métaux industriels"),
    ("IRON", "Minerai de fer (tonne)", 110.0, 0.0, 0.30, 0.01, "Métaux industriels"),
    ("MANG", "Manganèse (tonne)", 1500.0, 0.0, 0.25, 0.01, "Métaux industriels"),
    ("CHRO", "Chrome (tonne)", 9000.0, 0.0, 0.30, 0.01, "Métaux industriels"),
    ("MOLY", "Molybdène (tonne)", 40000.0, 0.0, 0.35, 0.02, "Métaux industriels"),
    ("COBT", "Cobalt (tonne)", 33000.0, 0.02, 0.45, 0.0, "Métaux industriels"),
    ("TUNG", "Tungstène (tonne)", 32000.0, 0.0, 0.30, 0.01, "Métaux industriels"),
    ("ANTM", "Antimoine (tonne)", 13000.0, 0.0, 0.35, 0.01, "Métaux industriels"),
    ("BISM", "Bismuth (tonne)", 8500.0, 0.0, 0.30, 0.01, "Métaux industriels"),
    ("CADM", "Cadmium (tonne)", 3000.0, 0.0, 0.35, 0.01, "Métaux industriels"),
    ("MAGN", "Magnésium (tonne)", 2500.0, 0.0, 0.30, 0.01, "Métaux industriels"),
    ("TITAN", "Titane (tonne)", 5500.0, 0.0, 0.28, 0.01, "Métaux industriels"),
    ("SILI", "Silicium métal (tonne)", 2600.0, 0.0, 0.32, 0.01, "Métaux industriels"),
    ("GALL", "Gallium (kg)", 280.0, 0.02, 0.40, 0.0, "Métaux industriels"),
    ("GERM", "Germanium (kg)", 1500.0, 0.0, 0.40, 0.0, "Métaux industriels"),

    # ---- Minéraux stratégiques (14) ----
    ("LITH", "Lithium carbonate (tonne)", 14000.0, 0.03, 0.50, -0.02, "Minéraux stratégiques"),
    ("REE",  "Terres rares — panier (tonne)", 60000.0, 0.0, 0.45, 0.0, "Minéraux stratégiques"),
    ("NEOD", "Néodyme (tonne)", 80000.0, 0.0, 0.40, 0.0, "Minéraux stratégiques"),
    ("PRAS", "Praséodyme (tonne)", 75000.0, 0.0, 0.40, 0.0, "Minéraux stratégiques"),
    ("DYSP", "Dysprosium (tonne)", 250000.0, 0.0, 0.45, 0.0, "Minéraux stratégiques"),
    ("GRAP", "Graphite (tonne)", 900.0, 0.01, 0.30, 0.0, "Minéraux stratégiques"),
    ("POTA", "Potasse (tonne)", 350.0, 0.0, 0.30, 0.01, "Minéraux stratégiques"),
    ("PHOS", "Phosphate (tonne)", 150.0, 0.0, 0.28, 0.01, "Minéraux stratégiques"),
    ("BORA", "Borate (tonne)", 400.0, 0.0, 0.25, 0.01, "Minéraux stratégiques"),
    ("FLUO", "Spath fluor (tonne)", 380.0, 0.0, 0.30, 0.01, "Minéraux stratégiques"),
    ("BARY", "Baryte (tonne)", 120.0, 0.0, 0.20, 0.01, "Minéraux stratégiques"),
    ("TALC", "Talc (tonne)", 250.0, 0.0, 0.18, 0.0, "Minéraux stratégiques"),
    ("MICA", "Mica (tonne)", 600.0, 0.0, 0.20, 0.0, "Minéraux stratégiques"),
    ("VANA", "Vanadium (tonne)", 28000.0, 0.0, 0.45, 0.0, "Minéraux stratégiques"),

    # ---- Céréales & oléagineux (14) ----
    ("WHEAT", "Blé (boisseau)", 6.0, 0.0, 0.30, 0.04, "Céréales & oléagineux"),
    ("CORN", "Maïs (boisseau)", 4.5, 0.0, 0.28, 0.03, "Céréales & oléagineux"),
    ("SOYB", "Soja (boisseau)", 13.0, 0.0, 0.30, 0.03, "Céréales & oléagineux"),
    ("SOYM", "Tourteau de soja (tonne)", 380.0, 0.0, 0.30, 0.03, "Céréales & oléagineux"),
    ("SOYO", "Huile de soja (livre)", 0.55, 0.0, 0.32, 0.03, "Céréales & oléagineux"),
    ("RICE", "Riz (cwt)", 17.0, 0.0, 0.25, 0.02, "Céréales & oléagineux"),
    ("OATS", "Avoine (boisseau)", 3.8, 0.0, 0.30, 0.02, "Céréales & oléagineux"),
    ("CANO", "Canola (tonne)", 600.0, 0.0, 0.28, 0.02, "Céréales & oléagineux"),
    ("PALM", "Huile de palme (tonne)", 950.0, 0.0, 0.35, 0.02, "Céréales & oléagineux"),
    ("SUNO", "Huile de tournesol (tonne)", 1100.0, 0.0, 0.33, 0.02, "Céréales & oléagineux"),
    ("RAPE", "Colza (tonne)", 580.0, 0.0, 0.28, 0.02, "Céréales & oléagineux"),
    ("BARL", "Orge (tonne)", 220.0, 0.0, 0.26, 0.02, "Céréales & oléagineux"),
    ("RYE",  "Seigle (boisseau)", 5.5, 0.0, 0.27, 0.02, "Céréales & oléagineux"),
    ("SORG", "Sorgho (boisseau)", 4.2, 0.0, 0.27, 0.02, "Céréales & oléagineux"),

    # ---- Softs & tropicaux (15) ----
    ("COFA", "Café Arabica (livre)", 1.8, 0.0, 0.35, 0.02, "Softs & tropicaux"),
    ("COFR", "Café Robusta (tonne)", 2300.0, 0.0, 0.35, 0.02, "Softs & tropicaux"),
    ("COCO", "Cacao (tonne)", 3000.0, 0.05, 0.45, -0.02, "Softs & tropicaux"),
    ("SUGA", "Sucre n°11 (livre)", 0.20, 0.0, 0.30, 0.02, "Softs & tropicaux"),
    ("COTT", "Coton (livre)", 0.85, 0.0, 0.30, 0.02, "Softs & tropicaux"),
    ("ORAN", "Jus d'orange concentré (livre)", 2.0, 0.0, 0.35, 0.0, "Softs & tropicaux"),
    ("RUBB", "Caoutchouc naturel (kg)", 1.5, 0.0, 0.35, 0.0, "Softs & tropicaux"),
    ("LUMB", "Bois de construction (1000 pi.pl.)", 480.0, 0.0, 0.45, 0.0, "Softs & tropicaux"),
    ("WOOL", "Laine (kg)", 12.0, 0.0, 0.25, 0.0, "Softs & tropicaux"),
    ("SILK", "Soie (kg)", 45.0, 0.0, 0.25, 0.0, "Softs & tropicaux"),
    ("TEA",  "Thé (kg)", 2.8, 0.0, 0.25, 0.0, "Softs & tropicaux"),
    ("VANI", "Vanille (kg)", 120.0, 0.0, 0.50, 0.0, "Softs & tropicaux"),
    ("PEPP", "Poivre (tonne)", 4500.0, 0.0, 0.30, 0.0, "Softs & tropicaux"),
    ("CAJU", "Noix de cajou (tonne)", 1300.0, 0.0, 0.30, 0.0, "Softs & tropicaux"),
    ("ALMD", "Amandes (livre)", 2.5, 0.0, 0.28, 0.0, "Softs & tropicaux"),

    # ---- Bétail & laitier (9) ----
    ("CATL", "Bovins vivants (livre)", 1.8, 0.0, 0.20, 0.01, "Bétail & laitier"),
    ("FCAT", "Bovins maigres — feeder (livre)", 2.4, 0.0, 0.22, 0.01, "Bétail & laitier"),
    ("HOGS", "Porcs maigres (livre)", 0.85, 0.0, 0.30, 0.01, "Bétail & laitier"),
    ("PORK", "Longes de porc (livre)", 0.95, 0.0, 0.28, 0.0, "Bétail & laitier"),
    ("MILK", "Lait classe III (cwt)", 17.0, 0.0, 0.25, 0.0, "Bétail & laitier"),
    ("BUTT", "Beurre (livre)", 2.5, 0.0, 0.30, 0.0, "Bétail & laitier"),
    ("CHES", "Fromage cheddar (livre)", 1.9, 0.0, 0.28, 0.0, "Bétail & laitier"),
    ("WHEY", "Lactosérum (livre)", 0.55, 0.0, 0.30, 0.0, "Bétail & laitier"),
    ("EGGS", "Œufs (douzaine)", 2.2, 0.0, 0.40, 0.0, "Bétail & laitier"),

    # ---- Matériaux & construction (11) ----
    ("CEMT", "Ciment (tonne)", 130.0, 0.0, 0.15, 0.0, "Matériaux & construction"),
    ("GYPS", "Gypse (tonne)", 25.0, 0.0, 0.15, 0.0, "Matériaux & construction"),
    ("SAND", "Sable industriel (tonne)", 35.0, 0.0, 0.15, 0.0, "Matériaux & construction"),
    ("GRAV", "Gravier (tonne)", 18.0, 0.0, 0.12, 0.0, "Matériaux & construction"),
    ("GLAS", "Verre plat (tonne)", 700.0, 0.0, 0.18, 0.0, "Matériaux & construction"),
    ("BRIC", "Brique (millier)", 450.0, 0.0, 0.15, 0.0, "Matériaux & construction"),
    ("ASPH", "Asphalte / bitume (tonne)", 480.0, 0.0, 0.25, 0.01, "Matériaux & construction"),
    ("PVC",  "PVC (tonne)", 1100.0, 0.0, 0.30, 0.01, "Matériaux & construction"),
    ("POLY", "Polyéthylène (tonne)", 1300.0, 0.0, 0.30, 0.01, "Matériaux & construction"),
    ("RESI", "Résine époxy (tonne)", 2800.0, 0.0, 0.30, 0.01, "Matériaux & construction"),
    ("INSU", "Laine isolante (tonne)", 1500.0, 0.0, 0.20, 0.0, "Matériaux & construction"),

    # ---- Exotiques & environnement (7) ----
    ("WATR", "Droits d'eau Californie (acre-pied)", 500.0, 0.0, 0.40, 0.0, "Exotiques & environnement"),
    ("FRGT", "Frêt sec en vrac — Baltic Dry (indice)", 1500.0, 0.0, 0.45, 0.0, "Exotiques & environnement"),
    ("DIAM", "Diamants industriels (carat)", 150.0, 0.0, 0.30, 0.0, "Exotiques & environnement"),
    ("HELI", "Hélium (Mcf)", 350.0, 0.0, 0.30, 0.0, "Exotiques & environnement"),
    ("NEON", "Néon (m³)", 800.0, 0.05, 0.50, 0.0, "Exotiques & environnement"),
    ("PLAS", "Déchets plastiques recyclés (tonne)", 250.0, 0.0, 0.35, 0.0, "Exotiques & environnement"),
    ("SOLA", "Crédits énergie solaire — REC (MWh)", 20.0, 0.0, 0.40, 0.0, "Exotiques & environnement"),
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


def history(market, cid, n=None):
    """Historique de spot complet (depuis l'origine) d'une commodity.
    `n` borne au dernier n points si fourni. Retourne une liste de floats."""
    if cid not in _BY_ID:
        return []
    step = int(getattr(market, "step_count", 0))
    path = _path(market, cid, step)[:step + 1]
    return path[-n:] if n else path


def quote(market, cid):
    c = _BY_ID.get(cid)
    if not c:
        return None
    sp = spot(market, cid)
    front = futures_price(market, cid, 1)
    structure = "Contango" if c[5] > 0 else "Backwardation" if c[5] < 0 else "Plate"
    return {"id": cid, "name": c[1], "spot": sp, "front": front,
            "slope": c[5], "structure": structure, "roll_yield": roll_yield(market, cid),
            "vol": c[4], "category": c[6], "liquidity": liq_mod.commodity_tier(c[6])}


def all_quotes(market):
    return [quote(market, c[0]) for c in COMMODITIES]


# ---------------------------------------------------------------- trading
def _contract_value(market, cid, qty):
    return futures_price(market, cid, 1) * MULTIPLIER * qty


def fill_price(market, cid, qty, side):
    """Prix d'exécution réel (spread + impact de marché, calibrés par tier de
    liquidité — métaux précieux/énergie liquides vs. minéraux stratégiques et
    exotiques illiquides, cf. core/liquidity.py) ET par le stress de marché courant
    (market.last_stress_level, 0..1) : un même ordre coûte plus cher en régime
    volatil/récession qu'en marché calme, comme pour les actions et obligations.
    Le prix coté (`quote()["front"]`) reste le mid utilisé pour la valorisation."""
    c = _BY_ID.get(cid)
    if not c:
        return None
    mid = futures_price(market, cid, 1)
    order_value = mid * MULTIPLIER * abs(qty)
    category = c[6]
    stress_level = getattr(market, "last_stress_level", 0.0)
    return liq_mod.fill_price(mid, order_value, liq_mod.commodity_depth(category),
                               liq_mod.commodity_tier(category), side, stress_level)


def buy(player, market, cid, qty):
    if cid not in _BY_ID:
        return {"ok": False, "reason": "id"}
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    price = fill_price(market, cid, qty, "buy")
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
    if qty == "ALL" or qty >= pos["qty"]:
        qty = pos["qty"]
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    price = fill_price(market, cid, qty, "sell")
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
