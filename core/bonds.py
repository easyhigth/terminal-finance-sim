"""
bonds.py — Marché obligataire tradable (logique pure, sans pygame).

Univers déterministe d'obligations SOUVERAINES (émises par les gouvernements de
core/governments.py) et CORPORATE (émises par de vraies sociétés du roster,
data/companies.py). Chaque obligation est pricée via core/finmath au rendement
exigé :

    YTM = niveau de la courbe (taux directeur macro + prime de terme)
        + spread de crédit du rating
        + prime de risque PAYS (souverains : instabilité + dette/PIB)
        + bump de crédit RÉGIONAL transitoire (événements politiques)

Quand les taux bougent (macro), les prix obligataires bougent en sens inverse —
la duration et la convexité deviennent jouables. Quand un événement politique
frappe une région (core/politics.py), les spreads de cette zone s'élargissent :
les prix des souverains ET des corporates de la région baissent (puis se
résorbent), créant des opportunités de portage / d'achat sur repli. Les coupons
sont versés à chaque tour.

Holdings : PlayerState.bonds = { bond_id : {"qty": nb d'obligations, "avg": prix moyen} }.
Nominal (face) = 1000 par obligation.
"""
from core import finmath
from core import governments as gov_mod
from data import companies as comp_data

FACE = 1000.0
COMMISSION = 0.0005       # 5 bps sur le notionnel échangé
TERM_PREMIUM = 0.0015     # prime de terme par année de maturité

# Spread de crédit par rating (sur le niveau de la courbe).
_RATING_SPREAD = {"AAA": 0.002, "AA": 0.004, "A": 0.007,
                  "BBB": 0.013, "BB": 0.030, "B": 0.055}
# Perte de crédit ATTENDUE annuelle par rating : le spread d'un high yield ne doit
# pas être un repas gratuit — il compense un risque de défaut. On la déduit des
# coupons encaissés (net carry réaliste : un B nette ~ un IG).
_RATING_LOSS = {"AAA": 0.0, "AA": 0.0005, "A": 0.001,
                "BBB": 0.004, "BB": 0.020, "B": 0.045}

# Niveau de courbe « nominal » servant à fixer le COUPON des obligations générées
# (de sorte qu'elles cotent près du pair à l'émission). Indépendant de la macro
# courante (qui, elle, fait varier le PRIX via le YTM).
_NOMINAL_CURVE = 0.030

# --------------------------------------------------------------------------
# Obligations « benchmark » curatées (icôniques) — conservées telles quelles.
# Champs : id, name, issuer, region, kind, rating, coupon, years, gov, ticker
# --------------------------------------------------------------------------
_CURATED = [
    dict(id="UST10", name="Trésor US 10 ans", issuer="Trésor américain", region="USA",
         kind="Souverain", rating="AAA", coupon=0.040, years=10, gov="US", ticker=None),
    dict(id="UST2", name="Trésor US 2 ans", issuer="Trésor américain", region="USA",
         kind="Souverain", rating="AAA", coupon=0.038, years=2, gov="US", ticker=None),
    dict(id="BUND10", name="Bund 10 ans", issuer="État allemand", region="Europe",
         kind="Souverain", rating="AAA", coupon=0.028, years=10, gov="DE", ticker=None),
    dict(id="OAT10", name="OAT 10 ans", issuer="État français", region="Europe",
         kind="Souverain", rating="AA", coupon=0.030, years=10, gov="FR", ticker=None),
    dict(id="JGB10", name="JGB 10 ans", issuer="État japonais", region="Asia",
         kind="Souverain", rating="A", coupon=0.010, years=10, gov="JP", ticker=None),
    dict(id="EM10", name="Souverain émergent 10 ans", issuer="État émergent", region="Am.Sud",
         kind="Souverain", rating="BB", coupon=0.075, years=10, gov=None, ticker=None),
    dict(id="CORP_IG", name="Corporate IG 7 ans", issuer="Grande capi notée A", region="USA",
         kind="Corporate", rating="A", coupon=0.050, years=7, gov=None, ticker=None),
    dict(id="CORP_IG2", name="Corporate IG 5 ans", issuer="Industrielle BBB", region="Europe",
         kind="Corporate", rating="BBB", coupon=0.055, years=5, gov=None, ticker=None),
    dict(id="CORP_HY", name="High Yield 5 ans", issuer="Émetteur spéculatif", region="USA",
         kind="Corporate", rating="B", coupon=0.090, years=5, gov=None, ticker=None),
    dict(id="CORP_HY2", name="High Yield 4 ans", issuer="LBO mid-cap", region="Europe",
         kind="Corporate", rating="BB", coupon=0.080, years=4, gov=None, ticker=None),
    dict(id="BANK_T2", name="Dette subordonnée bancaire", issuer="Banque systémique",
         region="Europe", kind="Corporate", rating="BBB", coupon=0.065, years=8, gov=None, ticker=None),
    dict(id="GREEN", name="Green bond 6 ans", issuer="Utility verte", region="Europe",
         kind="Corporate", rating="A", coupon=0.045, years=6, gov=None, ticker=None),
]

# --------------------------------------------------------------------------
# Obligations CORPORATE rattachées à de vraies sociétés du roster.
# (ticker, rating, maturité) — l'émetteur/la région sont lus dans companies.
# --------------------------------------------------------------------------
_CORP_ISSUERS = [
    ("POME", "AA", 7), ("MVC", "A", 7), ("JMP", "A", 6), ("EXOM", "BBB", 8),
    ("LWNH", "A", 7), ("TOTE", "A", 8), ("SHEL", "BBB", 6),
    ("TYTA", "A", 6), ("TSMX", "A", 7), ("SMSG", "A", 6),
    ("PTBR", "BB", 5), ("BHPX", "BBB", 7), ("NSPR", "BB", 5),
    ("RBQ", "A", 6),
]


def _coupon_for(rating, years, gov=None):
    """Coupon ≈ rendement attendu à l'émission → cote près du pair au départ."""
    cp = gov_mod.country_premium(gov_mod.get(gov)) if gov else 0.0
    y = _NOMINAL_CURVE + TERM_PREMIUM * years + _RATING_SPREAD.get(rating, 0.02) + cp
    return round(y, 3)


def _build_universe():
    """Construit la liste complète des obligations (curatées + générées)."""
    bonds = [dict(b) for b in _CURATED]
    seen = {b["id"] for b in bonds}

    # 1) souverains générés pour chaque gouvernement (maturités complémentaires)
    for g in gov_mod.GOVERNMENTS:
        for years in g.get("gen_mats", []):
            bid = f"{g['code']}{years}Y"
            if bid in seen:
                continue
            seen.add(bid)
            bonds.append(dict(
                id=bid, name=f"{g['name']} {years} ans",
                issuer=f"État — {g['name']}", region=g["region"], kind="Souverain",
                rating=g["rating"], coupon=_coupon_for(g["rating"], years, g["code"]),
                years=years, gov=g["code"], ticker=None))

    # 2) corporates rattachés à de vraies sociétés du roster
    for ticker, rating, years in _CORP_ISSUERS:
        c = comp_data.COMPANY_BY_TICKER.get(ticker)
        if not c:
            continue
        bid = f"CB_{ticker}"
        if bid in seen:
            continue
        seen.add(bid)
        bonds.append(dict(
            id=bid, name=f"{c['name']} {years} ans",
            issuer=c["name"], region=c["region"], kind="Corporate",
            rating=rating, coupon=_coupon_for(rating, years), years=years,
            gov=None, ticker=ticker))
    return bonds


BONDS = _build_universe()
_BY_ID = {b["id"]: b for b in BONDS}


# ---------------------------------------------------------------- spreads
def base_yield_level(market):
    """Niveau de référence de la courbe : taux directeur macro (en décimal)."""
    if market is not None and hasattr(market, "macro"):
        return market.macro["rate"]["v"] / 100.0
    return 0.03


def _region_bump(market, region):
    """Élargissement transitoire du spread de crédit régional (politique)."""
    if market is None:
        return 0.0
    return getattr(market, "region_credit_bump", {}).get(region, 0.0)


def ytm(market, bond_id):
    """Rendement exigé d'une obligation = courbe + prime de terme + spread crédit
    (+ prime pays pour les souverains) + bump de crédit régional (politique)."""
    b = _BY_ID[bond_id]
    y = (base_yield_level(market)
         + TERM_PREMIUM * b["years"]
         + _RATING_SPREAD.get(b["rating"], 0.02)
         + _region_bump(market, b["region"]))
    if b["kind"] == "Souverain" and b["gov"]:
        y += gov_mod.country_premium(gov_mod.get(b["gov"]))
    return y


def quote(market, bond_id):
    """Cotation complète d'une obligation : prix, YTM, duration, convexité."""
    b = _BY_ID.get(bond_id)
    if not b:
        return None
    y = ytm(market, bond_id)
    price = finmath.bond_price(FACE, b["coupon"], y, b["years"])
    dur = finmath.bond_modified_duration(FACE, b["coupon"], y, b["years"])
    conv = finmath.bond_convexity(FACE, b["coupon"], y, b["years"])
    return {"id": b["id"], "name": b["name"], "issuer": b["issuer"],
            "region": b["region"], "kind": b["kind"], "rating": b["rating"],
            "coupon": b["coupon"], "years": b["years"], "gov": b["gov"],
            "ticker": b["ticker"], "ytm": y, "price": price,
            "mod_duration": dur, "convexity": conv}


def all_quotes(market):
    return [quote(market, b["id"]) for b in BONDS]


def sovereign_quotes(market):
    return [q for q in all_quotes(market) if q["kind"] == "Souverain"]


def corporate_quotes(market):
    return [q for q in all_quotes(market) if q["kind"] == "Corporate"]


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
                    "kind": q["kind"], "region": q["region"],
                    "value": value, "pnl": value - pos["avg"] * pos["qty"]})
    out.sort(key=lambda h: h["value"], reverse=True)
    return out


def coupons(player, market, days):
    """Coupons versés sur `days` jours (au prorata annuel), NETS de la perte de
    crédit attendue du rating — un high yield ne rapporte pas « gratuitement »."""
    total = 0.0
    for bid, pos in getattr(player, "bonds", {}).items():
        b = _BY_ID.get(bid)
        if b:
            net_rate = b["coupon"] - _RATING_LOSS.get(b["rating"], 0.0)
            total += FACE * net_rate * pos["qty"] * (days / 365.0)
    return total
