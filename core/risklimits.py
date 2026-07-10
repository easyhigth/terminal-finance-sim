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

# Profils de limites sélectionnables par le joueur (cf. scenes/scene_risk.py).
# "default" == DEFAULT_LIMITS ; "strict" resserre les bornes (style mandat
# institutionnel) ; "souple" les desserre (style book prop discrétionnaire).
LIMIT_PROFILES = {
    "strict": {
        "position_pct": 15.0, "sector_pct": 25.0, "region_pct": 35.0,
        "class_pct": 50.0, "beta_max": 1.2, "illiquid_pct": 15.0,
    },
    "default": dict(DEFAULT_LIMITS),
    "souple": {
        "position_pct": 40.0, "sector_pct": 60.0, "region_pct": 70.0,
        "class_pct": 90.0, "beta_max": 3.0, "illiquid_pct": 50.0,
    },
}


def effective_limits(player):
    """Retourne les limites actives du joueur selon son profil sélectionné
    (`player.risk_limit_profile`), DEFAULT_LIMITS si profil inconnu."""
    profile = getattr(player, "risk_limit_profile", "default")
    return dict(LIMIT_PROFILES.get(profile, DEFAULT_LIMITS))


def set_profile(player, name):
    """Change le profil de limites actif du joueur. Retourne True si `name`
    est un profil connu, False sinon (aucun changement dans ce cas)."""
    if name not in LIMIT_PROFILES:
        return False
    player.risk_limit_profile = name
    return True


def check_limits(player, market, limits=None):
    """Vérifie les expositions du book réel contre les limites du profil actif
    du joueur (cf. `effective_limits`), ou contre `limits` si précisées.
    Retourne {ok, breaches}, `breaches` étant une liste de dicts
    {type, label, value, limit}."""
    lim = effective_limits(player)
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


# ---------------------------------------------------------------------------
# Limite de VaR IMPOSÉE PAR LA FIRME (par grade) — contrairement aux profils
# ci-dessus (choisis par le joueur), celle-ci ne se négocie pas : un jeune
# trader a un petit budget de risque, un MD un gros. Vérifiée à chaque pas
# par advance_step avec ESCALADE : avertissement → perte de réputation →
# RÉDUCTION FORCÉE du book (la firme coupe la position la plus grosse),
# comme dans une vraie salle. VaR 95 % à 1 pas, en millions (convention
# core/risk.simulate).
# ---------------------------------------------------------------------------
FIRM_VAR_LIMITS_M = [0.06, 0.10, 0.16, 0.25, 0.40, 0.65, 1.00, 1.60, 2.60, 4.00]
FIRM_WARN_STREAK = 1        # 1er pas en dépassement : avertissement
FIRM_REP_STREAK = 3         # 3 pas : la réputation trinque
FIRM_CUT_STREAK = 5         # 5 pas : réduction forcée


def firm_var_limit(player):
    """Limite de VaR (en M) du grade courant."""
    g = max(0, min(len(FIRM_VAR_LIMITS_M) - 1,
                   getattr(player, "grade_index", 0)))
    return FIRM_VAR_LIMITS_M[g]


def firm_var_check(player, market, n=4000):
    """VaR courante vs limite du grade. {'var', 'limit', 'ratio', 'breach'}.
    VaR nulle (book vide) = jamais de breach."""
    limit = firm_var_limit(player)
    if not player.portfolio and not getattr(player, "bonds", None):
        return {"var": 0.0, "limit": limit, "ratio": 0.0, "breach": False}
    from core import risk
    var = risk.simulate(player, market, confidence=0.95, n=n)["var"]
    return {"var": var, "limit": limit, "ratio": var / limit if limit else 0.0,
            "breach": var > limit}


def firm_var_enforce(player, market):
    """Escalade de la firme (appelée chaque pas par advance_step) :
    renvoie None ou un évènement {'level': 'warn'|'rep'|'cut', 'var',
    'limit', 'cut_ticker', 'cut_qty'} pour notification. La réduction
    forcée vend 30 % de la plus grosse position action longue."""
    chk = firm_var_check(player, market)
    if not chk["breach"]:
        player.flags["firm_var_streak"] = 0
        return None
    streak = player.flags.get("firm_var_streak", 0) + 1
    player.flags["firm_var_streak"] = streak
    ev = {"var": chk["var"], "limit": chk["limit"], "level": "warn",
          "cut_ticker": None, "cut_qty": 0}
    if streak >= FIRM_CUT_STREAK:
        from core import portfolio as pf
        longs = [(tk, pos) for tk, pos in player.portfolio.items()
                 if pos["shares"] > 0]
        if longs:
            tk, pos = max(longs,
                          key=lambda x: x[1]["shares"]
                          * (market.price_of(x[0]) or 0.0))
            qty = max(1, int(pos["shares"] * 0.30))
            r = pf.sell(player, market, tk, qty)
            if r.get("ok"):
                ev.update({"level": "cut", "cut_ticker": tk, "cut_qty": qty})
                player.flags["firm_var_streak"] = 0
                return ev
        ev["level"] = "rep"          # rien à couper côté actions : sanction
    elif streak >= FIRM_REP_STREAK:
        ev["level"] = "rep"
    if ev["level"] == "rep":
        from core.i18n import get_lang
        reason = ("Firm VaR limit breach" if get_lang() == "en"
                  else "Dépassement de la limite de VaR de la firme")
        player.adjust_reputation(-3, reason=reason)
    return ev
