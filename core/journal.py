"""
journal.py — Journal d'investissement du joueur : enregistre chaque trade
(date, raison, contexte macro, taille, résultat, commentaire) pour permettre
une revue ultérieure des décisions. Logique pure, aucune dépendance pygame.
"""

MAX_ENTRIES = 500  # borne le journal pour éviter une croissance illimitée des saves


def log_trade(player, market, *, asset_class, key, label, side, qty, price,
              fee=0.0, realized=None, reason=""):
    """Ajoute une entrée au journal du joueur et la retourne.

    asset_class : "Action", "ETF", "Obligation", "Commodity", "Crypto"...
    side : "achat", "vente", "short", "couverture"...
    realized : P&L réalisé de ce trade si connu immédiatement (vente/cover), sinon None.
    """
    entry = {
        "id": player.next_journal_id,
        "day": player.day,
        "asset_class": asset_class,
        "key": key,
        "label": label,
        "side": side,
        "qty": qty,
        "price": price,
        "fee": fee,
        "notional": abs(qty * price),
        "realized": realized,
        "regime": market.regime_label() if market is not None else "",
        "reason": reason,
        "comment": "",
    }
    player.next_journal_id += 1
    player.trade_journal.append(entry)
    if len(player.trade_journal) > MAX_ENTRIES:
        del player.trade_journal[: len(player.trade_journal) - MAX_ENTRIES]
    return entry


def get_entry(player, entry_id):
    for e in player.trade_journal:
        if e["id"] == entry_id:
            return e
    return None


def annotate(player, entry_id, *, reason=None, comment=None):
    """Met à jour la raison et/ou le commentaire d'une entrée existante.
    Retourne l'entrée modifiée, ou None si l'identifiant est inconnu."""
    entry = get_entry(player, entry_id)
    if entry is None:
        return None
    if reason is not None:
        entry["reason"] = reason
    if comment is not None:
        entry["comment"] = comment
    return entry


def list_entries(player, asset_class=None, limit=50):
    """Retourne les entrées les plus récentes (id décroissant), filtrées
    optionnellement par classe d'actif."""
    entries = player.trade_journal
    if asset_class:
        entries = [e for e in entries if e["asset_class"] == asset_class]
    return list(reversed(entries))[:limit]


def performance_stats(player, group_by="regime"):
    """Agrège le P&L réalisé du journal par `group_by` ("regime" ou "reason"),
    pour donner un retour pédagogique sur les décisions passées. Ignore les
    entrées sans P&L réalisé connu (positions encore ouvertes). Retourne une
    liste de dicts {label, count, wins, win_rate, avg_pnl, total_pnl} triée
    par nombre de trades décroissant."""
    groups = {}
    for e in player.trade_journal:
        if e["realized"] is None:
            continue
        key = e.get(group_by) or "—"
        g = groups.setdefault(key, {"label": key, "count": 0, "wins": 0, "total_pnl": 0.0})
        g["count"] += 1
        g["total_pnl"] += e["realized"]
        if e["realized"] > 0:
            g["wins"] += 1
    out = list(groups.values())
    for g in out:
        g["win_rate"] = g["wins"] / g["count"] * 100.0
        g["avg_pnl"] = g["total_pnl"] / g["count"]
    out.sort(key=lambda g: g["count"], reverse=True)
    return out
