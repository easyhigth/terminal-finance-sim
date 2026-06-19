"""
risklimits.py — Limites de risque configurables et détection de dépassement
(logique pure, sans pygame).

Le joueur (ou un mandat, cf. core.mandates) peut définir des limites par
ligne, par secteur, par région/pays, par facteur de risque (bêta) et par
classe d'actifs. `check_limits()` compare ces limites aux expositions réelles
du book (réutilise core.analytics.summary, déjà calculé pour le dashboard) et
retourne la liste des dépassements (alertes). Toutes les limites sont
optionnelles : une limite absente (None) n'est jamais vérifiée.
"""
from core import analytics

# Limites par défaut (en % du brut investi, sauf beta_max qui est un facteur).
DEFAULT_LIMITS = {
    "position_pct": 25.0,
    "sector_pct": 40.0,
    "region_pct": 50.0,
    "class_pct": 70.0,
    "beta_max": 2.0,
    "illiquid_pct": 30.0,
}


def check_limits(player, market, limits=None):
    """Vérifie les expositions du book réel contre des limites (ou
    DEFAULT_LIMITS si non précisées). Retourne {ok, breaches}, `breaches`
    étant une liste de dicts {type, label, value, limit}."""
    lim = dict(DEFAULT_LIMITS)
    if limits:
        lim.update(limits)   # une valeur explicite à None désactive ce contrôle
    s = analytics.summary(player, market)
    invested = s["invested"] or 1.0
    breaches = []

    if lim.get("position_pct") is not None and s["rows"]:
        worst = max(s["rows"], key=lambda r: abs(r["value"]))
        worst_pct = abs(worst["value"]) / invested * 100.0
        if worst_pct > lim["position_pct"]:
            breaches.append({"type": "position", "label": worst["label"],
                              "value": worst_pct, "limit": lim["position_pct"]})

    if lim.get("sector_pct") is not None:
        for sector, val in s["by_sector"].items():
            pct = val / invested * 100.0
            if pct > lim["sector_pct"]:
                breaches.append({"type": "sector", "label": sector,
                                  "value": pct, "limit": lim["sector_pct"]})

    if lim.get("region_pct") is not None:
        for region, val in s["by_region"].items():
            pct = val / invested * 100.0
            if pct > lim["region_pct"]:
                breaches.append({"type": "region", "label": region,
                                  "value": pct, "limit": lim["region_pct"]})

    if lim.get("class_pct") is not None:
        for cls, val in s["by_class"].items():
            pct = val / invested * 100.0
            if pct > lim["class_pct"]:
                breaches.append({"type": "class", "label": cls,
                                  "value": pct, "limit": lim["class_pct"]})

    if lim.get("beta_max") is not None and abs(s["beta"]) > lim["beta_max"]:
        breaches.append({"type": "beta", "label": "Bêta portefeuille",
                          "value": s["beta"], "limit": lim["beta_max"]})

    if lim.get("illiquid_pct") is not None:
        illiquid = s["by_liquidity"].get("Illiquide", 0.0)
        pct = illiquid / invested * 100.0
        if pct > lim["illiquid_pct"]:
            breaches.append({"type": "liquidity", "label": "Actifs illiquides",
                              "value": pct, "limit": lim["illiquid_pct"]})

    return {"ok": not breaches, "breaches": breaches}
