"""Tests de la messagerie « monde vivant » (core/inbox.py)."""
import random

from core import inbox
from core.game_state import PlayerState
from core.market import Market


def _player(track="General", grade_index=8, day=1):
    p = PlayerState()
    p.track = track
    p.grade_index = grade_index
    p.day = day
    p.cash = 1_000_000.0
    return p


# --------------------------------------------------------------- push / unread_count
def test_push_appends_well_formed_message_and_increments_id():
    p = _player()
    msg = inbox.push(p, "desk", "Desk", "Sujet", "Corps")
    assert p.inbox == [msg]
    assert msg["kind"] == "desk"
    assert msg["sender"] == "Desk"
    assert msg["subject"] == "Sujet"
    assert msg["body"] == "Corps"
    assert msg["read"] is False
    assert msg["day"] == p.day
    assert msg["id"] == 1
    assert p.next_msg_id == 2


def test_push_trims_oldest_message_beyond_max_inbox():
    p = _player()
    for i in range(inbox.MAX_INBOX):
        inbox.push(p, "desk", "Desk", f"Sujet {i}", "Corps")
    first_id = p.inbox[0]["id"]
    assert len(p.inbox) == inbox.MAX_INBOX
    inbox.push(p, "desk", "Desk", "Dernier", "Corps")
    assert len(p.inbox) == inbox.MAX_INBOX
    assert p.inbox[0]["id"] != first_id
    assert p.inbox[-1]["subject"] == "Dernier"


def test_unread_count_counts_only_unread():
    p = _player()
    inbox.push(p, "desk", "Desk", "A", "x")
    inbox.push(p, "desk", "Desk", "B", "x")
    assert inbox.unread_count(p) == 2
    p.inbox[0]["read"] = True
    assert inbox.unread_count(p) == 1


# --------------------------------------------------------------- déclencheurs contextuels
def test_on_promotion_sends_manager_message():
    p = _player(grade_index=0)
    inbox.on_promotion(p)
    assert len(p.inbox) == 1
    assert p.inbox[0]["kind"] == "manager"
    assert p.inbox[0]["sender"] == inbox.manager_name(p)


def test_on_promotion_adds_hr_message_at_high_grade():
    p = _player(grade_index=6)
    inbox.on_promotion(p)
    kinds = [m["kind"] for m in p.inbox]
    assert kinds == ["manager", "hr"]


def test_on_promotion_no_hr_message_below_threshold():
    p = _player(grade_index=5)
    inbox.on_promotion(p)
    kinds = [m["kind"] for m in p.inbox]
    assert kinds == ["manager"]


def test_on_quarter_no_message_without_report():
    p = _player()
    inbox.on_quarter(p, None)
    inbox.on_quarter(p, {"total": 0})
    assert p.inbox == []


def test_on_quarter_all_objectives_done_sends_hr_bonus():
    p = _player()
    inbox.on_quarter(p, {"done": 3, "total": 3})
    assert len(p.inbox) == 1
    assert p.inbox[0]["kind"] == "hr"
    assert "Bonus" in p.inbox[0]["subject"]


def test_on_quarter_zero_done_sends_manager_warning():
    p = _player()
    inbox.on_quarter(p, {"done": 0, "total": 3})
    assert len(p.inbox) == 1
    assert p.inbox[0]["kind"] == "manager"
    assert "décevant" in p.inbox[0]["subject"].lower()


def test_on_quarter_partial_done_sends_manager_review():
    p = _player()
    inbox.on_quarter(p, {"done": 1, "total": 3})
    assert len(p.inbox) == 1
    assert p.inbox[0]["kind"] == "manager"
    assert "trimestrielle" in p.inbox[0]["subject"].lower()


def test_on_crisis_good_sends_desk_opportunity():
    p = _player()
    inbox.on_crisis(p, "Boom techno", "good")
    assert p.inbox[0]["kind"] == "desk"
    assert "Opportunité" in p.inbox[0]["subject"]


def test_on_crisis_bad_sends_manager_alert():
    p = _player()
    inbox.on_crisis(p, "Krach obligataire", "bad")
    assert p.inbox[0]["kind"] == "manager"
    assert "Alerte marché" in p.inbox[0]["subject"]


def test_on_deal_sniped_sends_client_message():
    p = _player()
    deal = {"title": "Cession ACME"}
    inbox.on_deal_sniped(p, deal, "Rival Corp")
    msg = p.inbox[0]
    assert msg["kind"] == "client"
    assert "Rival Corp" in msg["body"]
    assert deal["title"] in msg["body"]
    assert deal["title"] in msg["sender"]


# --------------------------------------------------------------- _compliance_check
def test_compliance_check_no_position_returns_none():
    p = _player()
    m = Market(seed=1)
    assert inbox._compliance_check(p, m) is None
    assert p.inbox == []


def test_compliance_check_respects_cooldown(monkeypatch):
    from core import portfolio
    p = _player(day=100)
    p.portfolio = {"DUMMY": {"shares": 10, "avg": 1.0}}
    p.flags["compliance_day"] = p.day - (inbox.COMPLIANCE_COOLDOWN - 1)
    monkeypatch.setattr(portfolio, "portfolio_beta", lambda player, market: 2.0)
    monkeypatch.setattr(portfolio, "allocation_by", lambda player, market, key: {"Tech": 100.0})
    m = Market(seed=1)
    assert inbox._compliance_check(p, m) is None


def test_compliance_check_high_beta_triggers_alert(monkeypatch):
    from core import portfolio
    p = _player(day=1000)
    p.portfolio = {"DUMMY": {"shares": 10, "avg": 1.0}}
    monkeypatch.setattr(portfolio, "portfolio_beta", lambda player, market: 1.5)
    monkeypatch.setattr(portfolio, "allocation_by", lambda player, market, key: {"Tech": 100.0})
    m = Market(seed=1)
    msg = inbox._compliance_check(p, m)
    assert msg is not None
    assert msg["kind"] == "compliance"
    assert "bêta" in msg["body"]
    assert p.flags["compliance_day"] == p.day


def test_compliance_check_sector_concentration_triggers_alert(monkeypatch):
    from core import portfolio
    p = _player(day=1000)
    p.portfolio = {"DUMMY": {"shares": 10, "avg": 1.0}}
    monkeypatch.setattr(portfolio, "portfolio_beta", lambda player, market: 0.5)
    monkeypatch.setattr(
        portfolio, "allocation_by",
        lambda player, market, key: {"Tech": 80.0, "Santé": 20.0},
    )
    m = Market(seed=1)
    msg = inbox._compliance_check(p, m)
    assert msg is not None
    assert msg["kind"] == "compliance"
    assert "Concentration" in msg["subject"]
    assert p.flags["compliance_day"] == p.day


def test_compliance_check_low_beta_low_concentration_returns_none(monkeypatch):
    from core import portfolio
    p = _player(day=1000)
    p.portfolio = {"DUMMY": {"shares": 10, "avg": 1.0}}
    monkeypatch.setattr(portfolio, "portfolio_beta", lambda player, market: 0.5)
    monkeypatch.setattr(
        portfolio, "allocation_by",
        lambda player, market, key: {"Tech": 50.0, "Santé": 50.0},
    )
    m = Market(seed=1)
    assert inbox._compliance_check(p, m) is None


# --------------------------------------------------------------- _periodic
def test_periodic_sends_desk_brief_on_large_index_move(monkeypatch):
    p = _player()
    m = Market(seed=1)
    monkeypatch.setattr(m, "index_defs", [("WORLD50", "Global", None, 10)])
    monkeypatch.setattr(m, "index_change_pct", lambda name: 1.2)
    msg = inbox._periodic(p, m, random.Random(0))
    assert msg is not None
    assert msg["kind"] == "desk"
    assert "WORLD50" in msg["subject"]


def test_periodic_no_brief_on_small_index_move(monkeypatch):
    p = _player()
    m = Market(seed=1)
    monkeypatch.setattr(m, "index_defs", [("WORLD50", "Global", None, 10)])
    monkeypatch.setattr(m, "index_change_pct", lambda name: 0.1)
    assert inbox._periodic(p, m, random.Random(0)) is None


def test_periodic_negative_move_uses_recule_wording(monkeypatch):
    p = _player()
    m = Market(seed=1)
    monkeypatch.setattr(m, "index_defs", [("WORLD50", "Global", None, 10)])
    monkeypatch.setattr(m, "index_change_pct", lambda name: -0.8)
    msg = inbox._periodic(p, m, random.Random(0))
    assert msg is not None
    assert "recule" in msg["body"]


# --------------------------------------------------------------- on_step
def test_on_step_returns_list():
    p = _player()
    m = Market(seed=1)
    out = inbox.on_step(p, m, {}, rng=random.Random(0))
    assert isinstance(out, list)


def test_on_step_nothing_happens_without_portfolio_and_unlucky_roll():
    p = _player()
    m = Market(seed=1)
    # rng dont .random() renvoie toujours >= 0.35 -> jamais de _periodic
    class _AlwaysHigh:
        def random(self):
            return 0.99
    out = inbox.on_step(p, m, {}, rng=_AlwaysHigh())
    assert out == []


def test_on_step_triggers_compliance_message_when_due(monkeypatch):
    from core import portfolio
    p = _player(day=1000)
    p.portfolio = {"DUMMY": {"shares": 10, "avg": 1.0}}
    monkeypatch.setattr(portfolio, "portfolio_beta", lambda player, market: 2.0)
    monkeypatch.setattr(portfolio, "allocation_by", lambda player, market, key: {"Tech": 100.0})
    m = Market(seed=1)

    class _AlwaysHigh:
        def random(self):
            return 0.99
    out = inbox.on_step(p, m, {}, rng=_AlwaysHigh())
    assert len(out) == 1
    assert out[0]["kind"] == "compliance"


def test_on_step_triggers_periodic_message_when_lucky_roll(monkeypatch):
    p = _player()
    m = Market(seed=1)
    monkeypatch.setattr(m, "index_defs", [("WORLD50", "Global", None, 10)])
    monkeypatch.setattr(m, "index_change_pct", lambda name: 1.0)

    class _AlwaysLow:
        def random(self):
            return 0.0
    out = inbox.on_step(p, m, {}, rng=_AlwaysLow())
    assert len(out) == 1
    assert out[0]["kind"] == "desk"
