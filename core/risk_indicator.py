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


def assess(player, market):
    """{"level", "reasons": [str, ...]} — le niveau le plus grave parmi
    marge/levier/concentration l'emporte ; "reasons" liste ce qui y
    contribue, en langage simple (infobulle du badge)."""
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

    if not reasons:
        reasons.append("Rien à signaler : levier et concentration sous contrôle")
    return {"level": level, "reasons": reasons}
