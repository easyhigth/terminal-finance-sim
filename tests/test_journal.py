"""Tests du journal d'investissement (core/journal.py)."""
from core import journal as J
from core.game_state import PlayerState
from core.market import Market


def _setup():
    p = PlayerState()
    p.day = 42
    m = Market(seed=2024)
    m.fast_forward(10)
    return p, m


def test_log_trade_records_fields_and_increments_id():
    p, m = _setup()
    e1 = J.log_trade(p, m, asset_class="Action", key="ABC", label="ABC Corp",
                      side="achat", qty=10, price=25.0, fee=1.5, reason="value play")
    assert e1["id"] == 1
    assert p.next_journal_id == 2
    assert e1["day"] == 42
    assert e1["notional"] == 250.0
    assert e1["regime"] == m.regime_label()
    assert e1["reason"] == "value play"
    assert e1["comment"] == ""
    assert len(p.trade_journal) == 1

    e2 = J.log_trade(p, m, asset_class="Crypto", key="BTC", label="BTC",
                      side="vente", qty=2, price=100.0, realized=50.0)
    assert e2["id"] == 2
    assert e2["realized"] == 50.0
    assert len(p.trade_journal) == 2


def test_log_trade_caps_history_length():
    p, m = _setup()
    for i in range(J.MAX_ENTRIES + 20):
        J.log_trade(p, m, asset_class="Action", key="ABC", label="ABC",
                    side="achat", qty=1, price=1.0)
    assert len(p.trade_journal) == J.MAX_ENTRIES
    # les plus anciennes entrées ont été purgées, les plus récentes gardées
    assert p.trade_journal[-1]["id"] == J.MAX_ENTRIES + 20


def test_annotate_updates_existing_entry():
    p, m = _setup()
    e = J.log_trade(p, m, asset_class="Action", key="ABC", label="ABC",
                    side="achat", qty=10, price=25.0)
    updated = J.annotate(p, e["id"], reason="momentum", comment="bon timing")
    assert updated["reason"] == "momentum"
    assert updated["comment"] == "bon timing"
    assert J.annotate(p, 9999, comment="x") is None


def test_list_entries_filters_and_orders_most_recent_first():
    p, m = _setup()
    J.log_trade(p, m, asset_class="Action", key="ABC", label="ABC",
               side="achat", qty=1, price=1.0)
    J.log_trade(p, m, asset_class="Crypto", key="BTC", label="BTC",
               side="achat", qty=1, price=1.0)
    J.log_trade(p, m, asset_class="Action", key="DEF", label="DEF",
               side="vente", qty=1, price=1.0)

    all_entries = J.list_entries(p)
    assert [e["id"] for e in all_entries] == [3, 2, 1]

    stocks_only = J.list_entries(p, asset_class="Action")
    assert [e["key"] for e in stocks_only] == ["DEF", "ABC"]

    limited = J.list_entries(p, limit=1)
    assert len(limited) == 1
    assert limited[0]["id"] == 3


def test_performance_stats_ignores_open_positions():
    p, m = _setup()
    J.log_trade(p, m, asset_class="Action", key="ABC", label="ABC",
                side="achat", qty=10, price=25.0)  # pas de realized -> ignoré
    stats = J.performance_stats(p)
    assert stats == []


def test_performance_stats_groups_by_regime_and_computes_rates():
    p, m = _setup()
    regime = m.regime_label()
    J.log_trade(p, m, asset_class="Action", key="ABC", label="ABC",
                side="vente", qty=10, price=25.0, realized=100.0)
    J.log_trade(p, m, asset_class="Action", key="DEF", label="DEF",
                side="vente", qty=5, price=10.0, realized=-40.0)
    stats = J.performance_stats(p, group_by="regime")
    assert len(stats) == 1
    g = stats[0]
    assert g["label"] == regime
    assert g["count"] == 2
    assert g["wins"] == 1
    assert g["win_rate"] == 50.0
    assert g["total_pnl"] == 60.0
    assert g["avg_pnl"] == 30.0


def test_performance_stats_groups_by_reason():
    p, m = _setup()
    J.log_trade(p, m, asset_class="Action", key="ABC", label="ABC",
                side="vente", qty=1, price=1.0, realized=10.0, reason="momentum")
    J.log_trade(p, m, asset_class="Action", key="DEF", label="DEF",
                side="vente", qty=1, price=1.0, realized=5.0, reason="momentum")
    J.log_trade(p, m, asset_class="Action", key="GHI", label="GHI",
                side="vente", qty=1, price=1.0, realized=-2.0, reason="value")
    stats = J.performance_stats(p, group_by="reason")
    assert {g["label"] for g in stats} == {"momentum", "value"}
    momentum = next(g for g in stats if g["label"] == "momentum")
    assert momentum["count"] == 2
    assert momentum["total_pnl"] == 15.0
