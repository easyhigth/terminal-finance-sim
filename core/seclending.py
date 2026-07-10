"""
seclending.py — Prêt-emprunt de titres (securities lending), logique pure.

Les deux faces économiques du prêt de titres, absentes jusqu'ici :

- **Coût d'emprunt des SHORTS** : vendre à découvert suppose d'EMPRUNTER
  le titre — ça se paie. Le taux d'emprunt dépend de la liquidité (une
  petite capi est « hard to borrow » : rare au prêt, chère à emprunter —
  mêmes tiers que core/liquidity) et s'élargit avec le stress de marché.
  Couru chaque pas sur la valeur absolue des positions courtes (câblé
  dans advance_step) : un short n'est plus jamais gratuit à porter.

- **Revenu de PRÊT des positions longues** : activable dans le Desk
  Financement (player.flags['sec_lending']) — les actions détenues sont
  prêtées au marché contre une fraction du taux d'emprunt (la part
  prêteur, le reste va à l'agent, comme en vrai). Petit revenu régulier,
  qui augmente précisément sur les titres que le marché shorte le plus.
"""
from core import liquidity

BORROW_BASE = 0.005                  # 50 bp/an, grande capi, marché calme
# clés = tiers de core/liquidity.equity_tier_for_cap
TIER_PREMIUM = {"Liquide": 0.0, "Peu liquide": 0.010, "Illiquide": 0.030}
STRESS_PREMIUM = 0.020               # +200 bp à stress max
LENDER_SPLIT = 0.4                   # part du taux qui revient au prêteur


def _stress(market):
    return min(1.0, max(0.0, getattr(market, "last_stress_level", 0.0)))


def borrow_fee_rate(market, ticker):
    """Taux d'emprunt annuel du titre (coût d'un short, revenu brut d'un
    prêt) — liquidité + stress. 0 si ticker inconnu."""
    i = market.ticker_idx.get(ticker)
    if i is None:
        return 0.0
    cap = float(market.price[i] * market.shares[i])
    tier = liquidity.equity_tier_for_cap(cap)
    return (BORROW_BASE + TIER_PREMIUM.get(tier, 0.03)
            + STRESS_PREMIUM * _stress(market))


def lending_rate(market, ticker):
    """Taux touché par le PRÊTEUR (part LENDER_SPLIT du taux d'emprunt)."""
    return borrow_fee_rate(market, ticker) * LENDER_SPLIT


def accrue(player, market, days):
    """Flux net d'un pas : − frais d'emprunt des shorts, + revenu de prêt
    des longs (si player.flags['sec_lending']). Montant signé."""
    total = 0.0
    lending_on = bool(getattr(player, "flags", {}).get("sec_lending"))
    for tk, pos in getattr(player, "portfolio", {}).items():
        price = market.price_of(tk)
        if price is None or not pos["shares"]:
            continue
        value = abs(pos["shares"]) * price
        if pos["shares"] < 0:
            total -= value * borrow_fee_rate(market, tk) * (days / 365.0)
        elif lending_on:
            total += value * lending_rate(market, tk) * (days / 365.0)
    return total


def table(player, market):
    """Table du desk : chaque position action avec son taux (coût si short,
    revenu si long+prêt activé). [{ticker, side, value, rate, annual}]."""
    lending_on = bool(getattr(player, "flags", {}).get("sec_lending"))
    out = []
    for tk, pos in getattr(player, "portfolio", {}).items():
        price = market.price_of(tk)
        if price is None or not pos["shares"]:
            continue
        value = abs(pos["shares"]) * price
        if pos["shares"] < 0:
            rate = -borrow_fee_rate(market, tk)
            side = "short"
        else:
            rate = lending_rate(market, tk) if lending_on else 0.0
            side = "long"
        out.append({"ticker": tk, "side": side, "value": value,
                    "rate": rate, "annual": value * rate})
    out.sort(key=lambda x: x["annual"])
    return out
