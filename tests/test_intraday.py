"""Tests de core/intraday.py (Round 11 Phase 3) : animation déterministe des
prix entre deux pas du moteur de marché — épinglage exact aux clôtures,
amplitude bornée, reconstructibilité depuis (seed, step, clé, minute), gel
hors session de cotation."""
import pytest

from core import intraday
from core.sim_clock import SimClock


@pytest.fixture(autouse=True)
def _force_animations_on(monkeypatch):
    """Neutralise le réglage machine « réduire les animations » (persisté en
    JSON sous saves/) : s'il traîne à True sur la machine de test, tout le
    bruit intraday devient linéaire pur et ces tests échouent faussement."""
    from core import anim_settings
    monkeypatch.setattr(anim_settings, "reduce_motion", lambda: False)


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


def test_quantize_to_day_snaps_to_quantize_minutes():
    q = intraday.QUANTIZE_MINUTES
    assert intraday.quantize_to_day(0) == 0
    assert intraday.quantize_to_day(q - 1) == 0
    assert intraday.quantize_to_day(q) == q
    assert intraday.quantize_to_day(q + q // 2) == q
    assert intraday.quantize_to_day(intraday.MINUTES_PER_DAY) == intraday.MINUTES_PER_DAY


def test_quantize_is_finer_than_a_full_day():
    """La progression se rafraîchit plusieurs fois par jour de jeu (pas un
    seul saut quotidien) pour que le marché semble vivant à l'écran."""
    assert intraday.QUANTIZE_MINUTES < intraday.MINUTES_PER_DAY
    assert intraday.MINUTES_PER_DAY % intraday.QUANTIZE_MINUTES == 0


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
    # sessions par pas : USA -> AMERICAS, fermé au pas 0, ouvert au pas 1
    assert intraday.region_open_factor("USA", 0) == 0.0
    assert intraday.region_open_factor("USA", 1) == 1.0
    assert intraday.region_open_factor(None, 0) == 1.0    # pas de région -> pas de gel


def test_intraday_series_ends_at_live_point():
    """Le dernier point d'une fenêtre intraday == le point « en direct »
    (même chemin canonique, cf. tests/test_graph_canonical.py). `target` =
    clôture suivante déterministe, comme le passe scene_graph."""
    m = _FakeMarket()
    clock = SimClock()
    clock.game_minutes_acc = 3600.0
    history = [90.0, 95.0, 100.0]
    target = 104.0
    series = intraday.intraday_series(m, clock, day=1, key="AAA", history=history,
                                       window_minutes=5, n_points=10, target=target)
    assert len(series) == 10
    expected_last = intraday.live_point(m, clock, day=1, key="AAA", history=history,
                                        target=target)
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


def test_noise_amplitude_tuned_for_a_lively_looking_market():
    """Retour joueur (captures d'appli de trading grand public à l'appui) :
    l'intraday paraissait trop plat comparé à une vraie appli — verrouille
    que l'amplitude affichée reste dans un ordre de grandeur "vivant" (pas
    dérivé accidentellement vers une valeur ridiculement plate ou explosive
    lors d'un futur retouché)."""
    assert 0.003 <= intraday._NOISE_PCT <= 0.01
    lo, hi = intraday._VOL_MULT_RANGE
    assert lo >= 0.5
    assert hi <= 5.0


# ============ densification des graphes "par pas" (1M/3M/1A/3A/5A/MAX) ========
def test_points_per_segment_denser_for_shorter_periods():
    """Retour joueur : la densité de bruit doit "s'adapter à la taille de la
    période cliquée" — plus dense pour les fenêtres courtes/zoomées."""
    p1m = intraday.points_per_segment_for_n_steps(6)
    p3m = intraday.points_per_segment_for_n_steps(18)
    p1a = intraday.points_per_segment_for_n_steps(73)
    p3a = intraday.points_per_segment_for_n_steps(219)
    p5a = intraday.points_per_segment_for_n_steps(365)
    pmax = intraday.points_per_segment_for_n_steps(None)
    assert p1m >= p3m >= p1a >= p3a >= p5a >= 0
    assert pmax == 0
    assert p1m > 0


def test_densify_step_series_preserves_real_closes_exactly():
    m = _FakeMarket(step_count=10)
    closes = [90.0, 95.0, 100.0, 98.0]     # pas 7, 8, 9, 10
    dense = intraday.densify_step_series(m, "AAA", closes, points_per_segment=4)
    # chaque clôture réelle doit rester un point EXACT de la série renvoyée
    for c in closes:
        assert c in dense
    assert dense[0] == closes[0]
    assert dense[-1] == closes[-1]
    # pps points intermédiaires + la clôture de fin, par segment
    assert len(dense) == 1 + (len(closes) - 1) * 5
    assert dense[::5] == closes


def test_densify_step_series_noop_when_disabled_or_too_short():
    m = _FakeMarket(step_count=10)
    closes = [90.0, 95.0, 100.0]
    assert intraday.densify_step_series(m, "AAA", closes, points_per_segment=0) == closes
    assert intraday.densify_step_series(m, "AAA", [100.0], points_per_segment=4) == [100.0]
    assert intraday.densify_step_series(m, "AAA", [], points_per_segment=4) == []


def test_densify_step_series_deterministic_and_bounded():
    m = _FakeMarket(step_count=10)
    closes = [90.0, 95.0, 100.0, 98.0]
    a = intraday.densify_step_series(m, "AAA", closes, points_per_segment=4)
    b = intraday.densify_step_series(m, "AAA", closes, points_per_segment=4)
    assert a == b
    lo, hi = min(closes), max(closes)
    margin = hi * intraday._NOISE_PCT * intraday._VOL_MULT_RANGE[1] * 1.5
    assert all(lo - margin <= v <= hi + margin for v in a)


def test_densify_step_series_respects_region_freeze():
    # place fermée au pas DU SEGMENT -> damp=0 -> tracé linéaire pur (pas de
    # bruit). Convention forward : le segment closes[0]→closes[1] est le pont
    # du pas base_step = step_count - 1 ; step_count=1 -> pont du pas 0, où
    # les USA sont fermés (cf. core/market_hours, rotation par pas).
    m_closed = _FakeMarket(step_count=1)
    closes = [90.0, 100.0]
    dense_closed = intraday.densify_step_series(m_closed, "AAA", closes,
                                                 points_per_segment=4, region="USA")
    total = intraday.minutes_per_step()
    for j in range(1, 5):
        expected = 90.0 + (100.0 - 90.0) * (total * j / 5) / total
        assert dense_closed[j] == pytest.approx(expected)
