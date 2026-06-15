"""
history.py — Chronologie scénarisée d'événements historiques (logique pure).

Au-delà des crises aléatoires (core/scenarios.py), une CAMPAGNE d'événements
marquants se déclenche à des trimestres précis depuis le début de la partie :
chaque run traverse le même arc (krach systémique, choc de taux, bulle tech,
choc énergétique, pandémie, boom IA…). Chaque événement injecte un choc de
marché (core.market.Crisis) et porte une narration (FR/EN).

maybe_trigger(player, market) est appelé à chaque tour ; il déclenche l'événement
dont le trimestre-cible est atteint et pas encore joué (flags['history_fired']).
"""
from core.market import Crisis

# trimestres écoulés depuis le début (player.quarter - 1) -> événement.
TIMELINE = [
    {"q": 2, "id": "h_tighten", "kind": "bad", "steps": 4, "world": -0.02,
     "sectors": {"Immobilier": -0.03, "Finance": -0.03}, "vol": 1.6,
     "name": "Resserrement monétaire", "name_en": "Monetary tightening",
     "story": "La banque centrale accélère les hausses de taux : l'immobilier et "
              "les valeurs de croissance encaissent le premier coup de frein.",
     "story_en": "The central bank speeds up rate hikes: real estate and growth "
                 "stocks take the first hit."},
    {"q": 5, "id": "h_gfc", "kind": "bad", "steps": 8, "world": -0.05,
     "sectors": {"Finance": -0.07, "Immobilier": -0.05}, "vol": 2.8,
     "name": "Krach systémique", "name_en": "Systemic crash",
     "story": "Une cascade de défauts gèle le crédit interbancaire. Les banques "
              "s'effondrent, la liquidité s'évapore — l'onde de 2008 se rejoue.",
     "story_en": "A cascade of defaults freezes interbank credit. Banks collapse, "
                 "liquidity evaporates — the 2008 shock replays."},
    {"q": 8, "id": "h_recovery", "kind": "good", "steps": 6, "world": 0.02,
     "sectors": {"Industrie": 0.03, "Materiaux": 0.03, "Finance": 0.03}, "vol": 1.3,
     "name": "Plan de relance mondial", "name_en": "Global stimulus",
     "story": "Un vaste plan d'investissement public et des taux bas relancent "
              "l'activité : l'industrie et les financières rebondissent.",
     "story_en": "A vast public investment plan and low rates restart activity: "
                 "industrials and financials rebound."},
    {"q": 11, "id": "h_techbust", "kind": "bad", "steps": 5, "world": -0.025,
     "sectors": {"Tech": -0.06, "Semicon": -0.06}, "vol": 2.2,
     "name": "Éclatement de la bulle tech", "name_en": "Tech bubble bursts",
     "story": "Après des années d'euphorie, les multiples de la tech se dégonflent "
              "brutalement sur fond de résultats décevants.",
     "story_en": "After years of euphoria, tech multiples deflate sharply on "
                 "disappointing earnings."},
    {"q": 14, "id": "h_energy", "kind": "bad", "steps": 4, "world": -0.02,
     "sectors": {"Energie": 0.04, "Industrie": -0.04, "Conso": -0.03}, "vol": 1.8,
     "name": "Choc énergétique", "name_en": "Energy shock",
     "story": "Une rupture d'approvisionnement fait flamber l'énergie et étrangle "
              "l'industrie et la consommation.",
     "story_en": "A supply disruption sends energy soaring and squeezes industry "
                 "and consumers."},
    {"q": 18, "id": "h_pandemic", "kind": "bad", "steps": 7, "world": -0.04,
     "sectors": {"Sante": 0.03, "Conso": -0.04, "Industrie": -0.04}, "vol": 2.4,
     "name": "Choc sanitaire mondial", "name_en": "Global health shock",
     "story": "Une pandémie paralyse l'activité : la santé surperforme tandis que "
              "le reste de l'économie plonge.",
     "story_en": "A pandemic paralyses activity: healthcare outperforms while the "
                 "rest of the economy dives."},
    {"q": 22, "id": "h_aiboom", "kind": "good", "steps": 6, "world": 0.018,
     "sectors": {"Tech": 0.05, "Semicon": 0.06}, "vol": 1.4,
     "name": "Révolution de l'IA", "name_en": "AI revolution",
     "story": "Une percée majeure en intelligence artificielle propulse la tech et "
              "les semi-conducteurs vers de nouveaux sommets.",
     "story_en": "A major AI breakthrough propels tech and semiconductors to new highs."},
]
_BY_ID = {e["id"]: e for e in TIMELINE}


def localized(event, lang):
    """Renvoie (nom, récit) de l'événement dans la langue."""
    if lang == "en":
        return event["name_en"], event["story_en"]
    return event["name"], event["story"]


def maybe_trigger(player, market):
    """Déclenche l'événement historique dont le trimestre est atteint (une fois).
    Retourne un dict narratif {id, name, story, kind} ou None."""
    fired = player.flags.setdefault("history_fired", [])
    elapsed = max(0, player.quarter - 1)
    for ev in TIMELINE:
        if ev["q"] == elapsed and ev["id"] not in fired:
            market.add_crisis(Crisis(
                ev["name"], steps=ev["steps"], world=ev.get("world", 0.0),
                regions=ev.get("regions"), sectors=ev.get("sectors"),
                vol_mult=ev.get("vol", 1.0)))
            fired.append(ev["id"])
            return {"id": ev["id"], "name": ev["name"], "story": ev["story"],
                    "kind": ev["kind"], "event": ev}
    return None
