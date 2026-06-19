"""
screener.py — Filtres de recherche actions/ETF et vue de comparaison
multi-actifs (logique pure, sans pygame).

Réutilise les fondamentaux déjà calculés par core/market.py (`metrics()`,
`returns_over()`) et core/etfs.py (`quote()`), sans dupliquer de pricing :
ce module ne fait qu'agréger/filtrer des dicts déjà produits ailleurs.
"""
from core import etfs as etf_mod

_RATING_ORDER = {"AAA": 0, "AA": 1, "A": 2, "BBB": 3, "BB": 4, "B": 5}


def screen_stocks(market, region=None, sector=None, cap_min=None, cap_max=None,
                   pe_max=None, margin_min=None, growth_min=None, growth_max=None,
                   beta_max=None, momentum_min=None, momentum_period=18, limit=60):
    """Filtre l'univers actions par région/secteur/capitalisation/valorisation
    (P/E)/qualité (marge nette)/croissance (variation 1 an)/volatilité
    (bêta)/momentum (variation sur `momentum_period` pas). Retourne une liste
    de dicts `metrics()`, triée par capitalisation décroissante."""
    out = []
    mom = market.returns_over(momentum_period) if momentum_min is not None else None
    for c in market.companies:
        if region is not None and c["region"] != region:
            continue
        if sector is not None and c["sector"] != sector:
            continue
        mt = market.metrics(c["ticker"])
        if cap_min is not None and mt["mktcap"] < cap_min:
            continue
        if cap_max is not None and mt["mktcap"] > cap_max:
            continue
        if pe_max is not None and (mt["pe"] is None or mt["pe"] > pe_max):
            continue
        if margin_min is not None and mt["net_margin"] * 100.0 < margin_min:
            continue
        if growth_min is not None and mt["change_pct"] < growth_min:
            continue
        if growth_max is not None and mt["change_pct"] > growth_max:
            continue
        if beta_max is not None and mt["beta"] > beta_max:
            continue
        if momentum_min is not None:
            i = market.ticker_idx[c["ticker"]]
            if float(mom[i]) < momentum_min:
                continue
        out.append(mt)
    out.sort(key=lambda m: m["mktcap"], reverse=True)
    return out[:limit]


def screen_etfs(market, category=None, region=None, style=None, theme=None,
                 duration_min=None, duration_max=None, rating_min=None,
                 dividend_min=None, expense_max=None, limit=60):
    """Filtre l'univers ETF par catégorie/zone/style/thème/duration
    (obligataire)/qualité de crédit minimale/rendement de dividende/frais.
    Retourne une liste de dicts `etfs.quote()`."""
    out = []
    for etf in etf_mod.all_etfs():
        if category is not None and etf.category != category:
            continue
        e = etf.engine
        if region is not None:
            regions = e.get("regions") if e["type"] == "equity" else None
            if not regions or region not in regions:
                continue
        if style is not None and e.get("style") != style:
            continue
        if theme is not None and e.get("theme") != theme:
            continue
        if expense_max is not None and etf.expense > expense_max:
            continue
        if e["type"] == "bond":
            years = e["years"]
            if duration_min is not None and years < duration_min:
                continue
            if duration_max is not None and years > duration_max:
                continue
            if rating_min is not None and _RATING_ORDER.get(e["rating"], 99) > _RATING_ORDER.get(rating_min, 99):
                continue
        elif duration_min is not None or duration_max is not None or rating_min is not None:
            continue   # filtres obligataires non applicables aux autres familles
        q = etf_mod.quote(market, etf.id)
        if dividend_min is not None and q["yield"] * 100.0 < dividend_min:
            continue
        out.append(q)
    out.sort(key=lambda q: q["id"])
    return out[:limit]


def compare_stocks(market, tickers):
    """Assemble les fondamentaux de plusieurs actions côte à côte (vue
    Comparer)."""
    out = []
    for tk in tickers:
        mt = market.metrics(tk)
        if mt:
            out.append(mt)
    return out


def compare_etfs(market, eids):
    """Assemble les cotations de plusieurs ETF côte à côte (vue Comparer)."""
    out = []
    for eid in eids:
        q = etf_mod.quote(market, eid)
        if q:
            out.append(q)
    return out
