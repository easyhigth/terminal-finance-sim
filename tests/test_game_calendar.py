"""Tests de core/game_calendar.py : calendrier fictif des axes de graphes
(jour de jeu → date lisible), échelle adaptative minutes/heures/jours/mois/
années, robustesse sur la préhistoire (jours ≤ 0)."""
from core import game_calendar as cal


def test_day_one_is_january_first():
    assert cal.date_of(1) == (cal.BASE_YEAR, 0, 1)


def test_month_rollover_and_year_length():
    assert cal.date_of(31) == (cal.BASE_YEAR, 0, 31)
    assert cal.date_of(32) == (cal.BASE_YEAR, 1, 1)      # 1er févr.
    assert cal.date_of(365) == (cal.BASE_YEAR, 11, 31)   # 31 déc.
    assert cal.date_of(366) == (cal.BASE_YEAR + 1, 0, 1)  # 1er janv. année suivante
    assert sum(cal.MONTH_LENGTHS) == 365


def test_prehistory_days_fall_in_earlier_years():
    """Les graphes 5A/MAX en début de carrière remontent avant le jour 1 :
    le calendrier doit rester cohérent (jour 0 = 31 déc. de l'année d'avant)."""
    assert cal.date_of(0) == (cal.BASE_YEAR - 1, 11, 31)
    y, m, d = cal.date_of(1 - 5 * 365)
    assert y == cal.BASE_YEAR - 5 and (m, d) == (0, 1)


def test_axis_label_scales_with_span():
    day = 400   # ~ 4 févr. de l'an 2
    assert cal.axis_label(day, span_days=90) == cal.day_label(day)      # « 4 févr. »
    assert cal.axis_label(day, span_days=365) == cal.month_label(day)   # « févr. 2026 »
    assert cal.axis_label(day, span_days=1825) == cal.year_label(day)   # « 2026 »
    assert cal.year_label(day) == str(cal.BASE_YEAR + 1)


def test_rel_minutes_label_uses_human_units():
    assert cal.rel_minutes_label(0) in ("maintenant", "now")
    assert cal.rel_minutes_label(45) == "-45min"
    assert cal.rel_minutes_label(720) == "-12h"
    assert cal.rel_minutes_label(1440) == "-24h"
    assert cal.rel_minutes_label(10080) in ("-7j", "-7d")
    assert cal.rel_minutes_label(5040) in ("-3.5j", "-3.5d")
