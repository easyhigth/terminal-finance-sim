"""
certifications.py — Certifications professionnelles (CFA, FRM, CQF).

Passer une certification coûte des frais d'inscription et exige de réussir un
examen exigeant. Une certification liée à votre VOIE booste fortement la
réputation et accélère l'accès aux hauts postes (critères de promotion réduits).
Toutes les voies n'ont pas de certification — et c'est très bien.

État (PlayerState.certs) : {programme: niveau_obtenu}.
"""

PROGRAMS = {
    "CFA": {
        "name": "CFA", "full": "Chartered Financial Analyst",
        "track": "Portfolio", "levels": 3, "min_grade": 2,
        "fee": [15000, 25000, 40000], "rep": [5, 8, 12], "tier": 3,
        "desc": "Référence en gestion de portefeuille et analyse d'investissement.",
    },
    "FRM": {
        "name": "FRM", "full": "Financial Risk Manager",
        "track": "Risk", "levels": 2, "min_grade": 2,
        "fee": [20000, 35000], "rep": [8, 14], "tier": 4,
        "desc": "Référence en gestion des risques (marché, crédit, opérationnel).",
    },
    "CQF": {
        "name": "CQF", "full": "Certificate in Quantitative Finance",
        "track": "Quant", "levels": 1, "min_grade": 3,
        "fee": [45000], "rep": [16], "tier": 4,
        "desc": "Finance quantitative : dérivés, modèles stochastiques, ML.",
    },
    "ACI": {
        "name": "ACI", "full": "ACI Dealing Certificate",
        "track": None, "levels": 1, "min_grade": 5,
        "fee": [30000], "rep": [10], "tier": 4,
        "desc": "Référence des salles de marché en change (FX) : conventions de cotation, "
                "règlement, gestion du risque de change.",
    },
}

# Examen de certification : moins de questions mais plus dur, seuil plus élevé.
EXAM_N = 12
PASS_THRESHOLD = 0.75


def desc_for(program):
    """Description du programme dans la langue courante (FR par défaut)."""
    from core.i18n import get_lang
    if get_lang() == "en":
        from data.certifications_en import PROGRAMS_EN
        e = PROGRAMS_EN.get(program)
        if e:
            return e.get("desc", PROGRAMS[program]["desc"])
    return PROGRAMS[program]["desc"]


def level(player, program):
    return player.certs.get(program, 0)


def is_complete(player, program):
    return level(player, program) >= PROGRAMS[program]["levels"]


def status_label(player, program):
    from core.i18n import get_lang
    prog = PROGRAMS[program]
    lvl = level(player, program)
    en = get_lang() == "en"
    if lvl >= prog["levels"]:
        return "EARNED" if en else "OBTENU"
    return f"level {lvl}/{prog['levels']}" if en else f"niveau {lvl}/{prog['levels']}"


def can_attempt(player, program):
    """Retourne ('ok', fee, tier) ou un code d'erreur ('done'|'grade'|'cash')."""
    prog = PROGRAMS[program]
    lvl = level(player, program)
    if lvl >= prog["levels"]:
        return ("done", 0, 0)
    if player.grade_index < prog["min_grade"]:
        return ("grade", prog["min_grade"], 0)
    fee = prog["fee"][lvl]
    if player.cash < fee:
        return ("cash", fee, 0)
    return ("ok", fee, prog["tier"])


def pay_and_start(player, program):
    """Débite les frais d'inscription. Retourne (tier_examen, niveau_visé) ou None."""
    code, fee, tier = can_attempt(player, program)
    if code != "ok":
        return None
    player.adjust_cash(-fee, category="evenements")
    return tier, level(player, program)


def pass_stage(player, program):
    """Valide l'étape réussie : niveau +1, réputation, titre/badge si complet."""
    from core import career
    from core.i18n import get_lang
    en = get_lang() == "en"
    prog = PROGRAMS[program]
    lvl = level(player, program)
    if lvl >= prog["levels"]:
        return None
    player.certs[program] = lvl + 1
    player.adjust_reputation(prog["rep"][lvl], reason=(
        f"Certification: {prog['name']} level {lvl + 1}" if en
        else f"Certification : {prog['name']} niveau {lvl + 1}"))
    done = player.certs[program] >= prog["levels"]
    if done:
        title = f"{prog['name']} Charterholder"
        if title not in player.titles:
            player.titles.append(title)
        if en:
            career.log(player, "promo", f"Certification earned: {prog['name']} — {title}")
        else:
            career.log(player, "promo", f"Certification obtenue : {prog['name']} — {title}")
    else:
        if en:
            career.log(player, "info", f"{prog['name']} level {player.certs[program]} passed")
        else:
            career.log(player, "info", f"{prog['name']} niveau {player.certs[program]} réussi")
    return {"done": done, "rep": prog["rep"][lvl],
            "title": (f"{prog['name']} Charterholder" if done else None)}


def promotion_bonus(player):
    """Bonus de promotion si une certification COMPLÈTE correspond à la voie.
    Retourne (réduction_seuil_réputation, réduction_missions_requises)."""
    for prog_id, prog in PROGRAMS.items():
        if is_complete(player, prog_id) and prog["track"] == player.track:
            return (7, 1)
    return (0, 0)


def available_for(track):
    """Programmes pertinents pour une voie (les autres restent passables mais sans bonus)."""
    return [pid for pid, p in PROGRAMS.items() if p["track"] == track]
