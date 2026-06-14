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

Conventions :
  equity (valeur nette) = cash + Σ shares·prix   (les shorts pèsent négativement)
  exposition brute      = Σ |shares|·prix
  levier                = exposition brute / equity
"""
from core import config
from core import tracks

COMMISSION = 0.001        # 10 points de base par transaction
MAINT_MARGIN = 0.25       # equity/exposition mini avant appel de marge
MARGIN_SPREAD = 0.03      # surcoût annuel sur le taux directeur (emprunt sur marge)
SHORT_FEE_ANNUAL = 0.01   # frais d'emprunt de titres annuels (notionnel short)
LIQUIDATION_FEE = 0.005   # surcoût appliqué à la valeur liquidée lors d'un appel de marge


def max_leverage(grade_index):
    """Levier maximal autorisé, croissant avec le grade (1.5x → 4.0x)."""
    return min(4.0, 1.5 + 0.25 * grade_index)


def _commission(player):
    """Commission effective (réduite pour la voie Portfolio)."""
    return COMMISSION * tracks.perk(player, "commission_mult")


def _max_leverage(player):
    """Levier maximal effectif (bonus de voie Risk inclus)."""
    return max_leverage(player.grade_index) + tracks.perk(player, "max_leverage_add")


def _maint_margin(player):
    """Marge de maintenance effective (plus clémente pour la voie Risk)."""
    m = tracks.perk(player, "maint_margin")
    return MAINT_MARGIN if m is None else m


# ---------------------------------------------------------------------------
# Mesures d'état
# ---------------------------------------------------------------------------
def positions_value(player, market):
    """Valeur SIGNÉE des positions (les shorts comptent négativement)."""
    total = 0.0
    for t, p in player.portfolio.items():
        price = market.price_of(t)
        if price is not None:
            total += price * p["shares"]
    return total


def gross_exposure(player, market):
    """Exposition brute = somme des valeurs absolues des positions."""
    total = 0.0
    for t, p in player.portfolio.items():
        price = market.price_of(t)
        if price is not None:
            total += abs(price * p["shares"])
    return total


def net_worth(player, market):
    """Valeur nette = trésorerie (éventuellement négative) + positions signées."""
    return player.cash + positions_value(player, market)


def leverage(player, market):
    eq = net_worth(player, market)
    if eq <= 0:
        return float("inf") if gross_exposure(player, market) > 0 else 0.0
    return gross_exposure(player, market) / eq


def margin_status(player, market):
    """Synthèse de marge : equity, exposition, levier, pouvoir d'achat, alerte."""
    eq = net_worth(player, market)
    gross = gross_exposure(player, market)
    maxlev = _max_leverage(player)
    buying_power = max(0.0, maxlev * eq - gross)
    # appel de marge dès que l'equity passe sous la marge de maintenance
    # (y compris equity négative : c'est le cas le plus grave)
    call = gross > 0 and eq < _maint_margin(player) * gross
    return {"equity": eq, "gross": gross, "leverage": (gross / eq) if eq > 0 else float("inf"),
            "max_leverage": maxlev, "buying_power": buying_power,
            "borrowed": max(0.0, -player.cash), "margin_call": call}


def _would_exceed_leverage(player, market, new_gross, fee=0.0):
    """Vrai si une exposition brute `new_gross` dépasserait le levier autorisé."""
    eq = net_worth(player, market) - fee
    maxlev = _max_leverage(player)
    if eq <= 0:
        return new_gross > 0
    return new_gross > maxlev * eq + 1e-6


def _gross_excluding(player, market, ticker):
    """Exposition brute hors `ticker` (pour évaluer une nouvelle position)."""
    g = 0.0
    for t, p in player.portfolio.items():
        if t == ticker:
            continue
        price = market.price_of(t)
        if price is not None:
            g += abs(price * p["shares"])
    return g


# ---------------------------------------------------------------------------
# Achat / vente longue
# ---------------------------------------------------------------------------
def buy(player, market, ticker, qty):
    """Ouvre/renforce une position LONGUE (achat sur marge autorisé selon levier).
    Refuse si une position courte est ouverte (utiliser COVER d'abord)."""
    price = market.price_of(ticker)
    if price is None:
        return {"ok": False, "reason": "ticker"}
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    pos = player.portfolio.get(ticker)
    if pos and pos["shares"] < 0:
        return {"ok": False, "reason": "isshort"}
    cost = price * qty
    fee = cost * _commission(player)
    cur_shares = pos["shares"] if pos else 0.0
    new_gross = _gross_excluding(player, market, ticker) + abs((cur_shares + qty) * price)
    if _would_exceed_leverage(player, market, new_gross, fee):
        return {"ok": False, "reason": "leverage",
                "max_leverage": _max_leverage(player)}
    player.cash -= (cost + fee)
    if pos:
        n = pos["shares"] + qty
        pos["avg"] = (pos["shares"] * pos["avg"] + cost) / n
        pos["shares"] = n
    else:
        player.portfolio[ticker] = {"shares": float(qty), "avg": price}
    market.track_company(ticker)
    return {"ok": True, "price": price, "qty": qty, "fee": fee, "total": cost + fee}


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
    proceeds = price * qty
    fee = proceeds * _commission(player)
    net = proceeds - fee
    realized = (price - pos["avg"]) * qty - fee
    player.cash += net
    player.realized_pnl = getattr(player, "realized_pnl", 0.0) + realized
    pos["shares"] -= qty
    if abs(pos["shares"]) <= 1e-9:
        del player.portfolio[ticker]
    return {"ok": True, "price": price, "qty": qty, "net": net, "fee": fee,
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
    proceeds = price * qty
    fee = proceeds * _commission(player)
    cur_shares = pos["shares"] if pos else 0.0
    new_gross = _gross_excluding(player, market, ticker) + abs((cur_shares - qty) * price)
    if _would_exceed_leverage(player, market, new_gross, fee):
        return {"ok": False, "reason": "leverage",
                "max_leverage": _max_leverage(player)}
    player.cash += (proceeds - fee)
    if pos:
        n = pos["shares"] - qty                       # plus négatif
        pos["avg"] = (abs(pos["shares"]) * pos["avg"] + proceeds) / abs(n)
        pos["shares"] = n
    else:
        player.portfolio[ticker] = {"shares": float(-qty), "avg": price}
    market.track_company(ticker)
    return {"ok": True, "price": price, "qty": qty, "fee": fee, "net": proceeds - fee}


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
    cost = price * qty
    fee = cost * _commission(player)
    realized = (pos["avg"] - price) * qty - fee       # short gagne quand le prix baisse
    player.cash -= (cost + fee)
    player.realized_pnl = getattr(player, "realized_pnl", 0.0) + realized
    pos["shares"] += qty
    if abs(pos["shares"]) <= 1e-9:
        del player.portfolio[ticker]
    return {"ok": True, "price": price, "qty": qty, "cost": cost + fee, "fee": fee,
            "realized": realized}


# ---------------------------------------------------------------------------
# Financement (intérêts sur marge + frais d'emprunt de titres) & appel de marge
# ---------------------------------------------------------------------------
def accrue_financing(player, market, days):
    """Prélève les frais de financement du tour : intérêts sur le capital
    emprunté (cash négatif) + frais d'emprunt de titres sur les shorts."""
    yr = days / 365.0
    rate = market.macro["rate"]["v"] / 100.0 if hasattr(market, "macro") else 0.03
    borrowed = max(0.0, -player.cash)
    interest = borrowed * (rate + MARGIN_SPREAD * tracks.perk(player, "margin_spread_mult")) * yr
    short_notional = sum(abs(p["shares"]) * (market.price_of(t) or 0.0)
                         for t, p in player.portfolio.items() if p["shares"] < 0)
    borrow_fee = short_notional * SHORT_FEE_ANNUAL * yr
    total = interest + borrow_fee
    if total:
        player.cash -= total
    return {"interest": interest, "borrow_fee": borrow_fee, "total": total}


def check_margin_call(player, market):
    """Si l'equity passe sous la marge de maintenance, liquide d'office des
    positions (au prorata) pour ramener le levier en zone sûre. Retourne un
    rapport, ou None si rien à faire."""
    st = margin_status(player, market)
    if not st["margin_call"]:
        return None
    eq = st["equity"]
    safe_lev = min(_max_leverage(player), 1.5)
    target_gross = max(0.0, eq * safe_lev)
    gross = st["gross"]
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
    penalty = liquidated * LIQUIDATION_FEE
    player.cash -= penalty
    return {"triggered": True, "liquidated": liquidated, "penalty": penalty}


# ---------------------------------------------------------------------------
# Vues (détail, P&L, allocation, bêta, dividendes)
# ---------------------------------------------------------------------------
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
    """Bêta NET du portefeuille (les shorts réduisent l'exposition au marché)."""
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
    return b
