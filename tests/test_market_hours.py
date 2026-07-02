"""Tests pour core/market_hours.py — sessions de cotation par pas de marché."""
from core import market_hours


def test_exactly_one_session_closed_per_step():
    for step in range(20):
        closed = market_hours.closed_session(step)
        assert closed in ("AMERICAS", "ASIA", "EUROPE")


def test_closed_session_rotates_every_step():
    seq = [market_hours.closed_session(s) for s in range(6)]
    assert seq[0:3] == seq[3:6]
    assert len(set(seq[0:3])) == 3


def test_is_session_open_matches_closed_session():
    for step in range(9):
        closed = market_hours.closed_session(step)
        for session in ("AMERICAS", "ASIA", "EUROPE"):
            expected = session != closed
            assert market_hours.is_session_open(session, step) == expected


def test_open_sessions_has_exactly_two():
    for step in range(9):
        opened = market_hours.open_sessions(step)
        assert len(opened) == 2
        assert market_hours.closed_session(step) not in opened


def test_is_region_open_uses_region_session_mapping():
    for step in range(9):
        for region, session in market_hours.REGION_SESSION.items():
            expected = market_hours.is_session_open(session, step)
            assert market_hours.is_region_open(region, step) == expected


def test_closed_region_reopens_next_step():
    for step in range(9):
        for region in market_hours.REGION_SESSION:
            if not market_hours.is_region_open(region, step):
                assert market_hours.is_region_open(region, step + 1)


def test_steps_until_reopen_zero_when_open():
    for step in range(9):
        for region in market_hours.REGION_SESSION:
            if market_hours.is_region_open(region, step):
                assert market_hours.steps_until_reopen(region, step) == 0


def test_steps_until_reopen_positive_when_closed():
    for step in range(9):
        for region in market_hours.REGION_SESSION:
            if not market_hours.is_region_open(region, step):
                n = market_hours.steps_until_reopen(region, step)
                assert n >= 1
                assert market_hours.is_region_open(region, step + n)


def test_session_labels_fr_en_differ_and_cover_three_sessions():
    fr = market_hours.session_labels("fr")
    en = market_hours.session_labels("en")
    assert set(fr.keys()) == {"AMERICAS", "ASIA", "EUROPE"}
    assert set(en.keys()) == {"AMERICAS", "ASIA", "EUROPE"}


def test_region_status_label_reflects_open_closed():
    for step in range(9):
        for region in market_hours.REGION_SESSION:
            label = market_hours.region_status_label(region, step, "fr")
            assert isinstance(label, str) and label


def test_fmt_hhmm_basic():
    assert market_hours.fmt_hhmm(0) == "00:00"
    assert market_hours.fmt_hhmm(90) == "01:30"
    assert market_hours.fmt_hhmm(600) == "10:00"
