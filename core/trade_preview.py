"""
trade_preview.py — Simulateur AVANT → APRÈS d'une action de trading
(logique pure). LE chokepoint de lisibilité des outils :

    « Qu'est-ce que ça va faire à MON portefeuille ? »

Pour n'importe quelle action (achat d'action, d'obligation, ouverture d'un
CDS, d'un repo…), `preview()` applique l'action à une COPIE du joueur et
mesure l'état avant/après selon la MÊME grille, quelle que soit la
complexité de l'instrument :

    cash · levier · bêta · VaR (vs limite de la firme) · FLUX PAR TOUR

Le flux par tour est mesuré en rejouant les VRAIS accruals du moteur
(dividendes, coupons, carry, primes, financement — les mêmes fonctions que
core/step_hooks) sur la copie : pas une estimation parallèle qui divergerait,
le chiffre exact que le prochain pas produirait à marché constant.

`stress_compare()` réutilise le Labo de crise (core/crisis_lab.reprice) pour
répondre à « et si le marché prend -10 % / les taux +1 pt / la vol explose ? »
avant et après l'action.

Usage type (ticket d'ordre) :
    pv = trade_preview.preview(p, market,
                               lambda q, m: pf.buy(q, m, "MVC", 100))
    if pv["result"].get("ok"): afficher pv["before"]/pv["after"]/pv["flux"]…
"""
from dataclasses import asdict

from core import config
from core import portfolio as pf

VAR_SAMPLES = 1500     # précision suffisante pour un ticket, ~instantané
STRESS_SCENARIOS = [
    ("eq", ("Marché -10 %", "Market -10%"), {"eq_shock": -0.10, "dy": 0.0}),
    ("rates", ("Taux +1 pt", "Rates +1 pt"), {"eq_shock": 0.0, "dy": 0.01}),
    ("vol", ("Vol x2 (crunch)", "Vol x2 (crunch)"),
     {"eq_shock": -0.05, "dy": 0.0, "corr_crunch": True}),
]


def clone_player(player):
    """Copie profonde et indépendante du joueur (via le format de save :
    tout ce qui persiste est copié, rien d'autre n'est nécessaire)."""
    from core.game_state import PlayerState
    return PlayerState(**asdict(player))


def snapshot(player, market, with_var=True):
    """Photo de l'état : {nw, cash, leverage, beta, var, var_limit}."""
    from core import risklimits
    out = {
        "nw": pf.net_worth(player, market),
        "cash": player.cash,
        "leverage": pf.leverage(player, market),
        "beta": pf.portfolio_beta(player, market),
        "var": None,
        "var_limit": risklimits.firm_var_limit(player),
    }
    if with_var:
        from core import risk
        try:
            out["var"] = risk.simulate(player, market, confidence=0.95,
                                       n=VAR_SAMPLES)["var"]
        except Exception:
            from core import crashlog
            crashlog.swallowed("trade_preview.var")
    return out


def step_flow(player, market):
    """FLUX PAR TOUR à marché constant : somme des accruals réels du moteur
    (mêmes fonctions que core/step_hooks) moins le financement. À appeler
    sur une COPIE (certains accruals avancent des marqueurs internes)."""
    days = config.DAYS_PER_STEP
    total = pf.dividends(player, market, days)
    if getattr(player, "bonds", None):
        from core import bonds
        total += bonds.coupons(player, market, days)
    if getattr(player, "commodities", None):
        from core import commodities
        total += commodities.roll_cost(player, market, days)
    if getattr(player, "crypto", None):
        from core import crypto
        total += crypto.interest(player, market, days)
    if getattr(player, "fx_positions", None):
        from core import fx_carry
        total += fx_carry.accrue(player, market, days)
    if getattr(player, "repo_positions", None):
        from core import repo
        total += repo.accrue(player, market, days)
    if player.portfolio:
        from core import seclending
        total += seclending.accrue(player, market, days)
    from core import money_market
    total += money_market.sweep_accrue(player, market, days)
    if getattr(player, "cds_positions", None):
        from core import cds
        total += cds.accrue(player, market, days)
    if getattr(player, "irs_positions", None):
        from core import irs
        total += irs.accrue(player, market, days)
    if getattr(player, "convertibles", None):
        from core import convertibles
        total += convertibles.accrue(player, market, days)
    if getattr(player, "trs_positions", None):
        from core import trs
        total += trs.accrue(player, market, days)
    if getattr(player, "currency_swaps", None):
        from core import swaps
        flow, _expired = swaps.accrue(player, market, days)
        total += flow
    # financement (intérêts de marge + emprunt de titres) : débite la copie
    cash0 = player.cash
    pf.accrue_financing(player, market, days)
    total += player.cash - cash0
    return total


def preview(player, market, apply_fn, with_var=True):
    """Applique `apply_fn(copie, market)` et mesure l'avant/après.

    Retourne {"result": <retour de apply_fn>, "before": snap, "after": snap,
    "flux_before": float, "flux_after": float, "player_after": copie}.
    Si l'action échoue (result sans ok=True), after/flux_after sont None —
    l'appelant affiche la raison du refus telle quelle."""
    before = snapshot(player, market, with_var=with_var)
    flux_before = step_flow(clone_player(player), market)
    q = clone_player(player)
    result = apply_fn(q, market)
    ok = bool(result.get("ok")) if isinstance(result, dict) else bool(result)
    out = {"result": result, "before": before, "flux_before": flux_before,
           "after": None, "flux_after": None, "player_after": None}
    if ok:
        out["after"] = snapshot(q, market, with_var=with_var)
        out["flux_after"] = step_flow(clone_player(q), market)
        out["player_after"] = q
    return out


def stress_compare(player, market, player_after=None):
    """Effet des 3 scénarios de stress (Labo de crise) sur le portefeuille,
    AVANT et (si fourni) APRÈS l'action. Retourne
    [{key, label(fr,en), before, after|None}] — pertes négatives."""
    from core import crisis_lab
    out = []
    for key, label, kwargs in STRESS_SCENARIOS:
        row = {"key": key, "label": label,
               "before": crisis_lab.reprice(player, market, **kwargs)["total"],
               "after": None}
        if player_after is not None:
            row["after"] = crisis_lab.reprice(player_after, market, **kwargs)["total"]
        out.append(row)
    return out


def execution_cost(player, market, ticker, qty, side="buy"):
    """Décomposition du coût d'exécution RÉEL d'un ordre action/ETF :
    {mid, fill, spread_impact, fee, total, total_pct} — la différence entre
    « le prix affiché » et « ce que ça coûte vraiment »."""
    mid = market.price_of(ticker)
    if not mid or qty <= 0:
        return None
    fill = pf.fill_price(market, ticker, qty, side)
    spread_impact = abs(fill - mid) * qty
    notional = fill * qty
    fee = notional * pf._commission(player)
    total = spread_impact + fee
    return {"mid": mid, "fill": fill, "spread_impact": spread_impact,
            "fee": fee, "total": total,
            "total_pct": total / notional * 100.0 if notional else 0.0}


def position_weight_after(player, market, ticker, qty):
    """Poids (%) que pèserait la ligne `ticker` dans la valeur nette après
    l'achat de `qty` titres — « cette ligne fera X % de votre portefeuille »."""
    price = market.price_of(ticker)
    if not price:
        return None
    held = player.portfolio.get(ticker, {}).get("shares", 0.0)
    value = (held + qty) * price
    nw = pf.net_worth(player, market)
    return value / nw * 100.0 if nw > 0 else None
