"""
missions.py — Missions par grade (logique pure, sans pygame).

Chaque mission est un tirage de questions de la banque d'examens
(data/question_bank.py), filtrées et pondérées par grade — ce qui garantit
de la variété d'une mission à l'autre plutôt que des templates figés.
Le grade détermine seulement le "tier" (thème affiché : compte-rendu,
graphe, décision, portefeuille) via mission_tier().

Chaque mission rapporte de la RÉPUTATION (proportionnelle au score) et un petit
honoraire. Un seuil de réputation par grade débloque l'examen de promotion (EVAL).

Structures (dicts, transitoires — non sauvegardées) :
  Item  : {kind: "fill"|"mcq", prompt, choices?, answer, tol?/abstol?, unit?, expl, chart?}
  Mission: {grade, kind, title, brief, items, reward_rep, reward_cash, charts}
"""
import random

from data import question_bank

MAX_ITEMS = 5


def _L(fr, en):
    """Renvoie la version FR ou EN selon la langue courante du jeu."""
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr


# Seuil de réputation requis pour tenter l'EVAL, par grade (croissant).
def reputation_threshold(grade_index):
    return min(92, 58 + grade_index * 2)


def mission_tier(grade_index):
    """Type de mission selon le grade (échelle de 12 grades)."""
    if grade_index <= 1:        # Intern, Junior Analyst
        return "report"
    if grade_index <= 3:        # Analyst, Senior Analyst
        return "graph"
    if grade_index <= 5:        # Associate, Senior Associate
        return "decision"
    return "portfolio"          # VP et au-delà


# Réputation de base accordée pour une mission parfaite (croît avec le grade).
def _rep_base(grade_index):
    return 5 + grade_index // 2


# ---------------------------------------------------------------------------
# Helpers de construction d'items
# ---------------------------------------------------------------------------
def _mcq(prompt, choices, correct_idx, expl, rng, chart=None):
    order = list(range(len(choices)))
    rng.shuffle(order)
    shuffled = [choices[i] for i in order]
    return {"kind": "mcq", "prompt": prompt, "choices": shuffled,
            "answer": order.index(correct_idx), "expl": expl, "chart": chart}


def check_fill(item, value):
    """Vrai si la valeur saisie est dans la tolérance de la réponse attendue."""
    ans = item["answer"]
    if item.get("abstol") is not None:
        return abs(value - ans) <= item["abstol"]
    return abs(value - ans) <= max(1e-9, abs(ans) * item.get("tol", 0.05))


def _bank_items(grade_index, rng, count):
    """Pioche `count` questions de la banque d'examens (déjà rng-aware, donc
    déterministe) et les adapte au format d'item de mission."""
    from core.i18n import get_lang
    picked = question_bank.for_grade(grade_index, "General", count, rng=rng, lang=get_lang())
    return [_mcq(q["q"], list(q["choices"]), q["answer"], q["expl"], rng) for q in picked]


_TIER_TITLES = {
    "report": ("Compte-rendu d'analyse", "Analyst report"),
    "graph": ("Lecture de marché", "Market reading"),
    "decision": ("Décisions d'investissement", "Investment decisions"),
    "portfolio": ("Construction & couverture de portefeuille",
                  "Portfolio construction & hedging"),
}
_TIER_BRIEFS = {
    "report": ("Répondez aux questions de fond pour démontrer votre maîtrise des bases.",
               "Answer the fundamentals questions to show you've mastered the basics."),
    "graph": ("Analysez les marchés et justifiez vos réponses.",
              "Analyze the markets and justify your answers."),
    "decision": ("Pour chaque question, tranchez en mobilisant votre jugement d'investisseur.",
                 "For each question, decide using your investor judgment."),
    "portfolio": ("Décisions d'allocation et de hedging. À ce niveau, vous arbitrez "
                  "l'exposition au risque de marché, de change et de concentration.",
                  "Allocation and hedging decisions. At this level, you manage "
                  "exposure to market, currency and concentration risk."),
}


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def generate(grade_index, market, rng=None, region=None):
    """Génère une mission adaptée au grade courant : un tirage de questions
    de la banque d'examens (jusqu'à MAX_ITEMS), thématisé par mission_tier()."""
    rng = rng or random
    tier = mission_tier(grade_index)
    title = _L(*_TIER_TITLES[tier])
    brief = _L(*_TIER_BRIEFS[tier])
    items = _bank_items(grade_index, rng, MAX_ITEMS)
    return {"grade": grade_index, "kind": tier, "title": title, "brief": brief,
            "items": items, "reward_rep": _rep_base(grade_index), "reward_cash": 0,
            "charts": {}}


def grade_focus(grade_index):
    """Phrase décrivant l'objectif du grade (pour l'UI), selon le tier."""
    tier = mission_tier(grade_index)
    return _L(
        {
            "report": "Comprendre et organiser les données, produire des comptes-rendus.",
            "graph": "Lire les graphes, mesurer performance et risque.",
            "decision": "Décider d'investir, conserver ou vendre.",
            "portfolio": "Construire et couvrir des portefeuilles, arbitrer le risque.",
        }[tier],
        {
            "report": "Understand and organize data, produce reports.",
            "graph": "Read charts, measure performance and risk.",
            "decision": "Decide whether to buy, hold or sell.",
            "portfolio": "Build and hedge portfolios, manage risk.",
        }[tier],
    )


def compute_rewards(mission, correct, total):
    """Réputation + honoraire en fonction du score (ratio de bonnes réponses)."""
    ratio = correct / max(1, total)
    rep = int(round(mission["reward_rep"] * ratio))
    if correct > 0:
        rep = max(rep, 1)
    # honoraire de conseil, croissant avec le grade
    cash = round(9000 * (1 + mission["grade"]) * ratio, 2)
    return rep, cash
