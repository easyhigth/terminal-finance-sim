"""
global_search.py — Recherche globale sur les DONNÉES DE PARTIE du joueur
(positions, watchlist, inbox, mandats actifs, deals actifs).

Distincte de la palette de navigation (Ctrl+K, core/scene_manager.py), qui
cherche du contenu de RÉFÉRENCE (tickers du marché, glossaire, leçons,
scènes) — ici on cherche dans ce que le joueur possède/reçoit DÉJÀ dans SA
partie en cours : "où est ma position MVC", "quel message parlait de X",
"quel mandat concerne ce client". Logique pure (pas de pygame) : testable
seule, consommée par scenes/scene_desktop.py (raccourci Ctrl+/ — Ctrl+F est
déjà pris par le rail du terminal pour M&A, cf. RAIL_SHORTCUTS).

Chaque résultat : {"label": str, "kind": str, "action": {...}} où `action`
décrit la navigation à effectuer (interprétée par l'appelant, qui connaît le
bureau) — ce module ne dessine ni ne navigue lui-même.
"""
from core import fuzzy

RESULT_LIMIT = 30


def _company_name(market, ticker):
    if market is None:
        return ""
    i = market.ticker_idx.get(ticker)
    return market.companies[i]["name"] if i is not None else ""


def _position_entries(player, market):
    out = []
    for tk, pos in player.portfolio.items():
        name = _company_name(market, tk)
        side = "long" if pos["shares"] > 0 else "short"
        label = f"{tk} — {name} · position {side} ({pos['shares']:+.0f})"
        out.append({"label": label, "kind": "position", "haystack": f"{tk} {name}",
                    "action": {"open": "trading", "ticker": tk}})
    return out


def _watchlist_entries(player, market):
    out = []
    for tk in getattr(player, "watchlist", None) or []:
        name = _company_name(market, tk)
        out.append({"label": f"{tk} — {name} · suivi (watchlist)", "kind": "watchlist",
                    "haystack": f"{tk} {name}",
                    "action": {"open": "trading", "ticker": tk}})
    return out


def _inbox_entries(player):
    out = []
    for msg in getattr(player, "inbox", None) or []:
        subj = msg.get("subject", "")
        sender = msg.get("sender", "")
        label = f"Inbox · {subj} ({sender})"
        out.append({"label": label, "kind": "inbox",
                    "haystack": f"{subj} {sender} {msg.get('body', '')}",
                    "action": {"open": "scene", "name": "inbox"}})
    return out


def _mandate_entries(player):
    out = []
    for m in getattr(player, "mandates", None) or []:
        client = m.get("client", "?")
        label = f"Mandat · {client}"
        out.append({"label": label, "kind": "mandate", "haystack": client,
                    "action": {"open": "scene", "name": "mandates"}})
    return out


def _deal_entries(player):
    out = []
    for d in getattr(player, "deals", None) or []:
        title = d.get("title", "?")
        label = f"Deal · {title}"
        out.append({"label": label, "kind": "deal", "haystack": title,
                    "action": {"open": "scene", "name": "deals"}})
    return out


def all_entries(player, market):
    """Toutes les entrées cherchables (sans filtre) — utilisé pour la liste
    par défaut (requête vide) et comme base du filtrage."""
    return (_position_entries(player, market) + _watchlist_entries(player, market)
            + _inbox_entries(player) + _mandate_entries(player) + _deal_entries(player))


def search(player, market, query, limit=RESULT_LIMIT):
    """Renvoie les entrées correspondant à `query` (sous-séquence floue, cf.
    core/fuzzy.py), triées par pertinence. Requête vide -> tout, dans l'ordre
    naturel (positions puis watchlist puis inbox puis mandats puis deals)."""
    entries = all_entries(player, market)
    q = (query or "").strip()
    if not q:
        return entries[:limit]
    hits = fuzzy.filter_sorted(q, entries, key=lambda e: e["haystack"])
    return hits[:limit]
