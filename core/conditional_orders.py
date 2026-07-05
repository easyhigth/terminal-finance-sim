"""
conditional_orders.py — Ordres conditionnels (stop-loss / take-profit) sur les
positions LONGUES ET COURTES du portefeuille actions.

Contrairement à l'ALERTE de prix (core/... — notifie sans agir), un ordre
conditionnel s'EXÉCUTE automatiquement (une vente ou un cover réel, via
`core/portfolio.sell`/`core/portfolio.cover`) dès que le cours franchit le
seuil posé, à chaque pas de marché (`GameState.advance_step`, cf. `execute_due`)
— pas seulement quand le joueur regarde l'écran.

Types :
  - "stop"   (stop-loss)   : LONG  → vend si le cours ≤ seuil
                             SHORT → couvre si le cours ≥ seuil
  - "target" (take-profit) : LONG  → vend si le cours ≥ seuil
                             SHORT → couvre si le cours ≤ seuil

Un ordre est à usage unique (retiré dès exécution) et silencieusement abandonné
si la position sous-jacente a disparu entre-temps (vendue/couverte manuellement…)
— jamais d'exécution sur une position qui n'existe plus.
"""
from core import portfolio as pf_mod

KINDS = ("stop", "target")


def _next_id(player):
    oid = getattr(player, "next_conditional_order_id", 1)
    player.next_conditional_order_id = oid + 1
    return oid


def place(player, market, ticker, kind, trigger, qty="ALL"):
    """Pose un ordre conditionnel sur une position (longue ou courte) détenue.
    Retourne {"ok": True, "order": ...} ou {"ok": False, "reason": ...}."""
    if kind not in KINDS:
        return {"ok": False, "reason": "kind"}
    try:
        trigger = float(trigger)
    except (TypeError, ValueError):
        return {"ok": False, "reason": "trigger"}
    if trigger <= 0:
        return {"ok": False, "reason": "trigger"}

    # Cherche d'abord une position longue, puis une position courte
    pos = player.portfolio.get(ticker)
    is_short = False
    if not pos or pos.get("shares", 0) <= 0:
        # Vérifie les positions courtes
        shorts = getattr(player, "shorts", None) or {}
        pos = shorts.get(ticker)
        is_short = True
    if not pos or pos.get("shares", 0) <= 0:
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
             "trigger": trigger, "qty": qty, "is_short": is_short}
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
    """Détermine si l'ordre est déclenché au prix courant.
    Pour les shorts, la logique est inversée (un stop-loss sur short
    se déclenche quand le prix MONTE, un take-profit quand il BAISSE)."""
    is_short = order.get("is_short", False)
    if order["kind"] == "stop":
        return price >= order["trigger"] if is_short else price <= order["trigger"]
    # "target"
    return price <= order["trigger"] if is_short else price >= order["trigger"]


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
        is_short = order.get("is_short", False)
        if is_short:
            shorts = getattr(player, "shorts", None) or {}
            pos = shorts.get(order["ticker"])
        else:
            pos = player.portfolio.get(order["ticker"])
        if not pos or pos.get("shares", 0) <= 0:
            continue   # position disparue entre-temps : ordre abandonné silencieusement
        price = market.price_of(order["ticker"])
        if price is None or not _triggered(order, price):
            remaining.append(order)
            continue
        qty = order["qty"]
        if qty != "ALL":
            qty = min(qty, pos["shares"])
        if is_short:
            result = pf_mod.cover(player, market, order["ticker"], qty)
        else:
            result = pf_mod.sell(player, market, order["ticker"], qty)
        if result["ok"]:
            executed.append({"order": order, "result": result})
        else:
            remaining.append(order)   # échec (rare) : on retente au pas suivant
    player.conditional_orders = remaining
    return executed


# ---------------------------------------------------------------------------
# TRAILING STOPS — stop-loss qui suit le cours à distance fixe
# ---------------------------------------------------------------------------
def place_trailing(player, market, ticker, distance_pct, qty="ALL"):
    """Pose un trailing stop : le seuil de déclenchement suit le cours à une
    distance de `distance_pct` (ex: 5.0 = 5%). Pour un LONG, le stop remonte
    avec le cours ; pour un SHORT, le stop descend avec le cours.

    Le seuil initial est calculé à partir du prix courant du marché.
    Retourne le même format que `place()`."""
    price = market.price_of(ticker)
    if price is None or price <= 0:
        return {"ok": False, "reason": "price"}

    # Cherche la position (longue ou courte)
    pos = player.portfolio.get(ticker)
    is_short = False
    if not pos or pos.get("shares", 0) <= 0:
        shorts = getattr(player, "shorts", None) or {}
        pos = shorts.get(ticker)
        is_short = True
    if not pos or pos.get("shares", 0) <= 0:
        return {"ok": False, "reason": "noposition"}

    if qty != "ALL":
        try:
            qty = float(qty)
        except (TypeError, ValueError):
            return {"ok": False, "reason": "qty"}
        if qty <= 0:
            return {"ok": False, "reason": "qty"}
        qty = min(qty, pos["shares"])

    # Seuil initial : distance_pct% en-dessous du cours (long) ou au-dessus (short)
    if is_short:
        trigger = price * (1 + distance_pct / 100)
    else:
        trigger = price * (1 - distance_pct / 100)

    order = {"id": _next_id(player), "ticker": ticker, "kind": "trailing",
             "trigger": trigger, "qty": qty, "is_short": is_short,
             "distance_pct": distance_pct, "high_water": price}
    if not hasattr(player, "conditional_orders") or player.conditional_orders is None:
        player.conditional_orders = []
    player.conditional_orders.append(order)
    return {"ok": True, "order": order}


def update_trailing_stops(player, market):
    """Met à jour les seuils des trailing stops avant l'exécution.
    Pour les longs, le stop remonte avec le cours (high water mark).
    Pour les shorts, le stop descend avec le cours (low water mark).
    À appeler AVANT `execute_due` dans la boucle de pas de marché."""
    orders = getattr(player, "conditional_orders", None) or []
    for order in orders:
        if order.get("kind") != "trailing":
            continue
        price = market.price_of(order["ticker"])
        if price is None:
            continue
        is_short = order.get("is_short", False)
        dist = order.get("distance_pct", 5.0) / 100
        if is_short:
            # Le stop descend avec le cours (on suit le plus bas)
            low_water = order.get("high_water", price)  # réutilise le champ
            if price < low_water:
                order["high_water"] = price
                order["trigger"] = price * (1 + dist)
        else:
            # Le stop remonte avec le cours (on suit le plus haut)
            high_water = order.get("high_water", price)
            if price > high_water:
                order["high_water"] = price
                order["trigger"] = price * (1 - dist)
