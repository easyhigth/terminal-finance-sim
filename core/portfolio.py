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
from core import firms, liquidity, tracks
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
HALF_SPREAD = 0.0008      # demi-spread bid/ask de base (8 bps, grosse capi, marché calme)
SPREAD_TIER_MULT = {      # multiplicateur de demi-spread par tier de liquidité actions
    "Liquide": 1.0,       # (cf. core/liquidity.equity_tier_for_cap, dérivé de la capi —
    "Peu liquide": 1.6,   # même logique que pour obligations/matières premières/crypto :
    "Illiquide": 2.6,     # une petite capi cote avec un spread plus large qu'une
}                          # grosse capi, indépendamment de la taille de l'ordre passé)
SPREAD_STRESS_MAX_MULT = 1.5  # à stress maximal, le demi-spread est multiplié par
                               # (1 + ce facteur) — même calibrage que
                               # core/liquidity.STRESS_SPREAD_MAX_MULT, pour que toutes
                               # les classes d'actifs réagissent de façon cohérente
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
    """Commission effective (réduite pour la voie Portfolio, modulée par le
    focus du trimestre — cf. core/focus.py)."""
    from core import focus as _focus
    return (COMMISSION * tracks.perk(player, "commission_mult")
            * _focus.perk(player, "commission_mult"))


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

    Le demi-spread ET l'impact varient désormais tous les deux selon trois axes :
      - LIQUIDITÉ de l'action (tier dérivé de la capi, cf. core/liquidity.equity_tier) :
        une petite capi cote avec un spread plus large qu'une grosse capi, indépendamment
        de la taille de l'ordre passé (SPREAD_TIER_MULT) ;
      - RÉGIME / STRESS de marché courant (market.last_stress_level, 0..1, déjà calculé
        par Market._stress_level() à partir de l'asymétrie de volatilité et du régime
        de fond) : spread et impact s'élargissent tous deux en marché volatil/récession ;
      - TAILLE de l'ordre rapportée à la liquidité (capi, proxy de profondeur) — modèle
        d'impact non-linéaire (Almgren-Chriss) inchangé depuis le chantier précédent.
    Un gros ordre « mange » le carnet, et le carnet est plus mince en pleine crise ou
    sur une petite capi — ces trois effets se combinent (spread élargi + impact accru)."""
    i = market.ticker_idx.get(ticker)
    mid = market.price_of(ticker)
    if i is None or mid is None:
        return mid
    cap = float(market.price[i] * market.shares[i])            # capi (proxy de profondeur)
    order_value = abs(qty) * mid
    stress_level = getattr(market, "last_stress_level", 0.0)
    stress_frac = min(1.0, max(0.0, stress_level))
    tier = liquidity.equity_tier_for_cap(cap)
    tier_mult = SPREAD_TIER_MULT.get(tier, 1.0)
    half_spread = HALF_SPREAD * tier_mult * (1.0 + SPREAD_STRESS_MAX_MULT * stress_frac)
    impact = market_impact(order_value, cap, stress_level)
    cost_frac = half_spread + impact
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
            "realized": realized, "slippage": fill - price}


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
# Actions de portefeuille en un geste (rééquilibrage, liquidation)
# ---------------------------------------------------------------------------
def rebalance_equal_weights(player, market):
    """Ramène les positions ACTIONS LONGUES à poids égaux (FACTORISÉ depuis
    la commande REBALANCE du terminal, désormais partagé avec le bouton
    « ÉQUIL. » de l'app Portefeuille). Retourne {"ok", "reason"|"lines"}."""
    if len(player.portfolio) < 2:
        return {"ok": False, "reason": "need2"}
    pos_val = positions_value(player, market)
    target = pos_val / len(player.portfolio)
    for tk in list(player.portfolio.keys()):
        price = market.price_of(tk)
        if not price:
            continue
        cur = player.portfolio[tk]["shares"] * price
        diff = target - cur
        qty = int(abs(diff) // price)
        if qty <= 0:
            continue
        if diff > 0:
            buy(player, market, tk, qty)
        else:
            sell(player, market, tk, qty)
    return {"ok": True, "lines": len(player.portfolio)}


def liquidate_all(player, market):
    """Liquide TOUTES les positions, toutes classes d'actifs : vend les
    actions longues, couvre les shorts, vend ETF/obligations/matières
    premières/crypto/structurés/crédit. Geste de crise (bouton « TOUT
    VENDRE » du Portefeuille, derrière une confirmation) — chaque vente
    passe par le chemin d'exécution normal (spread/impact/commissions),
    aucune position n'est effacée gratuitement. Retourne un résumé
    {"closed": n, "realized": P&L réalisé total des ventes}."""
    from core import bonds as _bonds
    from core import commodities as _cm
    from core import crypto as _crypto
    from core import etfs as _etf
    from core import securitisation as _sec
    from core import structured as _struct
    closed = 0
    realized = 0.0
    for tk in list(player.portfolio.keys()):
        pos = player.portfolio.get(tk)
        if not pos:
            continue
        r = (sell(player, market, tk, "ALL") if pos["shares"] > 0
             else cover(player, market, tk, "ALL"))
        if r.get("ok"):
            closed += 1
            realized += r.get("realized", 0.0)
    for key in list(getattr(player, "etfs", {}) or {}):
        r = _etf.sell(player, market, key, player.etfs[key]["qty"])
        if r.get("ok"):
            closed += 1
            realized += r.get("realized", 0.0)
    for key in list(getattr(player, "bonds", {}) or {}):
        r = _bonds.sell_bond(player, market, key, player.bonds[key]["qty"])
        if r.get("ok"):
            closed += 1
            realized += r.get("realized", 0.0)
    for key in list(getattr(player, "commodities", {}) or {}):
        r = _cm.sell(player, market, key, player.commodities[key]["qty"])
        if r.get("ok"):
            closed += 1
            realized += r.get("realized", 0.0)
    for key in list(getattr(player, "crypto", {}) or {}):
        r = _crypto.sell(player, market, key, player.crypto[key]["qty"])
        if r.get("ok"):
            closed += 1
            realized += r.get("realized", 0.0)
    # structurés / titrisation : positions en LISTES de souscriptions
    # (player.structured / player.securitised), agrégées par identifiant de
    # produit avant vente (sell_by_type / sell prennent un notional total)
    struct_ids = {p.get("tpl_id", p.get("type")) for p in getattr(player, "structured", [])}
    for key in struct_ids:
        notional = _struct.held_notional(player, key)
        if notional <= 0:
            continue
        r = _struct.sell_by_type(player, market, key, notional)
        if r.get("ok"):
            closed += 1
            realized += r.get("realized", 0.0)
    sec_ids = {p["id"] for p in getattr(player, "securitised", [])}
    for key in sec_ids:
        notional = _sec.held_notional(player, key)
        if notional <= 0:
            continue
        r = _sec.sell(player, market, key, notional)
        if r.get("ok"):
            closed += 1
            realized += r.get("realized", 0.0)
    return {"closed": closed, "realized": realized}


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
