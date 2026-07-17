"""Tests du coach comportemental (core/coach.py) : détection des biais sur
le journal de trades, renforcement positif, livraison inbox."""
from core import coach
from core.game_state import GameState


def _player_with_trades(trades):
    gs = GameState()
    p = gs.player
    p.quarter = 1
    p.day = 30
    base = {"asset_class": "Action", "key": "MVC", "label": "Mavric",
            "side": "achat", "qty": 10, "price": 100.0, "fee": 5.0,
            "notional": 1000.0, "realized": None}
    for i, over in enumerate(trades):
        entry = dict(base, id=i + 1, day=over.get("day", 5 + i))
        entry.update(over)
        p.trade_journal.append(entry)
    return gs, p


def test_not_enough_trades_returns_none():
    _gs, p = _player_with_trades([{}] * (coach.MIN_TRADES - 1))
    assert coach.quarterly_review(p) is None


def test_disposition_effect_detected():
    trades = ([{"realized": 100.0}] * 6          # petits gains encaissés
              + [{"realized": -900.0}]           # une grosse perte laissée courir
              + [{}] * 2)
    _gs, p = _player_with_trades(trades)
    report = coach.quarterly_review(p)
    assert any(f["bias"] == "disposition" for f in report["findings"])


def test_concentration_detected():
    trades = ([{"key": "MVC", "notional": 9000.0}] * 5
              + [{"key": "GUGL", "notional": 500.0}] * 3)
    _gs, p = _player_with_trades(trades)
    report = coach.quarterly_review(p)
    assert any(f["bias"] == "concentration" for f in report["findings"])


def test_fee_drag_detected():
    trades = [{"realized": 100.0, "fee": 40.0}] * 8
    _gs, p = _player_with_trades(trades)
    report = coach.quarterly_review(p)
    assert any(f["bias"] == "fees" for f in report["findings"])


def test_disciplined_quarter_has_no_findings():
    # gains/pertes symétriques, volume réparti, frais négligeables
    trades = []
    for i, key in enumerate(["MVC", "GUGL", "POME", "RIVR"] * 2):
        realized = 200.0 if i % 2 == 0 else -190.0
        trades.append({"key": key, "realized": realized, "fee": 1.0,
                       "notional": 1000.0})
    _gs, p = _player_with_trades(trades)
    report = coach.quarterly_review(p)
    assert report is not None
    assert report["findings"] == []


def test_deliver_writes_inbox_message():
    trades = [{"realized": 100.0, "fee": 40.0}] * 8
    _gs, p = _player_with_trades(trades)
    report = coach.quarterly_review(p)
    coach.deliver(p, report)
    assert any("Coach" in m.get("sender", "") for m in p.inbox)


def test_only_current_quarter_trades_are_reviewed():
    from core import config
    trades = [{"realized": 100.0, "fee": 40.0, "day": 1}] * 8
    _gs, p = _player_with_trades(trades)
    p.quarter = 2
    p.day = config.DAYS_PER_QUARTER + 5   # T2 : les trades de T1 sont hors fenêtre
    assert coach.quarterly_review(p) is None
