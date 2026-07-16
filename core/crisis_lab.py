"""
crisis_lab.py — Simulateur de crise INTERACTIF (logique pure).

Contrairement au Stress test (scénarios nommés, core/risk.stress), ici le
joueur RÈGLE lui-même le scénario et voit son book réévalué ligne par
ligne :

- **Actions** : P&L = valeur × β_i × choc en régime normal. En mode
  « CORRÉLATIONS → 1 » (ce qui arrive VRAIMENT en crise : la diversification
  disparaît précisément quand on en a besoin), les valeurs DÉFENSIVES
  cessent de protéger — chaque titre encaisse AU MOINS le choc plein
  (β effectif = max(β, 1), les β élevés tombent toujours davantage) ; la
  différence entre les deux totaux EST le coût de l'illusion de
  diversification.
- **Obligations** : ΔP = V·(−D·Δy + ½·C·Δy²) (duration + convexité).
- **Options** (player.options) et **puts de couverture** (player.hedges) :
  re-pricés Black-Scholes au spot choqué et à la vol bumpée (une crise
  fait AUSSI exploser la vol implicite — les protections prennent de la
  valeur par le vega, pas seulement par l'intrinsèque).

Tout est déterministe : mêmes réglages → même résultat.
"""
from core import finmath as fm
from core import hedging as H
from core import options as opt
from core import portfolio as pf

CRUNCH_VOL_BUMP = 0.10          # +10 pts de vol implicite en mode crise


def reprice(player, market, eq_shock=-0.20, dy=0.010, corr_crunch=False):
    """Réévalue le book sous le scénario. Renvoie {lines: [{label, kind,
    value, pnl}], total, total_normal (sans crunch, pour comparaison),
    net_worth_pct} — pertes négatives."""
    lines = []
    total = 0.0
    diversified = 0.0            # ce que donnerait le même choc SANS crunch
    # --- actions (longues et courtes : le signe de la valeur fait foi)
    for h in pf.holdings(player, market):
        i = market.ticker_idx.get(h["ticker"])
        beta = float(market.beta[i]) if i is not None else 1.0
        pnl_beta = h["value"] * beta * eq_shock
        # crunch : les défensives (β < 1) tombent comme le marché,
        # les β élevés tombent toujours davantage — jamais moins pire.
        pnl = h["value"] * max(beta, 1.0) * eq_shock if corr_crunch else pnl_beta
        diversified += pnl_beta
        total += pnl
        lines.append({"label": h["ticker"], "kind": "Action",
                      "value": h["value"], "pnl": pnl})
    # --- obligations (duration + convexité)
    from core import rates_analytics as RT
    for x in RT.book_lines(player, market):
        pnl = x["value"] * (-x["duration"] * dy
                            + 0.5 * x["convexity"] * dy * dy)
        total += pnl
        diversified += pnl
        lines.append({"label": x["name"], "kind": "Obligation",
                      "value": x["value"], "pnl": pnl})
    vol_bump = CRUNCH_VOL_BUMP if corr_crunch else 0.0
    # --- options sur actions : re-pricing BS au spot choqué / vol bumpée
    r = opt.risk_free_rate(market)
    for pos in getattr(player, "options", []) or []:
        spot = market.price_of(pos["ticker"])
        if spot is None:
            continue
        steps_left = max(0, pos["maturity_step"] - market.step_count)
        t_left = steps_left / opt.STEPS_PER_YEAR
        sigma = opt._stock_vol(market, pos["ticker"])
        i = market.ticker_idx.get(pos["ticker"])
        beta = float(market.beta[i]) if i is not None else 1.0
        if corr_crunch:
            beta = max(beta, 1.0)
        spot_shocked = spot * (1.0 + beta * eq_shock)
        v0 = _bs_or_intrinsic(spot, pos, t_left, r, sigma) * pos["contracts"]
        v1 = _bs_or_intrinsic(spot_shocked, pos, t_left, r,
                              sigma + vol_bump) * pos["contracts"]
        pnl = v1 - v0
        total += pnl
        diversified += pnl
        lines.append({"label": f"{pos['option_type'].upper()} {pos['ticker']}",
                      "kind": "Option", "value": v0, "pnl": pnl})
    # --- puts de couverture sur l'indice
    for pos in getattr(player, "hedges", []) or []:
        level = market.index_value(pos["underlying"])
        steps_left = max(0, pos["maturity_step"] - market.step_count)
        t_left = steps_left / H.STEPS_PER_YEAR
        sigma = H._index_vol(market, pos["underlying"])
        unit0 = (fm.black_scholes(level, pos["strike"], t_left, r, sigma,
                                  option="put") / pos["start_level"]
                 if t_left > 0 else
                 max(0.0, (pos["strike"] - level) / pos["start_level"]))
        level1 = level * (1.0 + eq_shock)
        unit1 = (fm.black_scholes(level1, pos["strike"], t_left, r,
                                  sigma + vol_bump, option="put") / pos["start_level"]
                 if t_left > 0 else
                 max(0.0, (pos["strike"] - level1) / pos["start_level"]))
        pnl = (unit1 - unit0) * pos["notional"]
        total += pnl
        diversified += pnl
        lines.append({"label": f"PUT {pos['underlying']}", "kind": "Couverture",
                      "value": unit0 * pos["notional"], "pnl": pnl})
    lines.sort(key=lambda x: x["pnl"])
    nw = _net_worth_proxy(player, market)
    return {"lines": lines, "total": total, "total_normal": diversified,
            "net_worth_pct": (total / nw * 100.0) if nw else 0.0}


def _bs_or_intrinsic(spot, pos, t_left, r, sigma):
    if t_left > 0:
        return fm.black_scholes(spot, pos["strike"], t_left, r, sigma,
                                option=pos["option_type"])
    if pos["option_type"] == "call":
        return max(0.0, spot - pos["strike"])
    return max(0.0, pos["strike"] - spot)


def _net_worth_proxy(player, market):
    total = player.cash
    for h in pf.holdings(player, market):
        total += h["value"]
    return total if total > 0 else 0.0
