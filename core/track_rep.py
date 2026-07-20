"""
track_rep.py — Réputation SEGMENTÉE par métier (logique pure, sans pygame).

La réputation globale (`player.reputation`, 0-100) dit à quel point la banque
vous fait confiance. Elle ne dit pas POUR QUOI. `player.track_rep` ({voie:
points}) enregistre, lui, où vous avez bâti votre nom : chaque gain de
réputation crédite votre voie courante (cf. GameState.adjust_reputation).

À quoi ça sert :
  - au-delà d'un seuil dans une voie, vous devenez un SPÉCIALISTE reconnu :
    on vient vous proposer des mandats de VOTRE métier plus souvent
    (cf. core/mandates.maybe_offer, qui lit `offer_mult`) ;
  - l'écran Carrière l'affiche : une identité lisible, partie après partie.

Purement additif : `track_rep` vide (sauvegarde d'avant, voie "General") ->
aucun spécialiste, aucun bonus, comportement identique à l'existant.
"""
from core import config

SPECIALIST_THRESHOLD = 60   # points de réputation-métier pour être « reconnu »
SPECIALIST_OFFER_BONUS = 1.35   # un spécialiste reçoit ~35% d'offres en plus dans sa voie


def get(player, track):
    return int((getattr(player, "track_rep", None) or {}).get(track, 0))


def dominant(player):
    """(voie, points) où la réputation-métier est la plus haute, ou (None, 0)."""
    seg = getattr(player, "track_rep", None) or {}
    if not seg:
        return None, 0
    track = max(seg, key=lambda t: seg[t])
    return track, int(seg[track])


def specialist_track(player):
    """La voie où le joueur est un SPÉCIALISTE reconnu (>= seuil), ou None."""
    track, pts = dominant(player)
    return track if track and pts >= SPECIALIST_THRESHOLD else None


def offer_mult(player):
    """Multiplicateur de fréquence d'offres de mandat : un spécialiste, dont le
    métier correspond à sa voie active, est davantage sollicité."""
    spec = specialist_track(player)
    if spec and spec == getattr(player, "track", "General"):
        return SPECIALIST_OFFER_BONUS
    return 1.0


def label(player):
    """Libellé d'identité pour l'écran Carrière (ou None si voie non choisie)."""
    track, pts = dominant(player)
    if not track:
        return None
    if pts >= SPECIALIST_THRESHOLD:
        return f"Spécialiste {track} (réputation-métier {pts})"
    return f"{track} — réputation-métier {pts}"


def check_new_specialist(player):
    """À appeler après un gain de réputation : si le joueur vient TOUT JUSTE de
    franchir le seuil de spécialiste dans sa voie active, retourne la voie (pour
    un message d'inbox) et pose le drapeau anti-répétition ; sinon None."""
    spec = specialist_track(player)
    if not spec:
        return None
    seen = player.flags.setdefault("specialist_tracks", [])
    if spec in seen:
        return None
    seen.append(spec)
    return spec


# libellé de voie -> nom lisible (identique à config si présent, sinon la clé)
def track_name(track):
    return config.TRACK_LABELS.get(track, track) if hasattr(config, "TRACK_LABELS") else track
