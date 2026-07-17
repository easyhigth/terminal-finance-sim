"""
challenge_share.py — Partage SANS SERVEUR d'un score de « Défi du jour »
(core/difficulty.py::daily_seed) entre joueurs.

Encode un résumé de run (cf. core/hall_of_fame.py::make_entry) en un code
texte compact ("FSC1:...") que le joueur peut copier/coller (Discord, SMS,
n'importe quel canal texte) et qu'un AUTRE joueur colle dans son propre jeu
pour l'ajouter à SON classement local du défi du jour
(core/hall_of_fame.py::import_friend_code) — aucune inscription, aucun
serveur, juste un format texte partagé. Logique pure, testable seule.

Le code embarque un CHECKSUM (pas une signature cryptographique — inutile en
jeu solo/social, l'enjeu est de détecter une faute de frappe ou un
copier-coller tronqué, pas d'empêcher la triche délibérée) : un joueur mal
intentionné pourrait toujours fabriquer un faux score à la main, mais
l'enjeu — un classement LOCAL entre amis, purement social — ne justifie pas
davantage.
"""
import base64
import json
import zlib

_PREFIX = "FSC1:"
# champs utiles à l'affichage d'un classement (pas l'id local ni la date
# générale d'enregistrement, cf. hall_of_fame.make_entry).
# "curve" : courbe de patrimoine compressée (runs fantômes, cf. core/ghost.py)
# — absente des VIEUX codes (décodée à None, tolérée partout).
_FIELDS = ("name", "grade", "track", "continent", "quarters", "days",
           "best_nw", "score", "hardcore", "daily_date", "curve")


def encode_entry(entry):
    """Encode une entrée de panthéon en code texte partageable."""
    payload = {k: entry.get(k) for k in _FIELDS}
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    checksum = zlib.crc32(raw) & 0xFFFFFFFF
    blob = raw + b"|" + str(checksum).encode("ascii")
    return _PREFIX + base64.urlsafe_b64encode(blob).decode("ascii")


def decode_entry(code):
    """Décode un code (cf. encode_entry). Retourne le dict, ou None si le
    code est vide/mal formé/corrompu/tronqué — ne lève jamais."""
    try:
        code = code.strip()
        if not code.startswith(_PREFIX):
            return None
        blob = base64.urlsafe_b64decode(code[len(_PREFIX):].encode("ascii"))
        raw, sep, checksum_txt = blob.rpartition(b"|")
        if not sep or not raw:
            return None
        if int(checksum_txt) != (zlib.crc32(raw) & 0xFFFFFFFF):
            return None
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or not payload.get("daily_date") or not payload.get("name"):
            return None
        return {k: payload.get(k) for k in _FIELDS}
    except Exception:
        return None
