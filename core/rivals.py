"""
rivals.py — Concurrents et classement (logique pure, sans pygame).

Des banquiers rivaux nommés progressent au fil du temps (corrélés au marché).
Ils raflent les deals que le joueur laisse expirer, créant une pression
concurrentielle tangible. Un classement situe le joueur face à eux.

Le « score » d'un acteur est exprimé dans la même unité (monétaire) que la
valeur nette du joueur, pour permettre la comparaison.
"""
import random
from core import config

RIVAL_PROFILES = [
    {"name": "Marcus Vale", "firm": "Vale & Co.", "track": "M&A"},
    {"name": "Lena Ortega", "firm": "Ortega Capital", "track": "Risk"},
    {"name": "Kenji Sato", "firm": "Sato Quant", "track": "Quant"},
    {"name": "Sophia Brandt", "firm": "Brandt AM", "track": "Portfolio"},
    {"name": "Idris Cole", "firm": "Cole Advisory", "track": "Advisory"},
]


def ensure(player, rng=None):
    """Initialise les rivaux si nécessaire (scores proches du capital de départ)."""
    rng = rng or random
    if player.rivals:
        return
    player.rivals = []
    for prof in RIVAL_PROFILES:
        player.rivals.append({
            "name": prof["name"], "firm": prof["firm"], "track": prof["track"],
            "score": round(config.START_CASH * rng.uniform(0.7, 1.7), 2),
            "last": "se positionne sur le marché", "mood": "flat",
        })


def step(player, market, rng=None):
    """Fait évoluer le score des rivaux (dérive + couplage marché + bruit)."""
    rng = rng or random
    ensure(player, rng)
    world = getattr(market, "last_world", 0.0)
    for r in player.rivals:
        # dérive modérée + couplage marché atténué + bruit borné (anti-emballement)
        growth = 0.003 + 0.6 * world + rng.gauss(0.0, 0.018)
        growth = max(-0.12, min(0.12, growth))
        r["score"] = max(1000.0, r["score"] * (1 + growth))
        # humeur d'affichage (n'écrase pas une action marquante du tour)
        if r.get("mood", "flat") == "flat" or "last" not in r:
            r["mood"] = "up" if growth > 0.01 else "down" if growth < -0.01 else "flat"


def player_score(player, market):
    """Score composite du joueur : valeur nette + réputation + prestige."""
    from core import portfolio
    nw = portfolio.net_worth(player, market)
    return nw + player.reputation * 4000 + len(player.titles) * 40000


def leaderboard(player, market):
    """Classement décroissant joueur + rivaux. Retourne [{name, firm, score, is_player}]."""
    ensure(player)
    rows = [{"name": r["name"], "firm": r["firm"], "score": r["score"],
             "is_player": False} for r in player.rivals]
    rows.append({"name": player.name + " (vous)", "firm": player.firm_name or "vous",
                 "score": player_score(player, market), "is_player": True})
    rows.sort(key=lambda x: x["score"], reverse=True)
    for i, row in enumerate(rows):
        row["rank"] = i + 1
    return rows


def player_rank(player, market):
    for row in leaderboard(player, market):
        if row["is_player"]:
            return row["rank"], len(player.rivals) + 1
    return 0, 0


def snipe(player, deal, rng=None):
    """Un rival rafle un deal expiré : son score grimpe. Retourne son nom."""
    rng = rng or random
    ensure(player, rng)
    # de préférence un rival de la même voie que le deal
    same = [r for r in player.rivals if r["track"] == deal.get("kind")]
    rival = rng.choice(same) if same else rng.choice(player.rivals)
    # un deal raflé profite au rival, mais sans le faire exploser (fraction)
    rival["score"] += deal.get("reward_cash", 0) * 0.3
    _set_action(rival, f"rafle « {deal.get('title','?')} »", "up")
    return rival["name"]


# ---------------------------------------------------------------------------
# RIVAUX ACTIFS — ils agissent chaque tour, de façon visible
# ---------------------------------------------------------------------------
ACT_SURGE_PROB = 0.12      # un rival réalise un gros coup (bond de score)
ACT_SNIPE_PROB = 0.18      # un rival rafle un deal du joueur sur le point d'expirer
ACT_POACH_PROB = 0.14      # un rival débauche un mandat en attente
SNIPE_DAYS_THRESHOLD = 8   # un deal devient « vulnérable » sous ce nb de jours


def _set_action(rival, text, mood="flat"):
    rival["last"] = text
    rival["mood"] = mood


def _rival_of_track(player, track, rng):
    same = [r for r in player.rivals if r["track"] == track]
    return rng.choice(same) if same else rng.choice(player.rivals)


def nemesis(player, market):
    """Rival immédiatement au-dessus du joueur au classement (ou None si 1er)."""
    board = leaderboard(player, market)
    for i, row in enumerate(board):
        if row["is_player"]:
            return board[i - 1] if i > 0 else None
    return None


def recent_activity(player, limit=8):
    """Retourne les dernières entrées du journal de carrière qui concernent un
    rival nommé (percées, sniping, débauchage de mandats…), les plus récentes
    en premier. Dérivé de `player.journal`, déjà alimenté par `act()`/`snipe()`
    via `career.log()` — aucune donnée supplémentaire à persister."""
    names = {r["name"] for r in player.rivals}
    if not names:
        return []
    out = []
    for entry in reversed(player.journal):
        if any(name in entry.get("text", "") for name in names):
            out.append(entry)
            if len(out) >= limit:
                break
    return out


def act(player, market, rng=None):
    """Actions VISIBLES des rivaux ce tour. Modifie l'état (retire deals/mandats
    raflés, fait grimper les scores) et retourne une liste d'événements :
    {type, text, rival, kind, deal?/title?}. Le terminal en tire inbox/news/toasts.

    Réactivité au marché : en régime « Volatil » ou « Récession », les rivaux
    sont plus agressifs (percées et sniping plus fréquents, ~1.5-2x la
    probabilité de base) ; un depeg de stablecoin actif augmente légèrement
    leur propension au débauchage de mandats. En « Expansion »/« Calme », le
    comportement de base est inchangé."""
    rng = rng or random
    ensure(player, rng)
    events = []
    pscore = player_score(player, market)

    regime = getattr(market, "regime", None)
    stressed = regime in ("Volatil", "Récession")
    surge_prob = ACT_SURGE_PROB * 1.8 if stressed else ACT_SURGE_PROB
    snipe_prob = ACT_SNIPE_PROB * 1.5 if stressed else ACT_SNIPE_PROB

    from core import crypto
    depegged = bool(crypto.active_depegs(market))
    poach_prob = ACT_POACH_PROB * 1.3 if depegged else ACT_POACH_PROB

    # 1) PERCÉE : un rival réalise un gros coup -> bond de score (peut dépasser le joueur)
    if rng.random() < surge_prob:
        r = rng.choice(player.rivals)
        before = r["score"]
        r["score"] = before * (1.0 + rng.uniform(0.10, 0.28))
        passed = before <= pscore < r["score"]
        _set_action(r, "conclut une opération majeure", "up")
        txt = f"{r['name']} ({r['firm']}) conclut une opération de premier plan"
        events.append({"type": "surge", "rival": r["name"], "kind": "bad" if passed else "info",
                       "text": txt + (" et vous double au classement." if passed else ".")})

    # 2) SNIPING d'un deal du joueur sur le point d'expirer (pression : agir vite)
    if player.deals and rng.random() < snipe_prob:
        vulnerable = [d for d in player.deals if d["days_left"] <= SNIPE_DAYS_THRESHOLD]
        if vulnerable:
            d = rng.choice(vulnerable)
            r = _rival_of_track(player, d.get("kind"), rng)
            player.deals = [x for x in player.deals if x["id"] != d["id"]]
            r["score"] += d.get("reward_cash", 0) * 0.3
            player.adjust_reputation(-2)
            _set_action(r, f"vous coiffe sur « {d['title']} »", "up")
            events.append({"type": "snipe", "rival": r["name"], "kind": "bad",
                           "deal": d, "title": d["title"],
                           "text": f"{r['name']} vous coiffe au poteau sur « {d['title']} » "
                                   f"(−2 réputation)."})

    # 3) DÉBAUCHAGE d'un mandat en attente d'acceptation
    if getattr(player, "mandate_offers", None) and rng.random() < poach_prob:
        o = rng.choice(player.mandate_offers)
        player.mandate_offers = [x for x in player.mandate_offers if x.get("id") != o.get("id")]
        r = rng.choice(player.rivals)
        r["score"] += o.get("capital", 0) * 0.02
        client = o.get("client", "un client")
        _set_action(r, f"décroche le mandat {client}", "up")
        events.append({"type": "poach", "rival": r["name"], "kind": "bad", "client": client,
                       "text": f"{r['name']} décroche le mandat de {client} que vous étudiiez."})

    return events
