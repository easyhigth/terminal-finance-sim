"""
convertibles.py — Obligations convertibles (logique pure).

Le produit hybride par excellence : une obligation d'entreprise + un CALL
sur l'action — et tout existe déjà dans le jeu pour le pricer proprement :

    prix = PLANCHER OBLIGATAIRE (PV coupons + pair au rendement corporate)
         + ratio de conversion × CALL Black-Scholes(spot, strike, T, σ)

- le coupon est RÉDUIT vs une obligation classique (le droit de conversion
  se paie) ;
- le **delta** (ratio × Δ du call) dit dans quel monde vit le titre :
  proche de 0 = « c'est une obligation », proche du ratio = « c'est une
  action » — le fameux profil « bond floor + equity kicker » ;
- l'**arbitrage convertible** classique : long la convertible / short
  delta actions — on encaisse le portage en neutralisant la direction
  (le plan est fourni, l'exécution passe par core/portfolio.short).

Émission AU MOMENT DE L'ACHAT (strike = spot × PREMIUM, maturité fixe) :
chaque position porte ses propres termes, mark-to-model à chaque pas.
"""
from core import finmath as fm
from core import options as opt

FACE = 1000.0
MATURITY_YEARS = 5.0
CONVERSION_PREMIUM = 1.15      # strike = spot × 115 % à l'émission
COUPON_DISCOUNT = 0.015        # coupon = rendement corporate − 150 bp
CREDIT_SPREAD = 0.018          # rendement corporate ≈ base + 180 bp
STEPS_PER_YEAR = 52


def _bond_floor(rate_y, coupon, years):
    """PV des coupons + pair, actualisés au rendement corporate."""
    if years <= 0:
        return FACE
    pv = 0.0
    n = max(1, int(round(years)))
    for t in range(1, n + 1):
        pv += FACE * coupon / (1.0 + rate_y) ** t
    pv += FACE / (1.0 + rate_y) ** n
    return pv


def quote(market, ticker, strike=None, years=MATURITY_YEARS):
    """Cote d'une convertible sur `ticker` (émission au spot courant si
    `strike` absent). None si ticker inconnu. {price, bond_floor,
    option_value, ratio, strike, delta, coupon, premium_over_parity}."""
    from core import bonds as B
    spot = market.price_of(ticker)
    if spot is None or years <= 0:
        return None
    strike = strike if strike is not None else spot * CONVERSION_PREMIUM
    ratio = FACE / strike                            # actions par obligation
    rate_y = B.base_yield_level(market) + CREDIT_SPREAD
    coupon = max(0.0, rate_y - COUPON_DISCOUNT)
    sigma = opt._stock_vol(market, ticker)
    r = opt.risk_free_rate(market)
    floor = _bond_floor(rate_y, coupon, years)
    call = fm.black_scholes(spot, strike, years, r, sigma, option="call")
    greeks = fm.bs_greeks(spot, strike, years, r, sigma, option="call")
    price = floor + ratio * call
    parity = ratio * spot                            # valeur si conversion
    return {"ticker": ticker, "spot": spot, "strike": strike, "ratio": ratio,
            "coupon": coupon, "years": years, "bond_floor": floor,
            "option_value": ratio * call, "price": price,
            "delta": ratio * greeks["delta"], "parity": parity,
            "premium_over_parity": (price / parity - 1.0) if parity else 0.0}


def buy(player, market, ticker, qty):
    """Achète `qty` convertibles émises au spot courant (prime débitée)."""
    if qty < 1:
        return {"ok": False, "reason": "qty"}
    q = quote(market, ticker)
    if q is None:
        return {"ok": False, "reason": "ticker"}
    cost = q["price"] * qty
    if cost > player.cash:
        return {"ok": False, "reason": "cash"}
    player.cash -= cost
    player.convertibles = getattr(player, "convertibles", [])
    pos = {"id": max((c["id"] for c in player.convertibles), default=0) + 1,
           "ticker": ticker, "qty": int(qty), "strike": q["strike"],
           "entry_price": q["price"], "coupon": q["coupon"],
           "maturity_step": market.step_count
           + int(round(MATURITY_YEARS * STEPS_PER_YEAR))}
    player.convertibles.append(pos)
    return {"ok": True, "position": pos, "quote": q}


def position_quote(market, pos):
    """Cote courante d'une position (mêmes termes, temps restant)."""
    steps_left = max(0, pos["maturity_step"] - market.step_count)
    return quote(market, pos["ticker"], strike=pos["strike"],
                 years=max(1e-6, steps_left / STEPS_PER_YEAR))


def sell(player, market, pos_id):
    """Revend une position au mark-to-model."""
    for pos in getattr(player, "convertibles", []) or []:
        if pos["id"] == pos_id:
            q = position_quote(market, pos)
            if q is None:
                return {"ok": False, "reason": "ticker"}
            proceeds = q["price"] * pos["qty"]
            player.cash += proceeds
            pnl = proceeds - pos["entry_price"] * pos["qty"]
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + pnl
            player.convertibles.remove(pos)
            return {"ok": True, "proceeds": proceeds, "pnl": pnl}
    return {"ok": False, "reason": "notfound"}


def accrue(player, market, days):
    """Coupons courus des convertibles détenues."""
    return sum(FACE * pos["coupon"] * pos["qty"] * (days / 365.0)
               for pos in getattr(player, "convertibles", []) or [])


def arb_plan(market, pos):
    """Plan d'arbitrage convertible : short `delta × qty` actions pour
    neutraliser la direction. {ticker, shares} ou None."""
    q = position_quote(market, pos)
    if q is None:
        return None
    shares = int(round(q["delta"] * pos["qty"]))
    return {"ticker": pos["ticker"], "shares": shares} if shares >= 1 else None


def holdings(player, market):
    out = []
    for pos in getattr(player, "convertibles", []) or []:
        q = position_quote(market, pos)
        if q:
            out.append({**pos, "quote": q,
                        "value": q["price"] * pos["qty"],
                        "pnl": (q["price"] - pos["entry_price"]) * pos["qty"]})
    return out


def holdings_value(player, market):
    total = 0.0
    for pos in getattr(player, "convertibles", []) or []:
        q = position_quote(market, pos)
        if q:
            total += q["price"] * pos["qty"]
    return total
