"""
tests/test_history_scene.py — Tests de core/career_history.py (logique pure)
et smoke-test headless de scenes/scene_history.py::HistoryScene.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from core.career_history import format_timeline, kind_counts
from core.game_state import GameState


# ---------------------------------------------------------------------------
# core/career_history.py — logique pure
# ---------------------------------------------------------------------------
def test_format_timeline_empty():
    assert format_timeline([]) == []
    assert format_timeline(None) == []


def test_format_timeline_sorted_most_recent_first():
    journal = [
        {"day": 1, "quarter": 1, "kind": "info", "text": "Premier jour"},
        {"day": 40, "quarter": 2, "kind": "promo", "text": "Promotion"},
        {"day": 15, "quarter": 1, "kind": "deal", "text": "Deal conclu"},
    ]
    out = format_timeline(journal)
    assert out == [
        ("J40", "Promotion"),
        ("J15", "Deal conclu"),
        ("J1", "Premier jour"),
    ]


def test_format_timeline_respects_limit():
    journal = [{"day": i, "text": f"event {i}"} for i in range(30)]
    out = format_timeline(journal, limit=5)
    assert len(out) == 5
    assert out[0] == ("J29", "event 29")


def test_format_timeline_ignores_malformed_entries():
    journal = [
        {"day": 5, "text": "valide"},
        {"day": 6},          # pas de 'text' -> ignoré
        "pas un dict",        # ignoré
    ]
    out = format_timeline(journal)
    assert out == [("J5", "valide")]


def test_kind_counts():
    journal = [
        {"day": 1, "kind": "promo", "text": "a"},
        {"day": 2, "kind": "deal", "text": "b"},
        {"day": 3, "kind": "promo", "text": "c"},
        {"day": 4, "text": "d"},  # kind par défaut "info"
    ]
    counts = kind_counts(journal)
    assert counts == {"promo": 2, "deal": 1, "info": 1}


def test_kind_counts_empty():
    assert kind_counts([]) == {}
    assert kind_counts(None) == {}


# ---------------------------------------------------------------------------
# scenes/scene_history.py — smoke-test headless (pas d'exception au rendu)
# ---------------------------------------------------------------------------
class _FakeApp:
    """App minimal portant juste un GameState, pour instancier la scène sans
    dépendre de main.App ni des autres scènes du jeu."""
    def __init__(self, gs):
        self.gs = gs
        self.scenes = None  # non utilisé tant qu'on ne déclenche pas de transition


@pytest.fixture(scope="module", autouse=True)
def _pygame_init():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def _make_player_state():
    gs = GameState()
    p = gs.player
    p.name = "Test Trader"
    p.grade_index = 1
    p.day = 90
    p.quarter = 2
    p.cash = 125_000.0
    p.best_cash = 140_000.0
    p.continent = "Europe"
    p.cash_history = [10_000.0 + i * 1500 for i in range(20)]
    p.journal = [
        {"day": 5, "quarter": 1, "kind": "info", "text": "Premier jour au bureau"},
        {"day": 30, "quarter": 1, "kind": "deal", "text": "Premier deal conclu"},
        {"day": 60, "quarter": 1, "kind": "promo", "text": "Promu Analyst"},
        {"day": 85, "quarter": 2, "kind": "crisis", "text": "Krach éclair encaissé"},
    ]
    return gs


def test_history_scene_renders_without_exception():
    from scenes.scene_history import HistoryScene

    gs = _make_player_state()
    app = _FakeApp(gs)
    scene = HistoryScene(app)
    scene.on_enter(return_to="terminal")
    scene.update(0.016)

    surf = pygame.Surface((1280, 720))
    scene.draw(surf)


def test_history_scene_renders_with_empty_history():
    """Le MVP doit rester gracieux même sans historique (carrière qui démarre)."""
    from scenes.scene_history import HistoryScene

    gs = GameState()
    gs.player.cash_history = []
    gs.player.journal = []
    app = _FakeApp(gs)
    scene = HistoryScene(app)
    scene.on_enter(return_to="terminal")
    scene.update(0.016)

    surf = pygame.Surface((1280, 720))
    scene.draw(surf)
