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
]

TRIGGER_PROBABILITY = 0.06   # par tour

# régions éligibles par défaut pour un scénario "regional" qui ne précise pas
# region_pool — toutes les régions connues du marché.
_DEFAULT_REGION_POOL = ["USA", "Europe", "Asia", "Am.Nord", "Am.Sud", "Afrique", "Océanie"]


def _severity_label(sev):
    """Qualificatif FR de la sévérité tirée, pour la narration."""
    if sev < 0.7:
        return "légère"
    if sev < 1.0:
        return "modérée"
    if sev < 1.35:
        return "marquée"
    return "sévère"


def _scale_dict(d, factor):
    return {k: v * factor for k, v in (d or {}).items()}


def maybe_trigger(market, rng=None):
    """Déclenche éventuellement un scénario. Retourne un dict narratif ou None.

    Le dict retourné inclut désormais `severity` (multiplicateur réellement
    tiré) et `region` (région ciblée si le scénario est régional, sinon None),
    en plus des champs historiques {id, name, kind, story}.
    """
    rng = rng or random
    if rng.random() > TRIGGER_PROBABILITY:
        return None
    s = rng.choices(SCENARIOS, weights=[x["weight"] for x in SCENARIOS], k=1)[0]

    sev_min = s.get("sev_min", 1.0)
    sev_max = s.get("sev_max", 1.0)
    severity = rng.uniform(sev_min, sev_max) if sev_max > sev_min else sev_min

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
        regions=regions, sectors=sectors, vol_mult=vol))

    sev_word = _severity_label(severity)
    story = s["story"]
    if region:
        story = f"{story} (région touchée : {region}, sévérité {sev_word})"
    else:
        story = f"{story} (sévérité {sev_word})"

    return {"id": s["id"], "name": s["name"], "kind": s["kind"], "story": story,
            "severity": severity, "region": region}
