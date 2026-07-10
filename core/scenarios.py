"""
scenarios.py — Crises et booms déclenchés dans le temps (logique pure).

Chaque scénario applique un choc de facteurs au marché (via core.market.Crisis)
sur plusieurs pas : il se répercute donc sur les indices ET sur le portefeuille
du joueur. Inspirés de cas réels (renommés/fictionnalisés).

maybe_trigger() est appelé à chaque tour : faible probabilité de déclencher un
scénario, pondéré. Retourne une description narrative (ou None).

Profondeur ajoutée par rapport à la version d'origine (chocs fixes uniformes) :
  - SÉVÉRITÉ variable : chaque scénario définit une plage [sev_min, sev_max]
    (multiplicateur appliqué à ses chocs world/sectors/vol) ; la sévérité
    réellement tirée (via le rng SEEDÉ, donc déterministe pour une seed donnée)
    fait varier l'intensité d'une occurrence à l'autre — une « crise bancaire
    régionale » peut être un simple accès de nervosité ou un vrai décrochage ;
  - RÉGION ciblée : les scénarios marqués `regional=True` tirent une région
    parmi `region_pool` (sous-ensemble de core.config.CONTINENTS / les régions
    de marché) au lieu d'appliquer un choc générique ou fixe ;
  - NARRATION précise : le texte de l'événement (`story`) intègre la sévérité
    réelle (qualifiée en mots : légère/modérée/sévère...) et la région tirée,
    pour que le joueur comprenne ce qui s'est exactement passé.

Compatibilité : les anciens champs (world/sectors/regions/vol fixes) restent
les valeurs par défaut quand sev_min==sev_max==1.0 et regional=False ; aucun
scénario existant ne change de comportement moyen.
"""
import random

from core.market import Crisis

# (id, nom affiché, kind, steps, world, regions{}, sectors{}, vol_mult, poids, récit)
# sev_min/sev_max : plage du multiplicateur de sévérité tiré par occurrence
#   (1.0 = magnitude de référence ci-dessous). regional/region_pool : si fourni,
#   un choc régional supplémentaire est tiré parmi region_pool (sinon le scénario
#   reste mondial/sectoriel comme avant).
SCENARIOS = [
    {"id": "krach", "name": "Krach systémique", "kind": "bad", "steps": 6,
     "world": -0.05, "sectors": {"Finance": -0.06, "Immobilier": -0.04}, "vol": 2.6,
     "weight": 2, "sev_min": 0.6, "sev_max": 1.6,
     "story": "Une cascade de défauts gèle le crédit interbancaire — réminiscence de 2008."},
    {"id": "taux", "name": "Choc de taux", "kind": "bad", "steps": 4,
     "world": -0.025, "sectors": {"Finance": -0.045, "Immobilier": -0.035, "Utilities": -0.02},
     "vol": 1.8, "weight": 3, "sev_min": 0.5, "sev_max": 1.5,
     "story": "Une remontée brutale des taux fragilise banques régionales et immobilier (type 2023)."},
    {"id": "tornade", "name": "Catastrophe agricole", "kind": "bad", "steps": 3,
     "world": 0.0, "sectors": {"Agro": -0.07, "Conso": -0.02}, "vol": 1.4,
     "weight": 3, "sev_min": 0.6, "sev_max": 1.4,
     "story": "Tornades et sécheresses ravagent les récoltes : les valeurs agroalimentaires plongent."},
    {"id": "techbust", "name": "Éclatement bulle tech", "kind": "bad", "steps": 5,
     "world": -0.02, "sectors": {"Tech": -0.05, "Semicon": -0.06}, "vol": 2.0,
     "weight": 2, "sev_min": 0.5, "sev_max": 1.7,
     "story": "Les multiples de la tech se dégonflent violemment après des résultats décevants."},
    {"id": "energie", "name": "Choc énergétique", "kind": "bad", "steps": 4,
     "world": -0.015, "sectors": {"Energie": -0.05, "Industrie": -0.03}, "vol": 1.6,
     "weight": 2, "sev_min": 0.6, "sev_max": 1.5,
     "story": "Une rupture d'approvisionnement fait flamber puis dévisser le secteur énergie."},
    {"id": "asia", "name": "Tensions géopolitiques (Asie)", "kind": "bad", "steps": 4,
     "regions": {"Asia": -0.05}, "sectors": {"Semicon": -0.03}, "vol": 1.8,
     "weight": 2, "sev_min": 0.5, "sev_max": 1.6,
     "story": "Des tensions régionales en Asie déclenchent une fuite vers la qualité."},
    # booms (bonnes nouvelles)
    {"id": "techboom", "name": "Boom technologique", "kind": "good", "steps": 4,
     "world": 0.012, "sectors": {"Tech": 0.045, "Semicon": 0.05}, "vol": 1.3,
     "weight": 3, "sev_min": 0.6, "sev_max": 1.5,
     "story": "Une percée en IA propulse la tech et les semi-conducteurs."},
    {"id": "relance", "name": "Plan de relance mondial", "kind": "good", "steps": 5,
     "world": 0.02, "sectors": {"Industrie": 0.03, "Materiaux": 0.03}, "vol": 1.3,
     "weight": 2, "sev_min": 0.6, "sev_max": 1.4,
     "story": "Un vaste plan d'investissement public dope l'industrie et les matériaux."},
    {"id": "pandemie", "name": "Choc sanitaire", "kind": "bad", "steps": 6,
     "world": -0.035, "sectors": {"Sante": 0.03, "Conso": -0.03, "Industrie": -0.03},
     "vol": 2.2, "weight": 2, "sev_min": 0.5, "sev_max": 1.7,
     "story": "Une crise sanitaire paralyse l'activité ; la santé surperforme, le reste plonge."},
    {"id": "credit", "name": "Crise bancaire régionale", "kind": "bad", "steps": 4,
     "world": -0.006, "regions": {}, "sectors": {"Finance": -0.05, "Immobilier": -0.04},
     "vol": 1.7, "weight": 2, "sev_min": 0.4, "sev_max": 1.8,
     "regional": True, "region_extra": -0.018,
     "story": "Les conditions de crédit se durcissent brutalement dans une région ; banques et immobilier souffrent."},
    {"id": "ipo", "name": "Vague d'introductions en bourse", "kind": "good", "steps": 4,
     "world": 0.015, "sectors": {"Tech": 0.03, "Finance": 0.025}, "vol": 1.3,
     "weight": 2, "sev_min": 0.6, "sev_max": 1.4,
     "story": "Un marché euphorique relance les IPO ; tech et finance en profitent."},
    {"id": "matieres", "name": "Flambée des matières premières", "kind": "bad", "steps": 4,
     "world": -0.01, "sectors": {"Materiaux": 0.04, "Energie": 0.03, "Industrie": -0.03,
                                 "Conso": -0.02}, "vol": 1.6, "weight": 2,
     "sev_min": 0.6, "sev_max": 1.5,
     "story": "Les cours des matières premières s'envolent : gagnants et perdants sectoriels."},
    # crises ciblées (purement sectorielles/régionales, world=0.0) — opportunités
    # de short/hedge chirurgicales sans choc macro global.
    {"id": "scandale_finance", "name": "Scandale comptable bancaire", "kind": "bad", "steps": 3,
     "world": 0.0, "sectors": {"Finance": -0.06}, "vol": 1.8,
     "weight": 2, "sev_min": 0.5, "sev_max": 1.6,
     "story": "Un scandale de manipulation comptable éclate dans une grande banque : "
              "le secteur Finance dévisse sur fond de défiance des investisseurs."},
    {"id": "antitrust_tech", "name": "Amende antitrust tech", "kind": "bad", "steps": 3,
     "world": 0.0, "sectors": {"Tech": -0.045}, "vol": 1.6,
     "weight": 2, "sev_min": 0.5, "sev_max": 1.5,
     "story": "Les régulateurs infligent une amende record pour abus de position dominante : "
              "le secteur Tech encaisse le choc réglementaire."},
    {"id": "immo_asie", "name": "Crise immobilière (Asie)", "kind": "bad", "steps": 5,
     "world": 0.0, "regions": {"Asia": -0.045}, "sectors": {"Immobilier": -0.035}, "vol": 1.8,
     "weight": 2, "sev_min": 0.5, "sev_max": 1.6,
     "story": "Un promoteur surendetté fait défaut en Asie : la crise immobilière régionale "
              "se propage aux valeurs du secteur."},
    {"id": "immo_europe", "name": "Crise immobilière (Europe)", "kind": "bad", "steps": 5,
     "world": 0.0, "regions": {"Europe": -0.04}, "sectors": {"Immobilier": -0.03}, "vol": 1.7,
     "weight": 2, "sev_min": 0.5, "sev_max": 1.6,
     "story": "La hausse du coût du crédit fait éclater une bulle immobilière en Europe, "
              "fragilisant promoteurs et foncières de la région."},
    {"id": "fx_emergent", "name": "Crise de change (marché émergent)", "kind": "bad", "steps": 4,
     "world": 0.0, "regions": {}, "sectors": {}, "vol": 1.9,
     "weight": 2, "sev_min": 0.5, "sev_max": 1.7,
     "regional": True, "region_pool": ["Am.Sud", "Afrique"], "region_extra": -0.05,
     "story": "Une dévaluation brutale frappe une devise émergente, asséchant les flux de "
              "capitaux vers la région."},
    {"id": "sante_sectoriel", "name": "Rappel sanitaire massif", "kind": "bad", "steps": 4,
     "world": 0.0, "sectors": {"Sante": -0.05}, "vol": 1.7,
     "weight": 2, "sev_min": 0.5, "sev_max": 1.6,
     "story": "Un rappel de produits à grande échelle révèle des défauts de fabrication : "
              "le secteur Santé chute sur des craintes de litiges en cascade."},
    # ------------------------------------------------------------------
    # SCÉNARIOS HISTORIQUES — calibrés sur l'ARC réel de 4 crises célèbres
    # (poids 0 : JAMAIS tirés par maybe_trigger, uniquement déclenchables à la
    # demande via CRISIS <id> en mode bac à sable, cf. scene_terminal_career.py
    # ::_cmd_crisis — « étudier » une crise précise plutôt que la subir au
    # hasard). sev_min == sev_max == 1.0 : reproductibles à l'identique.
    {"id": "hist1987", "name": "Krach de 1987 (« Black Monday »)", "kind": "bad",
     "steps": 2, "world": -0.11, "sectors": {"Finance": -0.02}, "vol": 3.6,
     "weight": 0, "sev_min": 1.0, "sev_max": 1.0, "historic": True,
     "story": "Un krach éclair mondial sans déclencheur macro clair — le trading "
              "programmé amplifie la panique en quelques séances (19 octobre 1987)."},
    {"id": "hist2000", "name": "Éclatement de la bulle Internet (2000)", "kind": "bad",
     "steps": 16, "world": -0.006, "sectors": {"Tech": -0.032, "Semicon": -0.038},
     "vol": 2.1, "weight": 0, "sev_min": 1.0, "sev_max": 1.0, "historic": True,
     "story": "Les valorisations spéculatives de la tech se dégonflent sur une longue "
              "période, sans krach unique mais sans répit non plus (2000-2002)."},
    {"id": "hist2008", "name": "Crise financière mondiale (2008)", "kind": "bad",
     "steps": 10, "world": -0.042, "sectors": {"Finance": -0.058, "Immobilier": -0.05},
     "vol": 2.9, "weight": 0, "sev_min": 1.0, "sev_max": 1.0, "historic": True,
     "story": "L'effondrement du crédit hypothécaire gèle le système financier mondial : "
              "un choc long et profond, centré sur banques et immobilier."},
    {"id": "hist2020", "name": "Krach sanitaire (COVID, 2020)", "kind": "bad",
     "steps": 3, "world": -0.075, "sectors": {"Energie": -0.03, "Conso": -0.02},
     "vol": 3.4, "weight": 0, "sev_min": 1.0, "sev_max": 1.0, "historic": True,
     "story": "L'arrêt brutal de l'économie mondiale déclenche le krach le plus rapide "
              "de l'histoire — aussi bref que violent (février-mars 2020)."},
]

# Sous-ensemble de SCENARIOS marqué "historic" — les 4 scénarios ci-dessus,
# jamais tirés au hasard (weight=0). Exposé pour l'UI (liste dédiée, ex.
# commande CRISIS) sans avoir à filtrer SCENARIOS à chaque appel.
HISTORIC_IDS = [s["id"] for s in SCENARIOS if s.get("historic")]

TRIGGER_PROBABILITY = 0.06   # par tour

# régions éligibles par défaut pour un scénario "regional" qui ne précise pas
# region_pool — toutes les régions connues du marché.
_DEFAULT_REGION_POOL = ["USA", "Europe", "Asia", "Am.Nord", "Am.Sud", "Afrique", "Océanie"]

# ---- contagion entre crises -------------------------------------------------
# Quand un scénario de cette table se déclenche, les scénarios listés voient
# leur poids de tirage temporairement amplifié (cf. CONTAGION_BOOST, pendant
# CONTAGION_STEPS tours) : modélise le fait qu'une crise bancaire rend une
# crise de change ou un choc de taux plus probable peu après, etc.
CONTAGION = {
    "krach": ["credit", "taux", "scandale_finance"],
    "credit": ["krach", "fx_emergent", "taux"],
    "taux": ["credit", "immo_europe", "immo_asie"],
    "asia": ["fx_emergent", "immo_asie"],
    "immo_asie": ["asia", "credit"],
    "immo_europe": ["credit", "taux"],
    "fx_emergent": ["credit", "asia"],
    "energie": ["matieres"],
    "matieres": ["energie"],
    "pandemie": ["krach", "techbust"],
    "techbust": ["pandemie"],
}
CONTAGION_BOOST = 2.2
CONTAGION_STEPS = 6

# ---- signaux avant-crise -----------------------------------------------------
# Lorsque la tension macro est élevée mais qu'aucun scénario ne se déclenche
# ce tour, probabilité de pousser un avertissement ambigu (ne révèle ni le
# scénario exact ni le moment) : récompense la couverture proactive plutôt que
# la seule chance.
WARNING_STRESS_THRESHOLD = 1.6
WARNING_PROBABILITY = 0.3
WARNING_COOLDOWN_STEPS = 6

_WARNING_SIGNS_FR = [
    "Les spreads de crédit et la volatilité implicite grimpent sans déclencheur "
    "clair — les desks de couverture s'agitent.",
    "Plusieurs indicateurs avancés (courbe des taux, spreads HY, chômage) "
    "clignotent à l'orange. Rien d'imminent, mais la prudence est de mise.",
    "Le climat macro se tend nettement : les gérants prudents renforcent déjà "
    "leurs couvertures par précaution.",
]
_WARNING_SIGNS_EN = [
    "Credit spreads and implied volatility are creeping up with no clear "
    "trigger — hedging desks are getting nervous.",
    "Several leading indicators (yield curve, HY spreads, unemployment) are "
    "flashing amber. Nothing imminent, but caution is warranted.",
    "The macro backdrop is tightening noticeably: cautious managers are "
    "already reinforcing their hedges as a precaution.",
]


# ---- accès localisé (FR / EN) ----------------------------------------------
from data.scenarios_en import SCENARIOS_EN


def _localize_scenario(s):
    e = SCENARIOS_EN.get(s["id"])
    if not e:
        return s
    out = dict(s)
    out["name"] = e.get("name", s["name"])
    out["story"] = e.get("story", s["story"])
    return out


def localized(lang):
    """Renvoie la liste de scénarios dans la langue demandée."""
    if lang == "en":
        return [_localize_scenario(s) for s in SCENARIOS]
    return SCENARIOS


def _severity_label(sev, lang="fr"):
    """Qualificatif de la sévérité tirée, pour la narration."""
    if lang == "en":
        if sev < 0.7:
            return "light"
        if sev < 1.0:
            return "moderate"
        if sev < 1.35:
            return "marked"
        return "severe"
    if sev < 0.7:
        return "légère"
    if sev < 1.0:
        return "modérée"
    if sev < 1.35:
        return "marquée"
    return "sévère"


def _scale_dict(d, factor):
    return {k: v * factor for k, v in (d or {}).items()}


def macro_stress(market):
    """Score de tension macro (1.0 = neutre) dérivé des indicateurs macro
    courants : spread de crédit HY tendu, croissance proche de zéro/négative,
    chômage en hausse marquée, courbe des taux inversée. Sert à faire dépendre
    le déclenchement des crises de conditions macro cohérentes plutôt que d'un
    pur tirage indépendant du contexte (cf. CLAUDE.md, brief stratégique pt.5)."""
    if market is None or not hasattr(market, "macro"):
        return 1.0
    mc = market.macro
    from core.market import BASE_CREDIT_HY_BPS
    hy = mc.get("credit_hy", {}).get("v", BASE_CREDIT_HY_BPS)
    growth = mc.get("growth", {}).get("v", 2.0)
    unemp = mc.get("unemployment", {}).get("v", 5.0)
    score = 1.0
    score += max(0.0, (hy - BASE_CREDIT_HY_BPS) / BASE_CREDIT_HY_BPS) * 1.2
    score += max(0.0, 1.0 - growth) * 0.25
    score += max(0.0, unemp - 6.0) * 0.12
    if hasattr(market, "curve_inverted") and market.curve_inverted():
        score += 0.5
    return min(score, 4.0)


def maybe_trigger(market, rng=None, player=None):
    """Déclenche éventuellement un scénario. Retourne un dict narratif ou None.

    Le dict retourné inclut désormais `severity` (multiplicateur réellement
    tiré) et `region` (région ciblée si le scénario est régional, sinon None),
    en plus des champs historiques {id, name, kind, story}.

    `player` (optionnel) : la difficulté du run (core/difficulty.py) module le
    poids des scénarios NÉFASTES et leur sévérité — les booms (kind good) ne
    sont pas touchés. Comportement inchangé si omis (tests, sandbox).
    """
    from core.i18n import get_lang
    lang = get_lang()
    rng = rng or random
    # contagion : décroît d'un tour à chaque appel, même si rien ne se déclenche
    contagion = {k: v - 1 for k, v in (getattr(market, "contagion", None) or {}).items()
                 if v - 1 > 0}
    market.contagion = contagion
    if getattr(market, "crisis_cooldown", 0) > 0:
        return None   # accalmie forcée après une crise majeure : pas de nouveau choc
    stress = macro_stress(market)
    if rng.random() > min(0.9, TRIGGER_PROBABILITY * stress):
        return None
    bad_mult = sev_mult = 1.0
    if player is not None:
        from core import difficulty
        bad_mult = difficulty.crisis_bad_mult(player)
        sev_mult = difficulty.crisis_sev_mult(player)
    pool = localized(lang)
    weights = []
    for x in pool:
        w = x["weight"]
        if stress > 1.2 and x["kind"] == "bad":
            w *= stress
        elif stress < 0.85 and x["kind"] == "good":
            w *= (1.0 / max(stress, 0.4))
        if x["kind"] == "bad":
            w *= bad_mult          # difficulté du run (neutre à 1.0)
        if x["id"] in contagion:
            w *= CONTAGION_BOOST
        weights.append(w)
    s = rng.choices(pool, weights=weights, k=1)[0]
    related = CONTAGION.get(s["id"])
    if related:
        for rid in related:
            contagion[rid] = max(contagion.get(rid, 0), CONTAGION_STEPS)
        market.contagion = contagion

    sev_min = s.get("sev_min", 1.0)
    sev_max = s.get("sev_max", 1.0)
    severity = rng.uniform(sev_min, sev_max) if sev_max > sev_min else sev_min
    if s["kind"] == "bad":
        severity *= sev_mult       # difficulté du run (neutre à 1.0)

    regions = dict(s.get("regions") or {})
    region = None
    if s.get("regional"):
        pool = [r for r in s.get("region_pool", _DEFAULT_REGION_POOL)
                if r in getattr(market, "regions", _DEFAULT_REGION_POOL)] \
            or _DEFAULT_REGION_POOL
        region = rng.choice(pool)
        regions[region] = regions.get(region, 0.0) + s.get("region_extra", 0.0) * severity

    world = s.get("world", 0.0) * severity
    sectors = _scale_dict(s.get("sectors"), severity)
    regions = _scale_dict(regions, severity) if regions else None
    # la vol s'amplifie aussi avec la sévérité, mais reste bornée (anti dérive
    # extrême) — cohérent avec les bornes déjà appliquées ailleurs dans market.py.
    vol = min(4.0, max(1.0, s.get("vol", 1.0) * (0.5 + 0.5 * severity)))

    market.add_crisis(Crisis(
        s["name"], steps=s["steps"], world=world,
        regions=regions, sectors=sectors, vol_mult=vol,
        severity=severity, kind=s["kind"]))

    sev_word = _severity_label(severity, lang)
    story = s["story"]
    if lang == "en":
        if region:
            story = f"{story} (region affected: {region}, severity {sev_word})"
        else:
            story = f"{story} (severity {sev_word})"
    else:
        if region:
            story = f"{story} (région touchée : {region}, sévérité {sev_word})"
        else:
            story = f"{story} (sévérité {sev_word})"

    return {"id": s["id"], "name": s["name"], "kind": s["kind"], "story": story,
            "severity": severity, "region": region}


def maybe_warn(market, rng=None):
    """Signal avant-crise ambigu : à appeler quand aucun scénario ne s'est
    déclenché ce tour. Si la tension macro dépasse WARNING_STRESS_THRESHOLD,
    probabilité de pousser un avertissement flou (ne révèle ni le scénario
    exact ni le moment) — récompense la couverture proactive plutôt que la
    seule réaction après coup. Soumis à un délai de carence pour éviter le
    spam. Retourne un dict {kind, stress, story} ou None."""
    rng = rng or random
    cooldown = getattr(market, "warning_cooldown", 0)
    if cooldown > 0:
        market.warning_cooldown = cooldown - 1
        return None
    if getattr(market, "crisis_cooldown", 0) > 0:
        return None
    stress = macro_stress(market)
    if stress < WARNING_STRESS_THRESHOLD:
        return None
    if rng.random() > WARNING_PROBABILITY:
        return None
    market.warning_cooldown = WARNING_COOLDOWN_STEPS
    from core.i18n import get_lang
    signs = _WARNING_SIGNS_EN if get_lang() == "en" else _WARNING_SIGNS_FR
    story = rng.choice(signs)
    return {"kind": "warning", "stress": round(stress, 2), "story": story}


def trigger_by_id(market, scenario_id, severity=1.0):
    """Déclenche un scénario précis, de façon déterministe (sans rng) : utilisé
    par le mode bac à sable (commande CRISIS) pour tester des stress tests
    ad hoc, reproductibles à coup sûr pour une sévérité donnée.

    Mirroir de maybe_trigger() (même mise à l'échelle world/sectors/regions/vol)
    mais sans tirage probabiliste : la région (si le scénario est "regional")
    est la première du pool plutôt qu'un tirage rng.choice, et la sévérité est
    l'argument fourni (clampée à [sev_min, sev_max] du scénario), pas un
    rng.uniform. Retourne le dict narratif (mêmes clés que maybe_trigger), ou
    None si l'id est inconnu.
    """
    from core.i18n import get_lang
    lang = get_lang()
    pool = localized(lang)
    s = next((x for x in pool if x["id"] == scenario_id), None)
    if s is None:
        return None

    sev_min = s.get("sev_min", 1.0)
    sev_max = s.get("sev_max", 1.0)
    severity = max(sev_min, min(sev_max, severity)) if sev_max > sev_min else sev_min

    regions = dict(s.get("regions") or {})
    region = None
    if s.get("regional"):
        region_pool = [r for r in s.get("region_pool", _DEFAULT_REGION_POOL)
                       if r in getattr(market, "regions", _DEFAULT_REGION_POOL)] \
            or _DEFAULT_REGION_POOL
        region = region_pool[0]   # déterministe : pas de rng.choice
        regions[region] = regions.get(region, 0.0) + s.get("region_extra", 0.0) * severity

    world = s.get("world", 0.0) * severity
    sectors = _scale_dict(s.get("sectors"), severity)
    regions = _scale_dict(regions, severity) if regions else None
    vol = min(4.0, max(1.0, s.get("vol", 1.0) * (0.5 + 0.5 * severity)))

    crisis = Crisis(
        s["name"], steps=s["steps"], world=world,
        regions=regions, sectors=sectors, vol_mult=vol,
        severity=severity, kind=s["kind"])
    market.add_crisis(crisis)

    sev_word = _severity_label(severity, lang)
    story = s["story"]
    if lang == "en":
        if region:
            story = f"{story} (region affected: {region}, severity {sev_word})"
        else:
            story = f"{story} (severity {sev_word})"
    else:
        if region:
            story = f"{story} (région touchée : {region}, sévérité {sev_word})"
        else:
            story = f"{story} (sévérité {sev_word})"

    return {"id": s["id"], "name": s["name"], "kind": s["kind"], "story": story,
            "severity": severity, "region": region, "crisis": crisis}
