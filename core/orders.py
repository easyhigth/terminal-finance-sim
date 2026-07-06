"""
orders.py — Ordres avancés : fractionnés et TWAP (Time-Weighted Average Price).

Un ordre TWAP répartit l'exécution d'un volume total sur N pas de marché,
limitant l'impact de marché et permettant d'entrer/sortir progressivement.
Contrairement aux ordres conditionnels (core/conditional_orders.py), le TWAP
n'est pas lié à un seuil de prix : il est exécuté aux pas suivants, quoi qu'il
arrive, par tranches égales (ou ajustées au dernier pas).

Logique pure : ne dépend pas de pygame. Appelé à chaque pas de marché par
GameState.advance_step / TerminalTimeMixin._drain_pending_steps.
"""

import importlib

MAX_PENDING = 20


def _ensure_pending(player):
    if not hasattr(player, "pending_orders") or player.pending_orders is None:
        player.pending_orders = []


def _next_id(player):
    oid = getattr(player, "next_pending_order_id", 1)
    player.next_pending_order_id = oid + 1
    return oid


def _asset_module(asset_class):
    mapping = {
        "Action": "core.portfolio",
        "ETF": "core.etfs",
        "Obligation": "core.bonds",
        "Commodity": "core.commodities",
        "Crypto": "core.crypto",
    }
    mod = mapping.get(asset_class)
    return importlib.import_module(mod) if mod else None


def _buy_fn(module, asset_class):
    if asset_class in ("Obligation",):
        return getattr(module, "buy_bond", None)
    return getattr(module, "buy", None)


def _sell_fn(module, asset_class):
    if asset_class in ("Obligation",):
        return getattr(module, "sell_bond", None)
    return getattr(module, "sell", None)


def place_twap(player, market, asset_class, key, side, total_qty, steps, label=None):
    """Pose un ordre TWAP : exécute `total_qty` (achat ou vente) en `steps`
    tranches égales sur les prochains pas de marché.

    Retourne {"ok": True, "order": ...} ou {"ok": False, "reason": ...}.
    """
    _ensure_pending(player)
    if steps <= 0:
        return {"ok": False, "reason": "steps"}
    if total_qty <= 0:
        return {"ok": False, "reason": "qty"}
    if side not in ("buy", "sell"):
        return {"ok": False, "reason": "side"}
    mod = _asset_module(asset_class)
    if mod is None:
        return {"ok": False, "reason": "asset_class"}
    if len(player.pending_orders) >= MAX_PENDING:
        return {"ok": False, "reason": "max_pending"}

    order = {
        "id": _next_id(player),
        "asset_class": asset_class,
        "key": key,
        "side": side,
        "total_qty": float(total_qty),
        "remaining": float(total_qty),
        "steps_total": int(steps),
        "steps_left": int(steps),
        "label": label or key,
        "created_step": getattr(market, "step_count", 0),
    }
    player.pending_orders.append(order)
    return {"ok": True, "order": order}


def cancel(player, order_id):
    """Annule un ordre TWAP en attente."""
    _ensure_pending(player)
    before = len(player.pending_orders)
    player.pending_orders = [o for o in player.pending_orders if o["id"] != order_id]
    return len(player.pending_orders) < before


def execute_due(player, market):
    """Exécute une tranche de chaque ordre TWAP actif au pas courant.
    Retourne la liste des exécutions pour affichage/notification."""
    _ensure_pending(player)
    executed = []
    still = []
    for order in player.pending_orders:
        mod = _asset_module(order["asset_class"])
        if mod is None:
            continue
        side = order["side"]
        steps_left = max(1, order["steps_left"])
        chunk = order["remaining"] / steps_left
        if chunk <= 0:
            continue
        # dernière tranche : on éponge le reste pour éviter les décimales
        if order["steps_left"] == 1:
            chunk = order["remaining"]
        fn = _buy_fn(mod, order["asset_class"]) if side == "buy" else _sell_fn(mod, order["asset_class"])
        if fn is None:
            continue
        # arrondi à l'entier inférieur pour les actions (pas de fraction)
        if order["asset_class"] == "Action":
            chunk_int = int(chunk)
            if chunk_int <= 0:
                still.append(order)
                continue
            chunk = float(chunk_int)
        r = fn(player, market, order["key"], chunk)
        if r.get("ok"):
            order["remaining"] -= chunk
            order["steps_left"] -= 1
            executed.append({
                "id": order["id"],
                "asset_class": order["asset_class"],
                "key": order["key"],
                "side": side,
                "chunk": chunk,
                "price": r.get("price"),
                "realized": r.get("realized"),
                "remaining": order["remaining"],
            })
            if order["remaining"] <= 1e-9 or order["steps_left"] <= 0:
                continue  # ordre terminé
        else:
            # échec temporaire (liquidité, marché fermé) : on retente au prochain pas
            pass
        still.append(order)
    player.pending_orders = still
    return executed


def list_orders(player):
    """Liste les ordres TWAP actifs."""
    _ensure_pending(player)
    return list(player.pending_orders)
