"""
market_events.py — Événements d'entreprise ciblés avec impact réel sur les cours.

Ce module est une couche PURE au-dessus du moteur de marché : il tire, à chaque
pas, des événements spécifiques à certaines sociétés (produit, contrat, scandale,
OPA, etc.) et calcule le choc de cours correspondant. Les chocs sont injectés dans
le rendement du pas par `core/market.py` (cf. `_step_company_events`) et un log
d'événements est conservé par ticker pour l'affichage sur les graphes.

Contraintes de conception :
- DÉTERMINISME : un tirage rng est consommé à CHAQUE pas pour CHAQUE société,
  même quand aucun événement ne se déclenche. Cela garantit que
  (graine, nb de pas) reconstruit exactement le même état.
- IMPACT RÉEL : chaque événement modifie le cours via un choc log-rendement
  immédiat + un drift résiduel sur plusieurs pas (effet « echo »).
- NARRATIF : chaque modèle a un titre, une description et une icône FR/EN,
  réutilisables dans les news et les annotations de graphe.
- CALIBRAGE : la magnitude est bornée pour ne pas dénaturer le modèle à facteurs
  existant ; elle est aussi fonction de la volatilité propre de la société.
"""


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


# -----------------------------------------------------------------------------
# Modèles d'événements
# -----------------------------------------------------------------------------
# Chaque modèle :
#   id          : identifiant stable
#   kind        : "good" | "bad" | "info"
#   category    : "operational" | "corporate" | "external"
#   icon        : glyphe simple (1 caractère) affiché sur les graphes
#   base_prob   : probabilité de déclenchement par pas et par société
#   magnitude   : base du choc log (multiplié par sigma de la société)
#   decay_steps : durée du drift résiduel après le choc initial
#   title/desc  : tuples (fr, en)
#
# La probabilité réelle par pas est base_prob * 0.015 environ, ce qui donne
# quelques événements par an par société (réalisme) sans inonder le jeu.
EVENT_MODELS = [
    # ------------------------------- favorables -------------------------------
    {"id": "product_hit", "kind": "good", "category": "operational",
     "icon": "▲", "base_prob": 0.0040, "magnitude": 0.55, "decay_steps": 5,
     "title": ("Produit star lancé", "Breakout product launch"),
     "desc": ("Le dernier produit dépasse les pré-commandes ; les analystes"
              " relèvent leurs estimations.",
              "The latest product beats pre-orders; analysts raise estimates.")},
    {"id": "contract_win", "kind": "good", "category": "operational",
     "icon": "@", "base_prob": 0.0045, "magnitude": 0.42, "decay_steps": 4,
     "title": ("Gros contrat remporté", "Major contract won"),
     "desc": ("Un contrat stratégique de plusieurs années est signé avec un"
              " client de poids.",
              "A multi-year strategic contract is signed with a major client.")},
    {"id": "buyback", "kind": "good", "category": "corporate",
     "icon": "$", "base_prob": 0.0025, "magnitude": 0.30, "decay_steps": 3,
     "title": ("Programme de rachat d'actions", "Share buyback announced"),
     "desc": ("Le conseil annonce un rachat d'actions qui soutiendra le cours.",
              "The board announces a share buyback to support the stock.")},
    {"id": "guidance_raise", "kind": "good", "category": "corporate",
     "icon": "↑", "base_prob": 0.0030, "magnitude": 0.38, "decay_steps": 4,
     "title": ("Guidance relevée", "Guidance raised"),
     "desc": ("La direction relève ses prévisions annuelles de chiffre"
              " d'affaires et de marges.",
              "Management raises full-year revenue and margin guidance.")},
    {"id": "upgrade", "kind": "good", "category": "external",
     "icon": "*", "base_prob": 0.0035, "magnitude": 0.28, "decay_steps": 3,
     "title": ("Upgrade d'analyste", "Analyst upgrade"),
     "desc": ("Un grand bureau d'analyse relève sa recommandation et son"
              " objectif de cours.",
              "A major broker upgrades its rating and price target.")},

    # ------------------------------ défavorables ------------------------------
    {"id": "recall", "kind": "bad", "category": "operational",
     "icon": "!", "base_prob": 0.0035, "magnitude": -0.50, "decay_steps": 6,
     "title": ("Rappel de produit", "Product recall"),
     "desc": ("Un défaut de fabrication oblige un rappel massif et risque"
              " d'alourdir les provisions.",
              "A manufacturing defect triggers a large recall and may increase"
              " provisions.")},
    {"id": "contract_loss", "kind": "bad", "category": "operational",
     "icon": "X", "base_prob": 0.0038, "magnitude": -0.40, "decay_steps": 5,
     "title": ("Perte d'un client majeur", "Major client lost"),
     "desc": ("Le plus gros client annonce qu'il ne renouvellera pas son"
              " contrat l'année prochaine.",
              "The largest client announces it will not renew next year.")},
    {"id": "scandal", "kind": "bad", "category": "corporate",
     "icon": "SC", "base_prob": 0.0020, "magnitude": -0.70, "decay_steps": 8,
     "title": ("Scandale comptable", "Accounting scandal"),
     "desc": ("Des irrégularités comptables sont révélées ; le régulateur"
              " ouvre une enquête.",
              "Accounting irregularities are revealed; the regulator opens an"
              " investigation.")},
    {"id": "ceo_exit", "kind": "bad", "category": "corporate",
     "icon": "CEO", "base_prob": 0.0028, "magnitude": -0.35, "decay_steps": 4,
     "title": ("Départ surprise du CEO", "Surprise CEO departure"),
     "desc": ("Le CEO démissionne soudainement, suscitant des interrogations"
              " sur la stratégie.",
              "The CEO resigns abruptly, raising questions on strategy.")},
    {"id": "fine", "kind": "bad", "category": "external",
     "icon": "RG", "base_prob": 0.0025, "magnitude": -0.32, "decay_steps": 3,
     "title": ("Amende régulatoire", "Regulatory fine"),
     "desc": ("Une amende record pour non-conformité vient d'être infligée.",
              "A record fine for non-compliance has just been imposed.")},
    {"id": "downgrade", "kind": "bad", "category": "external",
     "icon": "↓", "base_prob": 0.0035, "magnitude": -0.28, "decay_steps": 3,
     "title": ("Downgrade d'analyste", "Analyst downgrade"),
     "desc": ("Un bureau d'analyse abaisse sa recommandation à cause des"
              " perspectives de croissance.",
              "A broker downgrades the stock on weaker growth outlook.")},

    # -------------------------------- neutres ---------------------------------
    {"id": "esg", "kind": "info", "category": "external",
     "icon": "ESG", "base_prob": 0.0020, "magnitude": 0.12, "decay_steps": 2,
     "title": ("Engagement ESG", "ESG commitment"),
     "desc": ("La société annonce un plan de neutralité carbone plus ambitieux.",
              "The firm announces a more ambitious net-zero plan.")},
    {"id": "cyber", "kind": "bad", "category": "operational",
     "icon": "CY", "base_prob": 0.0030, "magnitude": -0.28, "decay_steps": 4,
     "title": ("Cyberattaque", "Cyberattack"),
     "desc": ("Une intrusion informatique perturbe temporairement les"
              " opérations et menace des données.",
              "A cyber intrusion temporarily disrupts operations and threatens"
              " data.")},
]

EVENT_BY_ID = {e["id"]: e for e in EVENT_MODELS}

# -----------------------------------------------------------------------------
# Paramètres de calibration
# -----------------------------------------------------------------------------
# Probabilité cible nette par société par pas : ~0.04%, soit un événement par
# société tous les ~250 pas (~3,5 ans). Avec 320 sociétés, cela donne environ
# 1 à 2 événements par pas au niveau du marché entier — lisible sur les graphes
# sans inonder le joueur de notifications.
_MAX_EVENTS_PER_STEP = 2


def _prob_by_cap(base_prob, cap, min_cap=1e9, max_cap=2e11):
    """Les grosses capitalisations sont plus souvent couvertes par les news et
    les analystes : leur probabilité d'événement narratif est plus élevée. Les
    petites caps restent concernées mais moins fréquemment.
    Le facteur varie de ~0.35 (petite capi) à ~1.30 (grosse capi)."""
    ratio = max(0.0, min(1.0, (cap - min_cap) / (max_cap - min_cap)))
    return base_prob * (0.35 + 0.95 * ratio)


def _scale_by_cap(cap, min_cap=1e9, max_cap=2e11):
    """Les grandes capitalisations absorbent mieux les chocs : magnitude un peu
    plus faible. Les petites caps y sont plus sensibles.
    Le facteur varie de ~0.75 (grosse capi) à ~1.35 (petite capi)."""
    ratio = max(0.0, min(1.0, (cap - min_cap) / (max_cap - min_cap)))
    return 1.35 - 0.60 * ratio


def _instantiate(model, sigma, cap, step, rng):
    """Concrétise un modèle en événement pour une société donnée.
    Le choc log-rendement est proportionnel à `sigma` et à la capi.
    Le drift résiduel suit une décroissance exponentielle sur `decay_steps`.
    """
    cap_mult = _scale_by_cap(cap)
    # amplitude du choc initial : base * sigma * cap_mult, bornée
    base = model["magnitude"]
    shock = base * sigma * cap_mult * rng.uniform(0.8, 1.2)
    # bruits extrêmes plus rares mais plus marqués : ici calme, on borde
    shock = max(-0.12, min(0.12, shock))
    # drift résiduel : une fraction du choc initial qui s'éteint progressivement
    residual = shock * 0.35
    return {
        "id": model["id"],
        "kind": model["kind"],
        "category": model["category"],
        "icon": model["icon"],
        "title": _L(*model["title"]),
        "desc": _L(*model["desc"]),
        "step": step,
        "shock": float(shock),
        "residual": float(residual),
        "decay": int(model["decay_steps"]),
        "steps_left": int(model["decay_steps"]),
    }


# -----------------------------------------------------------------------------
# API publique
# -----------------------------------------------------------------------------
def step_events(n_companies, step_count, sigma_vec, cap_vec, rng):
    """Tire les événements d'entreprise pour un pas.

    Arguments :
        n_companies : nombre de sociétés
        step_count  : pas courant (pour le log)
        sigma_vec   : array-like de volatilités idiosyncratiques par société
        cap_vec     : array-like de capitalisations boursières (price*shares)
        rng         : générateur numpy RandomState du marché

    Retourne :
        shocks  : array numpy de chocs immédiats (log-rendements) de taille
                  n_companies (0.0 si pas d'événement)
        events  : liste d'événements concrets (dicts) indexés par société :
                  events[i] est None ou un dict événement.
    """
    import numpy as np
    shocks = np.zeros(n_companies)
    events = [None] * n_companies
    models = EVENT_MODELS
    weights = [m["base_prob"] for m in models]
    total_w = sum(weights)

    # Tirage déterministe : pour chaque société, on consomme une uniforme 0..1
    # et un choix d'événement. Même quand rien ne se déclenche, les tirages
    # sont effectués pour préserver la séquence rng.
    roll = rng.random_sample(n_companies)
    choice_idx = rng.choice(len(models), size=n_companies)

    # On limite le nombre d'événements par pas pour éviter un raz-de-marée
    # (important pour la jouabilité et la lisibilité des graphes).
    candidates = []
    for i in range(n_companies):
        prob = total_w
        if roll[i] >= prob:
            continue
        model = models[int(choice_idx[i])]
        # second tirage de confirmation (consume toujours)
        if rng.random_sample() < 0.55:
            candidates.append((i, model))

    # Trie par magnitude absolue décroissante pour prioriser les plus marquants
    # si on doit couper à _MAX_EVENTS_PER_STEP.
    candidates.sort(key=lambda t: abs(t[1]["magnitude"]), reverse=True)
    for i, model in candidates[:_MAX_EVENTS_PER_STEP]:
        ev = _instantiate(model, float(sigma_vec[i]), float(cap_vec[i]),
                          step_count, rng)
        shocks[i] = ev["shock"]
        events[i] = ev

    return shocks, events


def decay_residuals(active_events, n_companies):
    """Calcule le vecteur de drift résiduel pour le pas courant et met à jour
    les compteurs des événements actifs.

    Arguments :
        active_events : liste de taille n_companies ; active_events[i] est None
                        ou un dict événement dont `residual` et `steps_left` sont
                        mis à jour.

    Retourne :
        residual_shocks : vecteur numpy de drifts résiduels pour ce pas.
    """
    import numpy as np
    residual_shocks = np.zeros(n_companies)
    for i in range(n_companies):
        ev = active_events[i]
        if ev is None or ev.get("steps_left", 0) <= 0:
            continue
        residual_shocks[i] = ev["residual"] * (ev["steps_left"] / ev["decay"])
        ev["steps_left"] -= 1
    return residual_shocks


# -----------------------------------------------------------------------------
# Helpers de lecture
# -----------------------------------------------------------------------------
def localize_event(ev):
    """Renvoie un dict d'événement avec titre/description dans la langue courante
    (utile si l'événement a été stocké en FR et qu'on bascule en EN, ou inverse)."""
    if ev is None:
        return None
    model = EVENT_BY_ID.get(ev["id"])
    if model is None:
        return ev
    out = dict(ev)
    out["title"] = _L(*model["title"])
    out["desc"] = _L(*model["desc"])
    return out
