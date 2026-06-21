from core import career_history


def test_format_timeline_empty_journal():
    assert career_history.format_timeline(None) == []
    assert career_history.format_timeline([]) == []


def test_format_timeline_filters_and_sorts_desc():
    journal = [
        {"day": 1, "text": "Premier jour"},
        {"day": 5, "text": "Cinquième jour"},
        "not-a-dict",
        {"day": 3, "kind": "warn"},  # pas de "text" -> exclu
    ]
    out = career_history.format_timeline(journal)
    assert out == [("J5", "Cinquième jour"), ("J1", "Premier jour")]


def test_format_timeline_respects_limit():
    journal = [{"day": i, "text": f"e{i}"} for i in range(10)]
    out = career_history.format_timeline(journal, limit=3)
    assert len(out) == 3
    assert out[0] == ("J9", "e9")


def test_kind_counts_handles_none_and_non_dicts():
    assert career_history.kind_counts(None) == {}
    journal = [{"kind": "good"}, {"kind": "good"}, {"kind": "bad"}, "skip-me", {}]
    counts = career_history.kind_counts(journal)
    assert counts == {"good": 2, "bad": 1, "info": 1}
