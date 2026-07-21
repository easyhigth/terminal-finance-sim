"""
swaps.py — Swaps de devises (cross-currency swap), logique pure, sans pygame.

Le joueur échange le différentiel de taux entre sa devise (région du
continent choisi en début de partie) et une devise étrangère, sur un
notionnel et une maturité donnés — sans échange de principal : les flux
sont réglés net en cash, comme un swap réel dont seule la jambe nette est
payée. Le taux régional réutilise celui des obligations (taux directeur +
bump de crédit régional, cf. core/bonds.py) : le swap matérialise donc un
pari déterministe sur l'écart de taux entre deux devises.

Aucun cash n'est débité à l'entrée (le notionnel n'est qu'une référence de
calcul, comme le capital des mandats clients). À chaque tour, le flux net
(jambe reçue - jambe payée) est crédité/débité du cash jusqu'à l'échéance,
où le swap expire sans autre règlement.

Holdings : PlayerState.currency_swaps = [ {dict swap} ].
"""
from core import bonds as B
from core import config

TENORS = [2, 3, 5]                              # années
DIRECTIONS = ("receive_foreign", "receive_domestic")
DIRECTION_LABEL = {
    "receive_foreign": "Reçoit taux étranger / Paie taux domestique",
    "receive_domestic": "Reçoit taux domestique / Paie taux étranger",
}
_DIRECTION_LABEL_EN = {
    "receive_foreign": "Receives foreign rate / Pays domestic rate",
    "receive_domestic": "Receives domestic rate / Pays foreign rate",
}


def direction_label(direction):
    """Libellé localisé du sens du swap (les clés restent FR-agnostiques)."""
    from core.i18n import get_lang
    table = _DIRECTION_LABEL_EN if get_lang() == "en" else DIRECTION_LABEL
    return table.get(direction, direction)


def regional_rate(market, region):
    """Taux régional de référence (taux directeur + bump de crédit régional)."""
    if market is None:
        return 0.03
    return B.base_yield_level(market) + getattr(market, "region_credit_bump", {}).get(region, 0.0)


def foreign_regions(player):
    """Régions étrangères disponibles (toutes sauf le continent du joueur)."""
    return [r for r in config.CONTINENTS if r != player.continent]


def quote(market, player, foreign_region):
    """Cote du différentiel de taux pour un swap domestique <-> `foreign_region`."""
    home = player.continent
    r_home = regional_rate(market, home)
    r_foreign = regional_rate(market, foreign_region)
    return {"home_region": home, "foreign_region": foreign_region,
            "home_rate": r_home, "foreign_rate": r_foreign,
            "diff": r_foreign - r_home}


def _net_rate(market, sw):
    """Différentiel de taux net (jambe reçue - jambe payée), en décimal."""
    r_home = regional_rate(market, sw["home_region"])
    r_foreign = regional_rate(market, sw["foreign_region"])
    diff = r_foreign - r_home
    return diff if sw["direction"] == "receive_foreign" else -diff


def enter_swap(player, market, foreign_region, direction, notional, years):
    """Conclut un swap de devises (pas de débit de cash, cf. docstring du module)."""
    if foreign_region not in config.CONTINENTS or foreign_region == player.continent:
        return {"ok": False, "reason": "region"}
    if direction not in DIRECTIONS:
        return {"ok": False, "reason": "direction"}
    if notional <= 0:
        return {"ok": False, "reason": "notional"}
    if years not in TENORS:
        return {"ok": False, "reason": "years"}
    sw = {
        "id": player.next_swap_id,
        "home_region": player.continent,
        "foreign_region": foreign_region,
        "direction": direction,
        "notional": float(notional),
        "years": years,
        "days_left": int(years * 365),
    }
    player.next_swap_id += 1
    player.currency_swaps.append(sw)
    return {"ok": True, "swap": sw}


def accrue(player, market, days):
    """Flux net du tour (reçu - payé) pour les swaps actifs, et fait vieillir
    chaque swap jusqu'à expiration. Retourne (flux_net_total, swaps_expirés)."""
    total = 0.0
    expired, still = [], []
    for sw in getattr(player, "currency_swaps", []):
        if market is not None:
            total += sw["notional"] * _net_rate(market, sw) * (days / 365.0)
        sw["days_left"] -= days
        if sw["days_left"] <= 0:
            expired.append(sw)
        else:
            still.append(sw)
    player.currency_swaps = still
    return total, expired


def holdings(player, market):
    out = []
    for sw in getattr(player, "currency_swaps", []):
        net = _net_rate(market, sw)
        out.append({**sw, "net_rate": net,
                    "annual_carry": sw["notional"] * net,
                    "years_left": sw["days_left"] / 365.0})
    return out
