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
