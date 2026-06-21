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


def test_from_dict_ignores_unknown_keys_forward_compat():
    """Une sauvegarde produite par une version FUTURE du jeu peut contenir des
    clés inconnues de cette version : elles doivent être ignorées sans lever,
    pas faire planter le chargement d'une partie plus ancienne."""
    gs = GameState.from_dict({
        "player": {"name": "Future", "feature_from_next_version": {"x": 1}},
        "feature_top_level": True,
    })
    assert gs.player.name == "Future"
    assert not hasattr(gs.player, "feature_from_next_version")


def test_from_dict_tolerates_non_dict_top_level():
    gs = GameState.from_dict(["not", "a", "dict"])
    assert gs.player.name == "Trainee"


def test_from_dict_tolerates_non_dict_player_section():
    gs = GameState.from_dict({"player": "corrupted"})
    assert gs.player.name == "Trainee"
    assert gs.player.cash == 0.0


def test_load_corrupted_json_returns_none_without_raising(isolated_save_dir):
    path = isolated_save_dir / "broken.json"
    path.write_text("{not valid json", encoding="utf-8")
    assert GameState.load(slot="broken") is None


def test_load_unexpected_top_level_structure_falls_back_to_defaults(isolated_save_dir):
    """JSON valide mais de structure inattendue (ex. sauvegarde d'un format
    radicalement différent) : ne doit jamais lever, retombe sur un état par
    défaut plutôt que de planter."""
    path = isolated_save_dir / "weird.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    gs = GameState.load(slot="weird")
    assert gs is not None
    assert gs.player.name == "Trainee"


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


# ---------------------------------------------------------------------------
# Traçabilité des variations de réputation (rep_log) — un joueur doit pouvoir
# comprendre IMMÉDIATEMENT pourquoi sa réputation a bougé à chaque tour. Ces
# tests vérifient que adjust_reputation(..., reason=...) journalise bien le
# delta RÉELLEMENT appliqué (après bornage 0-100), sans changer le calcul.
# ---------------------------------------------------------------------------
def test_adjust_reputation_logs_reason_with_applied_delta():
    p = PlayerState(reputation=50)
    p.adjust_reputation(5, reason="Deal conclu")
    assert p.rep_log == [("Deal conclu", 5)]
    assert p.reputation == 55


def test_adjust_reputation_logs_negative_delta():
    p = PlayerState(reputation=50)
    p.adjust_reputation(-3, reason="Mandat échoué")
    assert p.rep_log == [("Mandat échoué", -3)]
    assert p.reputation == 47


def test_adjust_reputation_without_reason_does_not_log():
    p = PlayerState(reputation=50)
    p.adjust_reputation(5)
    assert p.rep_log == []


def test_adjust_reputation_zero_delta_not_logged_even_with_reason():
    p = PlayerState(reputation=50)
    p.adjust_reputation(0, reason="Rien ne se passe")
    assert p.rep_log == []


def test_adjust_reputation_logs_clamped_delta_not_requested_delta():
    """Si la réputation est déjà à 98 et qu'on demande +10, seul le delta
    RÉELLEMENT appliqué (+2, borné à 100) doit apparaître dans le journal —
    pas le delta brut demandé, pour que la somme du rep_log corresponde
    toujours exactement à reputation_apres - reputation_avant."""
    p = PlayerState(reputation=98)
    p.adjust_reputation(10, reason="Trimestre parfait")
    assert p.reputation == 100
    assert p.rep_log == [("Trimestre parfait", 2)]


def test_adjust_reputation_log_accumulates_across_calls():
    p = PlayerState(reputation=50)
    p.adjust_reputation(3, reason="Deal A")
    p.adjust_reputation(-1, reason="Pitch raté")
    p.adjust_reputation(2, reason="Deal B")
    assert p.rep_log == [("Deal A", 3), ("Pitch raté", -1), ("Deal B", 2)]
    total = sum(delta for _, delta in p.rep_log)
    assert p.reputation == 50 + total


def test_advance_step_resets_rep_log_and_reports_team_bonus_reason():
    """advance_step() doit vider rep_log en début de tour (pas de fuite d'un
    tour à l'autre) puis le repeupler ; le résumé retourné expose une copie
    de ce journal sous la clé 'rep_log'. Le bonus de réputation de l'équipe
    d'analystes (team_rep_accum) doit y apparaître avec sa propre raison dès
    qu'un point entier de réputation est franchi."""
    gs = GameState()
    p = gs.player
    p.rep_log = [("Tour précédent", 7)]   # résidu d'un tour antérieur
    p.analysts = [{"profile_id": "equity_junior", "hired_step": 0}]
    p.team_rep_accum = 0.99   # à un cheveu du palier entier -> déclenche +1 ce tour
    summary = gs.advance_step()
    # le résidu de l'ancien tour a bien été purgé
    assert ("Tour précédent", 7) not in p.rep_log
    assert ("Tour précédent", 7) not in summary["rep_log"]
    team_entries = [d for r, d in p.rep_log if "équipe" in r.lower()]
    assert team_entries == [1]
    assert summary["rep_log"] == p.rep_log


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
