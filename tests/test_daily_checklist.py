"""
tests/test_daily_checklist.py — Checklist de routine quotidienne
(core/daily_checklist.py, logique pure).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from core import daily_checklist as DC


class _FakePlayer:
    def __init__(self, day=1):
        self.day = day
        self.flags = {}


def test_enabled_by_default():
    p = _FakePlayer()
    assert DC.is_enabled(p) is True


def test_set_enabled_persists_in_flags():
    p = _FakePlayer()
    DC.set_enabled(p, False)
    assert DC.is_enabled(p) is False
    assert p.flags["daily_checklist_enabled"] is False


def test_items_for_today_all_undone_initially():
    p = _FakePlayer()
    items = DC.items_for_today(p)
    assert len(items) == len(DC.ITEMS)
    assert all(not it["done"] for it in items)


def test_toggle_marks_item_done():
    p = _FakePlayer()
    DC.toggle(p, "inbox")
    items = {it["id"]: it["done"] for it in DC.items_for_today(p)}
    assert items["inbox"] is True
    assert items["positions"] is False


def test_toggle_twice_marks_item_undone_again():
    p = _FakePlayer()
    DC.toggle(p, "inbox")
    DC.toggle(p, "inbox")
    items = {it["id"]: it["done"] for it in DC.items_for_today(p)}
    assert items["inbox"] is False


def test_all_done_today_false_until_every_item_checked():
    p = _FakePlayer()
    for it in DC.ITEMS[:-1]:
        DC.toggle(p, it["id"])
    assert DC.all_done_today(p) is False
    DC.toggle(p, DC.ITEMS[-1]["id"])
    assert DC.all_done_today(p) is True


def test_state_resets_on_new_day():
    p = _FakePlayer(day=1)
    DC.toggle(p, "inbox")
    assert DC.all_done_today(p) is False
    items = {it["id"]: it["done"] for it in DC.items_for_today(p)}
    assert items["inbox"] is True
    p.day = 2
    items = {it["id"]: it["done"] for it in DC.items_for_today(p)}
    assert items["inbox"] is False


def test_labels_localized_en():
    p = _FakePlayer()
    items = DC.items_for_today(p, lang="en")
    assert items[0]["label"] == DC.ITEMS[0]["label_en"]


def test_labels_localized_fr_default():
    p = _FakePlayer()
    items = DC.items_for_today(p, lang="fr")
    assert items[0]["label"] == DC.ITEMS[0]["label_fr"]
