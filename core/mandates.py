"""
mandates.py — Mandats clients (logique pure, sans pygame).

Un client confie un capital à gérer avec un OBJECTIF DE RENDEMENT sur un horizon
(en trimestres) et une LIMITE DE RISQUE (bêta max). À l'échéance :
  - succès si la valeur nette a crû d'au moins `target_pct` ET que le bêta du
    portefeuille respecte la limite → commission (% du capital) + réputation ;
  - échec sinon → perte de réputation (le client se détourne).

Disponible à partir d'un certain grade (on confie de l'argent aux seniors).

Structures (PlayerState) :
  mandate_offers : offres en attente d'acceptation
  mandates       : mandats acceptés en cours (avec snapshot de départ)
"""
import random

from core import archetypes, firms, tracks

MIN_GRADE = 6              # Vice President et au-delà (cf. unlocks)
MAX_ACTIVE = 2            # mandats simultanés
OFFER_PROB = 0.18         # proba d'une offre par tour (si place dispo)

# Mandat SOUVERAIN... non, ici : mandat TRANSFORMANT — un mandat hors-norme,
# réservé aux grades les plus seniors, qui peut transformer la firme (capital
# bien plus large, commission proportionnellement plus élevée). Rare par
# construction : un objectif de carrière à part, pas une opportunité courante.
TRANSFORMANT_MIN_GRADE = 9
TRANSFORMANT_PROB = 0.07   # proba, SI une offre est générée, qu'elle soit transformante
TRANSFORMANT_SCALE = 3.5

CLIENTS = [
    "Fonds de pension Helven", "Family Office Drax", "Assureur Norvik",
    "Fondation Maray", "Hedge Fund Cyrl", "Trésorerie Ostia", "Dotation Veles",
]

# ---------------------------------------------------------------------------
# PROFILS CLIENTS (item 4 du plan) : QUI est le client, par opposition au
# type de mandat (income/low_vol/esg/...) qui décrit le STYLE d'investissement
# visé. Un profil client a une identité propre (noms dédiés), une préférence
# pondérée pour certains types de mandat, des contraintes structurellement
# plus ou moins serrées (drawdown/duration/tracking error/liquidité — cf.
# core.alm pour l'intuition duration-matching d'un assureur/fonds de pension),
# un appétit pour le bêta, un horizon typique et un multiplicateur de
# récompense/pénalité cohérent avec sa tolérance au risque. Cette dimension
# compose avec (ne duplique pas) les perks d'archétype `mandate_offer_mult`/
# `mandate_reward_mult` (core.archetypes) : le profil influence QUEL mandat et
# QUELLES contraintes sont générées, les perks d'archétype restent un facteur
# multiplicatif appliqué par-dessus sur la fréquence/récompense globales.
CLIENT_PROFILES = [
    {
        "key": "assureur",
        "label": ("Assureur", "Insurer"),
        "names": ["Assureur Norvik", "Assurance Velmont", "Compagnie Hosk Vie"],
        "desc": ("Passif long et réglementé : duration-matching strict, faible "
                 "volatilité, drawdown très limité.",
                 "Long, regulated liabilities: strict duration-matching, low "
                 "volatility, very limited drawdown."),
        "type_weights": {"income": 3, "low_vol": 3, "capital_preservation": 2,
                          "inflation_hedge": 1},
        "horizon_choices": [3, 4],
        "beta_mult": 0.65,
        "drawdown_mult": 0.55,
        "duration_target": (4.0, 7.0),   # duration-matching : fenêtre resserrée autour d'une cible longue
        "tracking_error_mult": 0.6,
        "liquidity_mult": 1.3,
        "fee_mult": 0.85,
        "reward_rep_mult": 0.9,
        "penalty_rep_mult": 1.5,         # un assureur sanctionne durement un dépassement de contrainte
        "strict": True,                  # résilie le mandat dès qu'une contrainte casse, sans attendre l'échéance
    },
    {
        "key": "pension",
        "label": ("Fonds de pension", "Pension fund"),
        "names": ["Fonds de pension Helven", "Caisse de retraite Surin",
                  "Fonds de pension Adrel"],
        "desc": ("Passif long mais davantage de marge de croissance que "
                 "l'assureur : duration longue, tolérance au bêta modérée.",
                 "Long liabilities but more growth room than an insurer: "
                 "long duration, moderate beta tolerance."),
        "type_weights": {"income": 2, "growth": 2, "inflation_hedge": 2,
                          "low_vol": 1, "value": 1},
        "horizon_choices": [3, 4],
        "beta_mult": 0.85,
        "drawdown_mult": 0.75,
        "duration_target": (3.5, 6.5),
        "tracking_error_mult": 0.8,
        "liquidity_mult": 1.0,
        "fee_mult": 0.95,
        "reward_rep_mult": 1.0,
        "penalty_rep_mult": 1.2,
    },
    {
        "key": "family_office",
        "label": ("Family office", "Family office"),
        "names": ["Family Office Drax", "Family Office Sennel", "Maison Korvain"],
        "desc": ("Mandat large et flexible, mais soucieux de préserver le "
                 "capital sur plusieurs générations.",
                 "Broad, flexible mandate, but focused on preserving capital "
                 "across generations."),
        "type_weights": {"capital_preservation": 2, "value": 2, "esg": 2,
                          "growth": 1, "absolute_return": 1},
        "horizon_choices": [2, 3, 4],
        "beta_mult": 1.0,
        "drawdown_mult": 1.0,
        "duration_target": None,
        "tracking_error_mult": 1.1,
        "liquidity_mult": 0.9,
        "fee_mult": 1.0,
        "reward_rep_mult": 1.0,
        "penalty_rep_mult": 1.0,
    },
    {
        "key": "opportuniste",
        "label": ("Client opportuniste", "Opportunistic client"),
        "names": ["Hedge Fund Cyrl", "Trésorerie Ostia", "Pool Spéculatif Renn"],
        "desc": ("Horizon court, appétit au risque élevé : paie davantage pour "
                 "un bêta et une performance absolue ambitieux.",
                 "Short horizon, high risk appetite: pays more for ambitious "
                 "beta and absolute performance."),
        "type_weights": {"absolute_return": 3, "growth": 3, "value": 1},
        "horizon_choices": [2, 3],
        "beta_mult": 1.35,
        "drawdown_mult": 1.6,
        "duration_target": None,
        "tracking_error_mult": 1.6,
        "liquidity_mult": 0.6,
        "fee_mult": 1.3,
        "reward_rep_mult": 1.25,
        "penalty_rep_mult": 0.8,        # tolérant : accepte le risque qu'il a lui-même demandé
    },
    {
        "key": "institutionnel_prudent",
        "label": ("Institutionnel prudent", "Conservative institutional"),
        "names": ["Fondation Maray", "Dotation Veles", "Trésorerie d'État Korvin"],
        "desc": ("Tracking error et drawdown très contraints : diversification "
                 "conservatrice avant tout.",
                 "Very constrained tracking error and drawdown: conservative "
                 "diversification above all."),
        "type_weights": {"low_vol": 3, "value": 2, "capital_preservation": 2,
                          "esg": 1},
        "horizon_choices": [2, 3, 4],
        "beta_mult": 0.75,
        "drawdown_mult": 0.6,
        "duration_target": None,
        "tracking_error_mult": 0.5,
        "liquidity_mult": 1.1,
        "fee_mult": 0.9,
        "reward_rep_mult": 0.95,
        "penalty_rep_mult": 1.4,
        "strict": True,                  # même logique de résiliation anticipée que l'assureur
    },
]

_PROFILE_BY_KEY = {p["key"]: p for p in CLIENT_PROFILES}


def profile_label(profile_key):
    p = _PROFILE_BY_KEY.get(profile_key)
    return _L(*p["label"]) if p else profile_key


def profile_desc(profile_key):
    p = _PROFILE_BY_KEY.get(profile_key)
    return _L(*p["desc"]) if p else ""


def _pick_profile(rng):
    return rng.choice(CLIENT_PROFILES)


def _pick_type_for_profile(profile, rng):
    """Tire un type de mandat pondéré selon les préférences du profil client.
    Les types absents de `type_weights` restent tirables avec un poids
    minimal (1) pour ne jamais exclure totalement un type — un assureur reste
    rare en growth, mais pas strictement impossible."""
    weights = [profile["type_weights"].get(t, 1) for t in MANDATE_TYPES]
    return rng.choices(MANDATE_TYPES, weights=weights, k=1)[0]

# Types de mandat (item 17) : chacun ajoute, en plus de l'objectif de
# rendement et du bêta max (toujours présents), une ou des contraintes
# RÉALISTES SUPPLÉMENTAIRES (item 18) générées dans `maybe_offer` et
# vérifiées en continu/à l'échéance par `check_constraints`. Une contrainte
# absente d'un mandat (clé non présente) n'est jamais vérifiée — ce qui rend
# l'ajout de nouveaux types rétrocompatible avec les mandats déjà acceptés
# (saves existantes) et les mandats minimalistes utilisés en test.
MANDATE_TYPES = ["income", "low_vol", "inflation_hedge", "esg", "growth",
                  "value", "capital_preservation", "absolute_return"]

_TYPE_LABELS = {
    "income": ("Revenu", "Income"),
    "low_vol": ("Faible volatilité", "Low volatility"),
    "inflation_hedge": ("Couverture inflation", "Inflation hedge"),
    "esg": ("ESG", "ESG"),
    "growth": ("Croissance", "Growth"),
    "value": ("Valeur", "Value"),
    "capital_preservation": ("Préservation du capital", "Capital preservation"),
    "absolute_return": ("Performance absolue", "Absolute return"),
}

# Secteurs exclus pour un mandat ESG (cohérent avec la construction des ETF
# ESG existants, cf. core/etfs.py).
ESG_EXCLUDED_SECTORS = ["Energie"]


def type_label(mandate_type):
    return _L(*_TYPE_LABELS.get(mandate_type, (mandate_type, mandate_type)))


def _extra_constraints(mandate_type, rng, profile=None):
    """Génère les contraintes supplémentaires (item 18) propres à un type de
    mandat. Retourne un dict de champs à fusionner dans l'offre.
    Si `profile` (dict CLIENT_PROFILES) est fourni, les contraintes générées
    sont resserrées/desserrées par les multiplicateurs du profil — c'est CE
    QUI fait qu'un assureur et un client opportuniste, sur le MÊME type de
    mandat (ex. low_vol), n'offrent pas les mêmes limites : le type décrit le
    style visé, le profil décrit la rigueur avec laquelle le client l'exige."""
    dd_mult = profile["drawdown_mult"] if profile else 1.0
    te_mult = profile["tracking_error_mult"] if profile else 1.0
    liq_mult = profile["liquidity_mult"] if profile else 1.0
    out = {}
    if mandate_type == "income":
        out = {"target_yield": round(rng.uniform(2.5, 5.0), 2),
                "min_liquidity": round(rng.uniform(5.0, 15.0) * liq_mult, 1)}
    elif mandate_type == "low_vol":
        out = {"max_drawdown": round(rng.uniform(8.0, 15.0) * dd_mult, 1)}
    elif mandate_type == "inflation_hedge":
        out = {"max_duration": round(rng.uniform(3.0, 6.0), 1)}
    elif mandate_type == "esg":
        out = {"excluded_sectors": list(ESG_EXCLUDED_SECTORS)}
    elif mandate_type == "growth":
        out = {"max_tracking_error": round(rng.uniform(12.0, 18.0) * te_mult, 1)}
    elif mandate_type == "value":
        out = {"max_tracking_error": round(rng.uniform(5.0, 10.0) * te_mult, 1)}
    elif mandate_type == "capital_preservation":
        out = {"max_drawdown": round(rng.uniform(3.0, 6.0) * dd_mult, 1),
                "min_liquidity": round(rng.uniform(20.0, 35.0) * liq_mult, 1)}
    elif mandate_type == "absolute_return":
        out = {"max_drawdown": round(rng.uniform(10.0, 18.0) * dd_mult, 1)}
    # duration-matching (assureur/fonds de pension, cf. core.alm pour
    # l'intuition) : une fenêtre de duration cible resserrée autour d'une
    # valeur longue, indépendante du type de mandat — c'est une contrainte
    # STRUCTURELLE du profil, pas du style d'investissement visé.
    if profile and profile.get("duration_target") and "max_duration" not in out:
        lo, hi = profile["duration_target"]
        out["max_duration"] = round(rng.uniform(lo, hi), 1)
    return out


def _scale(grade):
    return 1.0 + 0.6 * grade


# Modulation par régime de marché courant (cf. core.market.REGIMES) : en phase
# de Récession/Volatil, les clients resserrent la limite de risque tolérée
# (mais paient plus pour la prudence) et visent des objectifs plus modestes ;
# en Expansion, ils tolèrent davantage de bêta et visent plus haut. Donne du
# sens aux mandats de risk management au-delà du seul profil du joueur.
_REGIME_MULT = {
    "Expansion": {"beta": 1.10, "fee": 0.90, "target": 1.15},
    "Calme":     {"beta": 1.00, "fee": 1.00, "target": 1.00},
    "Volatil":   {"beta": 0.85, "fee": 1.15, "target": 0.85},
    "Récession": {"beta": 0.70, "fee": 1.30, "target": 0.65},
}


def maybe_offer(player, rng=None, market=None):
    """Génère éventuellement une offre de mandat. Retourne l'offre ou None.
    Le profil de RISQUE du joueur (cf. core.career.risk_profile, dérivé du
    style de jeu plutôt que du grade) module l'ambition de l'offre (bêta max,
    commission) ; le profil CLIENT (cf. CLIENT_PROFILES, item 4 — qui est le
    client : assureur/fonds de pension/family office/opportuniste/
    institutionnel prudent) module en plus QUEL type de mandat est proposé et
    À QUEL POINT ses contraintes (drawdown/duration/tracking error/liquidité)
    sont serrées, ainsi que l'horizon typique et la sensibilité récompense/
    pénalité. Le régime de marché courant (`market`, si fourni) module aussi
    la limite de risque et l'objectif visés (cf. _REGIME_MULT)."""
    from core import career
    rng = rng or random
    if player.grade_index < MIN_GRADE:
        return None
    if len(player.mandates) + len(player.mandate_offers) >= MAX_ACTIVE + 1:
        return None
    offer_mult = (tracks.perk(player, "mandate_offer_mult") * archetypes.perk(player, "mandate_offer_mult")
                  * firms.perk(player, "mandate_offer_mult"))
    if rng.random() > OFFER_PROB * offer_mult:
        return None
    client_profile = _pick_profile(rng)
    capital = round(rng.uniform(300_000, 1_200_000) * _scale(player.grade_index), -3)
    horizon = rng.choice(client_profile["horizon_choices"])
    rmult = _REGIME_MULT.get(getattr(market, "regime", None), _REGIME_MULT["Calme"])
    target = round(rng.uniform(4.0, 7.0) * horizon * rmult["target"], 1)  # % cumulé sur l'horizon
    risk_profile = career.risk_profile(player)
    if risk_profile == "Risque élevé":
        max_beta = round(rng.choice([1.3, 1.5, 1.8, 2.0]), 2)
        fee_pct = rng.uniform(0.018, 0.035)
    elif risk_profile == "Modéré":
        max_beta = round(rng.choice([1.15, 1.3, 1.5, 1.65]), 2)
        fee_pct = rng.uniform(0.014, 0.028)
    else:
        max_beta = round(rng.choice([1.0, 1.15, 1.3, 1.5]), 2)
        fee_pct = rng.uniform(0.010, 0.025)
    max_beta = round(max_beta * rmult["beta"] * client_profile["beta_mult"], 2)
    fee_pct *= rmult["fee"] * client_profile["fee_mult"]
    transformant = (player.grade_index >= TRANSFORMANT_MIN_GRADE
                     and rng.random() < TRANSFORMANT_PROB)
    if transformant:
        capital = round(capital * TRANSFORMANT_SCALE, -3)
    mandate_type = _pick_type_for_profile(client_profile, rng)
    offer = {
        "id": player.next_mandate_id,
        "client": rng.choice(client_profile["names"]),
        "client_profile": client_profile["key"],
        "capital": capital,
        "target_pct": target,
        "horizon": horizon,
        "max_beta": max_beta,
        "reward_cash": round(capital * fee_pct * tracks.perk(player, "mandate_reward_mult")
                             * archetypes.perk(player, "mandate_reward_mult")
                             * firms.perk(player, "mandate_reward_mult"), 2),
        "reward_rep": round(rng.randint(6, 11) * (3 if transformant else 1)
                            * client_profile["reward_rep_mult"]),
        "penalty_rep": round(rng.randint(4, 8) * client_profile["penalty_rep_mult"]),
        "transformant": transformant,
        "type": mandate_type,
    }
    offer.update(_extra_constraints(mandate_type, rng, client_profile))
    player.next_mandate_id += 1
    player.mandate_offers.append(offer)
    return offer


def accept(player, mandate_id, market):
    """Accepte une offre : la déplace en mandat actif avec un snapshot de départ."""
    from core import portfolio
    offer = next((o for o in player.mandate_offers if o["id"] == mandate_id), None)
    if offer is None:
        return None
    if len(player.mandates) >= MAX_ACTIVE:
        return "full"
    player.mandate_offers = [o for o in player.mandate_offers if o["id"] != mandate_id]
    offer = dict(offer)
    offer["start_nw"] = portfolio.net_worth(player, market)
    offer["deadline_q"] = player.quarter + offer["horizon"]
    player.mandates.append(offer)
    return offer


def decline(player, mandate_id):
    before = len(player.mandate_offers)
    player.mandate_offers = [o for o in player.mandate_offers if o["id"] != mandate_id]
    return len(player.mandate_offers) < before


def progress(player, market, m):
    """Retourne (croissance_%, bêta_courant) d'un mandat actif."""
    from core import portfolio
    nw = portfolio.net_worth(player, market)
    growth = (nw / m["start_nw"] - 1) * 100 if m.get("start_nw") else 0.0
    return growth, portfolio.portfolio_beta(player, market)


MAX_HISTORY = 12   # nb de postmortems conservés pour affichage (scene_mandates)


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante du jeu."""
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


def _avg_duration(player, market):
    """Duration modifiée moyenne (pondérée par la valeur) du book obligataire."""
    if not getattr(player, "bonds", None):
        return 0.0
    from core import bonds as bonds_mod
    hold = bonds_mod.holdings(player, market)
    total = sum(h["value"] for h in hold)
    return (sum(h["value"] * h["mod_duration"] for h in hold) / total) if total > 0 else 0.0


def _portfolio_yield(player, market):
    """Rendement courant du book (%) : moyenne pondérée du dividend yield des
    actions longues et du YTM des obligations."""
    comp = {c["ticker"]: c for c in market.companies}
    total_value, total_yield = 0.0, 0.0
    for t, pos in player.portfolio.items():
        if pos["shares"] <= 0:
            continue
        price = market.price_of(t)
        c = comp.get(t)
        if price is None or not c:
            continue
        val = price * pos["shares"]
        total_value += val
        total_yield += val * c.get("div_yield", 0.0) * 100.0
    if getattr(player, "bonds", None):
        from core import bonds as bonds_mod
        for h in bonds_mod.holdings(player, market):
            total_value += h["value"]
            total_yield += h["value"] * h["ytm"] * 100.0
    return (total_yield / total_value) if total_value > 0 else 0.0


def _liquidity_pct(player, market):
    """Part de cash dans la valeur nette (%)."""
    from core import portfolio
    nw = portfolio.net_worth(player, market)
    return (player.cash / nw * 100.0) if nw > 0 else 0.0


def check_constraints(player, market, m, growth=None, beta=None):
    """Vérifie TOUTES les contraintes d'un mandat (item 18) : l'objectif de
    rendement et le bêta max sont toujours vérifiés ; les contraintes
    supplémentaires (drawdown max, tracking error max, duration max,
    rendement cible, liquidité minimale) ne sont vérifiées QUE si la clé
    correspondante est présente sur le mandat — ce qui rend la fonction
    rétrocompatible avec les mandats antérieurs à cette extension (saves) et
    les mandats minimalistes utilisés en test. Retourne
    {ok, breaches: [clés en échec], values: {...mesures courantes...}}."""
    if growth is None or beta is None:
        growth, beta = progress(player, market, m)
    breaches = []
    if growth < m["target_pct"]:
        breaches.append("target")
    if beta > m["max_beta"] + 0.01:
        breaches.append("beta")

    dd = te = avg_dur = yld = liq = None
    if m.get("max_drawdown") is not None:
        from core import risk as risk_mod
        dd = risk_mod.net_worth_drawdown(player) * 100.0
        if dd > m["max_drawdown"]:
            breaches.append("drawdown")
    if m.get("max_tracking_error") is not None:
        from core import analytics
        te = analytics.tracking_error(player, market)
        if te > m["max_tracking_error"]:
            breaches.append("tracking_error")
    if m.get("max_duration") is not None:
        avg_dur = _avg_duration(player, market)
        if avg_dur > m["max_duration"]:
            breaches.append("duration")
    if m.get("target_yield") is not None:
        yld = _portfolio_yield(player, market)
        if yld < m["target_yield"]:
            breaches.append("yield")
    if m.get("min_liquidity") is not None:
        liq = _liquidity_pct(player, market)
        if liq < m["min_liquidity"]:
            breaches.append("liquidity")

    return {"ok": not breaches, "breaches": breaches,
            "values": {"growth": growth, "beta": beta, "drawdown": dd,
                       "tracking_error": te, "duration": avg_dur,
                       "yield": yld, "liquidity": liq}}


_BREACH_MESSAGES = {
    "drawdown": lambda m, v: _L(f"Drawdown excessif : {v:.1f}% vs limite {m['max_drawdown']:.1f}%",
                                 f"Excess drawdown: {v:.1f}% vs limit {m['max_drawdown']:.1f}%"),
    "tracking_error": lambda m, v: _L(
        f"Tracking error excessive : {v:.1f}% vs limite {m['max_tracking_error']:.1f}%",
        f"Excess tracking error: {v:.1f}% vs limit {m['max_tracking_error']:.1f}%"),
    "duration": lambda m, v: _L(f"Duration trop élevée : {v:.1f} vs limite {m['max_duration']:.1f}",
                                 f"Duration too high: {v:.1f} vs limit {m['max_duration']:.1f}"),
    "yield": lambda m, v: _L(f"Rendement du book insuffisant : {v:.1f}% vs cible {m['target_yield']:.1f}%",
                              f"Portfolio yield too low: {v:.1f}% vs target {m['target_yield']:.1f}%"),
    "liquidity": lambda m, v: _L(f"Liquidité insuffisante : {v:.1f}% vs minimum {m['min_liquidity']:.1f}%",
                                  f"Liquidity too low: {v:.1f}% vs minimum {m['min_liquidity']:.1f}%"),
}


def failure_reason(m, growth, beta, extra=None):
    """Construit un message d'échec SPÉCIFIQUE (chiffré) plutôt qu'un « Échoué » générique.
    Un mandat peut échouer sur plusieurs critères à la fois. `extra`, si fourni,
    est le dict `values` retourné par `check_constraints` (contraintes
    supplémentaires du type de mandat, item 18) — optionnel et rétrocompatible
    avec les appels historiques à 3 arguments."""
    miss_target = growth < m["target_pct"]
    miss_risk = beta > m["max_beta"] + 0.01
    parts = []
    if miss_target:
        parts.append(_L(f"Rendement cible non atteint : {growth:+.1f}% vs objectif "
                         f"+{m['target_pct']:.1f}%",
                         f"Target return missed: {growth:+.1f}% vs target "
                         f"+{m['target_pct']:.1f}%"))
    if miss_risk:
        parts.append(_L(f"Risque dépassé : bêta {beta:.2f} vs limite {m['max_beta']:.2f}",
                         f"Risk limit exceeded: beta {beta:.2f} vs limit {m['max_beta']:.2f}"))
    if extra:
        for key, fmt in _BREACH_MESSAGES.items():
            val = extra.get(key)
            limit_key = {"drawdown": "max_drawdown", "tracking_error": "max_tracking_error",
                         "duration": "max_duration", "yield": "target_yield",
                         "liquidity": "min_liquidity"}[key]
            if val is None or m.get(limit_key) is None:
                continue
            breached = (val < m[limit_key]) if key in ("yield", "liquidity") else (val > m[limit_key])
            if breached:
                parts.append(fmt(m, val))
    if not parts:
        parts.append(_L("Échoué", "Failed"))
    return " · ".join(parts)


def _is_strict(m):
    """Un mandat est « strict » (résiliation anticipée sur dépassement de
    contrainte, item 4) si son profil client (assureur, institutionnel
    prudent) l'exige. Absence de `client_profile` (mandats antérieurs à cette
    extension, saves, mandats minimalistes de test) => jamais strict, donc
    rétrocompatible : ces mandats ne sont évalués qu'à l'échéance comme avant."""
    profile = _PROFILE_BY_KEY.get(m.get("client_profile"))
    return bool(profile and profile.get("strict"))


def evaluate_due(player, market):
    """Évalue les mandats arrivés à échéance (au changement de trimestre) ET,
    pour les profils clients « stricts » (assureur, institutionnel prudent —
    item 4), résilie immédiatement tout mandat dont une contrainte est
    rompue AVANT l'échéance plutôt que d'attendre la fin de l'horizon : un
    assureur réglementé ne tolère pas un dérapage de duration/drawdown
    pendant plusieurs trimestres avant de réagir. Applique
    récompenses/pénalités. Retourne la liste des résultats (chacun augmenté
    d'un champ `reason` pour le postmortem affiché dans l'UI)."""
    from core import career
    results = []
    still = []
    for m in player.mandates:
        due = player.quarter >= m["deadline_q"]
        growth, beta = progress(player, market, m)
        check = check_constraints(player, market, m, growth, beta)
        early_break = (not due) and _is_strict(m) and not check["ok"] and bool(check["breaches"])
        if not due and not early_break:
            still.append(m)
            continue
        ok = check["ok"] and due
        if ok:
            player.adjust_cash(m["reward_cash"])
            player.adjust_reputation(m["reward_rep"])
            player.flags["mandates_won"] = player.flags.get("mandates_won", 0) + 1
            if m.get("transformant"):
                player.flags["mandates_transformant_won"] = (
                    player.flags.get("mandates_transformant_won", 0) + 1)
            reason = _L(f"Objectif atteint : {growth:+.1f}% (cible +{m['target_pct']:.1f}%), "
                        f"bêta {beta:.2f} sous la limite {m['max_beta']:.2f}.",
                        f"Target reached: {growth:+.1f}% (target +{m['target_pct']:.1f}%), "
                        f"beta {beta:.2f} under the limit {m['max_beta']:.2f}.")
            career.log(player, "deal", _L(f"Mandat {m['client']} réussi (+{growth:.1f}%)",
                                          f"Mandate {m['client']} succeeded (+{growth:.1f}%)"))
        else:
            player.adjust_reputation(-m["penalty_rep"])
            reason = failure_reason(m, growth, beta, check["values"])
            if early_break:
                reason = _L(f"Mandat résilié avant échéance par le client ({reason})",
                             f"Mandate terminated early by the client ({reason})")
                career.log(player, "crisis", _L(f"Mandat {m['client']} résilié par anticipation ({reason})",
                                                f"Mandate {m['client']} terminated early ({reason})"))
            else:
                career.log(player, "crisis", _L(f"Mandat {m['client']} échoué ({reason})",
                                                f"Mandate {m['client']} failed ({reason})"))
        result = {"mandate": m, "ok": ok, "growth": growth, "beta": beta, "reason": reason,
                  "client": m["client"], "target_pct": m["target_pct"], "max_beta": m["max_beta"],
                  "reward_cash": m["reward_cash"], "reward_rep": m["reward_rep"],
                  "penalty_rep": m["penalty_rep"], "day": player.day, "quarter": player.quarter,
                  "early_terminated": early_break}
        results.append(result)
        player.mandate_history.append(result)
        if len(player.mandate_history) > MAX_HISTORY:
            player.mandate_history.pop(0)
    player.mandates = still
    return results
