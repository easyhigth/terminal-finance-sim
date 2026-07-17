"""
question_log.py — Registre des questions DÉJÀ VUES (logique pure, sans pygame).

Règle de jeu : on ne repose JAMAIS une question déjà rencontrée.
  - MISSIONS (révision — banque data/question_bank.py) : on évite d'abord les
    questions déjà vues ; on n'y RETOMBE que si la banque du grade est épuisée
    (un peu de répétition tolérée en révision, pour garder du volume).
  - EXAMENS (core/exam.py) : on n'y met JAMAIS une question déjà vue — ni en
    mission (les examens injectent des QCM de la MÊME banque via
    `_concept_from_bank`), ni dans un examen précédent. Vraiment jamais.

Identité d'une question (chaîne stable, comparable ENTRE les deux pools) :
  - banque   : "b:" + id            (indépendant de la langue — l'id ne bouge pas)
  - générée  : "g:" + prompt normalisé
Un item de banque converti (mission/examen) ne garde que son texte après passage
par `_mcq` : il conserve donc son id d'origine dans `src_id` pour qu'on retrouve
l'identité "b:" même une fois converti (sinon un même QCM aurait deux identités,
"b:" côté banque et "g:" côté item converti, et le dédoublonnage échouerait).

Le registre vit dans `player.seen_questions` (liste ordonnée d'identités,
JSON-sérialisable, plafonnée FIFO à MAX pour borner la sauvegarde).
"""
import unicodedata

MAX = 6000  # au-delà, on oublie les plus anciennes (partie exceptionnellement longue)


def _norm(text):
    """Texte -> clé stable : sans accents, minuscules, alphanumérique compacté."""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return " ".join("".join(c if c.isalnum() else " " for c in s).split())


def identity(item):
    """Identité stable d'un item de question, ou None si non identifiable.
    Priorité à l'id de banque (langue-indépendant) sur le texte normalisé."""
    if not isinstance(item, dict):
        return None
    sid = item.get("src_id")
    if sid:
        return "b:" + str(sid)
    if "id" in item and "q" in item:           # dict BRUT de la banque (avant conversion)
        return "b:" + str(item["id"])
    prompt = item.get("prompt") or item.get("q")
    if prompt:
        return "g:" + _norm(prompt)
    return None


def seen_set(player):
    """Ensemble des identités déjà posées à ce joueur (missions + examens)."""
    return set(getattr(player, "seen_questions", None) or [])


def is_seen(player, item):
    ident = identity(item)
    return ident is not None and ident in seen_set(player)


def mark_seen(player, items):
    """Ajoute les identités des `items` au registre (dédupliqué, ordre préservé,
    plafonné FIFO à MAX). Les items sans identité sont ignorés."""
    log = list(getattr(player, "seen_questions", None) or [])
    known = set(log)
    for it in items or []:
        ident = identity(it)
        if ident and ident not in known:
            log.append(ident)
            known.add(ident)
    if len(log) > MAX:
        log = log[-MAX:]
    player.seen_questions = log
