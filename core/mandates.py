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

from core import archetypes, tracks

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


def _extra_constraints(mandate_type, rng):
    """Génère les contraintes supplémentaires (item 18) propres à un type de
    mandat. Retourne un dict de champs à fusionner dans l'offre."""
    if mandate_type == "income":
        return {"target_yield": round(rng.uniform(2.5, 5.0), 2),
                "min_liquidity": round(rng.uniform(5.0, 15.0), 1)}
    if mandate_type == "low_vol":
        return {"max_drawdown": round(rng.uniform(8.0, 15.0), 1)}
    if mandate_type == "inflation_hedge":
        return {"max_duration": round(rng.uniform(3.0, 6.0), 1)}
    if mandate_type == "esg":
        return {"excluded_sectors": list(ESG_EXCLUDED_SECTORS)}
    if mandate_type == "growth":
        return {"max_tracking_error": round(rng.uniform(12.0, 18.0), 1)}
    if mandate_type == "value":
        return {"max_tracking_error": round(rng.uniform(5.0, 10.0), 1)}
    if mandate_type == "capital_preservation":
        return {"max_drawdown": round(rng.uniform(3.0, 6.0), 1),
                "min_liquidity": round(rng.uniform(20.0, 35.0), 1)}
    if mandate_type == "absolute_return":
        return {"max_drawdown": round(rng.uniform(10.0, 18.0), 1)}
    return {}


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
    Le profil de risque (cf. core.career.risk_profile, dérivé du style de jeu
    plutôt que du grade) module les offres : les clients qui acceptent un
    bêta plus large paient une commission plus élevée à un gérant réputé
    tolérant au risque ; un profil prudent reçoit des offres plus standard.
    Le régime de marché courant (`market`, si fourni) module aussi la limite
    de risque et l'objectif visés (cf. _REGIME_MULT)."""
    from core import career
    rng = rng or random
    if player.grade_index < MIN_GRADE:
        return None
    if len(player.mandates) + len(player.mandate_offers) >= MAX_ACTIVE + 1:
        return None
    offer_mult = tracks.perk(player, "mandate_offer_mult") * archetypes.perk(player, "mandate_offer_mult")
    if rng.random() > OFFER_PROB * offer_mult:
        return None
    capital = round(rng.uniform(300_000, 1_200_000) * _scale(player.grade_index), -3)
    horizon = rng.choice([2, 3, 4])
    rmult = _REGIME_MULT.get(getattr(market, "regime", None), _REGIME_MULT["Calme"])
    target = round(rng.uniform(4.0, 7.0) * horizon * rmult["target"], 1)  # % cumulé sur l'horizon
    profile = career.risk_profile(player)
    if profile == "Risque élevé":
        max_beta = round(rng.choice([1.3, 1.5, 1.8, 2.0]), 2)
        fee_pct = rng.uniform(0.018, 0.035)
    elif profile == "Modéré":
        max_beta = round(rng.choice([1.15, 1.3, 1.5, 1.65]), 2)
        fee_pct = rng.uniform(0.014, 0.028)
    else:
        max_beta = round(rng.choice([1.0, 1.15, 1.3, 1.5]), 2)
        fee_pct = rng.uniform(0.010, 0.025)
    max_beta = round(max_beta * rmult["beta"], 2)
    fee_pct *= rmult["fee"]
    transformant = (player.grade_index >= TRANSFORMANT_MIN_GRADE
                     and rng.random() < TRANSFORMANT_PROB)
    if transformant:
        capital = round(capital * TRANSFORMANT_SCALE, -3)
    mandate_type = rng.choice(MANDATE_TYPES)
    offer = {
        "id": player.next_mandate_id,
        "client": rng.choice(CLIENTS),
        "capital": capital,
        "target_pct": target,
        "horizon": horizon,
        "max_beta": max_beta,
        "reward_cash": round(capital * fee_pct * tracks.perk(player, "mandate_reward_mult")
                             * archetypes.perk(player, "mandate_reward_mult"), 2),
        "reward_rep": rng.randint(6, 11) * (3 if transformant else 1),
        "penalty_rep": rng.randint(4, 8),
        "transformant": transformant,
        "type": mandate_type,
    }
    offer.update(_extra_constraints(mandate_type, rng))
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


def evaluate_due(player, market):
    """Évalue les mandats arrivés à échéance (au changement de trimestre).
    Applique récompenses/pénalités. Retourne la liste des résultats (chacun
    augmenté d'un champ `reason` pour le postmortem affiché dans l'UI)."""
    from core import career
    results = []
    still = []
    for m in player.mandates:
        if player.quarter < m["deadline_q"]:
            still.append(m)
            continue
        growth, beta = progress(player, market, m)
        check = check_constraints(player, market, m, growth, beta)
        ok = check["ok"]
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
            career.log(player, "crisis", _L(f"Mandat {m['client']} échoué ({reason})",
                                            f"Mandate {m['client']} failed ({reason})"))
        result = {"mandate": m, "ok": ok, "growth": growth, "beta": beta, "reason": reason,
                  "client": m["client"], "target_pct": m["target_pct"], "max_beta": m["max_beta"],
                  "reward_cash": m["reward_cash"], "reward_rep": m["reward_rep"],
                  "penalty_rep": m["penalty_rep"], "day": player.day, "quarter": player.quarter}
        results.append(result)
        player.mandate_history.append(result)
        if len(player.mandate_history) > MAX_HISTORY:
            player.mandate_history.pop(0)
    player.mandates = still
    return results
