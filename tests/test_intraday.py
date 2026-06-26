"""Tests de core/intraday.py (Round 11 Phase 3) : animation déterministe des
prix entre deux pas du moteur de marché — épinglage exact aux clôtures,
amplitude bornée, reconstructibilité depuis (seed, step, clé, minute), gel
hors session de cotation."""
from core import intraday
from core.sim_clock import SimClock


class _FakeMarket:
    def __init__(self, seed=42, step_count=7):
        self.seed = seed
        self.step_count = step_count


def test_wiggle_pinned_at_step_boundaries():
    m = _FakeMarket()
    total = intraday.minutes_per_step()
    assert intraday.wiggle(m.seed, m.step_count, "AAA", 100.0, 110.0, 0.0) == 100.0
    assert intraday.wiggle(m.seed, m.step_count, "AAA", 100.0, 110.0, total) == 110.0


def test_wiggle_stays_close_to_linear_interpolation():
    m = _FakeMarket()
    total = intraday.minutes_per_step()
    for frac in (0.1, 0.25, 0.5, 0.75, 0.9):
        pm = total * frac
        base = 100.0 + (110.0 - 100.0) * frac
        val = intraday.wiggle(m.seed, m.step_count, "AAA", 100.0, 110.0, pm)
        assert abs(val - base) < base * intraday._NOISE_PCT * 1.5


def test_wiggle_deterministic_same_inputs():
    m = _FakeMarket()
    a = intraday.wiggle(m.seed, m.step_count, "AAA", 100.0, 110.0, 1234.0)
    b = intraday.wiggle(m.seed, m.step_count, "AAA", 100.0, 110.0, 1234.0)
    assert a == b


def test_wiggle_differs_by_key_and_step():
    m = _FakeMarket()
    a = intraday.wiggle(m.seed, m.step_count, "AAA", 100.0, 110.0, 1234.0)
    b = intraday.wiggle(m.seed, m.step_count, "BBB", 100.0, 110.0, 1234.0)
    c = intraday.wiggle(m.seed, m.step_count + 1, "AAA", 100.0, 110.0, 1234.0)
    assert a != b
    assert a != c


def test_wiggle_damp_zero_is_pure_linear():
    m = _FakeMarket()
    val = intraday.wiggle(m.seed, m.step_count, "AAA", 100.0, 110.0, 1800.0, damp=0.0)
    assert val == 100.0 + (110.0 - 100.0) * (1800.0 / intraday.minutes_per_step())


def test_live_point_progress_zero_equals_previous_close():
    m = _FakeMarket()
    clock = SimClock()
    clock.game_minutes_acc = 0.0
    history = [90.0, 95.0, 100.0]
    pt = intraday.live_point(m, clock, day=1, key="AAA", history=history)
    assert pt == 95.0


def test_append_live_does_not_mutate_original_history():
    m = _FakeMarket()
    clock = SimClock()
    clock.game_minutes_acc = 500.0
    history = [90.0, 95.0, 100.0]
    out = intraday.append_live(m, clock, day=1, key="AAA", history=history)
    assert history == [90.0, 95.0, 100.0]
    assert len(out) == 4


def test_append_live_empty_history_returns_copy():
    m = _FakeMarket()
    clock = SimClock()
    out = intraday.append_live(m, clock, day=1, key="AAA", history=[])
    assert out == []


def test_region_closed_freezes_noise_to_linear_base():
    assert intraday.region_open_factor("USA", 6, 14 * 60) == 0.0   # samedi
    assert intraday.region_open_factor(None, 6, 14 * 60) == 1.0    # pas de région -> pas de gel


def test_intraday_series_ends_at_live_point():
    m = _FakeMarket()
    clock = SimClock()
    clock.game_minutes_acc = 3600.0
    history = [90.0, 95.0, 100.0]
    series = intraday.intraday_series(m, clock, day=1, key="AAA", history=history,
                                       window_minutes=5, n_points=10)
    assert len(series) == 10
    expected_last = intraday.live_point(m, clock, day=1, key="AAA", history=history)
    assert series[-1] == expected_last


def test_intraday_series_reaches_back_across_step_boundary():
    """Si la fenêtre demandée dépasse les minutes déjà écoulées dans le pas
    courant, la série doit remonter dans le pas précédent sans planter."""
    m = _FakeMarket(step_count=2)
    clock = SimClock()
    clock.game_minutes_acc = 2.0   # tout juste après le début du pas courant
    history = [80.0, 90.0, 100.0]   # [-3]=avant-avant-clôture, [-2]=prev, [-1]=cur
    series = intraday.intraday_series(m, clock, day=1, key="AAA", history=history,
                                       window_minutes=10, n_points=5)
    assert len(series) == 5
    assert all(isinstance(v, float) for v in series)
