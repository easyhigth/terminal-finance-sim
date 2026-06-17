"""Tests de PlayerState/GameState (core/game_state.py), avec un accent sur la
sauvegarde/chargement (round-trip JSON) — c'est le chemin le plus sensible
à la perte de données. Le marché n'est JAMAIS sérialisé : seuls market_seed
et market_step doivent survivre au cycle save/load (cf. CLAUDE.md)."""
import pytest

from core import config
from core.game_state import GameState, PlayerState
from core.market import Market


@pytest.fixture
def isolated_save_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SAVE_DIR", str(tmp_path))
    return tmp_path


def _populated_state():
    gs = GameState()
    p = gs.player
    p.name = "Test Trader"
    p.continent = "Asia"
    p.track = "Risk"
    p.grade_index = 5
    p.reputation = 77
    p.cash = 123456.78
    p.day = 321
    p.quarter = 4
    p.competencies = {"valuation": 60}
    p.flags = {"hot_sector": "Tech"}
    p.deals = [{"id": 1, "title": "Deal X", "kind": "M&A", "reward_cash": 50000, "days_left": 10}]
    p.next_deal_id = 2
    p.portfolio = {"AAPL": {"shares": 10, "avg": 150.0}}
    p.titles = ["Risk Guardian"]
    p.certs = {"FRM": 1}
    p.heat = 12
    p.pending_dilemmas = [{"id": "missell", "category": "ethique", "title": "x",
                            "scenario": "y", "options": []}]
    p.journal = [{"day": 10, "quarter": 1, "kind": "info", "text": "hello"}]

    m = Market(seed=4242)
    m.sync_to(75)
    p.market_seed = m.seed
    p.market_step = m.step_count
    return gs, m


def test_to_dict_from_dict_round_trip_preserves_player_fields():
    gs, m = _populated_state()
    d = gs.to_dict()
    restored = GameState.from_dict(d)
    rp = restored.player
    op = gs.player
    assert rp.name == op.name
    assert rp.continent == op.continent
    assert rp.track == op.track
    assert rp.grade_index == op.grade_index
    assert rp.reputation == op.reputation
    assert rp.cash == op.cash
    assert rp.day == op.day
    assert rp.quarter == op.quarter
    assert rp.competencies == op.competencies
    assert rp.deals == op.deals
    assert rp.portfolio == op.portfolio
    assert rp.titles == op.titles
    assert rp.certs == op.certs
    assert rp.heat == op.heat
    assert rp.pending_dilemmas == op.pending_dilemmas
    assert rp.journal == op.journal


def test_round_trip_preserves_market_seed_and_step_not_prices():
    gs, m = _populated_state()
    d = gs.to_dict()
    # le marché lui-même n'est jamais sérialisé : pas de clé "price"/"companies"
    assert "price" not in d["player"]
    assert "market_seed" in d["player"] and "market_step" in d["player"]
    restored = GameState.from_dict(d)
    assert restored.player.market_seed == gs.player.market_seed
    assert restored.player.market_step == gs.player.market_step
    # reconstruction déterministe du marché à partir de (seed, step)
    rebuilt = Market(seed=restored.player.market_seed)
    rebuilt.sync_to(restored.player.market_step)
    assert rebuilt.step_count == m.step_count
    import numpy as np
    assert np.allclose(rebuilt.price, m.price)


def test_save_then_load_round_trip_on_disk(isolated_save_dir):
    gs, m = _populated_state()
    path = gs.save(slot="test_slot")
    assert path == str(isolated_save_dir / "test_slot.json")
    loaded = GameState.load(slot="test_slot")
    assert loaded is not None
    assert loaded.player.name == gs.player.name
    assert loaded.player.cash == gs.player.cash
    assert loaded.player.market_seed == gs.player.market_seed
    assert loaded.player.market_step == gs.player.market_step
    assert loaded.version == gs.version
    assert loaded.last_saved > 0


def test_load_missing_slot_returns_none(isolated_save_dir):
    assert GameState.load(slot="does_not_exist") is None


def test_from_dict_fills_missing_fields_with_defaults():
    gs = GameState.from_dict({"player": {"name": "Partial"}})
    assert gs.player.name == "Partial"
    assert gs.player.cash == 0.0
    assert gs.player.grade_index == 0
    assert gs.player.portfolio == {}


def test_delete_removes_existing_slot(isolated_save_dir):
    gs, _ = _populated_state()
    gs.save(slot="to_delete")
    assert GameState.delete("to_delete") is True
    assert GameState.load(slot="to_delete") is None


def test_delete_missing_slot_returns_false(isolated_save_dir):
    assert GameState.delete("never_existed") is False


def test_list_saves_returns_sorted_slot_names(isolated_save_dir):
    gs, _ = _populated_state()
    gs.save(slot="bravo")
    gs.save(slot="alpha")
    assert GameState.list_saves() == ["alpha", "bravo"]


def test_list_saves_empty_dir_returns_empty_list(isolated_save_dir):
    assert GameState.list_saves() == []


def test_slot_meta_summarizes_without_full_load(isolated_save_dir):
    gs, _ = _populated_state()
    gs.save(slot="meta_test")
    meta = GameState.slot_meta("meta_test")
    assert meta["name"] == gs.player.name
    assert meta["grade"] == config.GRADES[gs.player.grade_index]
    assert meta["continent"] == gs.player.continent
    assert meta["cash"] == gs.player.cash
    assert meta["game_over"] is False


def test_slot_meta_missing_slot_returns_none(isolated_save_dir):
    assert GameState.slot_meta("nope") is None


# ----------------------------------------------------------------------------
# PlayerState — logique pure
# ----------------------------------------------------------------------------
def test_grade_property_matches_config():
    p = PlayerState(grade_index=3)
    assert p.grade == config.GRADES[3]


def test_can_promote_false_at_last_grade():
    p = PlayerState(grade_index=len(config.GRADES) - 1)
    assert not p.can_promote()


def test_promote_increments_grade_and_resets_counters():
    p = PlayerState(grade_index=2, quarter=5)
    p.grade_deals = 3
    p.grade_missions = 4
    p.promote()
    assert p.grade_index == 3
    assert p.grade_deals == 0
    assert p.grade_missions == 0
    assert p.grade_start_quarter == 5


def test_promote_noop_at_max_grade():
    last = len(config.GRADES) - 1
    p = PlayerState(grade_index=last)
    p.promote()
    assert p.grade_index == last


def test_adjust_cash_and_reputation_clamping():
    p = PlayerState(reputation=50)
    p.adjust_cash(100.0)
    assert p.cash == 100.0
    p.adjust_reputation(1000)
    assert p.reputation == 100
    p.adjust_reputation(-1000)
    assert p.reputation == 0


def test_check_game_over_on_bankruptcy():
    p = PlayerState(cash=config.BANKRUPTCY_CASH - 1, reputation=50)
    assert p.check_game_over() is True
    assert p.game_over is True
    assert "Faillite" in p.game_over_reason


def test_check_game_over_on_zero_reputation():
    p = PlayerState(cash=1_000_000.0, reputation=config.MIN_REPUTATION)
    assert p.check_game_over(net_worth=1_000_000.0) is True
    assert "Réputation" in p.game_over_reason


def test_check_game_over_false_when_healthy():
    p = PlayerState(cash=1_000_000.0, reputation=50)
    assert p.check_game_over(net_worth=1_000_000.0) is False
    assert p.game_over is False
