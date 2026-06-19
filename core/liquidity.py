"""
liquidity.py — Modèle de liquidité partagé entre classes d'actifs (logique pure).

Les actions ont déjà un modèle d'exécution réaliste (spread + impact de marché
croissant avec la taille, core/portfolio.fill_price) calibré sur la capitalisation
boursière comme proxy de profondeur. Ce module généralise le même mécanisme
(demi-spread + impact = f(taille de l'ordre / profondeur)) aux obligations et aux
matières premières, et y ajoute un TIER explicite (« Liquide » / « Peu liquide »
/ « Illiquide ») afin que la différence liquide/illiquide soit visible dans le
prix d'exécution, dans l'ordre lui-même et dans le reporting de risque — plutôt
que de rester une simple conséquence implicite d'une formule.
"""

TIERS = ("Liquide", "Peu liquide", "Illiquide")

# (demi-spread, coefficient d'impact) par tier — le tier "Liquide" reste proche
# du calibrage actions existant (HALF_SPREAD=0.0008, IMPACT_K~0.12 dans
# core/portfolio.py) ; les tiers moins profonds pénalisent nettement plus.
_PARAMS = {
    "Liquide":     (0.0008, 0.08),
    "Peu liquide": (0.0025, 0.20),
    "Illiquide":   (0.0060, 0.45),
}
MAX_SLIPPAGE = 0.08


def params(tier):
    """(demi-spread, coefficient d'impact) du tier (replié sur 'Peu liquide')."""
    return _PARAMS.get(tier, _PARAMS["Peu liquide"])


def fill_price(mid, order_value, depth, tier, side):
    """Prix d'exécution = mid ± (demi-spread + impact), l'impact croissant avec
    order_value/depth et étant plafonné — même mécanique que les actions
    (core/portfolio.fill_price), paramétrée par tier de liquidité."""
    half_spread, impact_k = params(tier)
    impact = min(MAX_SLIPPAGE, impact_k * (order_value / depth)) if depth > 0 else 0.0
    cost_frac = half_spread + impact
    return mid * (1 + cost_frac) if side == "buy" else mid * (1 - cost_frac)


def equity_tier(market, ticker):
    """Tier de liquidité actions, dérivé de la capitalisation (profondeur)."""
    i = market.ticker_idx.get(ticker)
    if i is None:
        return "Peu liquide"
    cap = float(market.price[i] * market.shares[i])
    return equity_tier_for_cap(cap)


def equity_tier_for_cap(cap):
    if cap >= 20e9:
        return "Liquide"
    if cap >= 3e9:
        return "Peu liquide"
    return "Illiquide"


# ------------------------------------------------------------ obligations
_BOND_RATING_FACTOR = {"AAA": 1.0, "AA": 0.9, "A": 0.75, "BBB": 0.55, "BB": 0.35, "B": 0.20}


def bond_tier(bond):
    """Souverains notés (AAA/AA/A) très liquides ; souverains spéculatifs et
    corporate investment grade peu liquides ; corporate high yield illiquide."""
    if bond["kind"] == "Souverain":
        return "Liquide" if bond["rating"] in ("AAA", "AA", "A") else "Peu liquide"
    return "Peu liquide" if bond["rating"] in ("AAA", "AA", "A", "BBB") else "Illiquide"


def bond_depth(bond):
    """Profondeur de marché notionnelle (proxy) : souverains nettement plus
    profonds que les corporates, dégradée par le risque de crédit du rating."""
    base = 200_000_000.0 if bond["kind"] == "Souverain" else 20_000_000.0
    return base * _BOND_RATING_FACTOR.get(bond["rating"], 0.5)


# ------------------------------------------------------------ matières premières
_LIQUID_COMMODITY_CATEGORIES = {"Métaux précieux", "Énergie"}
_ILLIQUID_COMMODITY_CATEGORIES = {"Minéraux stratégiques", "Exotiques & environnement"}

_COMMODITY_DEPTH = {
    "Métaux précieux": 3_000_000_000.0,
    "Énergie": 5_000_000_000.0,
    "Métaux industriels": 1_000_000_000.0,
    "Minéraux stratégiques": 80_000_000.0,
    "Céréales & oléagineux": 500_000_000.0,
    "Softs & tropicaux": 200_000_000.0,
    "Bétail & laitier": 200_000_000.0,
    "Matériaux & construction": 150_000_000.0,
    "Exotiques & environnement": 50_000_000.0,
}


def commodity_tier(category):
    if category in _LIQUID_COMMODITY_CATEGORIES:
        return "Liquide"
    if category in _ILLIQUID_COMMODITY_CATEGORIES:
        return "Illiquide"
    return "Peu liquide"


def commodity_depth(category):
    return _COMMODITY_DEPTH.get(category, 150_000_000.0)
