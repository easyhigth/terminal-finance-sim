"""
histscenarios.py — Scénarios HISTORIQUES : runs courts scriptés (logique pure).

« Rejouez 2008 » : un preset = une graine de marché FIXE (tous les joueurs du
même scénario affrontent le même marché, comme le défi du jour), une CRISE
scriptée déclenchée à un pas précis via `core.scenarios.trigger_by_id`
(déterministe, sans rng), une position de départ imposée et un OBJECTIF de fin
(survivre et défendre sa valeur nette sur une durée donnée).

Choisi au setup de partie (scene_runsetup, sélecteur « Défi historique ») ;
l'état vit dans `player.flags["hist_scenario"]` :
    {"id", "fired": bool, "start_nw": float, "result": None|dict}
Le déclenchement et le verdict sont joués par le hook de pas
`hist_scenario` (core/step_hooks.py) — comme tout système du pas de marché.
"""
from core.i18n import get_lang


def _L(fr, en):
    return en if get_lang() == "en" else fr


# trigger_step / end_step sont RELATIFS au début de carrière (le marché
# démarre à market.WARMUP_STEPS ; le hook compare à market.step_count -
# WARMUP_STEPS). Objectif : nw_ratio_min = valeur nette finale minimale, en
# fraction de la valeur nette de départ, pour « réussir » le défi.
HIST_SCENARIOS = [
    {
        "id": "h2008",
        "name": ("Rejouez 2008", "Replay 2008"),
        "crisis_id": "krach", "severity": 1.6,
        "trigger_step": 10, "end_step": 46,        # ~3 ans de jeu après le choc
        "seed": 200_809_150,                        # 15/09/2008 — Lehman
        "cash": 800_000.0, "grade_index": 5,
        "nw_ratio_min": 0.85,
        "story": ("Septembre. Le crédit interbancaire se grippe, une grande banque "
                  "vacille. Vous êtes VP avec 800 K de capital : traversez le krach "
                  "systémique en préservant au moins 85 % de votre patrimoine.",
                  "September. Interbank credit seizes up, a major bank wobbles. "
                  "You are a VP with 800K in capital: get through the systemic "
                  "crash keeping at least 85% of your net worth."),
    },
    {
        "id": "h2023",
        "name": ("Choc de taux 2023", "2023 rate shock"),
        "crisis_id": "taux", "severity": 1.4,
        "trigger_step": 8, "end_step": 40,
        "seed": 202_303_100,                        # 10/03/2023 — SVB
        "cash": 600_000.0, "grade_index": 4,
        "nw_ratio_min": 0.90,
        "story": ("La banque centrale remonte les taux à marche forcée : banques "
                  "régionales et immobilier craquent. Protégez 90 % de votre "
                  "patrimoine pendant la purge.",
                  "The central bank hikes rates at a forced pace: regional banks "
                  "and real estate crack. Protect 90% of your net worth through "
                  "the purge."),
    },
    {
        "id": "hdotcom",
        "name": ("Bulle tech 2000", "Dot-com 2000"),
        "crisis_id": "techbust", "severity": 1.7,
        "trigger_step": 12, "end_step": 50,
        "seed": 200_003_100,                        # 10/03/2000 — pic du Nasdaq
        "cash": 500_000.0, "grade_index": 3,
        "nw_ratio_min": 0.85,
        "story": ("Les multiples de la tech défient la gravité — plus pour "
                  "longtemps. Éclatement de bulle violent : sortez-en avec au "
                  "moins 85 % de votre patrimoine.",
                  "Tech multiples defy gravity — not for long. A violent bubble "
                  "burst: come out with at least 85% of your net worth."),
    },
]

_BY_ID = {s["id"]: s for s in HIST_SCENARIOS}


def get(scenario_id):
    return _BY_ID.get(scenario_id)


def label(s):
    return _L(*s["name"])


def story(s):
    return _L(*s["story"])


def apply(player, scenario_id):
    """Configure un run sur un scénario historique : graine fixe, position de
    départ imposée, état de suivi dans les flags. À appeler au setup de
    partie APRÈS les autres presets (écrase graine/cash/grade)."""
    s = get(scenario_id)
    if s is None:
        return False
    player.market_seed = s["seed"]
    player.cash = s["cash"]
    player.grade_index = s["grade_index"]
    player.flags["hist_scenario"] = {"id": s["id"], "fired": False,
                                     "start_nw": None, "result": None}
    # pas de tutoriel au milieu d'un défi scripté court
    player.onboarding_done = True
    return True


def active(player):
    """État du scénario historique du run, ou None."""
    st = player.flags.get("hist_scenario")
    return st if isinstance(st, dict) and st.get("result") is None else None


def step(player, market, nw):
    """Joue la logique du scénario pour CE pas (appelé par le hook de pas,
    marché non-None) : mémorise l'ancre, déclenche la crise au pas prévu,
    rend le verdict au pas de fin. Retourne un évènement descriptif pour
    notification, ou None."""
    st = active(player)
    if st is None:
        return None
    s = get(st["id"])
    if s is None:
        player.flags.pop("hist_scenario", None)
        return None
    from core.market import WARMUP_STEPS
    rel = market.step_count - WARMUP_STEPS
    if st["start_nw"] is None:
        st["start_nw"] = nw if nw else player.cash
    if not st["fired"] and rel >= s["trigger_step"]:
        from core import scenarios as _scenarios
        crisis = _scenarios.trigger_by_id(market, s["crisis_id"], s["severity"])
        st["fired"] = True
        return {"kind": "crisis", "scenario": s, "crisis": crisis}
    if st["fired"] and rel >= s["end_step"]:
        ratio = (nw / st["start_nw"]) if st["start_nw"] else 0.0
        success = (not player.game_over) and ratio >= s["nw_ratio_min"]
        st["result"] = {"success": success, "ratio": round(ratio, 4)}
        from core import career
        verdict = _L("réussi", "passed") if success else _L("échoué", "failed")
        career.log(player, "good" if success else "warn",
                   _L(f"Défi historique « {label(s)} » {verdict} "
                      f"({ratio:.0%} du patrimoine préservé)",
                      f"Historical challenge “{label(s)}” {verdict} "
                      f"({ratio:.0%} of net worth preserved)"))
        return {"kind": "verdict", "scenario": s, "success": success, "ratio": ratio}
    return None
