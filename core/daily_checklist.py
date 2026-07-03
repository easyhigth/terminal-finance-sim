"""
daily_checklist.py — Checklist de routine quotidienne (logique pure).

Une poignée d'actions de base qu'un nouveau joueur ne pense pas forcément à
faire régulièrement (vérifier ses positions, lire l'inbox, regarder les
alertes, consulter le calendrier macro). Coché manuellement par le joueur
(pas une détection automatique comme core/todo.py, qui liste ce qui est
BLOQUANT) — sert de pense-bête, pas de contrainte. L'état coché est remis à
zéro chaque nouveau jour de jeu (`player.day`) ; désactivable une fois
maîtrisée (`player.flags["daily_checklist_enabled"]`, défaut activé).
"""

ITEMS = [
    {"id": "positions", "label_fr": "Vérifier mes positions ouvertes",
     "label_en": "Check my open positions"},
    {"id": "inbox", "label_fr": "Lire les nouveaux messages (Inbox)",
     "label_en": "Read new messages (Inbox)"},
    {"id": "alerts", "label_fr": "Regarder les alertes de prix",
     "label_en": "Check price alerts"},
    {"id": "calendar", "label_fr": "Consulter le calendrier macro",
     "label_en": "Check the macro calendar"},
]


def _L(fr, en, lang):
    return en if lang == "en" else fr


def is_enabled(player):
    return bool(player.flags.get("daily_checklist_enabled", True))


def set_enabled(player, value):
    player.flags["daily_checklist_enabled"] = bool(value)


def _state(player):
    """{"day": int, "done": [item_id, ...]} — remis à zéro si `player.day` a
    changé depuis la dernière consultation (nouvelle journée, nouvelle
    routine)."""
    st = player.flags.get("daily_checklist_state")
    if not st or st.get("day") != player.day:
        st = {"day": player.day, "done": []}
        player.flags["daily_checklist_state"] = st
    return st


def items_for_today(player, lang="fr"):
    """[{"id", "label", "done"}, ...] pour le jour de jeu courant."""
    st = _state(player)
    done = set(st["done"])
    return [{"id": it["id"], "label": _L(it["label_fr"], it["label_en"], lang),
             "done": it["id"] in done}
            for it in ITEMS]


def toggle(player, item_id):
    st = _state(player)
    done = set(st["done"])
    if item_id in done:
        done.discard(item_id)
    else:
        done.add(item_id)
    st["done"] = list(done)


def all_done_today(player):
    st = _state(player)
    return len(st["done"]) >= len(ITEMS)
