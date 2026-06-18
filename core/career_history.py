"""
career_history.py — Logique pure (sans pygame) pour l'écran d'historique de
carrière consultable à tout moment (scenes/scene_history.py).

Met en forme les entrées de `player.journal` (cf. core/career.py::log, format
{day, quarter, kind, text}) pour affichage en timeline, sans dépendance à
pygame : testable directement en pytest.
"""


def format_timeline(journal, limit=20):
    """Retourne les `limit` entrées les plus récentes de `journal`, triées du
    plus récent au plus ancien, sous forme de tuples (label, détail).

    `label` est un repère temporel court ("J{day}"), `détail` est le texte de
    l'entrée. Les entrées sans 'day' ou 'text' valides sont ignorées.
    """
    if not journal:
        return []
    # tri stable par jour décroissant ; les entrées sans 'day' exploitable
    # sont écartées plutôt que de planter le tri.
    valid = [e for e in journal if isinstance(e, dict) and "text" in e]
    ordered = sorted(valid, key=lambda e: e.get("day", 0), reverse=True)
    out = []
    for e in ordered[:limit]:
        day = e.get("day", 0)
        out.append((f"J{day}", e.get("text", "")))
    return out


def kind_counts(journal):
    """Dénombre les entrées du journal par 'kind' (promo/deal/crisis/...).
    Utile pour un résumé synthétique de la carrière."""
    counts = {}
    for e in journal or []:
        if not isinstance(e, dict):
            continue
        k = e.get("kind", "info")
        counts[k] = counts.get(k, 0) + 1
    return counts
