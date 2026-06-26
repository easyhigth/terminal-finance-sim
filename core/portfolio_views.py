"""
portfolio_views.py — Vues de reporting sur le portefeuille (détail des
positions, P&L latent, allocation, dividendes, bêta net). Lecture pure, sans
exécuter d'ordres ni modifier l'état du joueur (sauf, indirectement, aucune
modification du tout — ce module ne fait que lire).
"""
from core import firms
from core.portfolio_margin import net_worth


def holdings(player, market):
    """Détail des positions (valeur signée, P&L latent), triées par |valeur|."""
    out = []
    for t, p in player.portfolio.items():
        price = market.price_of(t)
        if price is None:
            continue
        value = price * p["shares"]
        pnl = (price - p["avg"]) * p["shares"]        # vrai pour long ET short
        # variation en faveur de la position (positive = gain)
        if p["avg"]:
            pnl_pct = ((price / p["avg"] - 1) if p["shares"] > 0
                       else (p["avg"] / price - 1)) * 100
        else:
            pnl_pct = 0.0
        out.append({
            "ticker": t, "shares": p["shares"], "avg": p["avg"], "price": price,
            "value": value, "pnl": pnl, "pnl_pct": pnl_pct,
            "short": p["shares"] < 0,
        })
    out.sort(key=lambda h: abs(h["value"]), reverse=True)
    return out


def unrealized_pnl(player, market):
    total = 0.0
    for t, p in player.portfolio.items():
        price = market.price_of(t)
        if price is not None:
            total += (price - p["avg"]) * p["shares"]
    return total


def sector_heatmap(player, market):
    """Agrège les positions actions par secteur (valeur signée, P&L latent,
    P&L % du coût de base). Lecture pure, sans modification d'état."""
    comp = {c["ticker"]: c for c in market.companies}
    agg = {}
    for h in holdings(player, market):
        c = comp.get(h["ticker"])
        if not c:
            continue
        sec = c["sector"]
        a = agg.setdefault(sec, {"sector": sec, "value": 0.0, "pnl": 0.0, "cost": 0.0})
        a["value"] += h["value"]
        a["pnl"] += h["pnl"]
        a["cost"] += abs(h["value"] - h["pnl"])
    out = list(agg.values())
    for a in out:
        a["pnl_pct"] = (a["pnl"] / a["cost"] * 100.0) if a["cost"] else 0.0
        del a["cost"]
    out.sort(key=lambda a: abs(a["value"]), reverse=True)
    return out


def allocation_by(player, market, key):
    """Répartition de l'exposition (brute) des positions par `key`."""
    comp = {c["ticker"]: c for c in market.companies}
    agg = {}
    for t, p in player.portfolio.items():
        price = market.price_of(t)
        c = comp.get(t)
        if price is None or not c:
            continue
        agg[c[key]] = agg.get(c[key], 0.0) + abs(price * p["shares"])
    return agg


def dividends(player, market, days):
    """Dividendes du tour : les longs en touchent, les shorts en PAIENT."""
    comp = {c["ticker"]: c for c in market.companies}
    total = 0.0
    for t, pos in player.portfolio.items():
        price = market.price_of(t)
        c = comp.get(t)
        if price and c:
            total += price * pos["shares"] * c.get("div_yield", 0.0) * (days / 365.0)
    return total


def portfolio_beta(player, market):
    """Bêta NET du portefeuille (les shorts réduisent l'exposition au marché),
    modulé par la sensibilité de marché de l'ADN de la firme (hedge fund plus
    exposé, desk obligataire/gestionnaire d'actifs plus prudents)."""
    comp = {c["ticker"]: c for c in market.companies}
    eq = net_worth(player, market)
    if eq <= 0:
        return 0.0
    b = 0.0
    for t, p in player.portfolio.items():
        price = market.price_of(t)
        c = comp.get(t)
        if price is None or not c:
            continue
        b += (price * p["shares"] / eq) * c["beta"]
    return b * firms.perk(player, "beta_exposure_mult")
