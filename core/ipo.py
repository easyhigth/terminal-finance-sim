"""
ipo.py — Desk d'IPO : introductions en bourse de sociétés privées fictives
(logique pure, sans pygame).

Le joueur reçoit occasionnellement une OFFRE d'IPO (entreprise fictive,
fourchette de prix, taille de l'opération, sursouscription estimée). Il peut
SOUSCRIRE un montant en cash avant la cotation : le cash est débité
immédiatement (comme un dépôt), et l'allocation reçue dépend de la
sursouscription (`demand_multiple`) — plus la demande dépasse l'offre, plus
l'allocation reçue est faible par rapport au montant réservé ; le surplus non
alloué est remboursé tout de suite.

À la cotation (market.step_count >= listing_step), le prix d'ouverture est
déterminé de façon déterministe via un rng seedé par (market.seed, offer id)
— même esprit que `core/crypto.py` (_hash/_path) : aucun aléa non reproductible.
Le résultat peut être un "pop" (forte hausse) ou un "flop" (perte), crédité/
débité au cash, puis la position est retirée.

Structures (PlayerState) :
  ipo_offers : offres en attente de souscription/refus
  ipos       : positions souscrites en attente de cotation (ou cotées non
               encore liquidées par evaluate_listings, transitoirement)
"""
import random
import numpy as np

MIN_GRADE = 4              # Associate et au-delà (cf. unlocks "ipo")
MAX_ACTIVE_OFFERS = 3       # offres simultanées en attente de décision
OFFER_PROB = 0.16           # proba d'une offre par tour (si place dispo)
LISTING_HORIZON = (3, 8)    # pas avant la cotation (min, max)

SECTORS = ["Tech", "Semicon", "Luxe", "Conso", "Finance", "Energie", "Sante",
           "Industrie", "Agro", "Telecom", "Materiaux", "Auto"]

# Préfixes/suffixes fictifs pour générer des noms de sociétés déterministes,
# dans le même esprit déformé que data/companies.py (noms inventés).
_PREFIXES = ["Nova", "Quanta", "Helio", "Veltra", "Brixa", "Sonex", "Aurion",
             "Drexel", "Marlow", "Talyn", "Cordis", "Pylos", "Vantra", "Krynn"]
_SUFFIXES = ["Systems", "Holdings", "Labs", "Dynamics", "Group", "Networks",
             "Biotech", "Robotics", "Capital", "Industries", "Materials", "Energy"]


def _scale(grade):
    return 1.0 + 0.55 * grade


def _company_name(rng):
    return f"{rng.choice(_PREFIXES)} {rng.choice(_SUFFIXES)}"


def _ticker(name, rng):
    letters = "".join(ch for ch in name.upper() if ch.isalpha())
    base = (letters[:3] or "IPO")
    return base + str(rng.randint(10, 99))


def maybe_offer(player, rng=None, market=None):
    """Génère éventuellement une nouvelle offre d'IPO. Retourne l'offre ou None.
    `market` (optionnel) sert à ancrer `listing_step` sur le pas de marché
    courant ; à défaut, l'horizon est relatif à 0 (le wiring appelant pourra
    décaler `listing_step` lui-même si besoin)."""
    rng = rng or random
    if player.grade_index < MIN_GRADE:
        return None
    if len(player.ipo_offers) >= MAX_ACTIVE_OFFERS:
        return None
    if rng.random() > OFFER_PROB:
        return None
    name = _company_name(rng)
    ticker = _ticker(name, rng)
    sector = rng.choice(SECTORS)
    scale = _scale(player.grade_index)
    pmin = round(rng.uniform(8.0, 40.0) * scale ** 0.3, 2)
    pmax = round(pmin * rng.uniform(1.15, 1.45), 2)
    shares_offered = int(round(rng.uniform(2_000_000, 20_000_000) * scale))
    demand_multiple = round(rng.uniform(1.0, 6.0), 2)   # sursouscription estimée
    sentiment = rng.choice(["bullish", "neutral", "bearish"])
    current_step = int(getattr(market, "step_count", 0)) if market is not None else 0
    listing_step = current_step + rng.randint(*LISTING_HORIZON)
    offer = {
        "id": player.next_ipo_id,
        "company_name": name,
        "ticker": ticker,
        "sector": sector,
        "price_min": pmin,
        "price_max": pmax,
        "shares_offered": shares_offered,
        "demand_multiple": demand_multiple,
        "listing_step": listing_step,
        "sentiment": sentiment,
    }
    player.next_ipo_id += 1
    player.ipo_offers.append(offer)
    return offer


def find_offer(player, offer_id):
    for o in player.ipo_offers:
        if o["id"] == offer_id:
            return o
    return None


def subscribe(player, offer_id, amount_cash, market):
    """
    Réserve `amount_cash` sur une offre d'IPO : débite le cash immédiatement.
    L'allocation reçue = amount_cash / demand_multiple (sursouscription ->
    allocation partielle). Le surplus non alloué est remboursé tout de suite.
    Retourne un dict résultat, ou {"ok": False, "reason": ...} en cas d'échec.
    """
    offer = find_offer(player, offer_id)
    if offer is None:
        return {"ok": False, "reason": "offer"}
    if amount_cash <= 0:
        return {"ok": False, "reason": "amount"}
    if amount_cash > player.cash:
        return {"ok": False, "reason": "cash"}
    player.cash -= amount_cash
    allocated_cash = amount_cash / max(1.0, offer["demand_multiple"])
    refund = amount_cash - allocated_cash
    if refund > 0:
        player.cash += refund
    price = offer["price_min"]   # prix d'introduction = bas de fourchette (référentiel)
    shares = allocated_cash / price if price > 0 else 0.0
    listing_step = offer["listing_step"]
    market_step = int(getattr(market, "step_count", 0))
    if listing_step <= market_step:
        listing_step = market_step + 1
    position = {
        "offer_id": offer["id"],
        "ticker": offer["ticker"],
        "company_name": offer["company_name"],
        "sector": offer["sector"],
        "shares": shares,
        "cost_basis": allocated_cash,
        "issue_price": price,
        "listing_step": listing_step,
        "demand_multiple": offer["demand_multiple"],
        "sentiment": offer["sentiment"],
    }
    player.ipos.append(position)
    player.ipo_offers = [o for o in player.ipo_offers if o["id"] != offer_id]
    return {"ok": True, "offer": offer, "allocated_cash": allocated_cash,
            "refund": refund, "shares": shares, "position": position}


def decline(player, offer_id):
    """Retire une offre d'IPO sans y souscrire. Retourne True si retirée."""
    before = len(player.ipo_offers)
    player.ipo_offers = [o for o in player.ipo_offers if o["id"] != offer_id]
    return len(player.ipo_offers) < before


def _hash(key):
    """Hash déterministe d'une chaîne -> entier (même pattern que crypto._hash)."""
    h = 0
    for ch in str(key):
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h


def _listing_seed(market, offer_id):
    seed = int(getattr(market, "seed", 12345)) & 0xFFFFFFFF
    return (seed + _hash(offer_id)) & 0xFFFFFFFF


_SENTIMENT_BIAS = {"bullish": 0.12, "neutral": 0.0, "bearish": -0.12}


def listing_price(position, market):
    """
    Prix de cotation déterministe (pop ou flop) pour une position IPO donnée,
    dérivé d'un rng seedé par (market.seed, offer_id). Toujours le même
    résultat pour une même seed de marché — aucun aléa non reproductible.
    """
    seed = _listing_seed(market, position["offer_id"])
    rng = np.random.RandomState(seed)
    bias = _SENTIMENT_BIAS.get(position.get("sentiment", "neutral"), 0.0)
    # rendement du premier jour de cotation : centré sur le biais de sentiment,
    # avec une dispersion large (les IPO sont volatiles : gros pop ou flop net).
    day1_return = rng.normal(bias, 0.30)
    price = position["issue_price"] * (1.0 + day1_return)
    return max(0.01, price)


def evaluate_listings(player, market):
    """
    Dénoue les positions IPO dont la cotation est due (market.step_count >=
    listing_step) : calcule le prix de cotation, crédite/débite le cash selon
    le prix vs cost_basis, retire la position. Retourne la liste des résultats.
    Les positions non encore cotées sont conservées intactes.
    """
    results = []
    still = []
    step = int(getattr(market, "step_count", 0))
    for pos in player.ipos:
        if step >= pos["listing_step"]:
            price = listing_price(pos, market)
            proceeds = price * pos["shares"]
            pnl = proceeds - pos["cost_basis"]
            player.cash += proceeds
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + pnl
            results.append({
                "position": pos, "listing_price": price, "proceeds": proceeds,
                "pnl": pnl, "pop": pnl >= 0,
            })
        else:
            still.append(pos)
    player.ipos = still
    return results


def holdings(player, market):
    """Détail des positions IPO en attente de cotation (ou pas encore liquidées)."""
    step = int(getattr(market, "step_count", 0))
    out = []
    for pos in player.ipos:
        listed = step >= pos["listing_step"]
        out.append({
            "offer_id": pos["offer_id"],
            "ticker": pos["ticker"],
            "company_name": pos["company_name"],
            "shares": pos["shares"],
            "cost_basis": pos["cost_basis"],
            "issue_price": pos["issue_price"],
            "listing_step": pos["listing_step"],
            "steps_left": max(0, pos["listing_step"] - step),
            "listed": listed,
        })
    return out
