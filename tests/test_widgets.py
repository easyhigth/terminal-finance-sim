"""Tests des helpers purs de graphes (ui/widgets.py) : agrégation OHLC et SMA.

(L'import de pygame est nécessaire mais aucun affichage n'est requis.)
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

# pygame n'est pas installé en CI (qui ne pose que numpy/scipy/pytest) : on saute
# proprement ce module au lieu de casser toute la collecte pytest.
pytest.importorskip("pygame")

from ui import widgets


def test_aggregate_ohlc_basic():
    closes = [10, 12, 8, 9, 14, 11, 7, 13]
    candles = widgets._aggregate_ohlc(closes, n_candles=2)
    assert len(candles) == 2
    o, h, l, c = candles[0]                      # premier groupe [10,12,8,9]
    assert (o, h, l, c) == (10, 12, 8, 9)
    o2, h2, l2, c2 = candles[1]                  # second groupe [14,11,7,13]
    assert (o2, h2, l2, c2) == (14, 14, 7, 13)


def test_aggregate_ohlc_handles_few_points():
    candles = widgets._aggregate_ohlc([5, 6], n_candles=32)
    assert len(candles) >= 1
    for o, h, l, c in candles:
        assert l <= o <= h and l <= c <= h


def test_sma_values():
    vals = [2, 4, 6, 8, 10]
    ma = widgets._sma(vals, 2)
    assert ma[0] is None                         # pas assez de points
    assert ma[1] == pytest.approx(3.0)           # (2+4)/2
    assert ma[4] == pytest.approx(9.0)           # (8+10)/2
    assert len(ma) == len(vals)


def test_scroll_state_clamps_to_content_bounds():
    import pygame
    st = widgets.ScrollState()
    list_area = pygame.Rect(0, 0, 200, 100)

    # Contenu plus court que la zone visible -> rien à défiler.
    st.set_bounds(list_area, content_h=50)
    assert st.max_scroll == 0
    assert st.scroll == 0
    st.scroll_by(48)
    assert st.scroll == 0

    # Contenu plus long -> défilement borné à [0, max_scroll].
    st.set_bounds(list_area, content_h=350)
    assert st.max_scroll == 250
    st.scroll_by(48)
    assert st.scroll == 48
    st.scroll_by(10_000)                         # tentative de dépasser le max
    assert st.scroll == st.max_scroll == 250
    st.scroll_by(-10_000)                        # tentative de descendre sous 0
    assert st.scroll == 0

    # Si le contenu rétrécit (ex: filtre réduit la liste), le scroll courant
    # doit être re-clampé au nouveau max plutôt que de rester hors bornes.
    st.scroll_by(200)
    assert st.scroll == 200
    st.set_bounds(list_area, content_h=120)      # nouveau max_scroll = 20
    assert st.max_scroll == 20
    assert st.scroll == 20


def test_scroll_state_handle_wheel_only_inside_rect():
    import pygame
    st = widgets.ScrollState()
    list_area = pygame.Rect(0, 0, 200, 100)
    st.set_bounds(list_area, content_h=400)      # max_scroll = 300

    inside = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=5, pos=(50, 50))
    outside = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=5, pos=(500, 500))
    other = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 50))

    assert st.handle_wheel(outside) is False
    assert st.scroll == 0
    assert st.handle_wheel(other) is False
    assert st.scroll == 0
    assert st.handle_wheel(inside) is True
    assert st.scroll == 48                       # molette bas = +48px


# ------------------------------------------------------------- TickFlash
def _fake_clock(monkeypatch, start=0):
    """Remplace pygame.time.get_ticks() par une horloge contrôlable (liste
    mutable [ms]) pour tester la décroissance du flash sans vrai sleep()."""
    import pygame
    now = [start]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: now[0])
    return now


def test_tick_flash_first_seen_is_base_color(monkeypatch):
    _fake_clock(monkeypatch)
    flash = widgets.TickFlash()
    base = (10, 10, 10)
    assert flash.tick("MVC", 100.0, (0, 255, 0), (255, 0, 0), base) == base


def test_tick_flash_up_is_full_saturation_during_hold(monkeypatch):
    now = _fake_clock(monkeypatch)
    flash = widgets.TickFlash()
    up, down, base = (0, 255, 0), (255, 0, 0), (10, 10, 10)
    flash.tick("MVC", 100.0, up, down, base)         # 1er point : référence
    now[0] += 10
    col = flash.tick("MVC", 101.0, up, down, base)    # hausse -> plein vert
    assert col == up
    now[0] += widgets.TickFlash.HOLD_MS - 1           # toujours dans le plateau
    col = flash.tick("MVC", 101.0, up, down, base)
    assert col == up


def test_tick_flash_down_decays_back_to_base(monkeypatch):
    now = _fake_clock(monkeypatch)
    flash = widgets.TickFlash()
    up, down, base = (0, 255, 0), (255, 0, 0), (10, 10, 10)
    flash.tick("MVC", 100.0, up, down, base)
    now[0] += 10
    col = flash.tick("MVC", 99.0, up, down, base)     # baisse -> plein rouge
    assert col == down
    now[0] += widgets.TickFlash.HOLD_MS + widgets.TickFlash.DECAY_MS + 50
    col = flash.tick("MVC", 99.0, up, down, base)     # largement décru -> couleur de base
    assert col == base


def test_tick_flash_no_change_keeps_previous_direction():
    flash = widgets.TickFlash()
    up, down, base = (0, 255, 0), (255, 0, 0), (10, 10, 10)
    flash.tick("MVC", 100.0, up, down, base)
    flash.tick("MVC", 105.0, up, down, base)
    col = flash.tick("MVC", 105.0, up, down, base)    # valeur inchangée : reste en vert (dans le plateau)
    assert col == up
