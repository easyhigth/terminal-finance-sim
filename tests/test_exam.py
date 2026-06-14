"""Tests du générateur d'examens (core/exam.py), focalisés sur le tagging des
leçons (pour le débrief des erreurs) et la cohérence des items générés.
"""
import random

import pytest

from core import exam
from data import lessons as lessons_data


def test_generate_count_and_structure():
    items = exam.generate(2, rng=random.Random(0))
    assert len(items) == exam.num_questions(2)
    for it in items:
        assert it["kind"] in ("mcq", "fill", "text", "graph")
        assert it["prompt"]
        assert "lesson" in it          # tag présent (éventuellement None)


def test_tagged_lessons_exist_in_academy():
    """Toute leçon référencée par un item doit exister dans l'Académie."""
    seen = set()
    for tier in range(5):
        items = exam.generate(tier * 2, rng=random.Random(tier))
        for it in items:
            lid = exam.lesson_for_item(it)
            if lid:
                seen.add(lid)
                assert lessons_data.get(lid) is not None
    assert seen  # au moins quelques items sont taggés


def test_gen_lesson_targets_are_valid():
    """Le mapping générateur->leçon ne pointe que sur des leçons réelles."""
    for lid in set(exam.GEN_LESSON.values()):
        assert lessons_data.get(lid) is not None


def test_glossary_generator_marks_correct_term():
    g = exam.g_glossary(random.Random(5))
    assert g["kind"] == "mcq" and len(g["choices"]) == 4
    # la réponse pointe sur un terme réel du glossaire
    from data.glossary_data import GLOSSARY
    assert g["choices"][g["answer"]] in GLOSSARY


def test_new_calc_generators_solvable():
    """Les nouveaux générateurs chiffrés produisent une réponse numérique cohérente."""
    rng = random.Random(7)
    for gen in (exam.g_gordon, exam.g_forward, exam.g_real_rate, exam.g_expected_loss,
                exam.g_treynor, exam.g_dscr, exam.g_cet1, exam.g_roll, exam.g_drawdown):
        it = gen(rng)
        assert it["kind"] == "fill" and isinstance(it["answer"], float)
        assert it["prompt"] and it["expl"]


def test_pass_threshold_constant():
    assert 0 < exam.PASS_THRESHOLD < 1
