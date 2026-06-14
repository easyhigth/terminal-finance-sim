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


def test_pass_threshold_constant():
    assert 0 < exam.PASS_THRESHOLD < 1
