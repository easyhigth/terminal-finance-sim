"""
macrocal.py — Calendrier macro : évènements économiques programmés à
l'avance (décision de banque centrale, inflation, emploi, croissance) sur
lesquels le joueur peut placer un pari directionnel en cash avant la
résolution (logique pure, sans pygame).

C'est un marché de paris AUTONOME : il ne modifie pas le moteur de marché
réel (`core/market.py`), il ne fait que générer/résoudre des paris en cash,
de façon déterministe — même esprit que `core/ipo.py` (offre programmée à
l'avance -> `listing_step`, ici `resolve_step`).

À l'annonce, l'évènement reçoit des probabilités a priori (légèrement
biaisées) pour ses 3 issues possibles ("positif"/"neutre"/"négatif", du
point de vue de la perception marché — convention unique quel que soit le
type d'évènement, pour rester simple). Le joueur peut parier sur une issue ;
le multiplicateur de gain est l'inverse de la probabilité a priori de cette
issue (plafonné). À résolution (market.step_count >= resolve_step), l'issue
réelle est tirée de façon déterministe via un rng seedé par
(market.seed, event_id) — aucun aléa non reproductible : pour un même seed
de marché et un même id d'évènement, la résolution est toujours identique.

Structures (PlayerState) :
  macro_events      : évènements programmés en attente de résolution
  macro_bets        : paris placés en attente de résolution
  next_macro_event_id : compteur d'identifiants d'évènements
  macro_bet_history : historique des derniers paris résolus (UI)
"""
import random

import numpy as np

EVENT_TYPES = [
    "Décision de taux (banque centrale)",
    "Inflation (CPI)",
    "Emploi (NFP)",
    "Croissance (PIB)",
    "Indice PMI (manufacturier/services)",
    "Émission de dette souveraine",
]

OUTCOMES = ["positif", "neutre", "négatif"]

EVENT_HORIZON = (5, 15)      # pas de marché avant résolution (min, max)
MAX_ACTIVE_EVENTS = 3        # évènements programmés simultanément en attente
EVENT_PROB = 0.18            # proba qu'un nouvel évènement soit programmé par tour
MIN_GRADE = 2                # accessible plus tôt que les marchés techniques (options, ipo)
MAX_MULTIPLIER = 4.0         # plafond du multiplicateur de gain
MAX_HISTORY = 20             # taille max de l'historique conservé pour l'UI

_CONSENSUS_LABELS = {
    "Décision de taux (banque centrale)": ["statu quo", "hausse de 25pb", "baisse de 25pb"],
    "Inflation (CPI)": ["en ligne", "léger dépassement", "léger ralentissement"],
    "Emploi (NFP)": ["en ligne", "créations supérieures aux attentes", "créations inférieures aux attentes"],
    "Croissance (PIB)": ["en ligne", "accélération", "ralentissement"],
    "Indice PMI (manufacturier/services)": ["en ligne", "expansion confirmée", "contraction"],
    "Émission de dette souveraine": ["demande conforme", "sur-souscription (forte demande)",
                                      "sous-souscription (demande faible)"],
}

# --- couche EN (affichage). Les valeurs FR restent les clés de logique et sont
# ce qui est sérialisé dans les saves ; on ne localise qu'à l'AFFICHAGE via
# event_type_label()/consensus_label(). ---
_EVENT_TYPE_EN = {
    "Décision de taux (banque centrale)": "Rate decision (central bank)",
    "Inflation (CPI)": "Inflation (CPI)",
    "Emploi (NFP)": "Employment (NFP)",
    "Croissance (PIB)": "Growth (GDP)",
    "Indice PMI (manufacturier/services)": "PMI index (manufacturing/services)",
    "Émission de dette souveraine": "Sovereign debt issuance",
}
_CONSENSUS_EN = {
    "statu quo": "hold", "hausse de 25pb": "25bp hike", "baisse de 25pb": "25bp cut",
    "en ligne": "in line", "léger dépassement": "slight beat", "léger ralentissement": "slight slowdown",
    "créations supérieures aux attentes": "hiring above expectations",
    "créations inférieures aux attentes": "hiring below expectations",
    "accélération": "acceleration", "ralentissement": "slowdown",
    "expansion confirmée": "expansion confirmed", "contraction": "contraction",
    "demande conforme": "demand in line", "sur-souscription (forte demande)": "oversubscribed (strong demand)",
    "sous-souscription (demande faible)": "undersubscribed (weak demand)",
}


def event_type_label(event_type):
    """Libellé localisé d'un type d'évènement macro (clé FR conservée)."""
    from core.i18n import get_lang
    return _EVENT_TYPE_EN.get(event_type, event_type) if get_lang() == "en" else event_type


def consensus_label(consensus):
    """Libellé localisé du consensus (clé FR conservée)."""
    from core.i18n import get_lang
    return _CONSENSUS_EN.get(consensus, consensus) if get_lang() == "en" else consensus


def _consensus(event_type, rng):
    labels = _CONSENSUS_LABELS.get(event_type, ["en ligne"])
    return rng.choice(labels)


def _prior_probabilities(rng):
    """Probabilités a priori des 3 issues, légèrement biaisées aléatoirement,
    sommant à 1.0."""
    base = [0.35, 0.30, 0.35]
    bias = rng.uniform(-0.12, 0.12)
    positif = max(0.05, min(0.85, base[0] + bias))
    negatif = max(0.05, min(0.85, base[2] - bias))
    neutre = max(0.05, 1.0 - positif - negatif)
    total = positif + neutre + negatif
    probs = {
        "positif": positif / total,
        "neutre": neutre / total,
        "négatif": negatif / total,
    }
    return probs


def maybe_schedule(player, rng=None, market=None):
    """Génère éventuellement un nouvel évènement macro programmé. Retourne
    l'évènement ou None. `market` (optionnel) sert à ancrer `resolve_step`
    sur le pas de marché courant."""
    rng = rng or random
    if player.grade_index < MIN_GRADE:
        return None
    if len(player.macro_events) >= MAX_ACTIVE_EVENTS:
        return None
    if rng.random() > EVENT_PROB:
        return None
    event_type = rng.choice(EVENT_TYPES)
    current_step = int(getattr(market, "step_count", 0)) if market is not None else 0
    resolve_step = current_step + rng.randint(*EVENT_HORIZON)
    probs = _prior_probabilities(rng)
    event = {
        "id": player.next_macro_event_id,
        "event_type": event_type,
        "resolve_step": resolve_step,
        "consensus": _consensus(event_type, rng),
        "probabilities": probs,
    }
    player.next_macro_event_id += 1
    player.macro_events.append(event)
    return event


def find_event(player, event_id):
    for e in player.macro_events:
        if e["id"] == event_id:
            return e
    return None


def _multiplier_for(event, outcome):
    p = event["probabilities"].get(outcome, 0.0)
    if p <= 0:
        return MAX_MULTIPLIER
    return round(min(MAX_MULTIPLIER, 1.0 / p), 2)


def place_bet(player, event_id, outcome, stake):
    """Place un pari directionnel sur un évènement macro programmé. Débite
    le cash immédiatement. Retourne un dict résultat, ou
    {"ok": False, "reason": ...} en cas d'échec."""
    event = find_event(player, event_id)
    if event is None:
        return {"ok": False, "reason": "event"}
    if outcome not in OUTCOMES:
        return {"ok": False, "reason": "outcome"}
    if stake is None or stake <= 0:
        return {"ok": False, "reason": "stake"}
    if stake > player.cash:
        return {"ok": False, "reason": "cash"}
    multiplier = _multiplier_for(event, outcome)
    player.cash -= stake
    bet = {
        "event_id": event_id,
        "outcome": outcome,
        "stake": stake,
        "multiplier": multiplier,
    }
    player.macro_bets.append(bet)
    return {"ok": True, "bet": bet, "event": event}


def pending_bets_for(player, event_id):
    """Liste des paris en attente pour un évènement donné (utilitaire UI)."""
    return [b for b in player.macro_bets if b["event_id"] == event_id]


def _hash(key):
    """Hash déterministe d'une chaîne -> entier (même pattern que ipo._hash)."""
    h = 0
    for ch in str(key):
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h


def _event_seed(market, event_id):
    seed = int(getattr(market, "seed", 12345)) & 0xFFFFFFFF
    return (seed + _hash(event_id)) % (2 ** 31)


def actual_outcome(event, market):
    """Issue réelle déterministe pour un évènement donné, dérivée d'un rng
    seedé par (market.seed, event_id), pondérée par les probabilités a
    priori. Toujours le même résultat pour une même seed de marché et un
    même id d'évènement."""
    seed = _event_seed(market, event["id"])
    rng = np.random.RandomState(seed)
    probs = event["probabilities"]
    outcomes = list(probs.keys())
    weights = [probs[o] for o in outcomes]
    total = sum(weights)
    weights = [w / total for w in weights]
    idx = rng.choice(len(outcomes), p=weights)
    return outcomes[idx]


def resolve_due_events(player, market):
    """Règle les évènements macro dont la résolution est due
    (market.step_count >= resolve_step) : tire l'issue réelle, règle tous
    les paris associés (crédite stake*multiplicateur si l'issue parié se
    réalise, sinon le stake — déjà débité — est perdu), retire l'évènement
    et les paris résolus. Les évènements non encore dus sont conservés
    intacts. Retourne la liste des résultats."""
    results = []
    still_events = []
    step = int(getattr(market, "step_count", 0))
    due_ids = set()
    for event in player.macro_events:
        if step >= event["resolve_step"]:
            due_ids.add(event["id"])
        else:
            still_events.append(event)

    still_bets = []
    bets_by_event = {}
    for bet in player.macro_bets:
        if bet["event_id"] in due_ids:
            bets_by_event.setdefault(bet["event_id"], []).append(bet)
        else:
            still_bets.append(bet)

    for event in player.macro_events:
        if event["id"] not in due_ids:
            continue
        outcome = actual_outcome(event, market)
        bets_resolved = []
        for bet in bets_by_event.get(event["id"], []):
            won = bet["outcome"] == outcome
            payout = bet["stake"] * bet["multiplier"] if won else 0.0
            if won:
                player.cash += payout
            entry = {
                "event_id": event["id"],
                "outcome": bet["outcome"],
                "stake": bet["stake"],
                "multiplier": bet["multiplier"],
                "won": won,
                "payout": payout,
            }
            bets_resolved.append(entry)
        result = {
            "event": event,
            "actual_outcome": outcome,
            "bets_resolved": bets_resolved,
        }
        results.append(result)
        history_entry = dict(result)
        player.macro_bet_history.append(history_entry)

    if results:
        player.macro_bet_history = player.macro_bet_history[-MAX_HISTORY:]

    player.macro_events = still_events
    player.macro_bets = still_bets
    return results
