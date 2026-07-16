"""
todo.py — « Que faire maintenant ? » (logique pure, sans pygame).

Agrège en UNE liste priorisée les actions qui attendent le joueur, aujourd'hui
éparpillées entre scènes (dilemme à trancher, revue de performance, stress
test, offres de mandat, deals qui expirent, marge sous tension, messages non
lus). Consommée par le widget « À FAIRE » du bureau (scenes/scene_desktop.py),
qui rend chaque entrée cliquable vers la scène concernée — la boucle de jeu
reste lisible même toutes fenêtres fermées.

Chaque entrée : {"label": str, "kind": "warn"|"info"|"bad", "scene": str}.
La liste est déjà triée par priorité (le plus urgent d'abord) et bornée à
`MAX_ITEMS` — le widget n'a qu'à l'afficher telle quelle.
"""
from core import crashlog

MAX_ITEMS = 4
DEAL_URGENT_DAYS = 5          # un deal à ≤ 5 jours d'échéance devient urgent
MARGIN_WATCH_RATIO = 1.2      # marge « sous surveillance » : equity < 120% du seuil


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


def suggestions(player, market=None):
    """Liste priorisée (urgent → informatif) des actions en attente."""
    items = []
    # 1) décision bloquante : dilemme en attente
    for d in (player.pending_dilemmas or []):
        items.append({"label": _L(f"Décision requise : {d.get('title', '?')}",
                                  f"Decision required: {d.get('title', '?')}"),
                      "kind": "warn", "scene": "dilemma"})
        break   # une seule ligne suffit, la scène montre le reste
    # 2) convocations : revue de performance / stress test réglementaire
    if getattr(player, "pending_review", None):
        items.append({"label": _L("Revue de performance : votre manager vous attend",
                                  "Performance review: your manager is waiting"),
                      "kind": "warn", "scene": "review"})
    if getattr(player, "pending_stresstest", None):
        items.append({"label": _L("Stress test réglementaire à passer",
                                  "Regulatory stress test to take"),
                      "kind": "warn", "scene": "stresstest"})
    # 3) marge sous tension : prévenir AVANT l'appel de marge
    if market is not None and player.portfolio:
        try:
            from core import portfolio_margin as pm
            st = pm.margin_status(player, market)
            if st["gross"] > 0:
                threshold = pm._maint_margin(player) * st["gross"]
                if threshold > 0 and st["equity"] < threshold * MARGIN_WATCH_RATIO:
                    items.append({"label": _L("Marge sous surveillance : réduisez le levier",
                                              "Margin under watch: reduce leverage"),
                                  "kind": "bad", "scene": "book"})
        except Exception:
            crashlog.swallowed("core.todo")  # 4) opportunités datées : offres de mandat, deals proches de l'échéance
    offers = getattr(player, "mandate_offers", None) or []
    if offers:
        items.append({"label": _L(f"{len(offers)} offre(s) de mandat en attente",
                                  f"{len(offers)} pending mandate offer(s)"),
                      "kind": "info", "scene": "mandates"})
    urgent_deals = [d for d in (player.deals or [])
                    if d.get("days_left", 99) <= DEAL_URGENT_DAYS]
    if urgent_deals:
        d = min(urgent_deals, key=lambda x: x.get("days_left", 99))
        items.append({"label": _L(f"Deal « {d.get('title', '?')} » expire dans {d.get('days_left', '?')}j",
                                  f"Deal “{d.get('title', '?')}” expires in {d.get('days_left', '?')}d"),
                      "kind": "warn", "scene": "deals"})
    # 5) informatif : messages non lus
    try:
        from core import inbox
        unread = inbox.unread_count(player)
    except Exception:
        unread = 0
    if unread:
        items.append({"label": _L(f"{unread} message(s) non lu(s)",
                                  f"{unread} unread message(s)"),
                      "kind": "info", "scene": "inbox"})
    return items[:MAX_ITEMS]
