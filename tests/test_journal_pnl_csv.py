"""Tests de la courbe de P&L cumulé et de l'export CSV du Journal de trading
(core/journal.py::cumulative_realized_series/export_csv + apps/app_journal.py)."""
import csv
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from core import journal as J
from core.game_state import PlayerState

pygame.font.init()


def _player_with_trades():
    p = PlayerState()
    # 2 achats (realized=None, ignorés) + 3 clôtures
    J.log_trade(p, None, asset_class="Action", key="AAA", label="AAA",
                side="achat", qty=10, price=100.0)
    J.log_trade(p, None, asset_class="Action", key="AAA", label="AAA",
                side="vente", qty=10, price=110.0, realized=100.0, reason="cible atteinte")
    J.log_trade(p, None, asset_class="Action", key="BBB", label="BBB",
                side="achat", qty=5, price=50.0)
    J.log_trade(p, None, asset_class="Action", key="BBB", label="BBB",
                side="vente", qty=5, price=40.0, realized=-50.0)
    J.log_trade(p, None, asset_class="ETF", key="ETF1", label="ETF1",
                side="vente", qty=2, price=200.0, realized=30.0)
    return p


# ------------------------------------------------- série cumulée (pure)
def test_cumulative_series_ignores_open_positions():
    p = _player_with_trades()
    assert J.cumulative_realized_series(p) == [100.0, 50.0, 80.0]


def test_cumulative_series_empty_journal():
    assert J.cumulative_realized_series(PlayerState()) == []


# --------------------------------------------------------- export CSV (pur)
def test_export_csv_writes_all_entries(tmp_path):
    p = _player_with_trades()
    path = tmp_path / "journal.csv"
    assert J.export_csv(p, str(path)) is True
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0][0] == "id"                      # en-tête
    assert len(rows) == 1 + len(p.trade_journal)   # une ligne par trade
    assert rows[1][3] == "AAA"                     # colonne "key"


def test_export_csv_bad_path_returns_false():
    p = _player_with_trades()
    assert J.export_csv(p, "/nonexistent/dir/journal.csv") is False


# ------------------------------------------------------------ UI (JournalApp)
@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    a.scenes.go("desktop")
    return a


def test_journal_app_csv_button_exports(app, tmp_path, monkeypatch):
    import os as _os
    monkeypatch.setattr(_os.path, "expanduser", lambda p: str(tmp_path))
    desk = app.scenes.current
    w = desk._open_scene_window("tradejournal")
    jr = w.app_obj
    J.log_trade(app.gs.player, app.market, asset_class="Action", key="MVC",
                label="MVC", side="vente", qty=1, price=10.0, realized=5.0)
    jr.draw(app.screen, pygame.Rect(0, 0, 1020, 640))
    assert jr._csv_rect is not None
    jr.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                        pos=jr._csv_rect.center),
                     pygame.Rect(0, 0, 1020, 640))
    assert "Exporté" in jr.msg
    assert (tmp_path / "journal_trading.csv").exists()


def test_journal_app_csv_button_empty_journal(app):
    desk = app.scenes.current
    w = desk._open_scene_window("tradejournal")
    jr = w.app_obj
    jr.draw(app.screen, pygame.Rect(0, 0, 1020, 640))
    jr.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                        pos=jr._csv_rect.center),
                     pygame.Rect(0, 0, 1020, 640))
    assert "vide" in jr.msg


def test_journal_app_draws_pnl_curve_when_wide(app):
    desk = app.scenes.current
    w = desk._open_scene_window("tradejournal")
    jr = w.app_obj
    for i in range(3):
        J.log_trade(app.gs.player, app.market, asset_class="Action", key="MVC",
                    label="MVC", side="vente", qty=1, price=10.0, realized=float(i))
    jr.draw(app.screen, pygame.Rect(0, 0, 1020, 640))    # large : courbe
    jr.draw(app.screen, pygame.Rect(0, 0, 700, 460))     # étroite : sans courbe, sans crash
