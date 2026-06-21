"""
score.py — Score composite de fin de run (logique pure, sans pygame).

Synthétise la carrière du joueur en 7 dimensions normalisées 0-100, lues
directement depuis les données déjà suivies par PlayerState (et quelques
accumulateurs minimaux ajoutés à cet effet — voir game_state.py) :

  performance       : croissance de la valeur nette (cash_history[0] -> finale)
  risque            : exposition au risque prise (VaR/vol du portefeuille si un
                      marché est fourni, sinon volatilité de cash_history)
  drawdown          : pire repli de valeur nette subi (finmath.max_drawdown)
  reputation        : réputation finale (déjà 0-100)
  conformite        : scrutin réglementaire (heat) + nb d'enquêtes subies
  qualite_execution : frais d'exécution cumulés + pénalités d'appel de marge,
                      rapportés à l'activité du joueur
  survie            : faillite/licenciement vs fin volontaire + longévité du run

Chaque sous-score est dans [0, 100] (100 = excellent). Le score composite est
une moyenne pondérée, accompagnée d'une note lettre. Aucune dépendance pygame :
testable en headless avec un PlayerState synthétique.
"""
from dataclasses import dataclass, field

from core import finmath


def _L(fr, en):
    from core.i18n import get_lang
    return en if get_lang() == "en" else fr

# Poids du composite (somme = 1.0) — performance et survie comptent le plus,
# car ce sont les deux dimensions qui déterminent si la carrière a "réussi".
WEIGHTS = {
    "performance": 0.25,
    "risque": 0.12,
    "drawdown": 0.13,
    "reputation": 0.15,
    "conformite": 0.13,
    "qualite_execution": 0.12,
    "survie": 0.10,
}

# Seuils pour la note lettre (borne inférieure incluse).
GRADE_THRESHOLDS = [
    (90, "S"), (80, "A"), (70, "B"), (60, "C"), (45, "D"), (30, "E"), (0, "F"),
]

_RANK_LABELS_RAW = {
    "S": ("Légende de la place", "Legend of the Street"),
    "A": ("Trader d'élite", "Elite trader"),
    "B": ("Professionnel solide", "Solid professional"),
    "C": ("Carrière honorable", "Honorable career"),
    "D": ("Parcours irrégulier", "Uneven track record"),
    "E": ("Carrière fragile", "Fragile career"),
    "F": ("Naufrage financier", "Financial wreck"),
}


def rank_label(grade):
    raw = _RANK_LABELS_RAW.get(grade)
    return _L(*raw) if raw else ""


def _clip(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def _score_performance(player):
    """Croissance de la valeur nette sur tout le run, normalisée en log pour
    ne pas saturer immédiatement sur de très gros multiples."""
    hist = list(getattr(player, "cash_history", None) or [])
    if len(hist) < 2:
        # run trop court pour juger : score neutre.
        return 50.0
    start = hist[0]
    end = hist[-1]
    if start <= 0:
        # capital de départ dégradé (rare) : juge sur le signe de la fin.
        return 100.0 if end > 0 else 0.0
    growth = end / start
    if growth <= 0:
        return 0.0
    import math
    # +100% de croissance (x2) -> ~75 ; x4 -> ~100 ; -50% -> ~25.
    score = 50.0 + 25.0 * math.log2(growth)
    return _clip(score)


def _score_risque(player, market=None):
    """Risque pris, mesuré par la VaR relative du book réel si un marché est
    fourni, sinon par la volatilité de la série de valeur nette. Score élevé
    = risque maîtrisé (faible exposition relative), pas absence de risque."""
    nw = None
    if market is not None:
        try:
            from core import portfolio as pf
            from core import risk as risk_mod
            nw = pf.net_worth(player, market)
            if nw and nw > 0:
                sim = risk_mod.simulate(player, market)
                var_frac = abs(sim["var"]) * 1e6 / nw
                # VaR (95%, 1 pas) à 2% de la valeur nette -> ~90 ; 10% -> ~50 ; 25%+ -> ~0.
                score = 100.0 - var_frac * 400.0
                return _clip(score)
        except Exception:
            pass
    hist = list(getattr(player, "cash_history", None) or [])
    if len(hist) < 3:
        return 70.0  # pas assez d'historique pour juger, score légèrement positif par défaut
    rets = [(hist[i] / hist[i - 1] - 1.0) for i in range(1, len(hist)) if hist[i - 1] > 0]
    if not rets:
        return 70.0
    import statistics
    vol = statistics.pstdev(rets) if len(rets) > 1 else 0.0
    # vol/pas de 1% -> ~90 ; 5% -> ~50 ; 10%+ -> ~0.
    score = 100.0 - vol * 100.0 * 10.0
    return _clip(score)


def _score_drawdown(player):
    """Pire repli de valeur nette subi (finmath.max_drawdown), inversé."""
    hist = list(getattr(player, "cash_history", None) or [])
    dd = finmath.max_drawdown(hist) if len(hist) >= 2 else 0.0
    # drawdown 10% -> ~80 ; 30% -> ~40 ; 50%+ -> ~0.
    score = 100.0 - dd * 200.0
    return _clip(score)


def _score_reputation(player):
    return _clip(float(getattr(player, "reputation", 50)))


def _score_conformite(player):
    """Scrutin réglementaire actuel + pénalité par enquête subie."""
    heat = float(getattr(player, "heat", 0))
    investigations = int(getattr(player, "investigations_count", 0))
    score = 100.0 - heat - investigations * 15.0
    return _clip(score)


def _score_qualite_execution(player):
    """Frais d'exécution + pénalités de marge, rapportés à la trésorerie de
    référence (record atteint) pour rester comparable entre petites et
    grosses carrières. Pénalise aussi les appels de marge répétés."""
    fees = float(getattr(player, "total_fees_paid", 0.0))
    margin_penalty = float(getattr(player, "total_margin_penalty", 0.0))
    margin_calls = int(getattr(player, "flags", {}).get("margin_call_count", 0))
    ref = max(float(getattr(player, "best_cash", 0.0)), 1.0)
    cost_frac = (fees + margin_penalty) / ref
    # coût cumulé = 1% de la référence -> ~90 ; 5% -> ~50 ; 10%+ -> ~0.
    score = 100.0 - cost_frac * 100.0 * 10.0
    score -= margin_calls * 5.0
    return _clip(score)


def _score_survie(player):
    """Fin de carrière propre (volontaire) vs forcée (faillite/licenciement),
    pondérée par la longévité du run (en trimestres)."""
    quarters = max(0, int(getattr(player, "quarter", 1)) - 1)
    longevity = _clip(quarters * 4.0, 0.0, 60.0)  # jusqu'à 15 trimestres -> 60 pts
    game_over = bool(getattr(player, "game_over", False))
    reason = getattr(player, "game_over_reason", "") or ""
    if not game_over:
        base = 100.0  # run en cours / fin volontaire : pas de sanction de survie
    elif "Faillite" in reason:
        base = 0.0
    elif "Réputation" in reason or "réputation" in reason.lower():
        base = 10.0
    else:
        base = 20.0
    # mélange : 70% issue, 30% longévité (une carrière forcée mais longue
    # reste meilleure qu'un échec immédiat).
    return _clip(0.7 * base + 0.3 * longevity)


@dataclass
class FinalScore:
    """Score composite de fin de run : 7 sous-scores (0-100) + total + grade."""
    performance: float = 0.0
    risque: float = 0.0
    drawdown: float = 0.0
    reputation: float = 0.0
    conformite: float = 0.0
    qualite_execution: float = 0.0
    survie: float = 0.0
    total: float = 0.0
    grade: str = "F"
    rank_label: str = ""
    breakdown: dict = field(default_factory=dict)

    def as_dict(self):
        return {
            "performance": self.performance,
            "risque": self.risque,
            "drawdown": self.drawdown,
            "reputation": self.reputation,
            "conformite": self.conformite,
            "qualite_execution": self.qualite_execution,
            "survie": self.survie,
            "total": self.total,
            "grade": self.grade,
            "rank_label": self.rank_label,
        }


def _letter_grade(total):
    for threshold, letter in GRADE_THRESHOLDS:
        if total >= threshold:
            return letter
    return "F"


def compute_final_score(player, market=None):
    """Calcule le score composite de fin de run pour `player`.
    `market` est optionnel : s'il est fourni (moteur de marché synchronisé),
    la dimension risque utilise la VaR réelle du book ; sinon elle retombe
    sur la volatilité de l'historique de valeur nette. N'altère aucun état
    du joueur — fonction pure, lecture seule."""
    sub = {
        "performance": _score_performance(player),
        "risque": _score_risque(player, market),
        "drawdown": _score_drawdown(player),
        "reputation": _score_reputation(player),
        "conformite": _score_conformite(player),
        "qualite_execution": _score_qualite_execution(player),
        "survie": _score_survie(player),
    }
    total = sum(sub[k] * WEIGHTS[k] for k in WEIGHTS)
    total = _clip(total)
    grade = _letter_grade(total)
    return FinalScore(
        performance=sub["performance"],
        risque=sub["risque"],
        drawdown=sub["drawdown"],
        reputation=sub["reputation"],
        conformite=sub["conformite"],
        qualite_execution=sub["qualite_execution"],
        survie=sub["survie"],
        total=total,
        grade=grade,
        rank_label=rank_label(grade),
        breakdown=dict(sub),
    )
