"""Tests de core/sim_clock.py (Round 11 Phase 1) et core/market_hours.py
(Round 11 Phase 2) : horloge de jeu temps réel et calendrier des sessions
de cotation par région."""
from core import market_hours as mh
from core.sim_clock import GAME_MINUTES_PER_REAL_SECOND_AT_X1 as _GMS, SimClock

# secondes réelles équivalentes à `m` minutes de jeu à x1 (indépendant de la
# cadence exacte choisie : les tests valident la LOGIQUE de bancarisation).
def _real_secs(game_minutes):
    return game_minutes / _GMS

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
    steps = c.advance(_real_secs(minutes_per_step - 1), 5)
    assert steps == 0
    # le complément déclenche exactement 1 pas, sans reste
    steps = c.advance(_real_secs(1), 5)
    assert steps == 1
    assert abs(c.game_minutes_acc) < 1e-6


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
    steps = c.advance(_real_secs(minutes_per_step / 3), 5)
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


def test_exactly_two_sessions_open_each_step():
    """Propriété centrale : à chaque pas, exactement 2 des 3 sessions sont
    ouvertes et 1 fermée."""
    for step in range(0, 12):
        opens = [s for s in mh.SESSIONS if mh.is_session_open(s, step)]
        assert len(opens) == 2
        assert mh.closed_session(step) not in opens


def test_each_pair_co_open_once_per_cycle():
    """Sur un cycle de 3 pas, chaque PAIRE de sessions est ouverte simultanément
    exactement une fois (chaque place croise les deux autres)."""
    from itertools import combinations
    seen = set()
    for step in range(3):
        opens = tuple(sorted(s for s in mh.SESSIONS if mh.is_session_open(s, step)))
        seen.add(opens)
    expected = {tuple(sorted(p)) for p in combinations(mh.SESSIONS, 2)}
    assert seen == expected


def test_closed_session_rotates_each_step():
    assert mh.closed_session(0) == "AMERICAS"
    assert mh.closed_session(1) == "ASIA"
    assert mh.closed_session(2) == "EUROPE"
    assert mh.closed_session(3) == "AMERICAS"  # cycle


def test_is_region_open_follows_session():
    # USA -> AMERICAS : fermé au pas 0, ouvert aux pas 1 et 2
    assert not mh.is_region_open("USA", 0)
    assert mh.is_region_open("USA", 1)
    assert mh.is_region_open("USA", 2)


def test_steps_until_reopen_is_one_when_closed():
    # une place fermée rouvre toujours au pas suivant
    assert mh.steps_until_reopen("USA", 0) == 1     # AMERICAS fermé au pas 0
    assert mh.steps_until_reopen("USA", 1) == 0     # ouvert -> 0


def test_fmt_hhmm():
    assert mh.fmt_hhmm(0) == "00:00"
    assert mh.fmt_hhmm(90) == "01:30"
    assert mh.fmt_hhmm(24 * 60) == "00:00"  # wrap


def test_region_status_label_open_and_closed():
    # Europe -> EUROPE : ouvert au pas 0, fermé au pas 2
    label_open = mh.region_status_label("Europe", 0, lang="fr")
    assert "ouvert" in label_open
    label_closed = mh.region_status_label("Europe", 2, lang="fr")
    assert "fermé" in label_closed
    label_en = mh.region_status_label("Europe", 2, lang="en")
    assert "closed" in label_en
