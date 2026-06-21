from core import fuzzy


def test_score_empty_query_matches_everything_neutrally():
    assert fuzzy.score("", "Quant Lab") == 0
    assert fuzzy.score("   ", "Quant Lab") == 0


def test_score_none_when_not_a_subsequence():
    assert fuzzy.score("xyz", "Quant Lab") is None


def test_score_case_insensitive_subsequence_match():
    assert fuzzy.score("qtl", "Quant Lab") is not None


def test_score_higher_for_prefix_match():
    s_prefix = fuzzy.score("quant", "Quant Lab")
    s_mid = fuzzy.score("ant", "Quant Lab")
    assert s_prefix > s_mid


def test_score_higher_for_contiguous_characters():
    s_contig = fuzzy.score("qua", "Quant Lab")
    s_scattered = fuzzy.score("qab", "Quant Lab")
    assert s_contig > s_scattered


def test_score_word_start_bonus():
    s_word_start = fuzzy.score("l", "Quant Lab")   # "L" démarre un mot
    s_mid_word = fuzzy.score("a", "Quant Lab")      # "a" est en milieu de mot (premier "a")
    assert s_word_start > s_mid_word


def test_filter_sorted_keeps_only_matches_and_sorts_by_score():
    items = [("Quant Lab", "quant"), ("Quantitative Models", "qmodels"),
             ("Glossary", "glossary"), ("Quarterly Report", "qreport")]
    out = fuzzy.filter_sorted("quant", items, key=lambda e: e[0])
    labels = [label for label, _ in out]
    assert "Glossary" not in labels        # pas de "q" du tout
    assert "Quarterly Report" not in labels  # pas de "n" (Quarterly/Report)
    assert labels[0] == "Quant Lab"  # préfixe exact -> meilleur score
    assert set(labels) == {"Quant Lab", "Quantitative Models"}


def test_filter_sorted_empty_query_returns_all_in_original_order():
    items = [("B", 1), ("A", 2), ("C", 3)]
    out = fuzzy.filter_sorted("", items, key=lambda e: e[0])
    assert out == items


def test_filter_sorted_stable_order_for_equal_scores():
    items = [("Alpha", 1), ("Alpine", 2), ("Albacore", 3)]
    out = fuzzy.filter_sorted("al", items, key=lambda e: e[0])
    assert [label for label, _ in out] == ["Alpha", "Alpine", "Albacore"]


def test_filter_sorted_no_matches_returns_empty_list():
    items = [("Quant Lab", "quant")]
    assert fuzzy.filter_sorted("zzz", items, key=lambda e: e[0]) == []


def test_score_rejects_overly_diffuse_subsequence():
    """Les lettres de la requête forment bien une sous-séquence de ce libellé
    (q-u-a-n-t apparaissent dans l'ordre dans "Équipe / analystes"), mais
    avec un trou bien trop grand entre "qu" et "a" pour être un résultat
    pertinent — doit être rejeté plutôt que pollué la liste."""
    assert fuzzy.score("quant", "Équipe / analystes") is None
