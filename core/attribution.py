"""
attribution.py — Attribution de performance du book réel (logique pure).

Décompose le P&L de PRIX du dernier pas selon 5 axes :
  - secteur / région : le P&L des positions actions ventilé par secteur/région
    (où la performance a-t-elle été générée ?) ;
  - style : Croissance vs Valeur, par un proxy simple sur le rendement du
    dividende (médiane du roster — pas de tag explicite dans data/companies.py) ;
  - sélection de titres / timing : réutilise market.factor_attribution(), qui
    décompose le rendement de chaque société (drift + monde + secteur + région
    + spécifique) — la composante SPÉCIFIQUE (non expliquée par les facteurs
    macro communs) mesure le stock-picking, les composantes MONDE + DÉRIVE
    mesurent l'effet de l'exposition globale au marché (timing).
"""


def _equity_holdings_map(player):
    return {t: p["shares"] for t, p in player.portfolio.items()}


def _grouped(player, market, key_fn):
    """P&L de prix du dernier pas des positions actions, groupé par `key_fn(company)`."""
    comp = {c["ticker"]: c for c in market.companies}
    out = {}
    if market.prev_price is None:
        return out
    for t, shares in _equity_holdings_map(player).items():
        c = comp.get(t)
        i = market.ticker_idx.get(t)
        if c is None or i is None or not shares:
            continue
        pnl = shares * (float(market.price[i]) - float(market.prev_price[i]))
        key = key_fn(c)
        out[key] = out.get(key, 0.0) + pnl
    return out


def sector_attribution(player, market):
    """P&L de prix du dernier pas, ventilé par secteur."""
    return _grouped(player, market, lambda c: c["sector"])


def region_attribution(player, market):
    """P&L de prix du dernier pas, ventilé par région."""
    return _grouped(player, market, lambda c: c["region"])


def style_attribution(player, market):
    """P&L de prix du dernier pas, ventilé Croissance/Valeur (proxy : rendement
    du dividende au-dessus/en-dessous de la médiane du roster)."""
    divs = sorted(c.get("div_yield", 0.0) for c in market.companies)
    median_div = divs[len(divs) // 2] if divs else 0.0
    return _grouped(player, market,
                     lambda c: "Valeur" if c.get("div_yield", 0.0) >= median_div else "Croissance")


def selection_timing_attribution(player, market):
    """Sélection de titres (composante spécifique du modèle à facteurs, non
    expliquée par monde/secteur/région) vs. timing (exposition monde + dérive),
    sur le dernier pas. Réutilise market.factor_attribution() (même modèle que
    core/risk.py)."""
    agg = market.factor_attribution(_equity_holdings_map(player))
    return {"selection": agg["specific"], "timing": agg["world"] + agg["drift"],
            "sector_factor": agg["sector"], "region_factor": agg["region"],
            "total": agg["total"]}
