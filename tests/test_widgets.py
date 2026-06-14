"""Tests des helpers purs de graphes (ui/widgets.py) : agrégation OHLC et SMA.

(L'import de pygame est nécessaire mais aucun affichage n'est requis.)
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

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
