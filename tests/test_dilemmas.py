"""Tests des dilemmes (core/dilemmas.py)."""
import random

import pytest

from core import dilemmas
from core.game_state import PlayerState


def _player(grade_index=0, heat=0):
    p = PlayerState(grade_index=grade_index)
    p.heat = heat
    return p


def test_eligible_filters_by_min_grade():
    p = _player(grade_index=1)
    pool = dilemmas.eligible(p)
    assert all(d["min_grade"] <= 1 for d in pool)
    assert pool   # "missell"/"expenses" ont min_grade=1


def test_eligible_empty_below_lowest_min_grade():
    p = _player(grade_index=0)
    assert dilemmas.eligible(p) == []


def test_eligible_grows_with_grade():
    low = dilemmas.eligible(_player(grade_index=1))
    high = dilemmas.eligible(_player(grade_index=9))
    assert len(high) >= len(low)


def test_generate_returns_none_when_no_eligible_dilemma():
    p = _player(grade_index=0)
    result = dilemmas.generate(p, rng=random.Random(0))
    assert result is None


def test_generate_falls_back_to_full_pool_if_category_empty():
    p = _player(grade_index=1)
    result = dilemmas.generate(p, rng=random.Random(0), category="signature")
    # aucun dilemme "signature" n'a min_grade <= 1 : generate retombe sur le pool complet
    assert result is not None


def test_generate_scales_cash_by_grade():
    tmpl = next(d for d in dilemmas.DILEMMAS if d["id"] == "missell")
    for grade_index in (1, 5, 10):
        d = dilemmas.generate(_player(grade_index=grade_index), rng=random.Random(0),
                               category="ethique")
        scale = 1.0 + 0.5 * grade_index
        # on ne connaît pas forcément quel dilemme a été tiré, donc on retrouve
        # son template par id pour comparer cash_k * scale à l'option générée
        tmpl = next(t for t in dilemmas.DILEMMAS if t["id"] == d["id"])
        for opt, tmpl_opt in zip(d["options"], tmpl["options"]):
            assert opt["cash"] == pytest.approx(tmpl_opt["cash_k"] * 1000 * scale)


def test_generate_structure():
    p = _player(grade_index=5)
    d = dilemmas.generate(p, rng=random.Random(3))
    assert d["title"] and d["scenario"]
    assert len(d["options"]) >= 2
    for opt in d["options"]:
        assert "label" in opt and "outcome" in opt
        assert isinstance(opt["cash"], float)


def test_maybe_trigger_respects_probability():
    p = _player(grade_index=3)
    rng = random.Random(1)
    triggered = dilemmas.maybe_trigger(p, rng=rng, base_prob=1.0)
    assert triggered is not None
    assert p.pending_dilemmas == [triggered]


def test_maybe_trigger_never_fires_with_zero_probability():
    p = _player(grade_index=3)
    rng = random.Random(1)
    for _ in range(20):
        assert dilemmas.maybe_trigger(p, rng=rng, base_prob=0.0) is None
    assert p.pending_dilemmas == []


def test_maybe_trigger_skips_if_already_pending():
    p = _player(grade_index=3)
    p.pending_dilemmas.append({"id": "x"})
    rng = random.Random(1)
    assert dilemmas.maybe_trigger(p, rng=rng, base_prob=1.0) is None
    assert len(p.pending_dilemmas) == 1


def test_apply_choice_adjusts_cash_rep_heat_and_logs():
    p = _player(grade_index=2)
    p.cash = 1000.0
    d = dilemmas.generate(p, rng=random.Random(5))
    p.pending_dilemmas.append(d)
    opt = dilemmas.apply_choice(p, d, 0)
    assert opt["label"] == d["options"][0]["label"]
    assert p.cash == pytest.approx(1000.0 + d["options"][0]["cash"])
    assert p.pending_dilemmas == []
    assert p.decisions_log[-1]["title"] == d["title"]
    assert p.decisions_log[-1]["choice"] == opt["label"]
    assert p.journal   # career.log a écrit une entrée


def test_apply_choice_clamps_heat_between_0_and_100():
    p = _player(grade_index=2, heat=98)
    d = {"id": "z", "category": "ethique", "title": "Test",
         "options": [{"label": "A", "cash": 0, "rep": 0, "heat": 50, "outcome": "x"}]}
    dilemmas.apply_choice(p, d, 0)
    assert p.heat == 100


def test_maybe_investigate_decays_heat_when_low():
    p = _player(grade_index=2, heat=10)
    rng = random.Random(0)
    result = dilemmas.maybe_investigate(p, rng=rng)
    assert result is None
    assert p.heat == 9


def test_maybe_investigate_can_trigger_with_high_heat():
    p = _player(grade_index=2, heat=100)
    rng = random.Random(2)
    fired = False
    for _ in range(100):
        p.heat = 100
        p.cash = 1_000_000.0
        p.reputation = 80
        result = dilemmas.maybe_investigate(p, rng=rng)
        if result is not None:
            assert result["fine"] > 0
            assert result["rep_loss"] >= 6
            assert p.inbox   # message de conformité poussé
            fired = True
            break
    assert fired


def test_maybe_investigate_never_triggers_below_threshold():
    p = _player(grade_index=2, heat=54)
    rng = random.Random(3)
    for _ in range(50):
        result = dilemmas.maybe_investigate(p, rng=rng)
        assert result is None
        if p.heat == 0:
            break


def test_apply_choice_frm_certification_reduces_heat_gain():
    d = {"id": "z", "category": "ethique", "title": "Test",
         "options": [{"label": "A", "cash": 0, "rep": 0, "heat": 50, "outcome": "x"}]}
    p_plain = _player(grade_index=2, heat=0)
    dilemmas.apply_choice(p_plain, d, 0)
    p_frm = _player(grade_index=2, heat=0)
    p_frm.certs["FRM"] = 2  # niveau max (cf. certifications.PROGRAMS["FRM"]["levels"])
    dilemmas.apply_choice(p_frm, d, 0)
    assert p_frm.heat < p_plain.heat
    assert p_frm.heat == pytest.approx(50 * 0.85)


def _generate_with_id(p, dilemma_id, category):
    """generate() pioche au hasard dans la catégorie : on boucle jusqu'à
    obtenir le dilemme voulu pour disposer de ses options déjà mises à
    l'échelle (champ `cash`, pas le `cash_k` brut du template)."""
    for seed in range(200):
        d = dilemmas.generate(p, rng=random.Random(seed), category=category)
        if d is not None and d["id"] == dilemma_id:
            return d
    raise AssertionError(f"dilemme {dilemma_id} jamais généré")


def test_apply_choice_decline_mandate_removes_offer_and_boosts_a_rival():
    p = _player(grade_index=3)
    p.mandate_offers = [{"id": 1, "client": "Caisse XYZ", "capital": 1_000_000}]
    d = _generate_with_id(p, "mandate", "strategie")
    before = [r["score"] for r in (p.rivals or [])]
    dilemmas.apply_choice(p, d, 1)  # "Décliner pour rester concentré"
    assert p.mandate_offers == []
    after = [r["score"] for r in p.rivals]
    assert any(a > b for a, b in zip(after, before)) or not before


def test_apply_choice_accept_poach_weakens_a_rival():
    p = _player(grade_index=6)
    from core import rivals as rivals_mod
    rivals_mod.ensure(p)
    before = [r["score"] for r in p.rivals]
    d = _generate_with_id(p, "poach", "strategie")
    dilemmas.apply_choice(p, d, 0)  # "Le recruter"
    after = [r["score"] for r in p.rivals]
    assert any(a < b for a, b in zip(after, before))
