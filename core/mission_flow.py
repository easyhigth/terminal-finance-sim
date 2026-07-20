"""
mission_flow.py — Résultat d'une mission (logique pure, sans pygame), partagé
par la scène plein écran (`scenes/scene_mission.py`) et l'app native
(`apps/app_mission.py`). Même principe que core/exam_flow pour les examens : la
logique métier (récompenses, marquage des questions, journal, avancée du temps)
vivait en double, à maintenir des deux côtés — elle vit désormais ici.

`apply_result(app, mission, score)` applique tout et retourne :
    {"rep_gain", "cash_gain", "toasts": [(texte, kind), ...]}
L'UI n'a plus qu'à mémoriser les gains (écran de récap) et jouer les toasts.
"""
from core import config


def apply_result(app, mission, score):
    from core import career, missions, question_log
    p = app.gs.player
    # les questions de banque servies ne seront jamais reposées (mission ou examen)
    question_log.mark_seen(p, [it for it in mission["items"] if it.get("src_id")])
    total = len(mission["items"])
    rep_gain, cash_gain = missions.compute_rewards(mission, score, total, player=p)
    p.adjust_reputation(rep_gain, reason=f"Mission : {mission.get('title', '')}")
    p.adjust_cash(cash_gain)
    p.missions_done += 1
    p.grade_missions += 1
    if score == total:
        career.log(p, "info", f"Mission '{mission['title']}' réussie ({score}/{total}).")
    # une mission prend du temps : le terminal avancera d'un tour au retour
    app.pending_market_steps += 1
    if not p.hardcore:
        app.gs.save(config.AUTOSAVE_SLOT)
    return {"rep_gain": rep_gain, "cash_gain": cash_gain,
            "toasts": [(f"Mission : +{rep_gain} réputation", "good")]}
