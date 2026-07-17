"""
themes.py — Thématiques de marché : investir par TENDANCE, pas seulement par
société (logique pure).

Un thème regroupe des sociétés de plusieurs secteurs autour d'un récit
(intelligence artificielle, transition énergétique, santé & démographie…). Deux
usages :
  - un PANIER tradable en un clic (`buy_basket` répartit un budget équipondéré
    sur les constituants via `core/portfolio.py`) — surfer une tendance sans
    sélectionner chaque titre à la main ;
  - un signal de FORCE / ROTATION : `theme_strength` mesure le momentum RÉEL des
    constituants (rendement glissant du panier vs le marché) — un thème « chaud »
    est simplement un thème dont les secteurs ont surperformé récemment. La
    tendance ÉMERGE donc du moteur de marché existant (facteurs sectoriels), sans
    injecter de nouveau facteur : c'est déterministe et non invasif.

Les constituants d'un thème sont STABLES (choisis sur le nombre de titres émis,
statique — pas sur la capitalisation courante qui bouge) pour qu'un panier reste
le même panier d'un pas à l'autre.
"""
from core import portfolio as PF

LOOKBACK = 18                # pas de marché pour le momentum (~3 mois)
BASKET_SIZE = 8              # nb de constituants par thème (les plus gros, stable)

# id -> (label_fr, label_en, desc_fr, desc_en, [secteurs])
THEMES = [
    ("ai", "Intelligence artificielle", "Artificial intelligence",
     "Puces, cloud et logiciels qui portent la vague de l'IA.",
     "Chips, cloud and software riding the AI wave.",
     ["Tech", "Semicon"]),
    ("energy_transition", "Transition énergétique", "Energy transition",
     "Renouvelables, réseaux et matériaux de l'électrification.",
     "Renewables, grids and the materials of electrification.",
     ["Utilities", "Materiaux", "Auto"]),
    ("health_demographics", "Santé & démographie", "Health & demographics",
     "Santé et consommation portées par le vieillissement.",
     "Healthcare and consumption driven by ageing populations.",
     ["Sante", "Conso"]),
    ("luxury_brands", "Luxe & marques", "Luxury & brands",
     "Pouvoir de marque et consommation haut de gamme.",
     "Brand power and premium consumption.",
     ["Luxe", "Conso"]),
    ("reshoring", "Relocalisation industrielle", "Industrial reshoring",
     "Industrie, matériaux et énergie de la relocalisation.",
     "Industry, materials and energy of supply-chain reshoring.",
     ["Industrie", "Materiaux", "Energie"]),
    ("digital_finance", "Finance digitale", "Digital finance",
     "Finance et télécoms de la digitalisation des paiements.",
     "Finance and telecom of payments digitalization.",
     ["Finance", "Telecom"]),
]
_BY_ID = {t[0]: t for t in THEMES}


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


def theme_label(theme_id):
    t = _BY_ID.get(theme_id)
    return _L(t[1], t[2]) if t else theme_id


def theme_desc(theme_id):
    t = _BY_ID.get(theme_id)
    return _L(t[3], t[4]) if t else ""


def theme_sectors(theme_id):
    t = _BY_ID.get(theme_id)
    return list(t[5]) if t else []


def constituents(market, theme_id, n=BASKET_SIZE):
    """Tickers du panier : les plus grosses sociétés (par nombre de titres
    émis — STATIQUE, donc panier stable dans le temps) des secteurs du thème."""
    sectors = set(theme_sectors(theme_id))
    if not sectors:
        return []
    members = [c for c in market.companies if c["sector"] in sectors]
    members.sort(key=lambda c: c.get("shares", 0.0), reverse=True)
    return [c["ticker"] for c in members[:n]]


def _trailing_return(market, ticker, lookback):
    hist = market.history_of(ticker, n=lookback + 1)
    if len(hist) < 2 or hist[0] <= 0:
        return 0.0
    return hist[-1] / hist[0] - 1.0


def _market_baseline(market, lookback):
    """Rendement glissant moyen d'un large échantillon (référence marché)."""
    sample = [c["ticker"] for c in market.companies[:60]]
    rets = [_trailing_return(market, t, lookback) for t in sample]
    return sum(rets) / len(rets) if rets else 0.0


def theme_strength(market, theme_id, lookback=LOOKBACK):
    """Momentum du thème : rendement glissant du panier, absolu ET relatif au
    marché. {basket_return, market_return, relative}."""
    tks = constituents(market, theme_id)
    if not tks:
        return {"basket_return": 0.0, "market_return": 0.0, "relative": 0.0}
    rets = [_trailing_return(market, t, lookback) for t in tks]
    basket = sum(rets) / len(rets)
    base = _market_baseline(market, lookback)
    return {"basket_return": basket, "market_return": base, "relative": basket - base}


def heat_ranking(market, lookback=LOOKBACK):
    """Thèmes triés du plus CHAUD au plus froid (force relative décroissante).
    [{id, label, strength}]."""
    rows = []
    for tid, *_r in THEMES:
        s = theme_strength(market, tid, lookback)
        rows.append({"id": tid, "label": theme_label(tid), "strength": s})
    rows.sort(key=lambda r: r["strength"]["relative"], reverse=True)
    return rows


def basket_exposure(player, market, theme_id):
    """Valeur des positions LONGUES du joueur qui recoupent le panier du thème
    (exposition thématique actuelle)."""
    tks = set(constituents(market, theme_id))
    total = 0.0
    for tk, pos in player.portfolio.items():
        if tk in tks and pos["shares"] > 0:
            price = market.price_of(tk)
            if price is not None:
                total += price * pos["shares"]
    return total


def buy_basket(player, market, theme_id, budget):
    """Répartit `budget` de façon équipondérée sur les constituants du thème
    (ordres entiers, best-effort via core/portfolio.buy — un ordre refusé
    (levier, secteur exclu…) est collecté sans bloquer les autres). Retourne
    {ok, bought: [(ticker, qty)], failed: [(ticker, reason)], spent}."""
    tks = constituents(market, theme_id)
    if not tks or budget <= 0:
        return {"ok": False, "bought": [], "failed": [], "spent": 0.0}
    per = budget / len(tks)
    bought, failed, spent = [], [], 0.0
    for tk in tks:
        price = market.price_of(tk)
        if price is None or price <= 0:
            failed.append((tk, "price"))
            continue
        qty = int(per // price)
        if qty <= 0:
            failed.append((tk, "budget"))
            continue
        res = PF.buy(player, market, tk, qty)
        if res.get("ok"):
            bought.append((tk, qty))
            spent += res.get("total", price * qty)
        else:
            failed.append((tk, res.get("reason", "?")))
    return {"ok": bool(bought), "bought": bought, "failed": failed, "spent": spent}
