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
    # Pas de pygame.quit() en teardown : ça invaliderait les pygame.font.Font
    # déjà mis en cache par ui/fonts.py, et ferait segfaulter tout module de
    # test qui les réutilise plus loin dans la même session pytest.
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield


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


def test_history_scene_renders_with_market_and_attribution():
    """Avec un marché et une attribution de trimestre déjà calculée, les
    panneaux perf-vs-indice et attribution doivent se dessiner sans erreur."""
    from core.market import Market
    from scenes.scene_history import HistoryScene

    gs = _make_player_state()
    p = gs.player
    p.last_quarter_attribution = {"salaire": 12000.0, "deals": -3000.0, "marches": 1500.0}
    app = _FakeApp(gs)
    app.market = Market(seed=1)
    for _ in range(25):
        app.market.step()
    scene = HistoryScene(app)
    scene.on_enter(return_to="terminal")
    scene.update(0.016)

    surf = pygame.Surface((1280, 720))
    scene.draw(surf)


# ---------------------------------------------------------------------------
# drawdown (running peak) — scenes/scene_history.py::_drawdowns
# ---------------------------------------------------------------------------
def test_drawdowns_zero_on_monotonic_increase():
    from scenes.scene_history import _drawdowns

    cur, mx = _drawdowns([100.0, 110.0, 120.0, 130.0])
    assert cur == pytest.approx(0.0)
    assert mx == pytest.approx(0.0)


def test_drawdowns_current_and_max_after_a_dip():
    from scenes.scene_history import _drawdowns

    # pic à 200, creux à 100 (-50%), puis remonte à 180 (toujours -10% du pic)
    cur, mx = _drawdowns([100.0, 200.0, 100.0, 180.0])
    assert mx == pytest.approx(50.0)
    assert cur == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# marqueurs de crise sur le graphe — scenes/scene_history.py::_crisis_markers
# ---------------------------------------------------------------------------
class _FakeMarket:
    def __init__(self, step_count, crisis_log):
        self.step_count = step_count
        self.crisis_log = crisis_log


def test_crisis_markers_maps_step_to_visible_index():
    from scenes.scene_history import _crisis_markers

    hist = [100.0] * 10  # 10 relevés -> steps couvrant [step_count-9, step_count]
    market = _FakeMarket(step_count=50, crisis_log=[
        {"step": 50, "name": "Crash récent", "kind": "bad", "severity": 2.0},
        {"step": 41, "name": "Crash limite", "kind": "bad", "severity": 1.0},
        {"step": 5, "name": "Trop ancien", "kind": "bad", "severity": 1.0},
    ])
    out = _crisis_markers(market, hist)
    idxs = {c["name"]: idx for idx, c in out}
    assert idxs["Crash récent"] == 9
    assert idxs["Crash limite"] == 0
    assert "Trop ancien" not in idxs


def test_crisis_markers_empty_without_market_or_history():
    from scenes.scene_history import _crisis_markers

    assert _crisis_markers(None, [1.0, 2.0]) == []
    assert _crisis_markers(_FakeMarket(5, []), []) == []
