"""
trs.py — Total Return Swaps sur les actions du roster (logique pure).

Le TRS transfère le RENDEMENT TOTAL d'un actif de référence (dividende +
appréciation du prix) d'une partie à l'autre, contre une jambe de financement
flottante (taux directeur + spread). Le receiver obtient l'exposition
économique à l'actif SANS en détenir la propriété légale — c'est l'outil
canonical de levier et de short synthétique :

- **RECEIVER** (long synthétique à levier) : encaisse le rendement total du
  sous-jacent (dividende + Δ prix réglé au dénouement via le MTM) et paie la
  jambe de financement (taux directeur + spread). Gain si l'actif monte plus
  vite que le coût de financement.
- **PAYER** (short synthétique) : symétrique — encaisse le financement et
  paie le rendement total. Gain si l'actif baisse.

Le financement se calibre sur les VRAIS systèmes du jeu, jamais des maquettes :
  - taux de référence = `fx_carry.base_rate(market)` (taux directeur macro) ;
  - spread de financement = marge du teneur + spread théorique de Merton
    (`credit_risk.merton_credit`) — un nom risqué se finance plus cher, comme
    un vrai repo où le collatéral détermine le haircut.

Contrairement au CDS (`core/cds.py`) dont le MTM ne bouge qu'avec la PEUR du
défaut (le spread), le TRS a un **MTM vivant** à chaque pas : il suit le prix
comme une position actionnée — c'est toute la différence entre assurer un
défaut (CDS) et détenir l'économie de l'actif (TRS).

- **MTM** (valeur de sortie) = notionnel × (prix/entrée − 1) côté receiver,
  amputé du financement couru ; opposé côté payer.
- **Flux courus** (`accrue`, chaque pas) : leg de financement + dividende du
  sous-jacent. Le Δ prix n'est PAS réglé en cash chaque pas (on le règle au
  dénouement via le MTM) — sinon double-comptage avec la valeur de marché.
- **Évènement de crédit** (action < TRIGGER_FRAC du niveau d'entrée, même
  convention que le CDS) : le receiver encaisse la perte comme un détenteur
  réel (−(1−RECOVERY)×notionnel), le payer réalise le gain symétrique.
- **Échéance** : règle le MTM en cash et dénoue.
"""
from core import credit_risk as CR
from core import fx_carry as FXC

RECOVERY = 0.40                 # taux de recouvrement conventionnel (cf. cds.py)
TRIGGER_FRAC = 0.25             # action < 25 % du niveau d'entrée = évènement
STEPS_PER_YEAR = 52             # convention crédit (comme cds/convertibles)
MARKET_SPREAD_BPS = 15.0        # marge du teneur de marché sur le théorique
TENORS = [1.0, 3.0, 5.0]
SIDES = ("receiver", "payer")


def quote(market, ticker, years):
    """Cote d'un TRS sur `ticker` : taux de référence + spread de financement
    (marge + PD de Merton). None si la société n'est pas analysable.
    {ref_rate, funding_bps, pd, years}."""
    f = CR.merton_credit(market, ticker, horizon=max(1.0, years))
    if f is None or f["debt"] <= 0:
        return None
    ref = FXC.base_rate(market)
    return {"ticker": ticker, "ref_rate": ref,
            "funding_bps": f["spread_bps"] + MARKET_SPREAD_BPS,
            "pd": f["pd"], "years": years}


def open_trs(player, market, ticker, notional, years, side):
    """Ouvre un TRS (aucun cash à l'entrée — synthétique, comme un vrai swap).
    `side` ∈ {"receiver","payer"}. {ok, position} ou {ok: False, reason}."""
    if notional <= 0 or years not in TENORS or side not in SIDES:
        return {"ok": False, "reason": "params"}
    q = quote(market, ticker, years)
    if q is None:
        return {"ok": False, "reason": "ticker"}
    price = market.price_of(ticker)
    if price is None:
        return {"ok": False, "reason": "ticker"}
    player.trs_positions = getattr(player, "trs_positions", [])
    pos = {"id": max((c["id"] for c in player.trs_positions), default=0) + 1,
           "ticker": ticker, "side": side, "notional": float(notional),
           "entry_price": price, "funding_bps": q["funding_bps"],
           "ref_rate": q["ref_rate"], "accrued_financing": 0.0,
           "years": years,
           "maturity_step": market.step_count + int(round(years * STEPS_PER_YEAR))}
    player.trs_positions.append(pos)
    return {"ok": True, "position": pos, "quote": q}


def _price_return(market, pos):
    """Rendement prix du sous-jacent depuis l'entrée (fraction)."""
    price = market.price_of(pos["ticker"])
    if price is None or pos["entry_price"] <= 0:
        return 0.0
    return price / pos["entry_price"] - 1.0


def mark_to_market(market, pos):
    """Valeur de sortie : performance prix × notionnel, amputée du financement
    couru, côté receiver (opposé côté payer). Dividende non inclus ici — il
    est réglé en cash chaque pas via `accrue`."""
    gross = pos["notional"] * _price_return(market, pos)
    net = gross - pos.get("accrued_financing", 0.0)
    return net if pos["side"] == "receiver" else -net


def accrue(player, market, days):
    """Flux net couru sur les TRS en cours (signé, crédité au cash chaque pas) :
    leg de financement + dividende du sous-jacent. Met à jour
    `accrued_financing` (qui alimente le MTM côté receiver)."""
    total = 0.0
    dt = days / 365.0
    for pos in getattr(player, "trs_positions", []) or []:
        rate = pos["ref_rate"] + pos["funding_bps"] / 10_000.0
        financing = pos["notional"] * rate * dt          # coût du portage
        mt = market.metrics(pos["ticker"])
        div = pos["notional"] * (mt["div_yield"] if mt else 0.0) * dt
        if pos["side"] == "receiver":
            # paie le financement, encaisse le dividende
            pos["accrued_financing"] = pos.get("accrued_financing", 0.0) + financing
            total += div - financing
        else:  # payer : encaisse le financement, paie le dividende
            pos["accrued_financing"] = pos.get("accrued_financing", 0.0) - financing
            total += financing - div
    return total


def evaluate_due(player, market):
    """Dénoue les TRS : ÉVÈNEMENT DE CRÉDIT (action < TRIGGER_FRAC de l'entrée)
    ou échéance (règle le MTM en cash). Renvoie [{ticker, side, kind, payoff}]
    pour notification. `payoff` est le flux net versé au joueur (signé)."""
    results, still = [], []
    for pos in getattr(player, "trs_positions", []) or []:
        price = market.price_of(pos["ticker"])
        triggered = (price is not None
                     and price < TRIGGER_FRAC * pos["entry_price"])
        if triggered:
            loss = (1.0 - RECOVERY) * pos["notional"]
            payoff = -loss if pos["side"] == "receiver" else loss
        elif market.step_count >= pos["maturity_step"]:
            payoff = mark_to_market(market, pos)
        else:
            still.append(pos)
            continue
        player.cash += payoff
        player.realized_pnl = getattr(player, "realized_pnl", 0.0) + payoff
        results.append({"ticker": pos["ticker"], "side": pos["side"],
                        "kind": "credit_event" if triggered else "expiry",
                        "payoff": payoff})
    player.trs_positions = still
    return results


def close(player, market, pos_id):
    """Sortie anticipée au mark-to-market. {ok, mtm} ou {ok: False}."""
    for pos in getattr(player, "trs_positions", []) or []:
        if pos["id"] == pos_id:
            mtm = mark_to_market(market, pos)
            player.cash += mtm
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + mtm
            player.trs_positions.remove(pos)
            return {"ok": True, "mtm": mtm}
    return {"ok": False, "reason": "notfound"}


def holdings(player, market):
    """TRS en cours, avec MTM et prix courant."""
    out = []
    for pos in getattr(player, "trs_positions", []) or []:
        steps_left = max(0, pos["maturity_step"] - market.step_count)
        price = market.price_of(pos["ticker"])
        out.append({**pos, "mtm": mark_to_market(market, pos),
                    "price": price, "steps_left": steps_left})
    return out


def holdings_value(player, market):
    """MTM total des TRS (peut être négatif)."""
    return sum(mark_to_market(market, pos)
               for pos in getattr(player, "trs_positions", []) or [])