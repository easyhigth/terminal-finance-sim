"""
events.py — Moteur d'événements de marché (logique pure, sans pygame).

Un événement modifie le cash et/ou la réputation du joueur et apparaît dans
le flux d'actualités du terminal. Les événements sont tirés au sort à chaque
tour d'avancement du temps, pondérés et filtrés par région/grade.

Chaque modèle d'événement :
  id        : identifiant court
  title     : titre affiché
  desc      : description / explication
  kind      : "good" | "bad" | "info"
  cash      : (lo, hi) — delta de trésorerie tiré uniformément (peut être 0,0)
  rep       : (lo, hi) — delta de réputation tiré uniformément
  weight    : poids de sélection (plus grand = plus fréquent)
  regions   : liste de continents concernés, ou None pour tous
  min_grade : grade minimal pour que l'événement puisse survenir
  cash_scale: si True, le delta cash est multiplié par un facteur d'échelle
              dépendant du grade (les montants grossissent avec la carrière)
"""
import random


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


# Atténuateur global de l'impact cash des événements aléatoires legacy.
# Mis à 0 : dans la refonte « autour du marché », l'impact financier d'un choc
# passe par les VARIATIONS DE PRIX (et donc le portefeuille du joueur), pas par
# des montants forfaitaires. Les événements ne portent donc plus que la
# réputation + l'actualité ; le cash vient du salaire, des coûts et des deals.
EVENT_CASH_SCALE = 0.0
# La réputation se gagne surtout en travaillant (EVAL, deals, missions) ; les
# événements de marché ne l'influencent que légèrement.
EVENT_REP_SCALE = 0.4


EVENT_TEMPLATES = [
    # ----------------------------- favorables -----------------------------
    {"id": "bull_run", "title": ("Rallye haussier sur les indices", "Bullish rally on the indices"),
     "desc": ("Un afflux de liquidités propulse les marchés ; vos positions en profitent.",
              "A flood of liquidity propels the markets; your positions benefit."),
     "kind": "good", "cash": (20_000, 90_000), "rep": (1, 3),
     "weight": 8, "regions": None, "min_grade": 0, "cash_scale": True},

    {"id": "good_call", "title": ("Votre note d'analyse fait mouche", "Your research note hits the mark"),
     "desc": ("Une recommandation s'avère payante ; le desk vous félicite.",
              "A recommendation pays off; the desk congratulates you."),
     "kind": "good", "cash": (5_000, 25_000), "rep": (3, 6),
     "weight": 7, "regions": None, "min_grade": 0, "cash_scale": True},

    {"id": "mandate_won", "title": ("Mandat remporté face à un concurrent", "Mandate won against a competitor"),
     "desc": ("La firme décroche un mandat prestigieux. Honoraires à la clé.",
              "The firm lands a prestigious mandate. Fees follow."),
     "kind": "good", "cash": (40_000, 150_000), "rep": (4, 8),
     "weight": 4, "regions": None, "min_grade": 3, "cash_scale": True},

    {"id": "carry_paid", "title": ("Versement de carried interest", "Carried interest payout"),
     "desc": ("Un fonds arrivé à maturité distribue sa surperformance.",
              "A matured fund distributes its outperformance."),
     "kind": "good", "cash": (80_000, 300_000), "rep": (2, 4),
     "weight": 3, "regions": None, "min_grade": 4, "cash_scale": True},

    # ---------------------------- défavorables ----------------------------
    {"id": "selloff", "title": ("Correction brutale des marchés", "Brutal market correction"),
     "desc": ("Un choc de volatilité fait dévisser les actifs risqués.",
              "A volatility shock sends risky assets plunging."),
     "kind": "bad", "cash": (-90_000, -25_000), "rep": (-2, 0),
     "weight": 8, "regions": None, "min_grade": 0, "cash_scale": True},

    {"id": "fat_finger", "title": ("Erreur de saisie sur un ordre", "Fat-finger order error"),
     "desc": ("Un 'fat finger' coûte cher au desk. Le risk management enquête.",
              "A 'fat finger' costs the desk dearly. Risk management investigates."),
     "kind": "bad", "cash": (-40_000, -10_000), "rep": (-5, -2),
     "weight": 5, "regions": None, "min_grade": 0, "cash_scale": True},

    {"id": "margin_call", "title": ("Appel de marge inattendu", "Unexpected margin call"),
     "desc": ("Le prime broker exige du collatéral supplémentaire sous 24h.",
              "The prime broker demands extra collateral within 24h."),
     "kind": "bad", "cash": (-120_000, -40_000), "rep": (-3, -1),
     "weight": 4, "regions": None, "min_grade": 2, "cash_scale": True},

    {"id": "fine", "title": ("Sanction du régulateur", "Regulatory sanction"),
     "desc": ("Un manquement de conformité entraîne une amende.",
              "A compliance breach leads to a fine."),
     "kind": "bad", "cash": (-150_000, -50_000), "rep": (-8, -4),
     "weight": 3, "regions": None, "min_grade": 3, "cash_scale": True},

    # --------------------- régionaux (saveur locale) ----------------------
    {"id": "ecb_surprise", "title": ("Décision surprise de la BCE", "Surprise ECB decision"),
     "desc": ("Un changement de cap monétaire rebat les cartes sur les taux EUR.",
              "A monetary policy shift reshuffles EUR rates."),
     "kind": "bad", "cash": (-60_000, 30_000), "rep": (-1, 1),
     "weight": 5, "regions": ["Europe"], "min_grade": 1, "cash_scale": True},

    {"id": "fed_pivot", "title": ("Pivot de la Fed", "Fed pivot"),
     "desc": ("Le marché US s'emballe sur un changement de discours de la Fed.",
              "The US market surges on a shift in Fed rhetoric."),
     "kind": "good", "cash": (10_000, 70_000), "rep": (0, 2),
     "weight": 5, "regions": ["USA"], "min_grade": 1, "cash_scale": True},

    {"id": "hkd_peg", "title": ("Pression sur le peg du HKD", "Pressure on the HKD peg"),
     "desc": ("La HKMA intervient ; les flux transfrontaliers se tendent.",
              "The HKMA intervenes; cross-border flows tighten."),
     "kind": "bad", "cash": (-70_000, 10_000), "rep": (-2, 1),
     "weight": 5, "regions": ["Asia"], "min_grade": 1, "cash_scale": True},

    # ------------------------------ neutres -------------------------------
    {"id": "quiet", "title": ("Séance sans tendance", "Trendless session"),
     "desc": ("Volumes faibles, marchés en attente de catalyseurs.",
              "Low volumes, markets waiting for catalysts."),
     "kind": "info", "cash": (0, 0), "rep": (0, 0),
     "weight": 10, "regions": None, "min_grade": 0, "cash_scale": False},

    {"id": "networking", "title": ("Conférence sectorielle", "Industry conference"),
     "desc": ("Vous étoffez votre réseau ; léger gain de réputation.",
              "You grow your network; small reputation gain."),
     "kind": "info", "cash": (0, 0), "rep": (1, 2),
     "weight": 5, "regions": None, "min_grade": 0, "cash_scale": False},
]


def _scale_factor(player):
    """Les montants grossissent avec le grade (carrière de plus en plus lourde)."""
    return 1.0 + 0.6 * player.grade_index


def _eligible(player):
    out = []
    for t in EVENT_TEMPLATES:
        if t["min_grade"] > player.grade_index:
            continue
        if t["regions"] is not None and player.continent not in t["regions"]:
            continue
        out.append(t)
    return out


def _instantiate(template, player, rng):
    """Concrétise un modèle en événement avec montants tirés au sort + appliqués."""
    cash = rng.uniform(*template["cash"]) if template["cash"] != (0, 0) else 0.0
    if cash and template.get("cash_scale"):
        cash *= _scale_factor(player)
    cash *= EVENT_CASH_SCALE
    rep = rng.randint(*template["rep"]) if template["rep"] != (0, 0) else 0
    cash = round(cash, 2)
    # atténuation de l'effet réputation des événements (cf. EVENT_REP_SCALE)
    if rep:
        rep = int(round(rep * EVENT_REP_SCALE))
    title = _L(*template["title"])
    player.adjust_cash(cash, category="evenements")
    player.adjust_reputation(rep, reason=title)
    return {
        "id": template["id"],
        "title": title,
        "desc": _L(*template["desc"]),
        "kind": template["kind"],
        "cash": cash,
        "rep": rep,
    }


def roll_events(player, rng=None, max_events=2):
    """
    Tire 1 à `max_events` événements pondérés, applique leurs effets au joueur
    et retourne la liste des événements concrétisés (pour affichage).
    """
    rng = rng or random
    pool = _eligible(player)
    if not pool:
        return []
    n = rng.randint(1, max_events)
    weights = [t["weight"] for t in pool]
    chosen = []
    seen = set()
    attempts = 0
    while len(chosen) < n and attempts < n * 4:
        attempts += 1
        t = rng.choices(pool, weights=weights, k=1)[0]
        if t["id"] in seen:
            continue
        seen.add(t["id"])
        chosen.append(_instantiate(t, player, rng))
    return chosen
