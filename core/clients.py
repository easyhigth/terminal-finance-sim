"""
clients.py — Carnet de CLIENTS RÉCURRENTS avec mémoire (logique pure).

Avant ce module, chaque mandat sortait un nom au hasard : réussir ou décevoir
n'engageait personne. Ici, un petit carnet de clients NOMMÉS et persistants
(`player.clients`) donne une mémoire à la relation :

  - un mandat RÉUSSI fait monter la CONFIANCE du client : il revient avec un
    capital plus gros (capital_mult croît), et au-delà d'un seuil de
    confiance il vous RÉFÈRE un nouveau client (le carnet grandit par le
    travail bien fait) ;
  - un mandat ÉCHOUÉ entame lourdement la confiance ; deux échecs (ou une
    confiance à zéro) et le client est PERDU DÉFINITIVEMENT — son nom reste
    dans le carnet, grisé, comme un reproche.

Intégration minimale dans core/mandates.py : `attach_client()` remplace le
nom jetable d'une offre par un client du carnet (le plus souvent), et
`record_outcome()` est appelé à la résolution. L'UI est l'app « Carnet
clients » (apps/app_clients.py). Entrée du carnet :
    {"name", "profile", "trust" 0-100, "capital_mult", "done", "failed",
     "lost": bool, "referred_by": str|None, "since_day": int}
"""
import random

from core.i18n import get_lang

BOOK_SEED_SIZE = 3      # clients initiaux à l'ouverture du carnet
BOOK_MAX = 8            # taille max du carnet (référencements compris)
RETURNING_PROB = 0.65   # proba qu'une offre vienne d'un client du carnet
TRUST_START = 50
TRUST_WIN = 12          # confiance gagnée par mandat réussi
TRUST_LOSS = 28         # confiance perdue par mandat échoué
TRUST_REFERRAL = 70     # seuil de confiance déclenchant un référencement
CAPITAL_GROWTH = 1.18   # croissance du capital confié par mandat réussi
CAPITAL_MULT_MAX = 3.0
MAX_FAILURES = 2        # au-delà : client perdu définitivement


def _L(fr, en):
    return en if get_lang() == "en" else fr


def _ensure_field(player):
    if not hasattr(player, "clients") or player.clients is None:
        player.clients = []


def _new_client(name, profile_key, day, referred_by=None):
    return {"name": name, "profile": profile_key, "trust": TRUST_START,
            "capital_mult": 1.0, "done": 0, "failed": 0, "lost": False,
            "referred_by": referred_by, "since_day": day}


def _unused_name(player, rng):
    """Tire un (nom, profil) de CLIENT_PROFILES absent du carnet."""
    from core.mandates import CLIENT_PROFILES
    taken = {c["name"] for c in player.clients}
    pool = [(name, prof["key"]) for prof in CLIENT_PROFILES
            for name in prof["names"] if name not in taken]
    if not pool:
        return None
    return rng.choice(pool)


def ensure_book(player, rng=None):
    """Amorce le carnet à sa première utilisation (3 clients)."""
    _ensure_field(player)
    rng = rng or random
    while len(player.clients) < BOOK_SEED_SIZE:
        pick = _unused_name(player, rng)
        if pick is None:
            break
        player.clients.append(_new_client(pick[0], pick[1], player.day))


def get(player, name):
    _ensure_field(player)
    return next((c for c in player.clients if c["name"] == name), None)


def active_clients(player):
    _ensure_field(player)
    return [c for c in player.clients if not c["lost"]]


def attach_client(player, offer, rng=None):
    """Raccroche une offre de mandat au carnet : le plus souvent (cf.
    RETURNING_PROB), le client est un client CONNU — son profil remplace
    celui tiré au hasard, et sa confiance module le capital confié et la
    commission. Sinon l'offre garde son nom jetable (rencontre ponctuelle).
    Retourne le client du carnet utilisé, ou None."""
    rng = rng or random
    ensure_book(player, rng)
    pool = active_clients(player)
    if not pool or rng.random() > RETURNING_PROB:
        return None
    c = rng.choice(pool)
    offer["client"] = c["name"]
    offer["client_profile"] = c["profile"]
    offer["from_book"] = True
    # la confiance paie : capital confié et commission grossissent avec elle
    scale = c["capital_mult"] * (0.85 + 0.005 * c["trust"])
    offer["capital"] = round(offer["capital"] * scale, -3)
    offer["reward_cash"] = round(offer["reward_cash"] * scale, 2)
    return c


def record_outcome(player, client_name, ok, rng=None):
    """Enregistre l'issue d'un mandat pour `client_name` (s'il est au
    carnet). Retourne une liste d'évènements narratifs à notifier :
    [{"kind": "referral"|"lost"|"trust", ...}]."""
    rng = rng or random
    c = get(player, client_name)
    if c is None or c["lost"]:
        return []
    events = []
    if ok:
        c["done"] += 1
        before = c["trust"]
        c["trust"] = min(100, c["trust"] + TRUST_WIN)
        c["capital_mult"] = min(CAPITAL_MULT_MAX, c["capital_mult"] * CAPITAL_GROWTH)
        # référencement : franchir le seuil de confiance amène un nouveau client
        if (before < TRUST_REFERRAL <= c["trust"]
                and len(player.clients) < BOOK_MAX):
            pick = _unused_name(player, rng)
            if pick is not None:
                newc = _new_client(pick[0], pick[1], player.day, referred_by=c["name"])
                player.clients.append(newc)
                events.append({"kind": "referral", "client": c, "new_client": newc})
        events.append({"kind": "trust", "client": c, "delta": c["trust"] - before})
    else:
        c["failed"] += 1
        c["trust"] = max(0, c["trust"] - TRUST_LOSS)
        if c["failed"] >= MAX_FAILURES or c["trust"] <= 0:
            c["lost"] = True
            events.append({"kind": "lost", "client": c})
        else:
            events.append({"kind": "trust", "client": c, "delta": -TRUST_LOSS})
    return events


def notify_events(player, events):
    """Pousse les évènements narratifs du carnet (référencement, client
    perdu) en notifications + inbox — séparé de record_outcome pour rester
    testable sans effets de bord."""
    from core import inbox as _inbox
    from core import notify_queue as _nq
    for ev in events:
        if ev["kind"] == "referral":
            c, n = ev["client"], ev["new_client"]
            _nq.push(player, _L(f"{c['name']} vous réfère un nouveau client : {n['name']}",
                                f"{c['name']} refers a new client to you: {n['name']}"),
                     "good", action="clients")
            _inbox.push(player, "client", c["name"],
                        _L("Une recommandation", "A referral"),
                        _L(f"Votre travail parle pour vous. J'ai recommandé vos services "
                           f"à {n['name']}, qui cherche un gérant de confiance.",
                           f"Your work speaks for itself. I recommended your services "
                           f"to {n['name']}, who is looking for a trusted manager."))
        elif ev["kind"] == "lost":
            c = ev["client"]
            _nq.push(player, _L(f"Client perdu : {c['name']} ne travaillera plus avec vous.",
                                f"Client lost: {c['name']} will no longer work with you."),
                     "bad", action="clients")
            _inbox.push(player, "client", c["name"],
                        _L("Fin de notre collaboration", "End of our relationship"),
                        _L("Après ces déceptions répétées, je confie mes actifs à une "
                           "autre maison. Ne me recontactez pas.",
                           "After these repeated disappointments, I am moving my assets "
                           "to another house. Do not contact me again."))
