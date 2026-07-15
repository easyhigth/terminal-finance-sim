"""
merger_arb.py — Arbitrage de fusion / trading événementiel (logique pure).

Un nouveau MODE de trading, distinct du directionnel : quand une OPA est
annoncée sur une société cotée du roster, l'acquéreur propose un prix (l'OFFRE)
au-dessus du cours — mais l'action ne saute pas exactement à l'offre : il reste
un ÉCART (le « deal spread ») qui rémunère le risque que l'opération CAPOTE
(régulateur, financement, vote des actionnaires…). L'arbitragiste achète la
cible sous l'offre et capture l'écart SI le deal se conclut ; il perd gros s'il
casse (le cours retombe à son niveau pré-annonce).

Design (calqué sur les instruments auto-contenus du jeu — cds/irs/repo/
convertibles) :
  - Les OPRATIONS sont DÉTERMINISTES : dérivées de `(market.seed, index)` par un
    rng DÉDIÉ qui ne consomme JAMAIS le rng du marché (pas de dérive des saves).
    Une opération est « active » (tradable) entre son pas d'annonce et son pas de
    résolution.
  - L'ISSUE (conclusion vs rupture) est elle aussi un pur produit de
    `(market.seed, index)` — la même pour tout le monde, décidée d'avance mais
    CACHÉE au joueur (il ne voit que la probabilité de rupture). Pas de rng tiré
    à la résolution → reconstructible.
  - La POSITION du joueur (`player.arb_positions`) fige à l'entrée tout ce dont
    la résolution a besoin (offre, cours non perturbé, pas de résolution, issue)
    → robuste au save/load, indépendant du recalcul d'affichage des opérations
    non prises.
  - `evaluate_due` est câblé dans `GameState.advance_step` : à la résolution,
    conclusion → paiement au prix d'offre ; rupture → paiement au cours pré-deal
    déprécié (perte). `holdings_value` marque les positions ouvertes au marché
    (l'écart se resserre à l'approche de la résolution → portage positif si ça
    conclut).
"""
import random

CADENCE = 16                 # ~1 opération annoncée tous les 16 pas de marché
HORIZON_CHOICES = [6, 8, 10, 12]   # pas avant résolution (durée d'une OPA)
PREMIUM_RANGE = (0.20, 0.45)       # prime de l'offre sur le cours pré-annonce
BREAK_PROB_RANGE = (0.08, 0.30)    # proba que l'opération capote
BREAK_RECOVERY = 0.97              # à la rupture, retour ≈ cours pré-deal (léger sur-ajustement à la baisse)
_LOOKBACK_I = 3                    # fenêtre d'indices scannée autour du pas courant
_SALT = 0x5A17E

_ACQUIRERS = [
    "Helvation Capital", "Brookmere Partners", "Sovra Industries", "Kessler Group",
    "Anvil Private Equity", "Northmoor Holdings", "Cendrix Global", "Valmereau SA",
    "Irongate Consortium", "Drayton & Co.", "Meridiel Partners", "Oakvane Capital",
]


def _deal_rng(seed, i):
    return random.Random((int(seed) & 0xFFFFFFFF) ^ (_SALT + (i * 2654435761 & 0xFFFFFFFF)))


def _deal_params(seed, i, n_companies):
    """Paramètres STABLES d'une opération d'index i (indépendants des cours
    courants — le choix de cible se fait sur l'INDICE roster, statique, pas sur
    la capitalisation qui bouge dans le temps)."""
    r = _deal_rng(seed, i)
    announce = i * CADENCE + r.randint(-5, 5)
    target_idx = r.randrange(n_companies)
    acquirer = r.choice(_ACQUIRERS)
    premium = round(r.uniform(*PREMIUM_RANGE), 3)
    horizon = r.choice(HORIZON_CHOICES)
    break_prob = round(r.uniform(*BREAK_PROB_RANGE), 3)
    # l'issue est décidée d'avance (même graine) mais cachée
    will_close = r.random() >= break_prob
    return {"index": i, "announce_step": max(0, announce), "target_idx": target_idx,
            "acquirer": acquirer, "premium": premium, "horizon": horizon,
            "break_prob": break_prob, "will_close": will_close}


def deal_outcome(seed, index, n_companies):
    """Issue déterministe (True = conclusion) d'une opération — pure, testable."""
    return _deal_params(seed, index, n_companies)["will_close"]


def _situation_from_params(params, market):
    step = market.step_count
    announce = params["announce_step"]
    resolve = announce + params["horizon"]
    if not (announce <= step <= resolve):
        return None
    ticker = market.companies[params["target_idx"]]["ticker"]
    price = market.price_of(ticker)
    if price is None or price <= 0:
        return None
    offer = price * (1 + params["premium"])
    # écart de deal : maximal à l'annonce, se resserre linéairement vers ~0 à la
    # résolution ; borné par la prime (au pire on retombe au cours pré-deal).
    frac_left = (resolve - step) / max(1, params["horizon"])
    base_spread = params["break_prob"] * params["premium"]
    spread = base_spread * frac_left
    implied = offer * (1 - spread)
    return {
        "id": params["index"], "ticker": ticker, "name": market.companies[params["target_idx"]]["name"],
        "acquirer": params["acquirer"], "premium": params["premium"],
        "offer": offer, "undisturbed": price, "implied": implied, "spread": spread,
        "announce_step": announce, "resolve_step": resolve, "steps_left": resolve - step,
        "break_prob": params["break_prob"],
    }


def active_situations(market):
    """Opérations d'OPA actuellement tradables (annoncées, non encore résolues),
    triées par échéance la plus proche."""
    step = market.step_count
    n = market.n
    out = []
    base_i = step // CADENCE
    for i in range(max(0, base_i - _LOOKBACK_I), base_i + 2):
        sit = _situation_from_params(_deal_params(market.seed, i, n), market)
        if sit is not None:
            out.append(sit)
    out.sort(key=lambda s: (s["steps_left"], s["id"]))
    return out


def get_situation(market, sid):
    return next((s for s in active_situations(market) if s["id"] == sid), None)


# --------------------------------------------------------------------- position
def enter(player, market, sid, qty):
    """Prend une position d'arbitrage sur l'opération `sid` : achète `qty`
    « parts » au cours implicite courant. Débite le cash. {ok, position} ou
    {ok: False, reason}."""
    if qty <= 0:
        return {"ok": False, "reason": "qty"}
    sit = get_situation(market, sid)
    if sit is None:
        return {"ok": False, "reason": "inconnue"}
    cost = sit["implied"] * qty
    if player.cash < cost:
        return {"ok": False, "reason": "cash"}
    player.arb_positions = getattr(player, "arb_positions", [])
    if any(p["deal_id"] == sid for p in player.arb_positions):
        return {"ok": False, "reason": "deja"}
    player.cash -= cost
    params = _deal_params(market.seed, sid, market.n)
    pos = {
        "id": player.next_arb_id, "deal_id": sid, "ticker": sit["ticker"],
        "name": sit["name"], "acquirer": sit["acquirer"], "qty": float(qty),
        "entry_price": sit["implied"], "offer": sit["offer"],
        "undisturbed": sit["undisturbed"], "resolve_step": sit["resolve_step"],
        "will_close": params["will_close"], "break_prob": sit["break_prob"],
        "entry_step": market.step_count,
    }
    player.arb_positions.append(pos)
    player.next_arb_id += 1
    return {"ok": True, "position": pos, "cost": cost}


def _mtm_price(pos, market):
    """Cours implicite courant d'une position ouverte : l'écart résiduel se
    resserre linéairement de l'entrée vers 0 à la résolution."""
    resolve = pos["resolve_step"]
    total = max(1, resolve - pos["entry_step"])
    left = max(0, resolve - market.step_count)
    frac_left = left / total
    # écart d'entrée reconstruit depuis prix d'entrée & offre
    entry_spread = 1.0 - (pos["entry_price"] / pos["offer"]) if pos["offer"] else 0.0
    spread = entry_spread * frac_left
    return pos["offer"] * (1 - spread)


def mark_to_market(pos, market):
    price = _mtm_price(pos, market)
    value = price * pos["qty"]
    pnl = value - pos["entry_price"] * pos["qty"]
    return {"price": price, "value": value, "pnl": pnl}


def holdings_value(player, market):
    return sum(mark_to_market(p, market)["value"]
               for p in (getattr(player, "arb_positions", None) or []))


def positions(player, market):
    out = []
    for p in (getattr(player, "arb_positions", None) or []):
        m = mark_to_market(p, market)
        out.append({**p, **m, "steps_left": max(0, p["resolve_step"] - market.step_count)})
    return out


def exit_position(player, market, pos_id):
    """Sortie anticipée : revend la position au marché (MTM courant)."""
    positions_list = getattr(player, "arb_positions", None) or []
    pos = next((p for p in positions_list if p["id"] == pos_id), None)
    if pos is None:
        return {"ok": False, "reason": "inconnue"}
    m = mark_to_market(pos, market)
    player.cash += m["value"]
    player.arb_positions = [p for p in positions_list if p["id"] != pos_id]
    return {"ok": True, "proceeds": m["value"], "pnl": m["pnl"]}


def evaluate_due(player, market):
    """Résout les positions arrivées à échéance (advance_step). Conclusion →
    paiement au prix d'offre ; rupture → paiement au cours pré-deal déprécié.
    Retourne la liste des résolutions (pour notification)."""
    positions_list = getattr(player, "arb_positions", None) or []
    if not positions_list:
        return []
    results = []
    still = []
    for pos in positions_list:
        if market.step_count < pos["resolve_step"]:
            still.append(pos)
            continue
        if pos["will_close"]:
            payoff_price = pos["offer"]
        else:
            payoff_price = pos["undisturbed"] * BREAK_RECOVERY
        proceeds = payoff_price * pos["qty"]
        cost = pos["entry_price"] * pos["qty"]
        player.cash += proceeds
        results.append({
            "ticker": pos["ticker"], "name": pos["name"], "acquirer": pos["acquirer"],
            "closed": pos["will_close"], "proceeds": proceeds, "pnl": proceeds - cost,
            "qty": pos["qty"],
        })
    player.arb_positions = still
    return results
