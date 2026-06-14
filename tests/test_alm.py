"""Tests du desk ALM (core/alm.py)."""
import pytest

from core import alm


def test_repricing_gap_and_nii():
    rg = alm.repricing_gap(400, 600)
    assert rg == -200                              # liability-sensitive
    # +100 bps -> la NII baisse (gap négatif)
    assert alm.nii_change(rg, 0.01) == pytest.approx(-2.0)


def test_duration_gap_and_eve():
    dg = alm.duration_gap(1000, 4.5, 900, 1.5)
    assert dg == pytest.approx(4.5 - 0.9 * 1.5)
    # duration gap positif -> hausse des taux détruit de la valeur des fonds propres
    assert alm.delta_eve(1000, dg, 0.01) < 0


def test_summary_profile():
    s = alm.summary(alm.DEFAULT_STATE, 0.01)
    assert s["profile"] == "liability-sensitive"
    assert s["equity"] == pytest.approx(100.0)     # 1000 - 900
    assert s["delta_nii"] < 0 and s["delta_eve"] < 0


def test_asset_sensitive_gains_on_hike():
    state = {"rsa": 700, "rsl": 300, "assets": 1000, "liabilities": 900,
             "dur_a": 1.0, "dur_l": 3.0}
    s = alm.summary(state, 0.01)
    assert s["profile"] == "asset-sensitive"
    assert s["delta_nii"] > 0                       # gap positif -> NII monte
    assert s["delta_eve"] > 0                       # duration gap négatif -> EVE monte
