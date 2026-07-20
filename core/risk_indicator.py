"""
risk_indicator.py — Indicateur de risque unifié (logique pure).

Une seule pastille couleur (vert/ambre/rouge) résumant "suis-je en danger ?"
à partir de plusieurs signaux dispersés (levier, marge sous tension,
concentration d'une position) — plutôt que de devoir interpréter soi-même
plusieurs chiffres séparés (levier ici, equity là, poids d'une ligne
ailleurs). Consommé par le badge de la barre supérieure du bureau
(scenes/scene_desktop.py), toujours visible même fenêtres fermées.
"""
from core import portfolio_margin as pm

LEVEL_OK, LEVEL_WARN, LEVEL_DANGER = "ok", "warn", "danger"
_RANK = {LEVEL_OK: 0, LEVEL_WARN: 1, LEVEL_DANGER: 2}

LEVERAGE_WARN = 1.0
LEVERAGE_DANGER = 2.0
# une position pesant plus de la moitié/des 4/5 du patrimoine net : concentration
# notable/dangereuse (pas de diversification, un seul choc de marché suffit).
CONCENTRATION_WARN = 0.5
CONCENTRATION_DANGER = 0.8
# scrutin réglementaire (core/dilemmas) : seuil d'enquête à 55 (danger), à
# surveiller dès 40 (warn) — la conformité fait partie du risque global.
HEAT_WARN = 40
HEAT_DANGER = 55
# VaR / limite de la firme (ratio) : au-delà de la limite = danger, on s'en
# approche = warn (cf. la jauge du widget patrimoine).
VAR_WARN = 0.75
VAR_DANGER = 1.0


def _worse(a, b):
    return a if _RANK[a] >= _RANK[b] else b


def _max_position_weight(player, market):
    nw = pm.net_worth(player, market)
    if nw <= 0 or not player.portfolio:
        return 0.0
    best = 0.0
    for tk, pos in player.portfolio.items():
        price = market.price_of(tk)
        if price is None:
            continue
        best = max(best, abs(pos["shares"] * price) / nw)
    return best


def assess(player, market, var_ratio=None):
    """{"level", "reasons": [str, ...]} — UNE lecture consolidée de « suis-je en
    danger ? » : le niveau le plus grave parmi marge, levier, concentration,
    VaR vs limite de la firme et scrutin réglementaire l'emporte ; "reasons"
    liste ce qui y contribue, en langage simple (infobulle du badge).

    `var_ratio` (VaR / limite de la firme) est PASSÉ par l'appelant, qui le met
    en cache par pas de marché (la simulation VaR coûte) — None = signal ignoré."""
    st = pm.margin_status(player, market)
    lev = st["leverage"] if st["leverage"] != float("inf") else 999.0
    weight = _max_position_weight(player, market)

    level = LEVEL_OK
    reasons = []
    if st["margin_call"]:
        level = _worse(level, LEVEL_DANGER)
        reasons.append("Appel de marge actif")
    elif lev > LEVERAGE_DANGER:
        level = _worse(level, LEVEL_DANGER)
        reasons.append(f"Levier élevé ({lev:.2f}x)")
    elif lev > LEVERAGE_WARN:
        level = _worse(level, LEVEL_WARN)
        reasons.append(f"Levier > 1x ({lev:.2f}x)")

    if weight >= CONCENTRATION_DANGER:
        level = _worse(level, LEVEL_DANGER)
        reasons.append(f"Position très concentrée ({weight * 100:.0f}% du patrimoine)")
    elif weight >= CONCENTRATION_WARN:
        level = _worse(level, LEVEL_WARN)
        reasons.append(f"Position concentrée ({weight * 100:.0f}% du patrimoine)")

    if var_ratio is not None:
        if var_ratio >= VAR_DANGER:
            level = _worse(level, LEVEL_DANGER)
            reasons.append(f"VaR au-delà de la limite ({var_ratio * 100:.0f}%)")
        elif var_ratio >= VAR_WARN:
            level = _worse(level, LEVEL_WARN)
            reasons.append(f"VaR proche de la limite ({var_ratio * 100:.0f}%)")

    heat = getattr(player, "heat", 0)
    if heat >= HEAT_DANGER:
        level = _worse(level, LEVEL_DANGER)
        reasons.append(f"Scrutin réglementaire critique ({heat}/100)")
    elif heat >= HEAT_WARN:
        level = _worse(level, LEVEL_WARN)
        reasons.append(f"Scrutin réglementaire élevé ({heat}/100)")

    if not reasons:
        reasons.append("Rien à signaler : levier, concentration, VaR et conformité sous contrôle")
    return {"level": level, "reasons": reasons}
