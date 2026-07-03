"""
tests/test_scene_stats.py — Écran Statistiques (scenes/scene_stats.py) :
synthèse session/trading/progression/score composite, jusqu'ici éparpillée
sans vitrine dédiée (journal de trades non affiché nulle part ailleurs).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import main
from core import journal as journal_mod


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    a.gs.player.grade_index = 5
    return a


def test_draws_without_error_on_a_fresh_career(app):
    app.scenes.go("stats", return_to="terminal")
    sc = app.scenes.current
    sc.update(0.016)
    sc.draw(app.screen)   # ne doit pas lever, même sans aucun trade


def test_draws_without_error_with_trade_history(app):
    p = app.gs.player
    m = app.market
    tk = m.top_companies(n=1)[0]["ticker"]
    journal_mod.log_trade(p, m, asset_class="Action", key=tk, label=tk,
                          side="achat", qty=10, price=100.0, fee=5.0)
    journal_mod.log_trade(p, m, asset_class="Action", key=tk, label=tk,
                          side="vente", qty=10, price=110.0, fee=5.0, realized=100.0)
    journal_mod.log_trade(p, m, asset_class="Action", key=tk, label=tk,
                          side="vente", qty=5, price=90.0, fee=2.0, realized=-50.0)
    app.scenes.go("stats", return_to="terminal")
    sc = app.scenes.current
    sc.update(0.016)
    sc.draw(app.screen)


def test_escape_returns_to_the_calling_scene(app):
    app.scenes.go("stats", return_to="markethub")
    sc = app.scenes.current
    esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")
    sc.handle_event(esc)
    assert app.scenes.current_name == "markethub"


def test_back_button_returns_to_the_calling_scene(app):
    app.scenes.go("stats", return_to="career")
    sc = app.scenes.current
    sc.draw(app.screen)
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                               pos=sc.back_btn.rect.center)
    sc.handle_event(click)
    assert app.scenes.current_name == "career"


def test_stats_command_opens_the_scene_from_the_terminal(app):
    app.scenes.go("terminal")
    term = app.scenes.current
    term._run_command("STATS")
    assert app.scenes.current_name == "stats"


def test_stats_scene_registered_in_app_catalog():
    from core.app_catalog import SECTIONS
    scenes = {scene for _title, items in SECTIONS for _label, scene, _kw, _desc in items}
    assert "stats" in scenes
