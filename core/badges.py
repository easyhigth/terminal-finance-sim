"""
badges.py — Succès / prestige (logique pure, sans pygame).

Des badges se débloquent en franchissant des jalons (grade, deals, valeur nette,
intégrité, crises survécues, 1ʳᵉ place du classement…). Ils récompensent et
matérialisent la montée en puissance. Stockés dans player.badges (liste d'ids).

check_new(player, market) attribue les nouveaux badges et les retourne pour
affichage (toast + journal).
"""

# Chaque badge : id, name, desc, test(player, market) -> bool
BADGES = [
    {"id": "first_deal", "name": "Premier deal", "desc": "Conclure votre premier deal.",
     "test": lambda p, m: p.deals_won >= 1},
    {"id": "dealmaker", "name": "Dealmaker", "desc": "Conclure 10 deals.",
     "test": lambda p, m: p.deals_won >= 10},
    {"id": "rainmaker", "name": "Rainmaker", "desc": "Conclure 25 deals.",
     "test": lambda p, m: p.deals_won >= 25},
    {"id": "scholar", "name": "Érudit", "desc": "Réaliser 15 missions.",
     "test": lambda p, m: p.missions_done >= 15},
    {"id": "analyst", "name": "Analyste confirmé", "desc": "Atteindre le grade Analyst.",
     "test": lambda p, m: p.grade_index >= 2},
    {"id": "vp", "name": "Vice President", "desc": "Atteindre le grade VP.",
     "test": lambda p, m: p.grade_index >= 6},
    {"id": "partner", "name": "Partner", "desc": "Atteindre le sommet : Partner.",
     "test": lambda p, m: p.grade_index >= 11},
    {"id": "millionaire", "name": "Millionnaire", "desc": "Valeur nette ≥ 1M.",
     "test": lambda p, m: max(p.best_cash, p.cash) >= 1_000_000},
    {"id": "tycoon", "name": "Magnat", "desc": "Valeur nette ≥ 10M.",
     "test": lambda p, m: max(p.best_cash, p.cash) >= 10_000_000},
    {"id": "survivor", "name": "Rescapé", "desc": "Traverser une crise de marché.",
     "test": lambda p, m: p.flags.get("crises", 0) >= 1},
    {"id": "veteran", "name": "Vétéran", "desc": "Traverser 3 crises.",
     "test": lambda p, m: p.flags.get("crises", 0) >= 3},
    {"id": "centurion", "name": "Endurance", "desc": "Survivre plus d'un an (365 j).",
     "test": lambda p, m: p.day >= 365},
    {"id": "clean_hands", "name": "Mains propres", "desc": "Réputation ≥ 85 sans scrutin, 10 missions.",
     "test": lambda p, m: p.reputation >= 85 and p.heat == 0 and p.missions_done >= 10},
    {"id": "titled", "name": "Signature", "desc": "Obtenir un titre de prestige.",
     "test": lambda p, m: len(p.titles) >= 1},
    {"id": "top_dog", "name": "Numéro un", "desc": "Dominer le classement des rivaux.",
     "test": lambda p, m: _is_top(p, m)},
    {"id": "mandate1", "name": "Gestionnaire", "desc": "Réussir un mandat client.",
     "test": lambda p, m: p.flags.get("mandates_won", 0) >= 1},
    {"id": "mandate_master", "name": "Gérant d'élite", "desc": "Réussir 3 mandats clients.",
     "test": lambda p, m: p.flags.get("mandates_won", 0) >= 3},
    {"id": "diversified", "name": "Diversifié", "desc": "Détenir des positions dans 5 secteurs.",
     "test": lambda p, m: len(_pf_alloc(p, m)) >= 5},
    {"id": "analyst_pro", "name": "Œil de l'analyste", "desc": "Produire 8 recherches.",
     "test": lambda p, m: len(p.research) >= 8},
    {"id": "graduate", "name": "Diplômé", "desc": "Lire toutes les leçons de l'Académie.",
     "test": lambda p, m: _all_lessons(p)},
    {"id": "certified", "name": "Certifié", "desc": "Obtenir une certification (CFA/FRM/CQF).",
     "test": lambda p, m: _has_full_cert(p)},
    {"id": "hedged", "name": "Parapluie prêt", "desc": "Souscrire un put protecteur.",
     "test": lambda p, m: len(getattr(p, "hedges", []) or []) >= 1},
    {"id": "hedge_in_the_money", "name": "Bien couvert", "desc": "Détenir un put protecteur actuellement dans la monnaie.",
     "test": lambda p, m: _has_itm_hedge(p, m)},
    {"id": "swapper", "name": "Cambiste", "desc": "Conclure un swap de devises.",
     "test": lambda p, m: len(getattr(p, "currency_swaps", []) or []) >= 1},
    {"id": "contagion_trader", "name": "Sang-froid crypto", "desc": "Détenir une crypto du groupe corrélé pendant un depeg actif, sans stablecoin décroché en portefeuille.",
     "test": lambda p, m: _traded_through_contagion(p, m)},
]


def _has_full_cert(player):
    try:
        from core import certifications as C
        return any(C.is_complete(player, pid) for pid in C.PROGRAMS)
    except Exception:
        return False


def _all_lessons(player):
    try:
        from data.lessons import LESSONS
        return len(player.learned) >= len(LESSONS)
    except Exception:
        return False


def _pf_alloc(player, market):
    try:
        from core import portfolio
        return portfolio.allocation_by(player, market, "sector")
    except Exception:
        return {}

def _has_itm_hedge(player, market):
    try:
        from core import hedging
        return any(h.get("in_money") for h in hedging.holdings(player, market))
    except Exception:
        return False


def _traded_through_contagion(player, market):
    try:
        from core import crypto
        depegged = set(crypto.active_depegs(market))
        if not depegged:
            return False
        held = getattr(player, "crypto", {}) or {}
        if any(cid in depegged for cid in held):
            return False
        return any(cid in crypto.CONTAGION_GROUP for cid in held)
    except Exception:
        return False


_BY_ID = {b["id"]: b for b in BADGES}


def _is_top(player, market):
    if not player.rivals:
        return False
    try:
        from core import rivals
        rank, _ = rivals.player_rank(player, market)
        return rank == 1
    except Exception:
        return False


def check_new(player, market):
    """Attribue les badges nouvellement mérités. Retourne la liste des badges gagnés."""
    earned = []
    for b in BADGES:
        if b["id"] in player.badges:
            continue
        try:
            ok = b["test"](player, market)
        except Exception:
            ok = False
        if ok:
            player.badges.append(b["id"])
            earned.append(b)
    return earned


def get(badge_id):
    return _BY_ID.get(badge_id)


def all_badges():
    return BADGES
