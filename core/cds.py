"""
cds.py — Credit Default Swaps sur les sociétés du roster (logique pure).

Le prolongement direct du Desk Crédit : la PD structurelle de Merton
(core/credit_risk.py) donne le SPREAD THÉORIQUE — le CDS le rend tradable :

- **Acheter de la protection** : on paie la prime (spread fixé à l'ENTRÉE,
  comme un vrai CDS), courue à chaque pas (advance_step) ;
- **Mark-to-market** : si le spread courant s'écarte au-delà du spread
  payé, la protection prend de la valeur — MTM ≈ (s_courant − s_entrée) ×
  duration risquée × notionnel. C'est la BASE du trading de crédit : on
  n'attend pas le défaut, on trade la PEUR du défaut ;
- **Évènement de crédit** : le roster ne fait pas juridiquement défaut,
  on utilise la convention du jeu — action sous 25 % de son niveau
  d'entrée = détresse déclenchante : la protection paie
  (1 − RECOVERY) × notionnel et se dénoue (evaluate_due, advance_step) ;
- à l'échéance sans évènement, le CDS expire sans valeur (la prime était
  le coût de l'assurance).
"""
from core import credit_risk as CR

RECOVERY = 0.40                 # taux de recouvrement conventionnel
TRIGGER_FRAC = 0.25             # action < 25 % du niveau d'entrée = évènement
STEPS_PER_YEAR = 52             # convention crédit (comme options/hedging)
MARKET_SPREAD_BPS = 15.0        # marge du teneur de marché sur le théorique
TENORS = [1.0, 3.0, 5.0]


def quote(market, ticker, years):
    """Cote de protection : spread théorique de Merton + marge de marché.
    None si la société n'est pas analysable. {spread_bps, pd, dd}."""
    f = CR.merton_credit(market, ticker, horizon=max(1.0, years))
    if f is None or f["debt"] <= 0:
        return None
    return {"ticker": ticker, "spread_bps": f["spread_bps"] + MARKET_SPREAD_BPS,
            "pd": f["pd"], "dd": f["dd"], "years": years}


def buy_protection(player, market, ticker, notional, years):
    """Achète la protection (aucun cash à l'entrée — la prime est courue,
    comme un vrai CDS). {ok, position} ou {ok: False, reason}."""
    if notional <= 0 or years not in TENORS:
        return {"ok": False, "reason": "params"}
    q = quote(market, ticker, years)
    if q is None:
        return {"ok": False, "reason": "ticker"}
    price = market.price_of(ticker)
    if price is None:
        return {"ok": False, "reason": "ticker"}
    player.cds_positions = getattr(player, "cds_positions", [])
    pos = {"id": max((c["id"] for c in player.cds_positions), default=0) + 1,
           "ticker": ticker, "notional": float(notional),
           "entry_spread_bps": q["spread_bps"], "entry_price": price,
           "years": years,
           "maturity_step": market.step_count + int(round(years * STEPS_PER_YEAR))}
    player.cds_positions.append(pos)
    return {"ok": True, "position": pos, "quote": q}


def mark_to_market(market, pos):
    """Valeur de sortie de la protection : (spread courant − spread payé) ×
    duration risquée approchée (années restantes) × notionnel."""
    steps_left = max(0, pos["maturity_step"] - market.step_count)
    years_left = steps_left / STEPS_PER_YEAR
    if years_left <= 0:
        return 0.0
    q = quote(market, pos["ticker"], max(1.0, years_left))
    if q is None:
        return 0.0
    return (q["spread_bps"] - pos["entry_spread_bps"]) / 10_000.0 \
        * years_left * pos["notional"]


def accrue(player, market, days):
    """Prime courue sur les protections en cours (coût, ≤ 0)."""
    total = 0.0
    for pos in getattr(player, "cds_positions", []) or []:
        total -= pos["notional"] * pos["entry_spread_bps"] / 10_000.0 \
            * (days / 365.0)
    return total


def evaluate_due(player, market):
    """Dénoue les CDS : ÉVÈNEMENT DE CRÉDIT (action < TRIGGER_FRAC du niveau
    d'entrée → paie (1−RECOVERY)×notionnel) ou échéance (expire sans
    valeur). Renvoie [{ticker, kind, payoff}] pour notification."""
    results, still = [], []
    for pos in getattr(player, "cds_positions", []) or []:
        price = market.price_of(pos["ticker"])
        triggered = (price is not None
                     and price < TRIGGER_FRAC * pos["entry_price"])
        if triggered:
            payoff = (1.0 - RECOVERY) * pos["notional"]
            player.cash += payoff
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + payoff
            results.append({"ticker": pos["ticker"], "kind": "credit_event",
                            "payoff": payoff})
        elif market.step_count >= pos["maturity_step"]:
            results.append({"ticker": pos["ticker"], "kind": "expiry",
                            "payoff": 0.0})
        else:
            still.append(pos)
    player.cds_positions = still
    return results


def close(player, market, pos_id):
    """Sortie anticipée au mark-to-market. {ok, mtm} ou {ok: False}."""
    for pos in getattr(player, "cds_positions", []) or []:
        if pos["id"] == pos_id:
            mtm = mark_to_market(market, pos)
            player.cash += mtm
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + mtm
            player.cds_positions.remove(pos)
            return {"ok": True, "mtm": mtm}
    return {"ok": False, "reason": "notfound"}


def holdings(player, market):
    """Protections en cours, avec MTM et spread courant."""
    out = []
    for pos in getattr(player, "cds_positions", []) or []:
        steps_left = max(0, pos["maturity_step"] - market.step_count)
        q = quote(market, pos["ticker"], max(1.0, steps_left / STEPS_PER_YEAR))
        out.append({**pos, "mtm": mark_to_market(market, pos),
                    "steps_left": steps_left,
                    "cur_spread_bps": q["spread_bps"] if q else None})
    return out


def holdings_value(player, market):
    """MTM total des protections (peut être négatif)."""
    return sum(mark_to_market(market, pos)
               for pos in getattr(player, "cds_positions", []) or [])
