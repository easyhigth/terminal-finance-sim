"""
politics.py — Événements POLITIQUES régionaux (logique pure, sans pygame).

Au-delà des crises de marché (core/scenarios.py) et de la campagne historique
(core/history.py), des événements POLITIQUES inspirés du réel surviennent dans un
PAYS (core/governments.py) et frappent sa RÉGION. Chaque événement :

  - injecte un choc de facteurs régional + sectoriel (core.market.Crisis) → il
    impacte réellement les ACTIONS des sociétés de la zone (modèle à facteurs) ;
  - élargit (mauvaise nouvelle) ou resserre (bonne nouvelle) le spread de crédit
    RÉGIONAL (market.bump_region_credit) → les prix des OBLIGATIONS souveraines
    ET corporate de la zone réagissent (cf. core/bonds.py) ;
  - porte une narration bilingue rattachée au pays (news, carte, journal, inbox).

Les pools d'événements sont propres à chaque région pour rester LOGIQUES (un bras
de fer sur le plafond de la dette aux USA, une crise budgétaire en Europe, une
crise immobilière en Asie, une poussée inflationniste en Amérique du Sud…).

maybe_trigger(player, market, rng) est appelé à chaque tour : faible probabilité,
choix d'un gouvernement pondéré par son INSTABILITÉ, puis d'un événement
approprié à sa région. Retourne un dict narratif (ou None).
"""
import random

from core import governments as gov_mod
from core.market import Crisis

TRIGGER_PROBABILITY = 0.07   # par tour (en plus des crises de marché)

# Pools d'événements par région. Champs d'un événement :
#   id, kind (good/bad/info), name/name_en (libellé court),
#   fr/en   : récit (peut contenir {country}),
#   sectors : {secteur: choc additif par pas}
#   region  : choc additif sur le facteur régional par pas
#   credit  : variation de spread régional en points de base (+ = élargit)
#   vol     : amplificateur de volatilité, steps : durée (pas)
_POOLS = {
    "USA": [
        {"id": "us_debt_ceiling", "kind": "bad", "name": "Plafond de la dette",
         "name_en": "Debt-ceiling standoff",
         "fr": "{country} : bras de fer politique sur le plafond de la dette ; les marchés redoutent un défaut technique.",
         "en": "{country}: a political standoff over the debt ceiling; markets fear a technical default.",
         "sectors": {"Finance": -0.02}, "region": -0.015, "credit": 45, "vol": 1.6, "steps": 3},
        {"id": "us_shutdown", "kind": "bad", "name": "Shutdown fédéral",
         "name_en": "Federal shutdown",
         "fr": "{country} : faute d'accord budgétaire, l'administration fédérale est partiellement à l'arrêt.",
         "en": "{country}: lacking a budget deal, the federal government partially shuts down.",
         "sectors": {}, "region": -0.010, "credit": 20, "vol": 1.3, "steps": 2},
        {"id": "us_tariffs", "kind": "bad", "name": "Nouveaux tarifs douaniers",
         "name_en": "New import tariffs",
         "fr": "{country} impose de nouveaux tarifs douaniers : tensions commerciales et pression sur l'industrie et les semi-conducteurs.",
         "en": "{country} imposes new tariffs: trade tensions weigh on industry and semiconductors.",
         "sectors": {"Industrie": -0.025, "Semicon": -0.025}, "region": -0.010, "credit": 20, "vol": 1.5, "steps": 3},
        {"id": "us_election", "kind": "info", "name": "Incertitude électorale",
         "name_en": "Election uncertainty",
         "fr": "{country} : une présidentielle indécise nourrit la volatilité avant la clarification de la politique économique.",
         "en": "{country}: a too-close-to-call presidential race fuels volatility ahead of policy clarity.",
         "sectors": {}, "region": -0.010, "credit": 25, "vol": 1.7, "steps": 3},
        {"id": "us_budget_deal", "kind": "good", "name": "Accord budgétaire",
         "name_en": "Bipartisan budget deal",
         "fr": "{country} : un accord budgétaire bipartisan rassure et fait refluer la prime de risque.",
         "en": "{country}: a bipartisan budget deal reassures markets and compresses the risk premium.",
         "sectors": {"Finance": 0.02}, "region": 0.012, "credit": -25, "vol": 1.1, "steps": 3},
    ],
    "Europe": [
        {"id": "eu_budget_crisis", "kind": "bad", "name": "Crise budgétaire",
         "name_en": "Budget crisis",
         "fr": "{country} : dérapage budgétaire et dette dégradée ; le spread souverain se tend brutalement.",
         "en": "{country}: a budget slippage and debt downgrade send the sovereign spread sharply wider.",
         "sectors": {"Finance": -0.025, "Immobilier": -0.015}, "region": -0.020, "credit": 60, "vol": 1.7, "steps": 4},
        {"id": "eu_strikes", "kind": "bad", "name": "Tensions sociales",
         "name_en": "Social unrest",
         "fr": "{country} : grèves et manifestations massives paralysent l'activité et la consommation.",
         "en": "{country}: mass strikes and protests paralyse activity and consumption.",
         "sectors": {"Conso": -0.02, "Industrie": -0.02}, "region": -0.012, "credit": 25, "vol": 1.4, "steps": 3},
        {"id": "eu_election", "kind": "info", "name": "Incertitude électorale",
         "name_en": "Election uncertainty",
         "fr": "{country} : des élections incertaines et une coalition fragile inquiètent les investisseurs.",
         "en": "{country}: uncertain elections and a fragile coalition worry investors.",
         "sectors": {}, "region": -0.014, "credit": 35, "vol": 1.5, "steps": 3},
        {"id": "eu_stimulus", "kind": "good", "name": "Plan de relance européen",
         "name_en": "EU recovery plan",
         "fr": "{country} bénéficie d'un déploiement de fonds de relance européens : industrie et matériaux rebondissent.",
         "en": "{country} benefits from EU recovery funds: industry and materials rebound.",
         "sectors": {"Industrie": 0.03, "Materiaux": 0.025}, "region": 0.015, "credit": -30, "vol": 1.1, "steps": 4},
    ],
    "Asia": [
        {"id": "as_geopol", "kind": "bad", "name": "Tensions géopolitiques",
         "name_en": "Geopolitical tensions",
         "fr": "{country} : des tensions régionales ravivent la prime de risque ; les semi-conducteurs décrochent.",
         "en": "{country}: regional tensions revive the risk premium; semiconductors slide.",
         "sectors": {"Semicon": -0.03, "Tech": -0.02}, "region": -0.020, "credit": 45, "vol": 1.8, "steps": 4},
        {"id": "as_property", "kind": "bad", "name": "Crise immobilière",
         "name_en": "Property crisis",
         "fr": "{country} : des défauts de promoteurs immobiliers ébranlent banques et confiance.",
         "en": "{country}: property-developer defaults rattle banks and confidence.",
         "sectors": {"Immobilier": -0.035, "Finance": -0.02}, "region": -0.018, "credit": 50, "vol": 1.7, "steps": 4},
        {"id": "as_techreg", "kind": "bad", "name": "Tour de vis réglementaire",
         "name_en": "Regulatory crackdown",
         "fr": "{country} durcit la régulation des géants de la tech : les valorisations se contractent.",
         "en": "{country} tightens regulation of tech giants: valuations contract.",
         "sectors": {"Tech": -0.03}, "region": -0.014, "credit": 30, "vol": 1.5, "steps": 3},
        {"id": "as_fx", "kind": "info", "name": "Intervention sur la devise",
         "name_en": "Currency intervention",
         "fr": "{country} : la banque centrale intervient pour défendre sa monnaie face à la pression des marchés.",
         "en": "{country}: the central bank intervenes to defend its currency against market pressure.",
         "sectors": {}, "region": -0.008, "credit": 15, "vol": 1.3, "steps": 2},
        {"id": "as_stimulus", "kind": "good", "name": "Plan de relance",
         "name_en": "Stimulus package",
         "fr": "{country} dévoile un vaste plan d'infrastructures : industrie et matériaux en profitent.",
         "en": "{country} unveils a vast infrastructure plan: industry and materials benefit.",
         "sectors": {"Industrie": 0.025, "Materiaux": 0.025}, "region": 0.015, "credit": -30, "vol": 1.1, "steps": 4},
    ],
    "Am.Sud": [
        {"id": "sa_inflation", "kind": "bad", "name": "Poussée inflationniste",
         "name_en": "Inflation surge",
         "fr": "{country} : flambée de l'inflation et contrôle des changes ; la prime de risque souveraine explose.",
         "en": "{country}: an inflation surge and capital controls; the sovereign risk premium spikes.",
         "sectors": {"Finance": -0.02}, "region": -0.020, "credit": 70, "vol": 1.8, "steps": 4},
        {"id": "sa_govchange", "kind": "info", "name": "Changement de gouvernement",
         "name_en": "Change of government",
         "fr": "{country} : un changement de gouvernement rebat les cartes de la politique économique.",
         "en": "{country}: a change of government reshuffles economic policy.",
         "sectors": {}, "region": -0.015, "credit": 40, "vol": 1.6, "steps": 3},
        {"id": "sa_imf", "kind": "bad", "name": "Tensions sur la dette",
         "name_en": "Debt tensions",
         "fr": "{country} : négociations tendues avec le FMI sur la restructuration de la dette.",
         "en": "{country}: tense IMF negotiations over debt restructuring.",
         "sectors": {}, "region": -0.025, "credit": 90, "vol": 1.9, "steps": 4},
        {"id": "sa_commodities", "kind": "good", "name": "Boom des matières premières",
         "name_en": "Commodity boom",
         "fr": "{country} profite d'un cycle haussier des matières premières : énergie et matériaux s'envolent.",
         "en": "{country} rides a commodity upcycle: energy and materials soar.",
         "sectors": {"Materiaux": 0.03, "Energie": 0.03}, "region": 0.018, "credit": -30, "vol": 1.2, "steps": 4},
    ],
    "Afrique": [
        {"id": "af_instability", "kind": "bad", "name": "Instabilité politique",
         "name_en": "Political instability",
         "fr": "{country} : l'instabilité politique fait fuir les capitaux et tend les spreads.",
         "en": "{country}: political instability drives capital flight and widens spreads.",
         "sectors": {"Finance": -0.02}, "region": -0.020, "credit": 70, "vol": 1.8, "steps": 4},
        {"id": "af_power", "kind": "bad", "name": "Pénuries d'énergie",
         "name_en": "Power shortages",
         "fr": "{country} : délestages électriques massifs ; l'industrie et les utilities souffrent.",
         "en": "{country}: massive load-shedding; industry and utilities suffer.",
         "sectors": {"Industrie": -0.025, "Utilities": -0.02}, "region": -0.018, "credit": 50, "vol": 1.6, "steps": 4},
        {"id": "af_imf", "kind": "good", "name": "Programme de réformes",
         "name_en": "Reform programme",
         "fr": "{country} lance un programme de réformes soutenu par le FMI : la confiance revient peu à peu.",
         "en": "{country} launches an IMF-backed reform programme: confidence gradually returns.",
         "sectors": {}, "region": 0.012, "credit": -40, "vol": 1.2, "steps": 4},
        {"id": "af_resources", "kind": "good", "name": "Boom de ressources",
         "name_en": "Resource boom",
         "fr": "{country} : une découverte de ressources dope les matières premières et l'énergie.",
         "en": "{country}: a resource discovery boosts commodities and energy.",
         "sectors": {"Materiaux": 0.03, "Energie": 0.025}, "region": 0.020, "credit": -25, "vol": 1.2, "steps": 4},
    ],
    "Am.Nord": [
        {"id": "na_trade", "kind": "good", "name": "Accord commercial",
         "name_en": "Trade agreement",
         "fr": "{country} signe un accord commercial régional : l'industrie exportatrice en profite.",
         "en": "{country} signs a regional trade agreement: exporting industry benefits.",
         "sectors": {"Industrie": 0.02}, "region": 0.012, "credit": -20, "vol": 1.1, "steps": 3},
        {"id": "na_energyreg", "kind": "bad", "name": "Réglementation énergétique",
         "name_en": "Energy regulation",
         "fr": "{country} durcit la réglementation énergétique : pipelines et producteurs sous pression.",
         "en": "{country} tightens energy regulation: pipelines and producers under pressure.",
         "sectors": {"Energie": -0.025}, "region": -0.012, "credit": 25, "vol": 1.3, "steps": 3},
        {"id": "na_trade_friction", "kind": "info", "name": "Tensions commerciales",
         "name_en": "Trade friction",
         "fr": "{country} : des frictions commerciales transfrontalières créent de l'incertitude.",
         "en": "{country}: cross-border trade friction creates uncertainty.",
         "sectors": {}, "region": -0.010, "credit": 20, "vol": 1.3, "steps": 2},
    ],
    "Océanie": [
        {"id": "oc_chinademand", "kind": "bad", "name": "Demande chinoise en berne",
         "name_en": "Weak Chinese demand",
         "fr": "{country} : le ralentissement de la demande chinoise pèse sur le minerai de fer et l'énergie.",
         "en": "{country}: slowing Chinese demand weighs on iron ore and energy.",
         "sectors": {"Materiaux": -0.03, "Energie": -0.02}, "region": -0.018, "credit": 35, "vol": 1.5, "steps": 4},
        {"id": "oc_minetax", "kind": "bad", "name": "Taxe sur les ressources",
         "name_en": "Resource tax",
         "fr": "{country} instaure une taxe sur les superprofits miniers : les producteurs reculent.",
         "en": "{country} introduces a windfall tax on mining: producers fall back.",
         "sectors": {"Materiaux": -0.025}, "region": -0.012, "credit": 20, "vol": 1.3, "steps": 3},
        {"id": "oc_minerals", "kind": "good", "name": "Boom des minerais critiques",
         "name_en": "Critical-minerals boom",
         "fr": "{country} : la demande en minerais critiques (transition énergétique) dope le secteur des matériaux.",
         "en": "{country}: demand for critical minerals (energy transition) boosts materials.",
         "sectors": {"Materiaux": 0.03}, "region": 0.018, "credit": -25, "vol": 1.2, "steps": 4},
    ],
}


def _pick_government(rng):
    """Choisit un gouvernement, pondéré par son INSTABILITÉ (les pays fragiles
    font plus souvent l'actualité politique)."""
    govs = [g for g in gov_mod.GOVERNMENTS if g["region"] in _POOLS]
    weights = [0.2 + (1.0 - g.get("stability", 0.8)) for g in govs]
    return rng.choices(govs, weights=weights, k=1)[0]


def maybe_trigger(player, market, rng=None):
    """Déclenche éventuellement un événement politique. Retourne un dict narratif
    {id, name, name_en, story, story_en, kind, region, country, country_en} ou None."""
    rng = rng or random
    if rng.random() > TRIGGER_PROBABILITY:
        return None
    gov = _pick_government(rng)
    pool = _POOLS.get(gov["region"])
    if not pool:
        return None
    ev = rng.choice(pool)
    # choc de marché régional + sectoriel (impacte les actions de la zone)
    market.add_crisis(Crisis(
        ev["name"], steps=ev.get("steps", 3), world=0.0,
        regions={gov["region"]: ev.get("region", 0.0)},
        sectors=ev.get("sectors") or None, vol_mult=ev.get("vol", 1.0)))
    # réaction du crédit régional (obligations souveraines + corporates de la zone)
    market.bump_region_credit(gov["region"], ev.get("credit", 0) / 10000.0)
    story = ev["fr"].format(country=gov["name"])
    story_en = ev["en"].format(country=gov["name_en"])
    return {"id": ev["id"], "name": f"{gov['name']} — {ev['name']}",
            "name_en": f"{gov['name_en']} — {ev['name_en']}",
            "story": story, "story_en": story_en, "kind": ev["kind"],
            "region": gov["region"], "country": gov["name"],
            "country_en": gov["name_en"], "gov": gov["code"]}
