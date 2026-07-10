"""
irs.py — Swap de taux d'intérêt (IRS) payeur/receveur de fixe, logique pure.

Distinct des swaps de DEVISES existants (core/swaps.py) : ici on échange
FIXE contre VARIABLE dans la même devise — l'outil de gestion du risque de
taux d'un vrai desk :

- **Payeur de fixe** (paie le taux fixé à l'entrée, reçoit le variable =
  taux directeur courant) : GAGNE quand les taux MONTENT — son DV01 est
  NÉGATIF, c'est LA couverture d'un book obligataire sans le vendre ;
- **Receveur de fixe** : l'inverse (duration synthétique, sans cash).

Aucun échange de principal : le flux NET (variable − fixe, signé selon le
sens) est réglé en cash chaque pas (advance_step). Mark-to-market =
(taux courant − taux fixé) × duration restante × notionnel (approximation
d'annuité standard). `hedge_notional` dimensionne le swap payeur qui
annule le DV01 du book obligataire (bouton du Desk Taux).
"""
from core import bonds as B

TENORS = [2.0, 5.0, 10.0]
SWAP_SPREAD = 0.001            # marge du teneur de marché sur le taux fixe
DURATION_FACTOR = 0.9          # duration d'annuité ≈ 0,9 × maturité restante
STEPS_PER_YEAR = 52


def par_rate(market, years):
    """Taux fixe « à la monnaie » du swap : taux directeur + prime de terme
    (même courbe que les obligations) + marge."""
    return (B.base_yield_level(market) + B.term_premium(market, years)
            + SWAP_SPREAD)


def swap_dv01(notional, years_left):
    """DV01 du swap (valeur d'1 bp) — approximation d'annuité."""
    return notional * DURATION_FACTOR * years_left * 1e-4


def enter_swap(player, market, direction, notional, years):
    """Entre dans un swap ('payer' = paie fixe / 'receiver' = reçoit fixe).
    Aucun cash à l'entrée. {ok, position} ou {ok: False, reason}."""
    if direction not in ("payer", "receiver") or years not in TENORS:
        return {"ok": False, "reason": "params"}
    if notional <= 0:
        return {"ok": False, "reason": "notional"}
    player.irs_positions = getattr(player, "irs_positions", [])
    pos = {"id": max((s["id"] for s in player.irs_positions), default=0) + 1,
           "direction": direction, "notional": float(notional),
           "fixed_rate": par_rate(market, years), "years": years,
           "maturity_step": market.step_count + int(round(years * STEPS_PER_YEAR))}
    player.irs_positions.append(pos)
    return {"ok": True, "position": pos}


def accrue(player, market, days):
    """Flux net couru d'un pas : (variable − fixe) × notionnel, signé
    (payeur gagne si le variable dépasse son fixe). Dénoue les swaps échus
    au passage (dernier flux, puis retrait). Montant total signé."""
    total = 0.0
    still = []
    floating = B.base_yield_level(market)
    for pos in getattr(player, "irs_positions", []) or []:
        sign = 1.0 if pos["direction"] == "payer" else -1.0
        total += sign * (floating - pos["fixed_rate"]) * pos["notional"] \
            * (days / 365.0)
        if market.step_count < pos["maturity_step"]:
            still.append(pos)
    if getattr(player, "irs_positions", None) is not None:
        player.irs_positions[:] = still
    return total


def mark_to_market(market, pos):
    """MTM du swap : (taux courant − fixe) × duration restante × notionnel,
    signé (payeur gagne quand les taux montent)."""
    steps_left = max(0, pos["maturity_step"] - market.step_count)
    years_left = steps_left / STEPS_PER_YEAR
    if years_left <= 0:
        return 0.0
    cur = par_rate(market, max(1.0, years_left))
    sign = 1.0 if pos["direction"] == "payer" else -1.0
    return sign * (cur - pos["fixed_rate"]) * DURATION_FACTOR \
        * years_left * pos["notional"]


def close(player, market, pos_id):
    """Sortie anticipée au mark-to-market."""
    for pos in getattr(player, "irs_positions", []) or []:
        if pos["id"] == pos_id:
            mtm = mark_to_market(market, pos)
            player.cash += mtm
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + mtm
            player.irs_positions.remove(pos)
            return {"ok": True, "mtm": mtm}
    return {"ok": False, "reason": "notfound"}


def hedge_notional(book_dv01, years=5.0):
    """Notionnel du swap PAYEUR qui annule un DV01 obligataire donné."""
    unit = DURATION_FACTOR * years * 1e-4
    return book_dv01 / unit if unit > 0 else 0.0


def portfolio_dv01(player, market):
    """DV01 NET du joueur : book obligataire (positif) + swaps (payeur
    négatif). L'objectif d'une couverture : le rapprocher de zéro."""
    from core import rates_analytics as RT
    total = RT.book_totals(RT.book_lines(player, market))["dv01"]
    for pos in getattr(player, "irs_positions", []) or []:
        steps_left = max(0, pos["maturity_step"] - market.step_count)
        sign = -1.0 if pos["direction"] == "payer" else 1.0
        total += sign * swap_dv01(pos["notional"], steps_left / STEPS_PER_YEAR)
    return total


def holdings(player, market):
    out = []
    for pos in getattr(player, "irs_positions", []) or []:
        steps_left = max(0, pos["maturity_step"] - market.step_count)
        out.append({**pos, "mtm": mark_to_market(market, pos),
                    "steps_left": steps_left,
                    "dv01": (-1.0 if pos["direction"] == "payer" else 1.0)
                    * swap_dv01(pos["notional"], steps_left / STEPS_PER_YEAR)})
    return out


def holdings_value(player, market):
    return sum(mark_to_market(market, pos)
               for pos in getattr(player, "irs_positions", []) or [])
