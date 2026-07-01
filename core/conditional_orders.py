"""
conditional_orders.py — Ordres conditionnels (stop-loss / take-profit) sur les
positions LONGUES du portefeuille actions.

Contrairement à l'ALERTE de prix (core/... — notifie sans agir), un ordre
conditionnel s'EXÉCUTE automatiquement (une vente réelle, via
`core/portfolio.sell`) dès que le cours franchit le seuil posé, à chaque pas
de marché (`GameState.advance_step`, cf. `execute_due`) — pas seulement quand
le joueur regarde l'écran. Deux types :
  - "stop"   (stop-loss)   : vend si le cours descend AU NIVEAU ou SOUS le seuil.
  - "target" (take-profit) : vend si le cours monte AU NIVEAU ou AU-DESSUS du seuil.

Un ordre est à usage unique (retiré dès exécution) et silencieusement abandonné
si la position sous-jacente a disparu entre-temps (vendue manuellement,
couverture clôturée...) — jamais d'exécution sur une position qui n'existe
plus. Ne gère que les positions LONGUES (short/cover hors scope : la notion de
"perte" s'inverse et mériterait sa propre UI).
"""
from core import portfolio as pf_mod

KINDS = ("stop", "target")


def _next_id(player):
    oid = getattr(player, "next_conditional_order_id", 1)
    player.next_conditional_order_id = oid + 1
    return oid


def place(player, market, ticker, kind, trigger, qty="ALL"):
    """Pose un ordre conditionnel sur une position longue détenue. Retourne
    {"ok": True, "order": ...} ou {"ok": False, "reason": ...}."""
    if kind not in KINDS:
        return {"ok": False, "reason": "kind"}
    try:
        trigger = float(trigger)
    except (TypeError, ValueError):
        return {"ok": False, "reason": "trigger"}
    if trigger <= 0:
        return {"ok": False, "reason": "trigger"}
    pos = player.portfolio.get(ticker)
    if not pos or pos["shares"] <= 0:
        return {"ok": False, "reason": "noposition"}
    if qty != "ALL":
        try:
            qty = float(qty)
        except (TypeError, ValueError):
            return {"ok": False, "reason": "qty"}
        if qty <= 0:
            return {"ok": False, "reason": "qty"}
        qty = min(qty, pos["shares"])
    order = {"id": _next_id(player), "ticker": ticker, "kind": kind,
             "trigger": trigger, "qty": qty}
    if not hasattr(player, "conditional_orders") or player.conditional_orders is None:
        player.conditional_orders = []
    player.conditional_orders.append(order)
    return {"ok": True, "order": order}


def cancel(player, order_id):
    orders = getattr(player, "conditional_orders", None) or []
    before = len(orders)
    player.conditional_orders = [o for o in orders if o["id"] != order_id]
    return len(player.conditional_orders) < before


def for_ticker(player, ticker):
    return [o for o in (getattr(player, "conditional_orders", None) or []) if o["ticker"] == ticker]


def _triggered(order, price):
    if order["kind"] == "stop":
        return price <= order["trigger"]
    return price >= order["trigger"]   # "target"


def execute_due(player, market):
    """Exécute les ordres conditionnels déclenchés par le cours COURANT du pas
    (appelé à chaque pas de marché, après le calcul des dividendes/avant le
    contrôle de marge — cf. GameState.advance_step). Retourne la liste des
    exécutions (pour affichage/notification), et retire de la liste les
    ordres exécutés OU devenus invalides (position disparue)."""
    orders = getattr(player, "conditional_orders", None) or []
    if not orders:
        return []
    executed = []
    remaining = []
    for order in orders:
        pos = player.portfolio.get(order["ticker"])
        if not pos or pos["shares"] <= 0:
            continue   # position disparue entre-temps : ordre abandonné silencieusement
        price = market.price_of(order["ticker"])
        if price is None or not _triggered(order, price):
            remaining.append(order)
            continue
        qty = order["qty"]
        if qty != "ALL":
            qty = min(qty, pos["shares"])
        result = pf_mod.sell(player, market, order["ticker"], qty)
        if result["ok"]:
            executed.append({"order": order, "result": result})
        else:
            remaining.append(order)   # échec (rare) : on retente au pas suivant
    player.conditional_orders = remaining
    return executed
