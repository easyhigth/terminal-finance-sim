"""
portfolio_margin.py — Levier, marge et valeur nette du portefeuille.

Calculs purs sur l'état du compte (equity, exposition brute, levier autorisé,
appel de marge, financement) — sans exécuter d'ordres. core/portfolio.py
s'appuie sur ce module pour vérifier le levier avant d'exécuter un ordre.

Conventions :
  equity (valeur nette) = cash + Σ shares·prix   (les shorts pèsent négativement)
  exposition brute      = Σ |shares|·prix
  levier                = exposition brute / equity
"""
from core import firms, tracks

MAINT_MARGIN = 0.25       # equity/exposition mini avant appel de marge
MARGIN_SPREAD = 0.03      # surcoût annuel sur le taux directeur (emprunt sur marge)
SHORT_FEE_ANNUAL = 0.01   # frais d'emprunt de titres annuels (notionnel short)


def max_leverage(grade_index):
    """Levier maximal autorisé, croissant avec le grade (1.5x → 4.0x)."""
    return min(4.0, 1.5 + 0.25 * grade_index)


def _max_leverage(player):
    """Levier maximal effectif (bonus de voie Risk + ADN de firme inclus)."""
    return (max_leverage(player.grade_index) + tracks.perk(player, "max_leverage_add")
            + firms.perk(player, "max_leverage_add"))


def _maint_margin(player):
    """Marge de maintenance effective (plus clémente pour la voie Risk,
    modulée par l'ADN de la firme — hedge fund plus stricte, etc.)."""
    m = tracks.perk(player, "maint_margin")
    base = MAINT_MARGIN if m is None else m
    return base * firms.perk(player, "maint_margin_mult")


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
    """Valeur nette = trésorerie + positions actions signées + TOUTES les autres
    classes d'actifs détenues (obligations, commodities, crypto, ETF, produits
    structurés, titrisation, M&A, options, FX, couvertures). Cette valeur nette
    sert aussi d'equity de base pour le levier et l'appel de marge : elle doit
    donc refléter l'intégralité du patrimoine, sinon le levier est surestimé."""
    nw = player.cash + positions_value(player, market)
    if getattr(player, "bonds", None):
        from core import bonds
        nw += bonds.holdings_value(player, market)
    if getattr(player, "commodities", None):
        from core import commodities
        nw += commodities.holdings_value(player, market)
    if getattr(player, "crypto", None):
        from core import crypto as crypto_mod
        nw += crypto_mod.holdings_value(player, market)
    if getattr(player, "etfs", None):
        from core import etfs as etfs_mod
        nw += etfs_mod.holdings_value(player, market)
    if getattr(player, "structured", None):
        from core import structured
        nw += structured.holdings_value(player, market)
    if getattr(player, "securitised", None):
        from core import securitisation
        nw += securitisation.holdings_value(player, market)
    if getattr(player, "ma_owned", None):
        from core import ma
        nw += ma.holdings_value(player)
    if getattr(player, "options", None):
        from core import options as options_mod
        nw += options_mod.holdings_value(player, market)
    if getattr(player, "fx_positions", None):
        from core import fx as fx_mod
        nw += fx_mod.holdings_value(player, market)
    if getattr(player, "hedges", None):
        from core import hedging
        nw += hedging.holdings_value(player, market)
    return nw


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
# Financement (intérêts sur marge + frais d'emprunt de titres)
# ---------------------------------------------------------------------------
def accrue_financing(player, market, days):
    """Prélève les frais de financement du tour : intérêts sur le capital
    emprunté (cash négatif) + frais d'emprunt de titres sur les shorts."""
    yr = days / 365.0
    rate = market.macro["rate"]["v"] / 100.0 if hasattr(market, "macro") else 0.03
    borrowed = max(0.0, -player.cash)
    spread_mult = tracks.perk(player, "margin_spread_mult") * firms.perk(player, "margin_spread_mult")
    interest = borrowed * (rate + MARGIN_SPREAD * spread_mult) * yr
    short_notional = sum(abs(p["shares"]) * (market.price_of(t) or 0.0)
                         for t, p in player.portfolio.items() if p["shares"] < 0)
    borrow_fee = short_notional * SHORT_FEE_ANNUAL * yr
    total = interest + borrow_fee
    if total:
        player.cash -= total
    return {"interest": interest, "borrow_fee": borrow_fee, "total": total}
