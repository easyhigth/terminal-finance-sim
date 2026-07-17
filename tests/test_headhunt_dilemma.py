"""Tests du dilemme « Offre d'une firme rivale » (core/dilemmas.py, id
headhunt) : le seul dilemme dont une option CHANGE la firme du joueur (et
ses perks), une autre augmente le salaire fixe, la troisième trace la
loyauté."""
import random

from core import dilemmas, firms
from core.game_state import PlayerState


def _instance(p):
    tmpl = next(d for d in dilemmas.DILEMMAS if d["id"] == "headhunt")
    rng = random.Random(1)
    # generate() avec un pool filtré sur ce template
    scale = 1.0 + 0.5 * p.grade_index
    options = [{"label": o["label"], "cash": o["cash_k"] * 1000 * scale,
                "rep": o["rep"], "heat": o["heat"], "outcome": o["outcome"]}
               for o in tmpl["options"]]
    del rng
    return {"id": tmpl["id"], "category": tmpl["category"], "title": tmpl["title"],
            "scenario": tmpl["scenario"], "options": options}


def _player():
    p = PlayerState()
    p.grade_index = 4
    p.cash = 100_000.0
    p.firm = firms.FIRMS[0]["id"]
    return p


def test_accept_transfer_changes_firm_and_pays_bonus():
    p = _player()
    old_firm = p.firm
    d = _instance(p)
    p.pending_dilemmas.append(d)
    dilemmas.apply_choice(p, d, 0)
    assert p.firm != old_firm
    assert p.firm in {f["id"] for f in firms.FIRMS}
    assert p.cash > 100_000.0          # prime de transfert encaissée
    assert not p.pending_dilemmas


def test_decline_marks_loyalty():
    p = _player()
    d = _instance(p)
    p.pending_dilemmas.append(d)
    dilemmas.apply_choice(p, d, 1)
    assert p.firm == firms.FIRMS[0]["id"]   # on reste
    assert p.flags.get("loyalty_proven") == 1


def test_counter_offer_raises_base_salary():
    p = _player()
    before = p.salary_bonus_per_step
    d = _instance(p)
    p.pending_dilemmas.append(d)
    dilemmas.apply_choice(p, d, 2)
    assert p.salary_bonus_per_step > before
    assert p.firm == firms.FIRMS[0]["id"]


def test_headhunt_is_eligible_from_grade_3():
    p = _player()
    p.grade_index = 2
    assert "headhunt" not in {d["id"] for d in dilemmas.eligible(p)}
    p.grade_index = 3
    assert "headhunt" in {d["id"] for d in dilemmas.eligible(p)}


def test_decision_is_logged():
    p = _player()
    d = _instance(p)
    p.pending_dilemmas.append(d)
    dilemmas.apply_choice(p, d, 1)
    assert any(e["title"] == "Offre d'une firme rivale" for e in p.decisions_log)
