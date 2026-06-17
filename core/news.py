"""
news.py — Fil d'actualités persistant & catégorisé (logique pure, sans pygame).

Le jeu produit déjà beaucoup d'événements à chaque tour (chocs de marché,
résultats, régime, scénarios, campagne historique, politique régionale,
réglementaire…). Ce module les CENTRALISE en un fil unique, CATÉGORISÉ et
PERSISTANT, qui alimente :

  - la scène NEWS & ÉVÉNEMENTS (filtrable par type / région), avec un historique
    consultable jusqu'à 3 ans en arrière ;
  - les marqueurs PERSISTANTS de la carte du monde (les news du jour restent
    affichées là où elles se produisent, puis sont remplacées le lendemain).

Chaque item : {"day", "cat", "kind", "region", "text", "source"}.
  - cat  : catégorie de filtrage (cf. CATEGORIES) ;
  - kind : "good" / "bad" / "info" (couleur) ;
  - region : région concernée (ou None = mondial).

Persistance : stocké dans PlayerState.news_history (sérialisé JSON). On purge
au-delà de MAX_AGE_DAYS (3 ans) et on borne la taille (MAX_HISTORY).
"""

CATEGORIES = [
    ("market",     "Marché"),
    ("macro",      "Macro"),
    ("corporate",  "Entreprises"),
    ("political",  "Politique"),
    ("regulatory", "Réglementaire"),
    ("event",      "Événements"),
]
CATEGORY_LABEL = {k: v for k, v in CATEGORIES}

MAX_AGE_DAYS = 365 * 3       # on garde jusqu'à 3 ans d'historique
MAX_HISTORY = 800            # borne dure (taille de sauvegarde)


def make(cat, kind, text, region=None, source=None):
    return {"cat": cat, "kind": kind, "text": text, "region": region, "source": source}


def categorize_market(item):
    """Catégorise un item de news du moteur de marché (core/market.py)."""
    txt = (item.get("text") or "")
    if txt.startswith("Résultats"):
        return "corporate"
    if txt.startswith("Bascule de régime"):
        return "macro"
    return "market"


def record(player, items, day):
    """Ajoute les items du jour à l'historique persistant, horodatés, puis purge
    les entrées de plus de 3 ans et borne la taille totale.
    `items` : liste de dicts make()/{cat,kind,text,region}. Retourne les items
    effectivement enregistrés (avec leur jour)."""
    hist = getattr(player, "news_history", None)
    if hist is None:
        player.news_history = hist = []
    stored = []
    for it in items:
        if not it or not it.get("text"):
            continue
        entry = {"day": day, "cat": it.get("cat", "market"),
                 "kind": it.get("kind", "info"), "region": it.get("region"),
                 "text": it["text"], "source": it.get("source")}
        hist.append(entry)
        stored.append(entry)
    # purge par âge (3 ans) puis par taille
    cutoff = day - MAX_AGE_DAYS
    if hist and hist[0]["day"] < cutoff:
        player.news_history = hist = [e for e in hist if e["day"] >= cutoff]
    if len(hist) > MAX_HISTORY:
        del hist[:len(hist) - MAX_HISTORY]
    return stored


def query(player, cat=None, region=None, kind=None, limit=None):
    """Renvoie l'historique filtré (plus récent en premier)."""
    hist = getattr(player, "news_history", []) or []
    out = []
    for e in reversed(hist):
        if cat and e["cat"] != cat:
            continue
        if region and e["region"] != region:
            continue
        if kind and e["kind"] != kind:
            continue
        out.append(e)
        if limit and len(out) >= limit:
            break
    return out


def for_day(player, day):
    """Items d'un jour donné (pour les marqueurs persistants de la carte)."""
    hist = getattr(player, "news_history", []) or []
    return [e for e in hist if e["day"] == day]


def counts_by_category(player):
    """Compte par catégorie (pour les badges de filtre)."""
    hist = getattr(player, "news_history", []) or []
    out = {k: 0 for k, _ in CATEGORIES}
    for e in hist:
        out[e["cat"]] = out.get(e["cat"], 0) + 1
    return out
