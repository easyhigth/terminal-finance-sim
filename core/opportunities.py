"""
opportunities.py — Critères de recherche sauvegardés par le joueur ("idées
d'investissement") : persiste des filtres définis une fois et les ré-exécute
à la demande via core/screener.py, sans dupliquer sa logique de filtrage.
"""
from core import screener

MAX_SCREENS = 20  # nombre de critères sauvegardés simultanément


def add_screen(player, kind, criteria, label=""):
    """Sauvegarde un nouveau critère (kind: "stock" ou "etf") et le retourne.
    Lève ValueError si la limite est atteinte ou le kind invalide."""
    if kind not in ("stock", "etf"):
        raise ValueError(f"kind invalide : {kind}")
    if len(player.saved_screens) >= MAX_SCREENS:
        raise ValueError("limite de critères sauvegardés atteinte")
    entry = {
        "id": player.next_screen_id,
        "kind": kind,
        "label": label or f"{kind}#{player.next_screen_id}",
        "criteria": dict(criteria),
    }
    player.next_screen_id += 1
    player.saved_screens.append(entry)
    return entry


def remove_screen(player, screen_id):
    before = len(player.saved_screens)
    player.saved_screens[:] = [s for s in player.saved_screens if s["id"] != screen_id]
    return len(player.saved_screens) < before


def list_screens(player):
    return list(player.saved_screens)


def run_screen(market, screen, limit=20):
    """Exécute un critère sauvegardé contre le marché courant. Retourne la
    liste de résultats (dicts `metrics()`/`etfs.quote()`)."""
    if screen["kind"] == "etf":
        return screener.screen_etfs(market, limit=limit, **screen["criteria"])
    return screener.screen_stocks(market, limit=limit, **screen["criteria"])


def run_all(player, market, limit=10):
    """Exécute tous les critères sauvegardés et retourne une liste de
    `(screen, résultats)`, dans l'ordre de sauvegarde."""
    return [(s, run_screen(market, s, limit=limit)) for s in player.saved_screens]


ALERT_LIMIT = 5  # nb max de nouveaux résultats remontés par alerte/critère


def check_alerts(player, market):
    """Évalue chaque critère sauvegardé contre le marché courant et notifie
    (inbox) les résultats NOUVEAUX depuis la dernière vérification — la liste
    des clés déjà vues est mémorisée sur le critère (`_seen`) pour qu'un même
    titre ne déclenche qu'une seule alerte. Retourne la liste des alertes
    poussées ce tour (pour tests), [] si rien de nouveau."""
    from core import inbox
    pushed = []
    for screen in player.saved_screens:
        seen = screen.setdefault("_seen", [])
        key_field = "ticker" if screen["kind"] == "stock" else "id"
        results = run_screen(market, screen, limit=ALERT_LIMIT)
        new = [r for r in results if r.get(key_field) not in seen]
        if not new:
            continue
        seen.extend(r.get(key_field) for r in new)
        names = ", ".join(f"{r.get('name', '?')} ({r.get(key_field, '?')})" for r in new)
        msg = inbox.push(
            player, "research", "Veille marché",
            f"Nouveau résultat : {screen['label']}",
            f"Votre critère sauvegardé « {screen['label']} » trouve {len(new)} "
            f"nouvelle(s) correspondance(s) : {names}.")
        pushed.append({"screen": screen, "new": new, "message": msg})
    return pushed
