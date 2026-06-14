"""
scenarios.py — Crises et booms déclenchés dans le temps (logique pure).

Chaque scénario applique un choc de facteurs au marché (via core.market.Crisis)
sur plusieurs pas : il se répercute donc sur les indices ET sur le portefeuille
du joueur. Inspirés de cas réels (renommés/fictionnalisés).

maybe_trigger() est appelé à chaque tour : faible probabilité de déclencher un
scénario, pondéré. Retourne une description narrative (ou None).
"""
import random
from core.market import Crisis

# (id, nom affiché, kind, steps, world, regions{}, sectors{}, vol_mult, poids, récit)
SCENARIOS = [
    {"id": "krach", "name": "Krach systémique", "kind": "bad", "steps": 6,
     "world": -0.05, "sectors": {"Finance": -0.06, "Immobilier": -0.04}, "vol": 2.6,
     "weight": 2,
     "story": "Une cascade de défauts gèle le crédit interbancaire — réminiscence de 2008."},
    {"id": "taux", "name": "Choc de taux", "kind": "bad", "steps": 4,
     "world": -0.025, "sectors": {"Finance": -0.045, "Immobilier": -0.035, "Utilities": -0.02},
     "vol": 1.8, "weight": 3,
     "story": "Une remontée brutale des taux fragilise banques régionales et immobilier (type 2023)."},
    {"id": "tornade", "name": "Catastrophe agricole", "kind": "bad", "steps": 3,
     "world": 0.0, "sectors": {"Agro": -0.07, "Conso": -0.02}, "vol": 1.4,
     "weight": 3,
     "story": "Tornades et sécheresses ravagent les récoltes : les valeurs agroalimentaires plongent."},
    {"id": "techbust", "name": "Éclatement bulle tech", "kind": "bad", "steps": 5,
     "world": -0.02, "sectors": {"Tech": -0.05, "Semicon": -0.06}, "vol": 2.0,
     "weight": 2,
     "story": "Les multiples de la tech se dégonflent violemment après des résultats décevants."},
    {"id": "energie", "name": "Choc énergétique", "kind": "bad", "steps": 4,
     "world": -0.015, "sectors": {"Energie": -0.05, "Industrie": -0.03}, "vol": 1.6,
     "weight": 2,
     "story": "Une rupture d'approvisionnement fait flamber puis dévisser le secteur énergie."},
    {"id": "asia", "name": "Tensions géopolitiques (Asie)", "kind": "bad", "steps": 4,
     "regions": {"Asia": -0.05}, "sectors": {"Semicon": -0.03}, "vol": 1.8,
     "weight": 2,
     "story": "Des tensions régionales en Asie déclenchent une fuite vers la qualité."},
    # booms (bonnes nouvelles)
    {"id": "techboom", "name": "Boom technologique", "kind": "good", "steps": 4,
     "world": 0.012, "sectors": {"Tech": 0.045, "Semicon": 0.05}, "vol": 1.3,
     "weight": 3,
     "story": "Une percée en IA propulse la tech et les semi-conducteurs."},
    {"id": "relance", "name": "Plan de relance mondial", "kind": "good", "steps": 5,
     "world": 0.02, "sectors": {"Industrie": 0.03, "Materiaux": 0.03}, "vol": 1.3,
     "weight": 2,
     "story": "Un vaste plan d'investissement public dope l'industrie et les matériaux."},
    {"id": "pandemie", "name": "Choc sanitaire", "kind": "bad", "steps": 6,
     "world": -0.035, "sectors": {"Sante": 0.03, "Conso": -0.03, "Industrie": -0.03},
     "vol": 2.2, "weight": 2,
     "story": "Une crise sanitaire paralyse l'activité ; la santé surperforme, le reste plonge."},
    {"id": "credit", "name": "Resserrement du crédit", "kind": "bad", "steps": 4,
     "world": -0.02, "sectors": {"Finance": -0.05, "Immobilier": -0.04}, "vol": 1.7,
     "weight": 2,
     "story": "Les conditions de crédit se durcissent brutalement ; banques et immobilier souffrent."},
    {"id": "ipo", "name": "Vague d'introductions en bourse", "kind": "good", "steps": 4,
     "world": 0.015, "sectors": {"Tech": 0.03, "Finance": 0.025}, "vol": 1.3,
     "weight": 2,
     "story": "Un marché euphorique relance les IPO ; tech et finance en profitent."},
    {"id": "matieres", "name": "Flambée des matières premières", "kind": "bad", "steps": 4,
     "world": -0.01, "sectors": {"Materiaux": 0.04, "Energie": 0.03, "Industrie": -0.03,
                                 "Conso": -0.02}, "vol": 1.6, "weight": 2,
     "story": "Les cours des matières premières s'envolent : gagnants et perdants sectoriels."},
]

TRIGGER_PROBABILITY = 0.06   # par tour


def maybe_trigger(market, rng=None):
    """Déclenche éventuellement un scénario. Retourne un dict narratif ou None."""
    rng = rng or random
    if rng.random() > TRIGGER_PROBABILITY:
        return None
    s = rng.choices(SCENARIOS, weights=[x["weight"] for x in SCENARIOS], k=1)[0]
    market.add_crisis(Crisis(
        s["name"], steps=s["steps"], world=s.get("world", 0.0),
        regions=s.get("regions"), sectors=s.get("sectors"), vol_mult=s.get("vol", 1.0)))
    return {"id": s["id"], "name": s["name"], "kind": s["kind"], "story": s["story"]}
