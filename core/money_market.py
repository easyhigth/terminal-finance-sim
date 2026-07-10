"""
money_market.py — Marché monétaire / gestion de trésorerie (logique pure).

Le réflexe n°1 d'un vrai gérant : le cash aussi doit travailler. Jusqu'ici
la trésorerie dormait à 0 % — désormais :

- **Dépôts à terme** : bloquer un montant N pas contre un taux meilleur
  (prime de terme croissante). Le principal est débité à l'ouverture et
  revient à l'échéance avec les intérêts (advance_step). Pas de sortie
  anticipée : la LIQUIDITÉ a un prix, c'est la leçon.
- **Sweep au jour le jour** (player.flags['mm_sweep']) : le cash oisif
  au-delà d'un coussin est rémunéré chaque pas au taux directeur moins un
  spread — comme un fonds monétaire. Jamais bloqué, mais moins payé que
  le terme : l'arbitrage liquidité/rendement rendu concret.

Le taux de base réutilise la courbe du jeu (core/bonds.base_yield_level) —
cohérent avec les obligations, le repo et le carry FX.
"""
from core import bonds as B

# (pas de blocage, prime de terme annuelle)
TERMS = [(6, 0.000), (18, 0.004), (36, 0.008)]
TERM_STEPS = [t for t, _p in TERMS]
DEPOSIT_SPREAD = -0.002          # dépôt = base − 20 bp (+ prime de terme)
SWEEP_SPREAD = -0.005            # sweep = base − 50 bp (liquide, moins payé)
SWEEP_BUFFER = 50_000.0          # coussin de cash jamais balayé
DAYS_PER_STEP = 5
MAX_DEPOSITS = 10


def deposit_rate(market, term_steps):
    """Taux annuel d'un dépôt à terme."""
    prem = dict(TERMS).get(term_steps, 0.0)
    return max(0.0, B.base_yield_level(market) + DEPOSIT_SPREAD + prem)


def sweep_rate(market):
    """Taux annuel du sweep au jour le jour."""
    return max(0.0, B.base_yield_level(market) + SWEEP_SPREAD)


def open_deposit(player, market, amount, term_steps):
    """Ouvre un dépôt à terme (principal débité, bloqué). {ok, deposit}
    ou {ok: False, reason}."""
    player.mm_deposits = getattr(player, "mm_deposits", [])
    if term_steps not in TERM_STEPS:
        return {"ok": False, "reason": "term"}
    if amount <= 0 or amount > player.cash:
        return {"ok": False, "reason": "cash"}
    if len(player.mm_deposits) >= MAX_DEPOSITS:
        return {"ok": False, "reason": "max_deposits"}
    player.cash -= amount
    dep = {"id": max((d["id"] for d in player.mm_deposits), default=0) + 1,
           "amount": float(amount), "rate": deposit_rate(market, term_steps),
           "term_steps": term_steps,
           "maturity_step": market.step_count + term_steps}
    player.mm_deposits.append(dep)
    return {"ok": True, "deposit": dep}


def mature_due(player, market):
    """Rembourse les dépôts arrivés à échéance (principal + intérêts).
    Renvoie [{amount, interest}] pour notification."""
    results, still = [], []
    for dep in getattr(player, "mm_deposits", []) or []:
        if market.step_count >= dep["maturity_step"]:
            days = dep["term_steps"] * DAYS_PER_STEP
            interest = dep["amount"] * dep["rate"] * (days / 365.0)
            player.cash += dep["amount"] + interest
            results.append({"amount": dep["amount"], "interest": interest})
        else:
            still.append(dep)
    player.mm_deposits = still
    return results


def sweep_accrue(player, market, days):
    """Intérêt du sweep sur le cash oisif (au-delà du coussin), si activé.
    Montant à créditer (≥ 0)."""
    if not getattr(player, "flags", {}).get("mm_sweep"):
        return 0.0
    idle = max(0.0, player.cash - SWEEP_BUFFER)
    return idle * sweep_rate(market) * (days / 365.0)


def holdings(player, market):
    """Dépôts en cours, avec pas restants et intérêt attendu."""
    out = []
    for dep in getattr(player, "mm_deposits", []) or []:
        days = dep["term_steps"] * DAYS_PER_STEP
        out.append({**dep,
                    "steps_left": max(0, dep["maturity_step"] - market.step_count),
                    "expected_interest": dep["amount"] * dep["rate"] * (days / 365.0)})
    return out


def holdings_value(player, market=None):
    """Principal des dépôts en cours (les intérêts tombent à l'échéance)."""
    return sum(d["amount"] for d in getattr(player, "mm_deposits", []) or [])
