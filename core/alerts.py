"""
alerts.py — Alertes de prix actionnables.

Module PURE : définit les règles d'alerte, les pose, les vérifie au pas de
marché et renvoie les alertes déclenchées avec un contexte d'action (ticker,
seuil franchi, direction). L'UI et les notifications utilisent ce contexte
pour router le joueur vers le Trading pré-filtré.

Types d'alerte :
  - "level"  : seuil de prix absolu (supérieur ou inférieur au cours)
  - "pct"    : variation en % par rapport au cours au moment de la pose
  - "trailing" : stop suiveur (déclenche si le cours recule de N% depuis son
                 meilleur niveau observé depuis la pose)

Chaque alerte porte un identifiant unique, ce qui permet à l'UI de les
lister/annuler individuellement et de conserver un historique déclenché.
"""

MAX_ACTIVE = 50
MAX_HISTORY = 30

KINDS = ("level", "pct", "trailing")


def _next_id(player):
    oid = getattr(player, "next_alert_id", 1)
    player.next_alert_id = oid + 1
    return oid


def _ensure_lists(player):
    if not hasattr(player, "alerts") or player.alerts is None:
        player.alerts = []
    if not hasattr(player, "alerts_history") or player.alerts_history is None:
        player.alerts_history = []
    # migration : les sauvegardes antérieures aux alertes multi-types
    # stockaient {ticker, price, above} sans "kind"/"id"/"value" — on les
    # requalifie en alerte de NIVEAU plutôt que de faire planter check()
    # (cf. tests/test_save_compat.py).
    for a in player.alerts:
        if "kind" not in a:
            a["kind"] = "level"
            a.setdefault("value", float(a.get("price", 0.0) or 0.0))
            a.setdefault("above", True)
            a.setdefault("set_price", 0.0)
            a.setdefault("best_price", 0.0)
            a.setdefault("is_index", False)
        if "id" not in a:
            a["id"] = _next_id(player)


def _match_index(market, name):
    """Nom d'INDICE régional exact (insensible à la casse), ou None. Les
    alertes marchent aussi sur les indices (« C&D 500 », « NKX 225 »…) —
    ils étaient déjà affichés partout (bandeau du terminal, bande ambiante
    du bureau) mais impossibles à surveiller sans garder l'écran ouvert."""
    if market is None or not getattr(market, "index_region", None):
        return None
    up = name.upper()
    for idx_name in market.index_region:
        if idx_name.upper() == up:
            return idx_name
    return None


def _normalize_ticker(market, ticker):
    if ticker is None:
        return None
    idx = _match_index(market, ticker)
    if idx is not None:
        return idx
    tk = ticker.upper()
    if market and hasattr(market, "resolve"):
        return market.resolve(tk) or (tk if tk in getattr(market, "ticker_idx", {}) else None)
    return tk


def _price(market, ticker):
    if market is None:
        return None
    if _match_index(market, ticker) is not None:
        return market.index_value(ticker)
    if not hasattr(market, "price_of"):
        return None
    return market.price_of(ticker)


def place(player, market, ticker, kind, value, direction=None):
    """Pose une alerte.

    kind:
      - "level"    : value = prix absolu
      - "pct"      : value = pourcentage (positif = hausse, négatif = baisse)
      - "trailing" : value = distance % (positif) pour un stop suiveur
    direction: pour "level" uniquement, force "above" ou "below" ; sinon
               déduit de value.
    """
    _ensure_lists(player)
    tk = _normalize_ticker(market, ticker)
    if tk is None:
        return {"ok": False, "reason": "ticker"}
    price = _price(market, tk)
    if price is None or price <= 0:
        return {"ok": False, "reason": "price"}
    try:
        value = float(value)
    except (TypeError, ValueError):
        return {"ok": False, "reason": "value"}

    if kind == "level":
        if value <= 0:
            return {"ok": False, "reason": "value"}
        above = direction == "above" if direction else value > price
    elif kind == "pct":
        if value == 0:
            return {"ok": False, "reason": "value"}
        above = value > 0
        value = abs(value)
    elif kind == "trailing":
        if value <= 0:
            return {"ok": False, "reason": "value"}
        above = False  # trailing = recul depuis le meilleur niveau
    else:
        return {"ok": False, "reason": "kind"}

    order = {
        "id": _next_id(player),
        "ticker": tk,
        "kind": kind,
        "value": value,
        "above": above,
        "set_price": price,
        "set_step": getattr(market, "step_count", 0),
        "best_price": price,  # pour trailing
        # indice régional (pas une action) : l'UI route le clic de la
        # notification vers le hub Marché plutôt que Trading
        "is_index": _match_index(market, tk) is not None,
    }
    player.alerts.append(order)
    if len(player.alerts) > MAX_ACTIVE:
        player.alerts = player.alerts[-MAX_ACTIVE:]
    return {"ok": True, "alert": order}


def cancel(player, alert_id):
    """Annule une alerte active par son id."""
    _ensure_lists(player)
    before = len(player.alerts)
    player.alerts = [a for a in player.alerts if a["id"] != alert_id]
    return len(player.alerts) < before


def reset(player):
    """Vide les alertes actives et l'historique."""
    _ensure_lists(player)
    player.alerts = []
    player.alerts_history = []


def _triggered_level(alert, price):
    return (price >= alert["value"]) if alert["above"] else (price <= alert["value"])


def _triggered_pct(alert, price):
    base = alert["set_price"]
    if not base:
        return False
    pct = (price / base - 1.0) * 100.0
    return pct >= alert["value"] if alert["above"] else pct <= -alert["value"]


def _triggered_trailing(alert, price):
    """Stop suiveur : met à jour le meilleur niveau observé et déclenche si
    le cours recule de value % depuis ce meilleur niveau (LONG) ou remonte
    de value % depuis le plus bas (SHORT n'a pas de sens ici, on traite comme
    un suiveur de baisse)."""
    if price > alert["best_price"]:
        alert["best_price"] = price
    best = alert["best_price"]
    if not best:
        return False
    return price <= best * (1.0 - alert["value"] / 100.0)


def check(player, market):
    """Vérifie toutes les alertes actives au cours courant. Retourne la liste
    des alertes déclenchées (dict avec alerte originale + prix + message) et
    met à jour la liste active / l'historique."""
    _ensure_lists(player)
    triggered = []
    still = []
    for alert in player.alerts:
        price = _price(market, alert["ticker"])
        if price is None:
            continue
        kind = alert["kind"]
        if kind == "level":
            fired = _triggered_level(alert, price)
        elif kind == "pct":
            fired = _triggered_pct(alert, price)
        elif kind == "trailing":
            fired = _triggered_trailing(alert, price)
        else:
            fired = False
        if fired:
            event = {
                "id": alert["id"],
                "ticker": alert["ticker"],
                "kind": kind,
                "value": alert["value"],
                "above": alert["above"],
                "price": price,
                "set_price": alert.get("set_price"),
                "is_index": alert.get("is_index", False),
            }
            triggered.append(event)
            player.alerts_history.append(event)
        else:
            still.append(alert)
    player.alerts = still
    if len(player.alerts_history) > MAX_HISTORY:
        player.alerts_history = player.alerts_history[-MAX_HISTORY:]
    return triggered


def summary(player):
    """Résumé pour affichage : actives + historique."""
    _ensure_lists(player)
    return {
        "active": list(player.alerts),
        "history": list(player.alerts_history),
    }


def format_trigger(event):
    """Message utilisateur pour une alerte déclenchée."""
    tk = event["ticker"]
    price = event["price"]
    kind = event["kind"]
    if kind == "level":
        sens = "au-dessus" if event["above"] else "en-dessous"
        return f"{tk} a franchi {sens} de {event['value']:.2f} (cours {price:.2f})."
    if kind == "pct":
        sign = "hausse" if event["above"] else "baisse"
        return f"{tk} : {sign} de {event['value']:.1f}% atteinte (cours {price:.2f})."
    return f"{tk} : stop suiveur déclenché (cours {price:.2f})."
