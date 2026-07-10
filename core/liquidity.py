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

# Sous stress de marché (stress_level 0..1, cf. Market.last_stress_level —
# même signal que core/portfolio.fill_price, dérivé déterministement de
# l'asymétrie de volatilité et du régime de fond courant), le demi-spread et
# le coefficient d'impact sont tous deux élargis : à stress_level=1.0, le
# demi-spread est multiplié par (1+STRESS_SPREAD_MAX_MULT) et le coefficient
# d'impact par (1+STRESS_IMPACT_MAX_MULT). L'impact réagit plus fort que le
# spread (c'est surtout la PROFONDEUR du carnet qui s'évapore en crise, pas
# seulement la cotation) — cohérent avec IMPACT_STRESS_MAX_MULT=3.0 utilisé
# pour les actions dans core/portfolio.py.
STRESS_SPREAD_MAX_MULT = 1.5
STRESS_IMPACT_MAX_MULT = 3.0


def params(tier):
    """(demi-spread, coefficient d'impact) du tier (replié sur 'Peu liquide')."""
    return _PARAMS.get(tier, _PARAMS["Peu liquide"])


def fill_price(mid, order_value, depth, tier, side, stress_level=0.0):
    """Prix d'exécution = mid ± (demi-spread + impact), l'impact croissant avec
    order_value/depth et étant plafonné — même mécanique que les actions
    (core/portfolio.fill_price), paramétrée par tier de liquidité ET par le
    stress de marché courant (`stress_level`, 0..1, cf. Market.last_stress_level) :
    pour un même ordre, le coût d'exécution est plus élevé en régime
    volatil/récession qu'en marché calme, quelle que soit la classe d'actif."""
    half_spread, impact_k = params(tier)
    stress_frac = min(1.0, max(0.0, stress_level))
    half_spread *= (1.0 + STRESS_SPREAD_MAX_MULT * stress_frac)
    impact_k *= (1.0 + STRESS_IMPACT_MAX_MULT * stress_frac)
    impact = min(MAX_SLIPPAGE, impact_k * (order_value / depth)) if depth > 0 else 0.0
    cost_frac = half_spread + impact
    return mid * (1 + cost_frac) if side == "buy" else mid * (1 - cost_frac)


DEPTH_CLIPS = (10e3, 50e3, 250e3, 1e6, 5e6)     # tailles d'ordre (en devise)


def depth_ladder(market, ticker, clips=DEPTH_CLIPS):
    """PROFONDEUR DE CARNET simulée : le modèle de microstructure du jeu
    (spread par tier + impact Almgren-Chriss, cf. core/portfolio.fill_price)
    rendu VISIBLE — pour chaque taille d'ordre cumulée, le prix d'exécution
    à l'achat (ask) et à la vente (bid), et le coût en points de base. Un
    gros ordre « mange » le carnet ; le carnet est plus mince sur une
    petite capi et en crise. None si ticker inconnu."""
    from core import portfolio as pf
    mid = market.price_of(ticker)
    if mid is None or mid <= 0:
        return None
    rows = []
    for clip in clips:
        qty = clip / mid
        ask = pf.fill_price(market, ticker, qty, "buy")
        bid = pf.fill_price(market, ticker, qty, "sell")
        rows.append({"clip": clip, "ask": ask, "bid": bid,
                     "cost_bps": (ask - mid) / mid * 1e4})
    return {"mid": mid, "tier": equity_tier(market, ticker), "rows": rows,
            "stress": min(1.0, max(0.0, getattr(market, "last_stress_level", 0.0)))}


def equity_tier(market, ticker):
    """Tier de liquidité actions, dérivé de la capitalisation (profondeur)."""
    i = market.ticker_idx.get(ticker)
    if i is None:
        return "Peu liquide"
    cap = float(market.price[i] * market.shares[i])
    return equity_tier_for_cap(cap)


def equity_tier_for_cap(cap):
    """Tier par capitalisation. UNITÉ : les capitalisations du jeu
    (`market.price × market.shares`, `metrics()['mktcap']`) sont en
    MILLIONS — les seuils aussi (20e3 = 20 Md, 3e3 = 3 Md). Les anciens
    seuils étaient exprimés en unités (20e9/3e9) : × 10⁶ trop hauts, TOUTES
    les actions du roster tombaient en « Illiquide » (spread max pour tout
    le monde, même les méga-capis)."""
    if cap >= 20e3:
        return "Liquide"
    if cap >= 3e3:
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


# ------------------------------------------------------------ crypto-actifs
# Carnet bien plus mince que les grandes capi actions ou les souverains notés :
# même les plus grosses crypto-actifs (BITC/ETHR) restent "Peu liquide" ; les
# petites caps spéculatives (SOLR/DOGY) sont "Illiquide". Le stablecoin et la
# CBDC sont arrimés et très profonds (cotation quasi 1:1, peu de slippage).
_LIQUID_CRYPTO_IDS = {"USDX", "CBDC"}
_ILLIQUID_CRYPTO_IDS = {"SOLR", "DOGY"}

_CRYPTO_DEPTH = {
    "BITC": 800_000_000.0,
    "ETHR": 400_000_000.0,
    "SOLR": 60_000_000.0,
    "DOGY": 20_000_000.0,
    "USDX": 2_000_000_000.0,
    "CBDC": 5_000_000_000.0,
}


def crypto_tier(cid):
    if cid in _LIQUID_CRYPTO_IDS:
        return "Liquide"
    if cid in _ILLIQUID_CRYPTO_IDS:
        return "Illiquide"
    return "Peu liquide"


def crypto_depth(cid):
    return _CRYPTO_DEPTH.get(cid, 50_000_000.0)
