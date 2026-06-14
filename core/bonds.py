"""
bonds.py — Marché obligataire tradable (logique pure, sans pygame).

Univers déterministe d'obligations souveraines et corporate. Chaque obligation
est pricée via core/finmath au rendement exigé = niveau de la courbe (taux
directeur macro + prime de terme) + spread de crédit selon le rating. Quand les
taux bougent (macro), les prix obligataires bougent en sens inverse — la
duration et la convexité deviennent réellement jouables. Les coupons sont versés
à chaque tour.

Holdings : PlayerState.bonds = { bond_id : {"qty": nb d'obligations, "avg": prix moyen} }.
Nominal (face) = 1000 par obligation.
"""
from core import finmath

FACE = 1000.0
COMMISSION = 0.0005       # 5 bps sur le notionnel échangé
TERM_PREMIUM = 0.0015     # prime de terme par année de maturité

# Spread de crédit par rating (sur le niveau de la courbe).
_RATING_SPREAD = {"AAA": 0.002, "AA": 0.004, "A": 0.007,
                  "BBB": 0.013, "BB": 0.030, "B": 0.055}

# (id, nom, émetteur, région, type, rating, coupon, maturité)
BONDS = [
    ("UST10", "Trésor US 10 ans", "Trésor américain", "USA", "Souverain", "AAA", 0.040, 10),
    ("UST2",  "Trésor US 2 ans", "Trésor américain", "USA", "Souverain", "AAA", 0.038, 2),
    ("BUND10", "Bund 10 ans", "État allemand", "Europe", "Souverain", "AAA", 0.028, 10),
    ("OAT10", "OAT 10 ans", "État français", "Europe", "Souverain", "AA", 0.030, 10),
    ("JGB10", "JGB 10 ans", "État japonais", "Asia", "Souverain", "AA", 0.010, 10),
    ("EM10",  "Souverain émergent 10 ans", "État émergent", "Am.Sud", "Souverain", "BB", 0.075, 10),
    ("CORP_IG", "Corporate IG 7 ans", "Grande capi notée A", "USA", "Corporate", "A", 0.050, 7),
    ("CORP_IG2", "Corporate IG 5 ans", "Industrielle BBB", "Europe", "Corporate", "BBB", 0.055, 5),
    ("CORP_HY", "High Yield 5 ans", "Émetteur spéculatif", "USA", "Corporate", "B", 0.090, 5),
    ("CORP_HY2", "High Yield 4 ans", "LBO mid-cap", "Europe", "Corporate", "BB", 0.080, 4),
    ("BANK_T2", "Dette subordonnée bancaire", "Banque systémique", "Europe", "Corporate", "BBB", 0.065, 8),
    ("GREEN", "Green bond 6 ans", "Utility verte", "Europe", "Corporate", "A", 0.045, 6),
]
_BY_ID = {b[0]: b for b in BONDS}


def base_yield_level(market):
    """Niveau de référence de la courbe : taux directeur macro (en décimal)."""
    if market is not None and hasattr(market, "macro"):
        return market.macro["rate"]["v"] / 100.0
    return 0.03


def ytm(market, bond_id):
    """Rendement exigé d'une obligation = courbe + prime de terme + spread crédit."""
    b = _BY_ID[bond_id]
    _, _, _, _, _, rating, _, years = b
    return base_yield_level(market) + TERM_PREMIUM * years + _RATING_SPREAD.get(rating, 0.02)


def quote(market, bond_id):
    """Cotation complète d'une obligation : prix, YTM, duration, convexité."""
    b = _BY_ID.get(bond_id)
    if not b:
        return None
    bid, name, issuer, region, kind, rating, coupon, years = b
    y = ytm(market, bond_id)
    price = finmath.bond_price(FACE, coupon, y, years)
    dur = finmath.bond_modified_duration(FACE, coupon, y, years)
    conv = finmath.bond_convexity(FACE, coupon, y, years)
    return {"id": bid, "name": name, "issuer": issuer, "region": region, "kind": kind,
            "rating": rating, "coupon": coupon, "years": years,
            "ytm": y, "price": price, "mod_duration": dur, "convexity": conv}


def all_quotes(market):
    return [quote(market, b[0]) for b in BONDS]


# ---------------------------------------------------------------- trading
def buy_bond(player, market, bond_id, qty):
    q = quote(market, bond_id)
    if q is None:
        return {"ok": False, "reason": "id"}
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    cost = q["price"] * qty
    fee = cost * COMMISSION
    total = cost + fee
    if total > player.cash:
        return {"ok": False, "reason": "cash", "need": total}
    player.cash -= total
    pos = player.bonds.get(bond_id)
    if pos:
        n = pos["qty"] + qty
        pos["avg"] = (pos["qty"] * pos["avg"] + cost) / n
        pos["qty"] = n
    else:
        player.bonds[bond_id] = {"qty": float(qty), "avg": q["price"]}
    return {"ok": True, "price": q["price"], "qty": qty, "total": total, "fee": fee}


def sell_bond(player, market, bond_id, qty):
    pos = player.bonds.get(bond_id)
    if not pos:
        return {"ok": False, "reason": "noposition"}
    q = quote(market, bond_id)
    if qty == "ALL" or qty >= pos["qty"]:
        qty = pos["qty"]
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    proceeds = q["price"] * qty
    fee = proceeds * COMMISSION
    net = proceeds - fee
    realized = (q["price"] - pos["avg"]) * qty - fee
    player.cash += net
    player.realized_pnl = getattr(player, "realized_pnl", 0.0) + realized
    pos["qty"] -= qty
    if pos["qty"] <= 1e-9:
        del player.bonds[bond_id]
    return {"ok": True, "price": q["price"], "qty": qty, "net": net, "realized": realized}


# ---------------------------------------------------------------- valuation
def holdings_value(player, market):
    """Valeur de marché des obligations détenues."""
    total = 0.0
    for bid, pos in getattr(player, "bonds", {}).items():
        q = quote(market, bid)
        if q:
            total += q["price"] * pos["qty"]
    return total


def holdings(player, market):
    """Détail des positions obligataires (valeur, P&L latent)."""
    out = []
    for bid, pos in getattr(player, "bonds", {}).items():
        q = quote(market, bid)
        if not q:
            continue
        value = q["price"] * pos["qty"]
        out.append({"id": bid, "name": q["name"], "qty": pos["qty"], "avg": pos["avg"],
                    "price": q["price"], "ytm": q["ytm"], "mod_duration": q["mod_duration"],
                    "value": value, "pnl": value - pos["avg"] * pos["qty"]})
    out.sort(key=lambda h: h["value"], reverse=True)
    return out


def coupons(player, market, days):
    """Coupons versés sur `days` jours (au prorata annuel)."""
    total = 0.0
    for bid, pos in getattr(player, "bonds", {}).items():
        b = _BY_ID.get(bid)
        if b:
            total += FACE * b[6] * pos["qty"] * (days / 365.0)
    return total
