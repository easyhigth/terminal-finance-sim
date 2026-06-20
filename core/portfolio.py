"""
portfolio.py — Portefeuille du joueur, P&L réel, LEVIER & VENTE À DÉCOUVERT.

Le joueur achète/vend de vraies sociétés du roster. Les positions sont SIGNÉES :
  shares > 0  → position longue (on parie à la hausse)
  shares < 0  → position courte / short (on parie à la baisse)

Levier : on peut acheter sur marge (la trésorerie devient négative = capital
emprunté) et vendre à découvert, dans la limite d'un levier maximal CROISSANT
avec le grade. Le capital emprunté et les shorts coûtent des frais de financement
chaque tour, et un APPEL DE MARGE liquide d'office si l'equity passe sous le
seuil de maintenance — un krach peut donc réellement ruiner.

État (PlayerState) :
  portfolio    : dict ticker -> {"shares": float signé, "avg": prix d'entrée moyen}
  realized_pnl : P&L réalisé cumulé

Ce module exécute les ORDRES (buy/sell/short/cover) et l'appel de marge. Le
calcul du levier/de la marge vit dans core/portfolio_margin.py, les vues de
reporting (détail des positions, allocation, dividendes...) dans
core/portfolio_views.py — réexportés ici pour que l'API publique (`pf.xxx`)
reste un point d'entrée unique.
"""
from core import firms, tracks
from core.portfolio_margin import (  # noqa: F401 (réexporté, API publique de pf.)
    MAINT_MARGIN,
    MARGIN_SPREAD,
    SHORT_FEE_ANNUAL,
    _gross_excluding,
    _maint_margin,
    _max_leverage,
    _would_exceed_leverage,
    accrue_financing,
    gross_exposure,
    leverage,
    margin_status,
    max_leverage,
    net_worth,
    positions_value,
)
from core.portfolio_views import (  # noqa: F401 (réexporté, API publique de pf.)
    allocation_by,
    dividends,
    holdings,
    portfolio_beta,
    unrealized_pnl,
)

COMMISSION = 0.001        # 10 points de base par transaction
HALF_SPREAD = 0.0008      # demi-spread bid/ask de base (8 bps)
IMPACT_K = 0.12           # coefficient d'impact de marché de base (à tension nulle)
IMPACT_ALPHA = 0.6        # exposant sous-linéaire (style Almgren-Chriss, typiquement
                          # 0.5-0.7) : l'impact croît avec (taille/liquidité)**alpha,
                          # une courbe racine-carré-like — convexe en valeur absolue
                          # mais qui s'aplatit par unité d'ordre (pas purement linéaire)
IMPACT_STRESS_MAX_MULT = 3.0  # à stress de marché maximal (last_stress_level=1.0, cf.
                               # Market._stress_level()/self.last_stress_level), le
                               # coefficient d'impact est multiplié par (1 + ce facteur)
                               # = x4 vs marché calme : la liquidité s'évapore en
                               # crise, le même ordre glisse bien plus qu'en régime calme
MAX_SLIPPAGE = 0.20       # plafond de sécurité (avant : 5 % avec modèle linéaire).
                          # La courbe non-linéaire tasse déjà naturellement l'impact
                          # pour les ordres réalistes ; ce plafond n'évite qu'un fill
                          # absurde sur une taille d'ordre pathologique.
LIQUIDATION_FEE = 0.005   # surcoût appliqué à la valeur liquidée lors d'un appel de marge


def _commission(player):
    """Commission effective (réduite pour la voie Portfolio)."""
    return COMMISSION * tracks.perk(player, "commission_mult")


def market_impact(order_value, liquidity, stress_level=0.0):
    """Impact de marché NON-LINÉAIRE = k_eff * (order_value / liquidité) ** alpha.

    Modèle à la Almgren-Chriss : avec alpha < 1 (ici 0.6), doubler la taille de
    l'ordre NE double PAS l'impact (la courbe est sous-linéaire par unité d'ordre,
    mais reste convexe en valeur absolue) — contrairement à l'ancien modèle
    linéaire-puis-plafonné. Le coefficient effectif k_eff croît avec `stress_level`
    (0..1, cf. Market.last_stress_level / Market._stress_level(), déjà calculé de
    façon déterministe à partir de l'asymétrie de volatilité et du régime de fond
    courant) : un même ordre coûte plus cher en pleine crise qu'en marché calme,
    la liquidité s'évaporant sous stress. Plafonné à MAX_SLIPPAGE par sécurité
    (ordre pathologique)."""
    if liquidity <= 0 or order_value <= 0:
        return 0.0
    stress_frac = min(1.0, max(0.0, stress_level))
    k_eff = IMPACT_K * (1.0 + IMPACT_STRESS_MAX_MULT * stress_frac)
    impact = k_eff * (order_value / liquidity) ** IMPACT_ALPHA
    return min(MAX_SLIPPAGE, impact)


def fill_price(market, ticker, qty, side):
    """Prix d'exécution réel (microstructure) = mid ± demi-spread ± impact de marché.
    L'impact croît de façon NON-LINÉAIRE avec la taille de l'ordre rapportée à la
    liquidité (capi, proxy de profondeur) et avec le stress de marché courant
    (market.last_stress_level, 0..1, cf. core/market.py chantier sur l'asymétrie de
    volatilité) : un gros ordre « mange » le carnet, et le carnet est plus mince en
    pleine crise — pour un même order_value, le slippage est donc plus élevé sur une
    petite capi que sur une grosse, et plus élevé en stress qu'en marché calme."""
    i = market.ticker_idx.get(ticker)
    mid = market.price_of(ticker)
    if i is None or mid is None:
        return mid
    liquidity = float(market.price[i] * market.shares[i])      # capi (proxy de profondeur)
    order_value = abs(qty) * mid
    stress_level = getattr(market, "last_stress_level", 0.0)
    impact = market_impact(order_value, liquidity, stress_level)
    cost_frac = HALF_SPREAD + impact
    return mid * (1 + cost_frac) if side == "buy" else mid * (1 - cost_frac)


# ---------------------------------------------------------------------------
# Achat / vente longue
# ---------------------------------------------------------------------------
def buy(player, market, ticker, qty):
    """Ouvre/renforce une position LONGUE (achat sur marge autorisé selon levier).
    Refuse si une position courte est ouverte (utiliser COVER d'abord), ou si
    le secteur est exclu par l'ADN de la firme (ex. maison ESG vs Énergie)."""
    price = market.price_of(ticker)
    if price is None:
        return {"ok": False, "reason": "ticker"}
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    i = market.ticker_idx.get(ticker)
    sector = market.companies[i]["sector"] if i is not None else None
    if sector is not None and not firms.sector_allowed(player, sector):
        return {"ok": False, "reason": "sector_excluded", "sector": sector}
    pos = player.portfolio.get(ticker)
    if pos and pos["shares"] < 0:
        return {"ok": False, "reason": "isshort"}
    fill = fill_price(market, ticker, qty, "buy")    # prix d'exécution (spread + impact)
    cost = fill * qty
    fee = cost * _commission(player)
    cur_shares = pos["shares"] if pos else 0.0
    new_gross = _gross_excluding(player, market, ticker) + abs((cur_shares + qty) * price)
    if _would_exceed_leverage(player, market, new_gross, fee):
        return {"ok": False, "reason": "leverage",
                "max_leverage": _max_leverage(player)}
    player.cash -= (cost + fee)
    player.total_fees_paid = getattr(player, "total_fees_paid", 0.0) + fee
    if pos:
        n = pos["shares"] + qty
        pos["avg"] = (pos["shares"] * pos["avg"] + cost) / n
        pos["shares"] = n
    else:
        player.portfolio[ticker] = {"shares": float(qty), "avg": fill}
    market.track_company(ticker)
    return {"ok": True, "price": fill, "qty": qty, "fee": fee, "total": cost + fee,
            "slippage": fill - price}


def sell(player, market, ticker, qty):
    """Réduit/clôture une position LONGUE (vend des actions détenues)."""
    pos = player.portfolio.get(ticker)
    if not pos or pos["shares"] <= 0:
        return {"ok": False, "reason": "noposition"}
    price = market.price_of(ticker)
    if price is None:
        return {"ok": False, "reason": "ticker"}
    if qty == "ALL" or qty >= pos["shares"]:
        qty = pos["shares"]
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    fill = fill_price(market, ticker, qty, "sell")
    proceeds = fill * qty
    fee = proceeds * _commission(player)
    net = proceeds - fee
    realized = (fill - pos["avg"]) * qty - fee
    player.cash += net
    player.realized_pnl = getattr(player, "realized_pnl", 0.0) + realized
    player.total_fees_paid = getattr(player, "total_fees_paid", 0.0) + fee
    pos["shares"] -= qty
    if abs(pos["shares"]) <= 1e-9:
        del player.portfolio[ticker]
    return {"ok": True, "price": fill, "qty": qty, "net": net, "fee": fee,
            "realized": realized}


# ---------------------------------------------------------------------------
# Vente à découvert (short) / rachat (cover)
# ---------------------------------------------------------------------------
def short(player, market, ticker, qty):
    """Ouvre/renforce une position COURTE (vend à découvert). Crédite la
    trésorerie du produit de la vente mais crée une dette de titres."""
    price = market.price_of(ticker)
    if price is None:
        return {"ok": False, "reason": "ticker"}
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    pos = player.portfolio.get(ticker)
    if pos and pos["shares"] > 0:
        return {"ok": False, "reason": "islong"}
    fill = fill_price(market, ticker, qty, "sell")
    proceeds = fill * qty
    fee = proceeds * _commission(player)
    cur_shares = pos["shares"] if pos else 0.0
    new_gross = _gross_excluding(player, market, ticker) + abs((cur_shares - qty) * price)
    if _would_exceed_leverage(player, market, new_gross, fee):
        return {"ok": False, "reason": "leverage",
                "max_leverage": _max_leverage(player)}
    player.cash += (proceeds - fee)
    player.total_fees_paid = getattr(player, "total_fees_paid", 0.0) + fee
    if pos:
        n = pos["shares"] - qty                       # plus négatif
        pos["avg"] = (abs(pos["shares"]) * pos["avg"] + proceeds) / abs(n)
        pos["shares"] = n
    else:
        player.portfolio[ticker] = {"shares": float(-qty), "avg": fill}
    market.track_company(ticker)
    return {"ok": True, "price": fill, "qty": qty, "fee": fee, "net": proceeds - fee}


def cover(player, market, ticker, qty):
    """Rachète (clôture) une position COURTE. Réalise le P&L du short."""
    pos = player.portfolio.get(ticker)
    if not pos or pos["shares"] >= 0:
        return {"ok": False, "reason": "noshort"}
    price = market.price_of(ticker)
    if price is None:
        return {"ok": False, "reason": "ticker"}
    short_qty = -pos["shares"]
    if qty == "ALL" or qty >= short_qty:
        qty = short_qty
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    fill = fill_price(market, ticker, qty, "buy")
    cost = fill * qty
    fee = cost * _commission(player)
    realized = (pos["avg"] - fill) * qty - fee        # short gagne quand le prix baisse
    player.cash -= (cost + fee)
    player.realized_pnl = getattr(player, "realized_pnl", 0.0) + realized
    player.total_fees_paid = getattr(player, "total_fees_paid", 0.0) + fee
    pos["shares"] += qty
    if abs(pos["shares"]) <= 1e-9:
        del player.portfolio[ticker]
    return {"ok": True, "price": fill, "qty": qty, "cost": cost + fee, "fee": fee,
            "realized": realized}


# ---------------------------------------------------------------------------
# Appel de marge
# ---------------------------------------------------------------------------
def check_margin_call(player, market):
    """Si l'equity passe sous la marge de maintenance, liquide d'office des
    positions (au prorata) pour ramener le levier en zone sûre. Retourne un
    rapport (avec de quoi expliquer la CAUSE et l'effet au joueur), ou None
    si rien à faire."""
    st = margin_status(player, market)
    if not st["margin_call"]:
        return None
    eq = st["equity"]
    gross = st["gross"]
    leverage_before = st["leverage"]
    threshold = _maint_margin(player) * gross
    safe_lev = min(_max_leverage(player), 1.5)
    target_gross = max(0.0, eq * safe_lev)
    if gross <= target_gross:
        return None
    reduce_frac = min(1.0, (gross - target_gross) / gross)
    liquidated = 0.0
    for t, pos in list(player.portfolio.items()):
        price = market.price_of(t)
        if price is None:
            continue
        qty = abs(pos["shares"]) * reduce_frac
        if qty <= 0:
            continue
        liquidated += qty * price
        if pos["shares"] > 0:
            sell(player, market, t, qty)
        else:
            cover(player, market, t, qty)
    from core import archetypes, firms
    penalty = (liquidated * LIQUIDATION_FEE * archetypes.perk(player, "margin_call_penalty_mult")
               * firms.perk(player, "margin_call_penalty_mult"))
    player.cash -= penalty
    player.flags["margin_call_count"] = player.flags.get("margin_call_count", 0) + 1
    player.total_margin_penalty = getattr(player, "total_margin_penalty", 0.0) + penalty
    leverage_after = leverage(player, market)
    return {"triggered": True, "liquidated": liquidated, "penalty": penalty,
            "equity": eq, "threshold": threshold, "gross_before": gross,
            "leverage_before": leverage_before, "leverage_after": leverage_after,
            "reduce_frac": reduce_frac}
