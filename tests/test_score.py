"""Tests du score composite de fin de run (core/score.py)."""
import pytest

from core import portfolio as pf
from core import score
from core.game_state import PlayerState
from core.market import Market


def _fresh_player(**overrides):
    p = PlayerState()
    for k, v in overrides.items():
        setattr(p, k, v)
    return p


# ---------------------------------------------------------------------------
# Sous-scores individuels
# ---------------------------------------------------------------------------
def test_performance_score_rewards_growth():
    p = _fresh_player(cash_history=[100_000, 120_000, 150_000, 200_000])
    sc = score.compute_final_score(p)
    assert sc.performance > 50.0


def test_performance_score_penalises_loss():
    p = _fresh_player(cash_history=[100_000, 80_000, 50_000, 30_000])
    sc = score.compute_final_score(p)
    assert sc.performance < 50.0


def test_performance_score_neutral_without_history():
    p = _fresh_player(cash_history=[])
    sc = score.compute_final_score(p)
    assert sc.performance == pytest.approx(50.0)


def test_drawdown_score_high_when_no_drawdown():
    p = _fresh_player(cash_history=[100_000, 110_000, 120_000, 130_000])
    sc = score.compute_final_score(p)
    assert sc.drawdown == pytest.approx(100.0)


def test_drawdown_score_low_on_severe_drawdown():
    p = _fresh_player(cash_history=[100_000, 50_000, 10_000])
    sc = score.compute_final_score(p)
    assert sc.drawdown < 20.0


def test_reputation_score_matches_field():
    p = _fresh_player(reputation=72)
    sc = score.compute_final_score(p)
    assert sc.reputation == pytest.approx(72.0)


def test_reputation_score_clips_to_0_100():
    p = _fresh_player(reputation=0)
    sc = score.compute_final_score(p)
    assert sc.reputation == pytest.approx(0.0)


def test_conformite_score_penalised_by_heat_and_investigations():
    clean = _fresh_player(heat=0, investigations_count=0)
    dirty = _fresh_player(heat=80, investigations_count=3)
    sc_clean = score.compute_final_score(clean)
    sc_dirty = score.compute_final_score(dirty)
    assert sc_clean.conformite > sc_dirty.conformite
    assert sc_dirty.conformite == pytest.approx(0.0)


def test_qualite_execution_penalised_by_fees_and_margin_calls():
    clean = _fresh_player(best_cash=1_000_000.0)
    costly = _fresh_player(
        best_cash=1_000_000.0,
        total_fees_paid=80_000.0,
        total_margin_penalty=40_000.0,
        flags={"margin_call_count": 4},
    )
    sc_clean = score.compute_final_score(clean)
    sc_costly = score.compute_final_score(costly)
    assert sc_clean.qualite_execution > sc_costly.qualite_execution


def test_survie_score_high_for_voluntary_end():
    p = _fresh_player(game_over=False, quarter=10)
    sc = score.compute_final_score(p)
    assert sc.survie > 80.0


def test_survie_score_zero_for_bankruptcy():
    p = _fresh_player(game_over=True, game_over_reason="Faillite : liquidités à -500000.",
                       quarter=2)
    sc = score.compute_final_score(p)
    assert sc.survie < 15.0


def test_survie_score_rewards_longevity_even_when_forced_out():
    short_run = _fresh_player(game_over=True, game_over_reason="Faillite.", quarter=2)
    long_run = _fresh_player(game_over=True, game_over_reason="Faillite.", quarter=14)
    sc_short = score.compute_final_score(short_run)
    sc_long = score.compute_final_score(long_run)
    assert sc_long.survie > sc_short.survie


def test_risque_score_without_market_uses_cash_history_volatility():
    stable = _fresh_player(cash_history=[100_000] * 10)
    volatile = _fresh_player(cash_history=[100_000, 150_000, 70_000, 160_000, 60_000,
                                            170_000, 50_000, 180_000, 40_000, 190_000])
    sc_stable = score.compute_final_score(stable)
    sc_volatile = score.compute_final_score(volatile)
    assert sc_stable.risque > sc_volatile.risque


# ---------------------------------------------------------------------------
# Composite / structure
# ---------------------------------------------------------------------------
def test_all_subscores_in_0_100_range():
    p = _fresh_player(
        cash_history=[100_000, 50_000, 200_000, 10_000],
        reputation=30, heat=90, investigations_count=5,
        total_fees_paid=500_000.0, total_margin_penalty=200_000.0,
        best_cash=50_000.0, flags={"margin_call_count": 10},
        game_over=True, game_over_reason="Faillite.", quarter=3,
    )
    sc = score.compute_final_score(p)
    for key, _ in [("performance", None), ("risque", None), ("drawdown", None),
                   ("reputation", None), ("conformite", None),
                   ("qualite_execution", None), ("survie", None), ("total", None)]:
        val = getattr(sc, key)
        assert 0.0 <= val <= 100.0, f"{key} hors bornes : {val}"


def test_total_is_weighted_average_of_subscores():
    p = _fresh_player(cash_history=[100_000, 110_000], reputation=60)
    sc = score.compute_final_score(p)
    manual = sum(getattr(sc, k) * w for k, w in score.WEIGHTS.items())
    assert sc.total == pytest.approx(max(0.0, min(100.0, manual)))


def test_grade_letter_consistent_with_total():
    excellent = _fresh_player(cash_history=[100_000, 100_000, 100_000], reputation=100,
                               quarter=10, game_over=False)
    sc = score.compute_final_score(excellent)
    assert sc.grade in ("S", "A", "B")
    assert sc.rank_label


def test_as_dict_contains_all_dimensions():
    p = _fresh_player()
    sc = score.compute_final_score(p)
    d = sc.as_dict()
    for key in ("performance", "risque", "drawdown", "reputation", "conformite",
                "qualite_execution", "survie", "total", "grade", "rank_label"):
        assert key in d


def test_compute_final_score_does_not_mutate_player():
    p = _fresh_player(cash_history=[100_000, 120_000], reputation=55, heat=20,
                       cash=120_000.0)
    before = (list(p.cash_history), p.reputation, p.heat, p.cash)
    score.compute_final_score(p)
    after = (list(p.cash_history), p.reputation, p.heat, p.cash)
    assert before == after


# ---------------------------------------------------------------------------
# Avec marché réel (dimension risque via VaR)
# ---------------------------------------------------------------------------
def test_risque_score_uses_var_when_market_given():
    m = Market(seed=2024)
    p = PlayerState()
    p.cash = 2_000_000.0
    for tk in (m.companies[0]["ticker"], m.companies[10]["ticker"]):
        m.price[m.ticker_idx[tk]] = 100.0
        pf.buy(p, m, tk, 500)
    sc_with_market = score.compute_final_score(p, market=m)
    sc_without = score.compute_final_score(p, market=None)
    # les deux doivent rester des scores valides, potentiellement différents.
    assert 0.0 <= sc_with_market.risque <= 100.0
    assert 0.0 <= sc_without.risque <= 100.0


def test_risque_score_graceful_with_empty_portfolio_and_market():
    m = Market(seed=2024)
    p = PlayerState()
    p.cash = 100_000.0
    sc = score.compute_final_score(p, market=m)
    assert 0.0 <= sc.risque <= 100.0
