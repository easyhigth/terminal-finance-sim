"""Tests de l'équipe d'analystes juniors (core/team.py).

NB : la clé "team" est ajoutée à `unlocks.UNLOCKS` par l'orchestrateur central
(cf. CLAUDE.md de la tâche), pas par ce module. Pour tester le gating par
grade indépendamment de cet ajout, ces tests forcent temporairement la
présence de la clé via un fixture monkeypatch, en restaurant l'état d'origine
après chaque test.
"""
import pytest

from core import team
from core import unlocks
from core.game_state import PlayerState

REQUIRED_GRADE = 6  # grade recommandé (Vice President), cohérent avec hedge/leverage/mandates/options


@pytest.fixture(autouse=True)
def _ensure_team_unlock_key():
    """Garantit que la clé "team" existe dans UNLOCKS pendant le test, quel que
    soit l'état d'intégration de l'orchestrateur, puis restaure l'état initial."""
    had_key = "team" in unlocks.UNLOCKS
    original = unlocks.UNLOCKS.get("team")
    unlocks.UNLOCKS["team"] = REQUIRED_GRADE
    yield
    if had_key:
        unlocks.UNLOCKS["team"] = original
    else:
        del unlocks.UNLOCKS["team"]


def _mk(grade_index=6, cash=100_000.0):
    return PlayerState(grade_index=grade_index, cash=cash)


# ---------------------------------------------------------------------------
# gating par grade
# ---------------------------------------------------------------------------
def test_hire_fails_below_required_grade():
    required = unlocks.required_grade("team")
    p = _mk(grade_index=max(0, required - 1))
    r = team.hire(p, "equity_junior")
    assert r["ok"] is False
    assert r["reason"] == "grade"
    assert p.analysts == []


def test_hire_succeeds_at_required_grade():
    required = unlocks.required_grade("team")
    p = _mk(grade_index=required)
    r = team.hire(p, "equity_junior")
    assert r["ok"] is True
    assert len(p.analysts) == 1
    assert p.analysts[0]["profile_id"] == "equity_junior"


def test_hire_defensive_even_if_caller_skips_unlocked_check():
    """hire() doit lui-même vérifier le grade, même si l'appelant ne le fait pas."""
    p = _mk(grade_index=0)
    assert not unlocks.unlocked(p, "team")
    r = team.hire(p, "equity_junior")
    assert r["ok"] is False
    assert r["reason"] == "grade"


# ---------------------------------------------------------------------------
# hire : profil inconnu / budget
# ---------------------------------------------------------------------------
def test_hire_unknown_profile():
    p = _mk()
    r = team.hire(p, "nonexistent_profile")
    assert r["ok"] is False
    assert r["reason"] == "unknown_profile"


def test_hire_fails_without_budget():
    p = _mk(cash=0.0)
    r = team.hire(p, "equity_junior")
    assert r["ok"] is False
    assert r["reason"] == "budget"
    assert p.analysts == []


def test_hire_debits_hire_cost():
    p = _mk(cash=50_000.0)
    before = p.cash
    r = team.hire(p, "equity_junior")
    assert r["ok"] is True
    assert p.cash == before - team.HIRE_COST


# ---------------------------------------------------------------------------
# fire
# ---------------------------------------------------------------------------
def test_fire_removes_analyst():
    p = _mk()
    team.hire(p, "equity_junior")
    team.hire(p, "credit_junior")
    assert len(p.analysts) == 2
    r = team.fire(p, 0)
    assert r["ok"] is True
    assert r["removed"]["profile_id"] == "equity_junior"
    assert len(p.analysts) == 1
    assert p.analysts[0]["profile_id"] == "credit_junior"


def test_fire_bad_index():
    p = _mk()
    r = team.fire(p, 0)
    assert r["ok"] is False
    assert r["reason"] == "bad_index"
    r2 = team.fire(p, -1)
    assert r2["ok"] is False


# ---------------------------------------------------------------------------
# coûts / bonus agrégés (fonctions pures)
# ---------------------------------------------------------------------------
def test_team_cost_per_step_empty():
    p = _mk()
    assert team.team_cost_per_step(p) == 0.0


def test_team_cost_per_step_sums_profiles():
    p = _mk()
    team.hire(p, "equity_junior")
    team.hire(p, "credit_junior")
    profiles = team.available_profiles()
    expected = (profiles["equity_junior"]["cost_per_step"]
                + profiles["credit_junior"]["cost_per_step"])
    assert team.team_cost_per_step(p) == expected


def test_team_bonus_rep_per_step_sums_profiles():
    p = _mk()
    team.hire(p, "equity_junior")
    team.hire(p, "macro_junior")
    profiles = team.available_profiles()
    expected = (profiles["equity_junior"]["rep_per_step"]
                + profiles["macro_junior"]["rep_per_step"])
    assert abs(team.team_bonus_rep_per_step(p) - expected) < 1e-9


def test_team_cost_and_bonus_not_wired_automatically():
    """Ces fonctions sont pures : elles ne modifient pas player.cash/reputation."""
    p = _mk(cash=10_000.0)
    p.reputation = 50
    team.hire(p, "equity_junior")
    cash_before = p.cash
    rep_before = p.reputation
    team.team_cost_per_step(p)
    team.team_bonus_rep_per_step(p)
    assert p.cash == cash_before
    assert p.reputation == rep_before


def test_available_profiles_catalogue():
    profiles = team.available_profiles()
    assert len(profiles) >= 3
    for pid, profile in profiles.items():
        assert "label" in profile
        assert "cost_per_step" in profile
        assert profile["cost_per_step"] > 0
