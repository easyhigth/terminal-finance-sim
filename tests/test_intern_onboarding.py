"""
Garde-fou de la PREMIÈRE HEURE (stagiaire) : après avoir rendu l'Intern minimal
et étalé les déblocages, ce test verrouille l'expérience de départ — le bureau
réduit, la boucle mission→réputation→examen fonctionnelle, et la carotte de
progression visible. Il protège tout ce remodelage contre une régression future.
"""
import random

from core import exam_flow, missions, todo, unlocks
from core.game_state import PlayerState
from scenes.scene_desktop_common import APPS, ICON_FEATURE, QUICK_APPS

_FACTORY_ONLY = {"dilemma", "review", "evaluation", "deals", "company",
                 "shop", "analytics", "explorer"}

# Le bureau du stagiaire : QUE les basiques (apprendre, faire ses missions,
# passer l'examen ; le Terminal sert de fenêtre sur le marché).
INTERN_ICONS = {"terminal", "mission", "qexamcert", "qdecide",
                "inbox", "manual", "save", "qcommands"}


def _visible_icons(grade):
    p = PlayerState()
    p.grade_index = grade
    keys = ["terminal"] + [k for k, _l, _kd, _c in APPS] + [k for k, _l, _kd, _s in QUICK_APPS]
    return {k for k in keys if k not in _FACTORY_ONLY
            and (ICON_FEATURE.get(k) is None or unlocks.unlocked(p, ICON_FEATURE.get(k)))}


def test_intern_desktop_is_the_bare_minimum():
    assert _visible_icons(0) == INTERN_ICONS


def test_no_analysis_or_trading_tools_at_intern():
    v = _visible_icons(0)
    for k in ("markethub", "book", "trading", "research", "watchlist",
              "qgraph", "qshop", "qexplorer", "vardesk", "sheet"):
        assert k not in v, k


def test_grade_one_unlocks_the_investing_analyst_kit():
    gained = _visible_icons(1) - _visible_icons(0)
    assert {"markethub", "book", "trading", "research", "watchlist", "qgraph"} <= gained


def test_intern_core_loop_is_playable():
    p = PlayerState()
    p.grade_index = 0
    # une mission est jouable dès le premier jour
    m = missions.generate(0, market=None, rng=random.Random(1), player=p)
    assert m["items"]
    # un examen de promotion est servable
    items, thr, target = exam_flow.serve(p)
    assert items and 0 < thr <= 1 and target


def test_progression_carrot_is_visible_from_day_one():
    p = PlayerState()
    p.grade_index = 0
    hints = [it for it in todo.suggestions(p) if it.get("kind") == "hint"]
    assert hints, "le widget À FAIRE doit montrer le prochain déblocage"
    assert "Junior Analyst" in hints[0]["label"]
    assert hints[0]["scene"] == "unlockhistory"


def test_perfect_mission_rewards_are_meaningful():
    p = PlayerState()
    p.grade_index = 0
    m = missions.generate(0, market=None, rng=random.Random(2), player=p)
    total = len(m["items"])
    rep, cash = missions.compute_rewards(m, total, total, player=p)
    assert rep >= 1 and cash > 0
