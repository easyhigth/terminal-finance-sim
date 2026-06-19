"""
securitisation.py — Desk crédit / titrisation (logique pure, sans pygame).

Un pool de prêts est découpé en TRANCHES (equity / mezzanine / senior). Les
pertes du pool sont absorbées de bas en haut (subordination) via la cascade
(waterfall) : l'equity encaisse les premières pertes, puis la mezzanine, enfin
le senior. Le joueur investit dans une tranche ; à l'échéance, le taux de défaut
RÉALISÉ détermine la perte du pool et, par la cascade, la perte de sa tranche.

Holdings : PlayerState.securitised = [ {dict position} ].
"""
import numpy as np

STEPS_PER_YEAR = 52
YEARS = 3
LGD = 0.55                      # perte en cas de défaut
EXPECTED_DEFAULT = 0.08        # taux de défaut cumulé attendu du pool
DEFAULT_VOL = 0.06             # incertitude sur le taux réalisé
LOT = 50_000.0                  # notionnel investi par clic (desk & boutique)
EARLY_EXIT_HAIRCUT = 0.02       # décote de sortie anticipée (illiquidité ABS)

# (id, nom, point d'attache, point de détachement, coupon annuel, rating)
TRANCHES = [
    ("EQUITY", "Equity (first loss)", 0.00, 0.10, 0.22, "NR"),
    ("MEZZ",   "Mezzanine", 0.10, 0.25, 0.11, "BB"),
    ("SENIOR", "Senior", 0.25, 1.00, 0.045, "AAA"),
]
_BY_ID = {t[0]: t for t in TRANCHES}


def tranche_loss_fraction(pool_loss, attach, detach):
    """Fraction de la tranche [attach, detach] détruite par une perte de pool."""
    if detach <= attach:
        return 0.0
    return float(np.clip((pool_loss - attach) / (detach - attach), 0.0, 1.0))


def expected_pool_loss(market=None):
    """Perte attendue du pool = taux de défaut attendu × LGD, élargie en cas de
    stress macro (régime de marché, crise active) — comme un spread de crédit
    qui s'élargit en récession. `market=None` retourne le niveau de base (utilisé
    par les tests et avant le premier pas)."""
    dr = EXPECTED_DEFAULT
    if market is not None:
        regime = getattr(market, "regime", "")
        if regime == "Récession":
            dr += 0.03
        elif regime == "Volatil":
            dr += 0.015
        if getattr(market, "crises", None):
            dr += 0.05
    return dr * LGD


def realized_pool_loss(market, salt=0):
    """Perte de pool RÉALISÉE (déterministe via graine+pas). Une crise en cours
    aggrave les défauts."""
    seed = (int(getattr(market, "seed", 12345)) + 7919 * (salt + 1)
            + int(getattr(market, "step_count", 0))) & 0xFFFFFFFF
    rng = np.random.RandomState(seed)
    dr = rng.normal(EXPECTED_DEFAULT, DEFAULT_VOL)
    # régime/crises de marché : aggravation des défauts en récession
    if getattr(market, "crises", None):
        dr += 0.05
    if getattr(market, "regime", "") == "Récession":
        dr += 0.03
    dr = float(np.clip(dr, 0.0, 1.0))
    return dr * LGD


def tranche_quote(tranche_id, market=None):
    t = _BY_ID[tranche_id]
    el = expected_pool_loss(market)
    exp_tranche_loss = tranche_loss_fraction(el, t[2], t[3])
    return {"id": t[0], "name": t[1], "attach": t[2], "detach": t[3],
            "coupon": t[4], "rating": t[5], "exp_loss": exp_tranche_loss,
            "thickness": t[3] - t[2]}


def all_quotes(market=None):
    return [tranche_quote(t[0], market) for t in TRANCHES]


def invest(player, market, tranche_id, notional):
    if tranche_id not in _BY_ID:
        return {"ok": False, "reason": "id"}
    if notional <= 0 or notional > player.cash:
        return {"ok": False, "reason": "cash"}
    t = _BY_ID[tranche_id]
    salt = len(player.securitised)
    player.cash -= notional
    player.securitised.append({
        "id": t[0], "name": t[1], "attach": t[2], "detach": t[3],
        "coupon": t[4], "notional": float(notional), "salt": salt,
        "maturity_step": market.step_count + YEARS * STEPS_PER_YEAR})
    return {"ok": True, "price": LOT}


def evaluate_due(player, market):
    """Dénoue les tranches arrivées à échéance via la cascade des pertes."""
    results, still = [], []
    for pos in getattr(player, "securitised", []):
        if market.step_count >= pos["maturity_step"]:
            pool_loss = realized_pool_loss(market, pos["salt"])
            loss_frac = tranche_loss_fraction(pool_loss, pos["attach"], pos["detach"])
            coupons = pos["notional"] * pos["coupon"] * YEARS
            principal = pos["notional"] * (1.0 - loss_frac)
            payoff = coupons + principal
            player.cash += payoff
            player.realized_pnl = getattr(player, "realized_pnl", 0.0) + (payoff - pos["notional"])
            results.append({"position": pos, "pool_loss": pool_loss,
                            "loss_frac": loss_frac, "payoff": payoff,
                            "pnl": payoff - pos["notional"]})
        else:
            still.append(pos)
    player.securitised = still
    return results


def mark_to_model(pos, market):
    """Valeur de sortie anticipée d'une tranche (avant échéance) : perte attendue
    courante (cf. expected_pool_loss, sensible au régime/crises) + coupons accrus
    au prorata du temps écoulé, minorée d'une décote d'illiquidité ABS."""
    el = expected_pool_loss(market)
    exp_loss_frac = tranche_loss_fraction(el, pos["attach"], pos["detach"])
    start_step = pos["maturity_step"] - YEARS * STEPS_PER_YEAR
    elapsed_years = max(market.step_count - start_step, 0) / STEPS_PER_YEAR
    accrued_coupon = pos["notional"] * pos["coupon"] * elapsed_years
    principal = pos["notional"] * (1.0 - exp_loss_frac)
    return (accrued_coupon + principal) * (1.0 - EARLY_EXIT_HAIRCUT)


def sell(player, market, tranche_id, notional):
    """Dénoue par anticipation jusqu'à `notional` de notionnel investi dans la
    tranche `tranche_id` (FIFO sur les positions ouvertes), à la valeur
    mark-to-model courante. Retourne un dict compatible avec le format
    générique des autres marchés (qty=lots vendus, price=LOT, realized=P&L)."""
    items = getattr(player, "securitised", [])
    remaining = notional
    total_value, total_pnl, sold_any = 0.0, 0.0, False
    i = 0
    while i < len(items) and remaining > 1e-6:
        pos = items[i]
        if pos["id"] != tranche_id:
            i += 1
            continue
        sell_amt = min(remaining, pos["notional"])
        frac = sell_amt / pos["notional"] if pos["notional"] else 0.0
        value = mark_to_model(pos, market) * frac
        total_value += value
        total_pnl += value - sell_amt
        player.cash += value
        pos["notional"] -= sell_amt
        remaining -= sell_amt
        sold_any = True
        if pos["notional"] <= 1e-6:
            items.pop(i)
        else:
            i += 1
    if not sold_any:
        return {"ok": False, "reason": "noposition"}
    player.realized_pnl = getattr(player, "realized_pnl", 0.0) + total_pnl
    return {"ok": True, "qty": (notional - remaining) / LOT, "price": LOT,
            "realized": total_pnl, "value": total_value}


def held_notional(player, tranche_id):
    return sum(p["notional"] for p in getattr(player, "securitised", []) if p["id"] == tranche_id)


def holdings_value(player, market):
    return sum(p["notional"] for p in getattr(player, "securitised", []))


def holdings(player, market):
    out = []
    for p in getattr(player, "securitised", []):
        steps_left = max(0, p["maturity_step"] - market.step_count)
        out.append({"name": p["name"], "notional": p["notional"], "coupon": p["coupon"],
                    "years_left": steps_left / STEPS_PER_YEAR})
    return out
