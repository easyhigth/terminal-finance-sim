"""
order_confirm.py — Seuil de confirmation pour les ordres à fort impact.

Un achat/vente qui engage une grosse part du patrimoine net peut être une
simple faute de frappe sur la quantité (ex. 1000 au lieu de 10, un zéro de
trop). Plutôt que d'exécuter silencieusement, l'app Trading
(apps/app_trading.py) demande une confirmation explicite au-delà du seuil.
Module PUR (aucun état, aucun rendu) : ne connaît que `player`/`market`.
"""
from core import portfolio_margin as pm_mod

HIGH_IMPACT_THRESHOLD = 0.30   # part du patrimoine net (30%)
LARGE_POSITION_THRESHOLD = 0.50  # part de la position vendue (50%)


def impact_ratio(player, market, notional):
    """Part du patrimoine net qu'engage un ordre de valeur absolue
    `notional`. Renvoie 0.0 si le patrimoine net est nul/négatif (pas de
    division par zéro, et pas de confirmation absurde dans ce cas limite —
    le contrôle de marge normal s'en charge déjà)."""
    nw = pm_mod.net_worth(player, market)
    if nw <= 0:
        return 0.0
    return abs(notional) / nw


def needs_confirmation(player, market, notional, threshold=HIGH_IMPACT_THRESHOLD):
    return impact_ratio(player, market, notional) >= threshold


def is_large_position_sell(player, ticker, qty):
    """Vérifie si la vente de `qty` actions de `ticker` représente plus de
    LARGE_POSITION_THRESHOLD (50%) de la position détenue. Protège contre
    les liquidations accidentelles d'une position entière."""
    pos = player.portfolio.get(ticker)
    if not pos or pos.get("shares", 0) <= 0:
        return False
    held = pos["shares"]
    if qty == "ALL":
        return True
    try:
        qty = float(qty)
    except (TypeError, ValueError):
        return False
    return qty > 0 and (qty / held) >= LARGE_POSITION_THRESHOLD
