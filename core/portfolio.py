"""
portfolio.py — Portefeuille du joueur et P&L réel (logique pure, sans pygame).

Le joueur achète/vend de vraies sociétés du roster avec sa trésorerie. Les
positions se revalorisent au fil des mouvements de marché : un krach fait
réellement chuter la valeur nette, un bon choix la fait grimper.

État (PlayerState) :
  portfolio    : dict ticker -> {"shares": float, "avg": prix de revient moyen}
  realized_pnl : P&L réalisé cumulé (sur les ventes)

Conventions : une commission est prélevée à l'achat comme à la vente.
"""

COMMISSION = 0.001   # 10 points de base par transaction


def buy(player, market, ticker, qty):
    """Achète `qty` actions de `ticker`. Retourne un dict résultat."""
    price = market.price_of(ticker)
    if price is None:
        return {"ok": False, "reason": "ticker"}
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    cost = price * qty
    fee = cost * COMMISSION
    total = cost + fee
    if total > player.cash:
        return {"ok": False, "reason": "cash", "need": total, "have": player.cash}
    player.cash -= total
    pos = player.portfolio.get(ticker)
    if pos:
        n = pos["shares"] + qty
        pos["avg"] = (pos["shares"] * pos["avg"] + cost) / n
        pos["shares"] = n
    else:
        player.portfolio[ticker] = {"shares": float(qty), "avg": price}
    market.track_company(ticker)
    return {"ok": True, "price": price, "qty": qty, "fee": fee, "total": total}


def sell(player, market, ticker, qty):
    """Vend `qty` actions (ou tout si qty == 'ALL' / qty >= position)."""
    pos = player.portfolio.get(ticker)
    if not pos:
        return {"ok": False, "reason": "noposition"}
    price = market.price_of(ticker)
    if price is None:
        return {"ok": False, "reason": "ticker"}
    if qty == "ALL" or qty >= pos["shares"]:
        qty = pos["shares"]
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    proceeds = price * qty
    fee = proceeds * COMMISSION
    net = proceeds - fee
    realized = (price - pos["avg"]) * qty - fee
    player.cash += net
    player.realized_pnl = getattr(player, "realized_pnl", 0.0) + realized
    pos["shares"] -= qty
    if pos["shares"] <= 1e-9:
        del player.portfolio[ticker]
    return {"ok": True, "price": price, "qty": qty, "net": net, "fee": fee,
            "realized": realized}


def positions_value(player, market):
    total = 0.0
    for t, p in player.portfolio.items():
        price = market.price_of(t)
        if price is not None:
            total += price * p["shares"]
    return total


def net_worth(player, market):
    return player.cash + positions_value(player, market)


def holdings(player, market):
    """Détail des positions (valeur, P&L latent), triées par valeur décroissante."""
    out = []
    for t, p in player.portfolio.items():
        price = market.price_of(t)
        if price is None:
            continue
        value = price * p["shares"]
        cost = p["avg"] * p["shares"]
        out.append({
            "ticker": t, "shares": p["shares"], "avg": p["avg"], "price": price,
            "value": value, "pnl": value - cost,
            "pnl_pct": (price / p["avg"] - 1) * 100 if p["avg"] else 0.0,
        })
    out.sort(key=lambda h: h["value"], reverse=True)
    return out


def unrealized_pnl(player, market):
    total = 0.0
    for t, p in player.portfolio.items():
        price = market.price_of(t)
        if price is not None:
            total += (price - p["avg"]) * p["shares"]
    return total


def allocation_by(player, market, key):
    """Répartition de la valeur des positions par `key` (sector/region)."""
    comp = {c["ticker"]: c for c in market.companies}
    agg = {}
    for t, p in player.portfolio.items():
        price = market.price_of(t)
        c = comp.get(t)
        if price is None or not c:
            continue
        agg[c[key]] = agg.get(c[key], 0.0) + price * p["shares"]
    return agg


def dividends(player, market, days):
    """Dividendes versés par les positions sur `days` jours (rendement annuel prorata)."""
    comp = {c["ticker"]: c for c in market.companies}
    total = 0.0
    for t, pos in player.portfolio.items():
        price = market.price_of(t)
        c = comp.get(t)
        if price and c:
            total += price * pos["shares"] * c.get("div_yield", 0.0) * (days / 365.0)
    return total


def portfolio_beta(player, market):
    """Bêta moyen pondéré du portefeuille (exposition au risque de marché)."""
    comp = {c["ticker"]: c for c in market.companies}
    tot = positions_value(player, market)
    if tot <= 0:
        return 0.0
    b = 0.0
    for t, p in player.portfolio.items():
        price = market.price_of(t)
        c = comp.get(t)
        if price is None or not c:
            continue
        b += (price * p["shares"] / tot) * c["beta"]
    return b
