"""Tests pour data/question_bank.py — intégrité de la banque de questions
d'examen et couverture des nouveaux systèmes (ordres conditionnels stop-loss/
take-profit, sessions de cotation régionales)."""
from data import question_bank as qb
from data.question_bank_en import QUESTIONS_EN


def test_all_ids_unique():
    ids = [q["id"] for q in qb.QUESTIONS]
    assert len(ids) == len(set(ids))


def test_answer_index_within_choices():
    for q in qb.QUESTIONS:
        assert 0 <= q["answer"] < len(q["choices"])


def test_every_question_has_english_translation():
    for q in qb.QUESTIONS:
        assert q["id"] in QUESTIONS_EN, q["id"]
        e = QUESTIONS_EN[q["id"]]
        assert e["q"] and e["choices"] and e["expl"]
        assert len(e["choices"]) == len(q["choices"])


def test_localized_en_keeps_metadata_but_swaps_text():
    fr_by_id = {q["id"]: q for q in qb.QUESTIONS}
    for q in qb.localized("en"):
        fr = fr_by_id[q["id"]]
        assert q["grade"] == fr["grade"]
        assert q["track"] == fr["track"]
        assert q["answer"] == fr["answer"]
        assert q["q"] == QUESTIONS_EN[q["id"]]["q"]


def test_stop_loss_and_take_profit_questions_present():
    ids = {q["id"] for q in qb.QUESTIONS}
    assert "q59" in ids and "q60" in ids
    stop = qb.QUESTIONS[[q["id"] for q in qb.QUESTIONS].index("q59")]
    take = qb.QUESTIONS[[q["id"] for q in qb.QUESTIONS].index("q60")]
    assert "stop-loss" in stop["q"].lower()
    assert "take-profit" in take["q"].lower()
    assert stop["track"] == "General" and take["track"] == "General"


def test_trading_sessions_question_present_and_available_at_intern_grade():
    q61 = next(q for q in qb.QUESTIONS if q["id"] == "q61")
    assert q61["grade"] == 0
    pool = qb.available_pool(0, "General", "fr")
    assert any(q["id"] == "q61" for q in pool)


def test_new_questions_reachable_via_for_grade(monkeypatch):
    import random
    rng = random.Random(1)
    picked_ids = set()
    for _ in range(200):
        chosen = qb.for_grade(1, "General", count=5, rng=rng)
        picked_ids.update(q["id"] for q in chosen)
    assert "q59" in picked_ids
    assert "q60" in picked_ids
