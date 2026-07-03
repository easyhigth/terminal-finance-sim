"""
fuzzy.py — Correspondance approximative (fuzzy) pour les recherches texte du
jeu : palette de navigation (Ctrl+K, core/scene_manager.py) et recherche du
menu Démarrer du bureau (scenes/scene_desktop_menus.py). Logique pure, sans
pygame.

`score(query, text)` retourne None si `query` n'est pas une sous-séquence
(dans l'ordre, insensible à la casse/accents) de `text`, sinon un score
positif — plus haut = meilleure correspondance. Une requête vide correspond
toujours (score neutre), pour que la liste non filtrée reste affichée.
"""

# Bonus de score : préfixe exact, début de mot, caractères contigus.
_PREFIX_BONUS = 100
_WORD_START_BONUS = 40
_CONSECUTIVE_BONUS = 15
_BASE_MATCH = 1

# Écart maximal toléré (en caractères de `text`) entre deux lettres consécutives
# de `query` : sans ce plafond, une requête courte finit par matcher n'importe
# quel libellé long sans rapport (sous-séquence trop diffuse pour être utile).
_MAX_GAP = 5


def score(query, text):
    """None si `query` n'est pas une sous-séquence SUFFISAMMENT COMPACTE de
    `text` (chaque lettre de `query` doit apparaître dans l'ordre, sans trou
    de plus de `_MAX_GAP` caractères) ; sinon un score, plus haut = meilleur.
    Les espaces de `query` sont ignorés (donc "qq" après "qq " continue de
    matcher)."""
    q = query.strip().lower()
    t = text.lower()
    if not q:
        return 0
    ti = 0
    total = 0
    prev_matched_at = -2
    for qc in q:
        if qc == " ":
            continue
        idx = t.find(qc, ti)
        if idx == -1:
            return None
        if prev_matched_at >= 0 and idx - prev_matched_at - 1 > _MAX_GAP:
            return None
        total += _BASE_MATCH
        if idx == 0 or (idx > 0 and t[idx - 1] in (" ", "-", "_", "/", "(")):
            total += _WORD_START_BONUS
        if idx == prev_matched_at + 1:
            total += _CONSECUTIVE_BONUS
        prev_matched_at = idx
        ti = idx + 1
    if t.startswith(q):
        total += _PREFIX_BONUS
    return total


def _levenshtein(a, b):
    """Distance d'édition classique (insertion/suppression/substitution = 1)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[-1]


def suggest(token, candidates, max_distance=2):
    """Renvoie le candidat le plus proche de `token` (typo probable), ou None
    si aucun n'est à distance d'édition <= max_distance. Utilisé pour
    proposer un « vouliez-vous dire... ? » sur une commande inconnue."""
    token = token.upper()
    best, best_dist = None, max_distance + 1
    for c in candidates:
        d = _levenshtein(token, c.upper())
        if d < best_dist:
            best, best_dist = c, d
    return best if best_dist <= max_distance else None


def filter_sorted(query, items, key):
    """Filtre `items` (itérable quelconque) aux éléments dont `key(item)`
    matche `query`, triés par score décroissant (ordre d'origine conservé en
    cas d'égalité, via un index stable)."""
    scored = []
    for i, item in enumerate(items):
        s = score(query, key(item))
        if s is not None:
            scored.append((s, i, item))
    scored.sort(key=lambda triple: (-triple[0], triple[1]))
    return [item for _, _, item in scored]
