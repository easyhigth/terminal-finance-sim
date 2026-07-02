"""
story_arcs.py — Arcs narratifs de l'inbox (logique pure, sans pygame).

De petites histoires en 3 messages (data/story_arcs.py) étalées sur des
semaines de jeu — un mentor, une journaliste, un petit client inquiet — avec
un dénouement à léger effet (réputation / trésorerie via `adjust_*`, catégorie
d'attribution "relations"). Par opposition aux évènements mécaniques
(mandats, crises), un arc a une CONTINUITÉ : le même expéditeur revient, et la
partie gagne une mémoire.

Déterminisme : le déclenchement et l'espacement sont dérivés du pas de marché
(`market.step_count`) et de l'ordre fixe des ARCS — pas de tirage non seedé.
Un arc démarre tous les `ARC_INTERVAL` pas (premier à `FIRST_ARC_STEP` pas
après le début de carrière), tant qu'il reste des arcs non joués. État dans
`player.flags` : "story_arc" (arc actif : id/stage/next_step) et
"story_arcs_done" (ids terminés) — JSON-sérialisable, persiste au save.

`on_step(player, market)` est appelé à CHAQUE pas par le moteur du terminal
(scenes/scene_terminal_time.py) et retourne la liste des messages livrés ce
pas ({"sender","subject","finale":bool}) pour le log/toast.
"""
from core import inbox
from data.story_arcs import ARCS

ARC_INTERVAL = 22      # pas entre deux départs d'arc (~110 jours de jeu)
FIRST_ARC_STEP = 6     # premier arc peu après le début de carrière (~30 jours)

_BY_ID = {a["id"]: a for a in ARCS}


def _career_step(player, market):
    """Pas écoulés depuis le DÉBUT DE CARRIÈRE (le marché démarre avec un
    passé de WARMUP_STEPS pas, cf. scene_runsetup)."""
    from core.market import WARMUP_STEPS
    start = WARMUP_STEPS if player.market_step >= WARMUP_STEPS else 0
    return market.step_count - start


def _next_arc(player):
    done = player.flags.get("story_arcs_done", [])
    for arc in ARCS:
        if arc["id"] not in done:
            return arc
    return None


def _deliver(player, arc, stage_idx):
    """Livre le message du stage dans l'inbox ; applique l'effet au dernier."""
    stage = arc["stages"][stage_idx]
    inbox.push(player, stage["category"], stage["sender"],
               stage["subject"], stage["body"])
    finale = stage_idx == len(arc["stages"]) - 1
    if finale:
        eff = arc.get("effect") or {}
        if eff.get("rep"):
            player.adjust_reputation(eff["rep"], reason=eff.get("reason"))
        if eff.get("cash"):
            player.adjust_cash(eff["cash"], category="relations")
    return {"sender": stage["sender"], "subject": stage["subject"], "finale": finale}


def on_step(player, market):
    """Avance la machine à arcs d'un pas de marché. Retourne les messages
    livrés ce pas (souvent 0 ou 1)."""
    delivered = []
    step = market.step_count
    state = player.flags.get("story_arc")

    # arc actif : livrer le stage arrivé à échéance
    if state:
        arc = _BY_ID.get(state.get("id"))
        if arc is None:                      # contenu retiré : on abandonne
            player.flags["story_arc"] = None
        elif step >= state.get("next_step", 0):
            idx = state.get("stage", 0)
            delivered.append(_deliver(player, arc, idx))
            if idx + 1 >= len(arc["stages"]):
                done = list(player.flags.get("story_arcs_done", []))
                done.append(arc["id"])
                player.flags["story_arcs_done"] = done
                player.flags["story_arc"] = None
            else:
                player.flags["story_arc"] = {
                    "id": arc["id"], "stage": idx + 1,
                    "next_step": step + arc["stages"][idx + 1]["delay"],
                }
        return delivered

    # pas d'arc actif : en démarrer un à cadence fixe, s'il en reste
    cstep = _career_step(player, market)
    if cstep < FIRST_ARC_STEP or (cstep - FIRST_ARC_STEP) % ARC_INTERVAL != 0:
        return delivered
    arc = _next_arc(player)
    if arc is None:
        return delivered
    player.flags["story_arc"] = {
        "id": arc["id"], "stage": 0,
        "next_step": step + arc["stages"][0]["delay"],
    }
    return delivered
