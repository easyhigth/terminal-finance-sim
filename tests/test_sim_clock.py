"""Tests de core/sim_clock.py (Round 11 Phase 1) et core/market_hours.py
(Round 11 Phase 2) : horloge de jeu temps réel et calendrier des sessions
de cotation par région."""
from core import market_hours as mh
from core.sim_clock import SimClock


# --------------------------------------------------------------- SimClock

def test_effective_speed_paused():
    c = SimClock()
    assert c.effective_speed() == 1
    c.toggle_pause()
    assert c.effective_speed() == 0
    assert not c.is_running()


def test_effective_speed_auto_paused_overrides_speed():
    c = SimClock()
    c.set_speed(3)
    c.set_auto_paused(True)
    assert c.effective_speed() == 0
    c.set_auto_paused(False)
    assert c.effective_speed() == 3


def test_set_speed_clears_manual_pause():
    c = SimClock()
    c.toggle_pause()
    assert c.paused
    c.set_speed(2)
    assert not c.paused
    assert c.speed == 2


def test_advance_banks_one_step_at_threshold():
    c = SimClock()
    minutes_per_step = 5 * 24 * 60  # DAYS_PER_STEP=5
    # juste sous le seuil : 0 pas
    steps = c.advance(minutes_per_step - 1, 5)
    assert steps == 0
    # le complément déclenche exactement 1 pas, sans reste
    steps = c.advance(1, 5)
    assert steps == 1
    assert c.game_minutes_acc == 0


def test_advance_zero_when_paused():
    c = SimClock()
    c.toggle_pause()
    assert c.advance(10_000, 5) == 0
    assert c.game_minutes_acc == 0


def test_advance_scales_with_speed():
    c = SimClock()
    c.set_speed(3)
    minutes_per_step = 5 * 24 * 60
    # à vitesse x3, 1/3 du temps réel suffit pour banquer 1 pas
    steps = c.advance(minutes_per_step / 3, 5)
    assert steps == 1


def test_current_time_within_first_day():
    c = SimClock()
    c.game_minutes_acc = 90.0  # 01:30
    day, minute = c.current_time(base_day=10)
    assert day == 10
    assert minute == 90


def test_current_time_rolls_into_later_sub_day():
    c = SimClock()
    c.game_minutes_acc = 1440 * 2 + 30.0  # 2 jours pleins + 30 min
    day, minute = c.current_time(base_day=1)
    assert day == 3
    assert minute == 30


# ------------------------------------------------------------ market_hours

def test_session_for_region_groups_continents():
    assert mh.session_for_region("Asia") == "ASIA"
    assert mh.session_for_region("Océanie") == "ASIA"
    assert mh.session_for_region("Europe") == "EUROPE"
    assert mh.session_for_region("Afrique") == "EUROPE"
    assert mh.session_for_region("USA") == "AMERICAS"
    assert mh.session_for_region("Am.Nord") == "AMERICAS"
    assert mh.session_for_region("Am.Sud") == "AMERICAS"


def test_is_weekday_open_mon_to_fri_only():
    # convention : jour 1 = lundi
    opens = [mh.is_weekday_open(d) for d in range(1, 8)]
    assert opens == [True, True, True, True, True, False, False]


def test_sessions_not_all_open_simultaneously():
    """Propriété centrale demandée : à aucune minute de la journée, les
    3 sessions ne sont ouvertes en même temps."""
    for minute in range(0, 24 * 60, 5):
        open_sessions = [s for s in mh.SESSION_HOURS if mh.is_session_open(s, minute)]
        assert len(open_sessions) < 3


def test_is_region_open_respects_window_and_weekday():
    # USA -> AMERICAS, ouvert 13:30-20:00, lundi (jour 1)
    assert not mh.is_region_open("USA", 1, 13 * 60)        # 13:00, pas encore ouvert
    assert mh.is_region_open("USA", 1, 13 * 60 + 30)       # 13:30, ouverture
    assert mh.is_region_open("USA", 1, 19 * 60 + 59)       # 19:59, encore ouvert
    assert not mh.is_region_open("USA", 1, 20 * 60)        # 20:00, fermé
    assert not mh.is_region_open("USA", 6, 14 * 60)        # samedi, fermé


def test_next_open_same_day_before_open():
    day, minute = mh.next_open("Europe", 1, 5 * 60)  # 05:00, avant ouverture 07:00
    assert (day, minute) == (1, 7 * 60)


def test_next_open_skips_to_next_day_after_close():
    day, minute = mh.next_open("Europe", 1, 16 * 60)  # 16:00, déjà fermé
    assert day == 2
    assert minute == 7 * 60


def test_next_open_skips_weekend():
    # vendredi (jour 5) après fermeture -> réouverture lundi (jour 8), pas samedi/dimanche
    day, minute = mh.next_open("USA", 5, 21 * 60)
    assert day == 8
    assert minute == 13 * 60 + 30


def test_fmt_hhmm():
    assert mh.fmt_hhmm(0) == "00:00"
    assert mh.fmt_hhmm(90) == "01:30"
    assert mh.fmt_hhmm(24 * 60) == "00:00"  # wrap


def test_region_status_label_open_and_closed():
    label_open = mh.region_status_label("Europe", 1, 9 * 60, lang="fr")
    assert "ouvert" in label_open
    label_closed = mh.region_status_label("Europe", 1, 20 * 60, lang="fr")
    assert "fermé" in label_closed
    label_en = mh.region_status_label("Europe", 1, 20 * 60, lang="en")
    assert "closed" in label_en
