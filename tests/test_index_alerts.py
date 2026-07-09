"""Tests des alertes de prix sur les INDICES régionaux (core/alerts.py,
étendu au-delà des seules actions) : pose par nom d'indice (insensible à la
casse), déclenchement sur la valeur d'indice, routage du toast vers le hub
Marché, et indices listés en tête de l'app Alertes."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from core import alerts as ALERTS
from core import notify_queue
from core.game_state import GameState, PlayerState
from core.market import Market

pygame.font.init()


def _player():
    p = PlayerState()
    p.grade_index = 9
    return p


def _first_index(m):
    return next(iter(m.index_region))


# ----------------------------------------------------------- core/alerts
def test_place_alert_on_index_by_exact_name():
    m = Market(seed=3)
    p = _player()
    name = _first_index(m)
    r = ALERTS.place(p, m, name, "level", m.index_value(name) * 1.05)
    assert r["ok"] is True
    assert r["alert"]["ticker"] == name
    assert r["alert"]["is_index"] is True


def test_place_alert_on_index_case_insensitive():
    m = Market(seed=3)
    p = _player()
    name = _first_index(m)
    r = ALERTS.place(p, m, name.lower(), "level", m.index_value(name) * 1.05)
    assert r["ok"] is True
    assert r["alert"]["ticker"] == name   # nom canonique restauré


def test_index_alert_triggers_on_index_value():
    m = Market(seed=3)
    p = _player()
    name = _first_index(m)
    # seuil juste SOUS la valeur courante, direction "au-dessus" → déclenche
    ALERTS.place(p, m, name, "level", m.index_value(name) * 0.99, direction="above")
    fired = ALERTS.check(p, m)
    assert len(fired) == 1
    assert fired[0]["ticker"] == name
    assert fired[0]["is_index"] is True


def test_stock_alerts_still_work():
    m = Market(seed=3)
    p = _player()
    tk = m.companies[0]["ticker"]
    r = ALERTS.place(p, m, tk, "level", m.price_of(tk) * 1.05)
    assert r["ok"] is True
    assert r["alert"]["is_index"] is False


def test_index_alert_toast_routes_to_markethub():
    m = Market(seed=3)
    p = _player()
    name = _first_index(m)
    ALERTS.place(p, m, name, "level", m.index_value(name) * 0.99, direction="above")
    gs = GameState()
    gs.player = p
    gs.advance_step(market=m)
    toasts = notify_queue.drain(p)
    hit = next(t for t in toasts if name in t["text"])
    assert hit["action"] == "markethub"


# ----------------------------------------------------------- app Alertes
def test_alerts_app_lists_indices_first():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    a.scenes.go("desktop")
    desk = a.scenes.current
    w = desk._launch("alerts")
    rows = w.app_obj.rows
    n_idx = len(a.market.index_region)
    assert all(r["sector"] == "Indice" for r in rows[:n_idx])
    assert rows[n_idx]["sector"] != "Indice"
    w.app_obj.draw(a.screen, pygame.Rect(0, 0, 900, 560))   # rendu sans exception
