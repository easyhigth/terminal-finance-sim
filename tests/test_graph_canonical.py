"""
tests/test_graph_canonical.py — Invariants du CHEMIN DE PRIX CANONIQUE
(core/intraday.py) : toutes les vues (fenêtres 1J/1W, point « en direct »,
densification des graphes par pas) échantillonnent le même chemin déterministe,
comme dans une vraie app de trading. Remplace les scripts racine
test_graph_consistency.py / test_real_time_updates.py (impressions sans
assertions) par de vraies vérifications.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from core import intraday
from core.market import Market

# grille d'échantillonnage alignée sur QUANTIZE_MINUTES pour que deux fenêtres
# différentes évaluent le chemin AUX MÊMES instants absolus (comparables).
_Q = intraday.QUANTIZE_MINUTES
_DAY = 1440
_WEEK = 7 * 1440


@pytest.fixture(autouse=True)
def _force_animations_on(monkeypatch):
    """Neutralise le réglage machine « réduire les animations » : s'il traîne
    à True, tout le chemin devient linéaire et ces tests ne testeraient rien."""
    from core import anim_settings
    monkeypatch.setattr(anim_settings, "reduce_motion", lambda: False)


class _Clock:
    def __init__(self, minutes=0.0, speed=1):
        self.game_minutes_acc = minutes
        self.speed = speed


@pytest.fixture(scope="module")
def market():
    m = Market(seed=987654)
    for _ in range(30):
        m.step()
    return m


def _ticker(market):
    return market.top_companies(n=1)[0]["ticker"]


def _series(market, tk, clock, window, n_points):
    hist = market.history_of(tk, 6)
    return intraday.intraday_series(
        market, clock, 1, tk, hist, window_minutes=window, n_points=n_points,
        vol_mult=1.0, target=market.next_price_of(tk))


def test_1j_is_exact_tail_of_1w(market):
    """La vue 1 jour doit être LA QUEUE de la vue 1 semaine (mêmes valeurs aux
    mêmes instants) — c'était le cœur du reproche « on dirait des sociétés
    différentes selon la période »."""
    tk = _ticker(market)
    clock = _Clock(minutes=3 * _Q)
    day = _series(market, tk, clock, _DAY, _DAY // _Q + 1)
    week = _series(market, tk, clock, _WEEK, _WEEK // _Q + 1)
    tail = week[-len(day):]
    assert day == pytest.approx(tail)


def test_canonical_path_passes_through_engine_closes(market):
    """Le chemin canonique vaut EXACTEMENT close(s) en début de pont du pas s
    et close(s+1) en fin — les fenêtres intraday recoupent donc les clôtures
    des vues 1M/3M/1A."""
    tk = _ticker(market)
    hist = market.history_of(tk, 6)
    total = intraday.minutes_per_step()
    for back in (1, 2, 3):
        s = market.step_count - back
        assert intraday.canonical_point(market, tk, hist, s, 0) \
            == pytest.approx(hist[-1 - back])
        assert intraday.canonical_point(market, tk, hist, s, total) \
            == pytest.approx(hist[-back])


def test_window_last_point_matches_live_point(market):
    """Le dernier point de n'importe quelle fenêtre == le point « en direct »
    (ticker/sparkline) : le prix affiché est le même partout."""
    tk = _ticker(market)
    clock = _Clock(minutes=5 * _Q)
    hist = market.history_of(tk, 6)
    target = market.next_price_of(tk)
    live = intraday.live_point(market, clock, 1, tk, hist, vol_mult=1.0, target=target)
    for window, n in ((_DAY, _DAY // _Q + 1), (_WEEK, _WEEK // _Q + 1)):
        series = _series(market, tk, clock, window, n)
        assert series[-1] == pytest.approx(live)


def test_past_points_never_change_as_time_advances(market):
    """Quand le temps avance d'un palier, la fenêtre GLISSE : l'ancien dernier
    point devient l'avant-dernier, à valeur STRICTEMENT identique (le passé ne
    se réécrit jamais)."""
    tk = _ticker(market)
    n = _DAY // _Q + 1
    s1 = _series(market, tk, _Clock(minutes=2 * _Q), _DAY, n)
    s2 = _series(market, tk, _Clock(minutes=3 * _Q), _DAY, n)
    assert s2[-2] == pytest.approx(s1[-1])
    assert s2[:-1] == pytest.approx(s1[1:])


def test_speed_does_not_alter_the_path(market):
    """La vitesse de jeu (x1/x2/x3) ne doit PAS changer les valeurs du chemin
    (sinon changer de vitesse « redessinait » le passé)."""
    tk = _ticker(market)
    n = _DAY // _Q + 1
    a = _series(market, tk, _Clock(minutes=2 * _Q, speed=1), _DAY, n)
    b = _series(market, tk, _Clock(minutes=2 * _Q, speed=3), _DAY, n)
    assert a == pytest.approx(b)


def test_densified_series_keeps_exact_closes(market):
    """La densification des vues par pas (1M/3M…) garde chaque clôture réelle
    comme point EXACT de la série (le bruit est épinglé aux bornes)."""
    tk = _ticker(market)
    closes = market.history_of(tk, 8)
    pps = 4
    dense = intraday.densify_step_series(market, tk, closes, pps)
    assert dense[:: pps + 1] == pytest.approx(closes)


def test_densified_texture_matches_canonical_path(market):
    """La texture entre deux clôtures d'une vue 1M est un sous-échantillonnage
    du MÊME pont que la vue 1W sur la même période (convention forward :
    segment closes[i]→closes[i+1] = pont du pas correspondant)."""
    tk = _ticker(market)
    closes = market.history_of(tk, 4)
    pps = 4
    dense = intraday.densify_step_series(market, tk, closes, pps)
    total = intraday.minutes_per_step()
    hist = market.history_of(tk, 6)
    # 1er point intermédiaire du dernier segment (pont du pas step_count-1)
    s = market.step_count - 1
    minute = total * 1 / (pps + 1)
    expected = intraday.canonical_point(market, tk, hist, s, minute)
    got = dense[-(pps + 1)]     # 1er point après l'avant-dernière clôture
    assert got == pytest.approx(expected)


def test_reduce_motion_gives_pure_interpolation(market, tmp_path, monkeypatch):
    """Réglage « réduire les animations » : le chemin retombe en interpolation
    linéaire pure entre clôtures (comportement historique conservé)."""
    from core import anim_settings
    monkeypatch.setattr(anim_settings, "reduce_motion", lambda: True)
    tk = _ticker(market)
    hist = market.history_of(tk, 6)
    total = intraday.minutes_per_step()
    s = market.step_count - 1
    mid = intraday.canonical_point(market, tk, hist, s, total / 2)
    assert mid == pytest.approx((hist[-2] + hist[-1]) / 2)
