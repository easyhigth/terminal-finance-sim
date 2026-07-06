"""
notify_queue.py — File de notifications différées (logique pure).

Certaines actions de gameplay (advance_step, résolution de mandats, etc.)
n'ont pas accès direct à `app.notify()`. Elles empilent ici un toast ; le
SceneManager consomme la file à chaque frame pour l'afficher via
`app.notify()`.
"""

MAX_PENDING = 20


def push(player, text, kind="info", action=None, action_kwargs=None):
    """Ajoute une notification en attente d'affichage."""
    q = player.flags.setdefault("_pending_toasts", [])
    q.append({"text": text, "kind": kind, "action": action,
              "action_kwargs": action_kwargs or {}})
    if len(q) > MAX_PENDING:
        q.pop(0)


def drain(player):
    """Récupère et vide la file de notifications en attente."""
    q = player.flags.get("_pending_toasts", [])
    if not q:
        return []
    out = list(q)
    q.clear()
    return out
