"""Tests des fonctions de desk EN DIRECT ajoutées au Tableur (apps/app_sheet.py
::_market_fn) : =YTM()/=REPO_RATE()/=CDS_SPREAD()/=PD()/=IV() — symétriques des
fonctions de marché existantes (PRICE/INDEX/FX…), même résolveur externe
injecté dans core/spreadsheet_engine."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main

pygame.font.init()


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    for _ in range(30):
        a.market.step()
    a.scenes.go("desktop")
    return a


def _sheet_app(app):
    desk = app.scenes.current
    w = desk._open_sheet_app()
    return w.app_obj


def _set_and_eval(sheet_app, formula):
    sheet = sheet_app.sheet
    sheet_app._sync_market()
    sheet.set("A1", formula)
    return sheet.get_value("A1")


def test_ytm_resolves_a_real_bond(app):
    from core import bonds
    sa = _sheet_app(app)
    bond_id = bonds.sovereign_quotes(app.market)[0]["id"]
    v = _set_and_eval(sa, f'=YTM("{bond_id}")')
    assert isinstance(v, float)
    assert v == pytest.approx(bonds.ytm(app.market, bond_id))


def test_ytm_unknown_bond_is_na(app):
    sa = _sheet_app(app)
    v = _set_and_eval(sa, '=YTM("NOPE_NOT_A_BOND")')
    assert v == "#N/A"


def test_repo_rate_matches_module(app):
    from core import repo
    sa = _sheet_app(app)
    v = _set_and_eval(sa, "=REPO_RATE()")
    assert v == pytest.approx(repo.repo_rate(app.market))


def test_cds_spread_matches_module(app):
    from core import cds, credit_risk as cr
    sa = _sheet_app(app)
    tk = cr.market_scan(app.market, n=1)[0]["ticker"]
    v = _set_and_eval(sa, f'=CDS_SPREAD("{tk}",3)')
    q = cds.quote(app.market, tk, 3.0)
    assert v == pytest.approx(q["spread_bps"])


def test_pd_matches_module(app):
    from core import credit_risk as cr
    sa = _sheet_app(app)
    tk = cr.market_scan(app.market, n=1)[0]["ticker"]
    v = _set_and_eval(sa, f'=PD("{tk}",3)')
    f = cr.merton_credit(app.market, tk, horizon=3.0)
    assert v == pytest.approx(f["pd"])


def test_iv_recovers_input_vol_via_bs_price(app):
    from core import option_pricing as op
    from core import options as opt

    sa = _sheet_app(app)
    tk = app.market.top_companies(n=1)[0]["ticker"]
    spot = app.market.price_of(tk)
    r = opt.risk_free_rate(app.market)
    sigma = 0.28
    years = 1.0
    price = op.bs_price(spot, spot, years, r, sigma, option="call")
    v = _set_and_eval(sa, f'=IV("{tk}",1,{years},{price})')
    assert v == pytest.approx(sigma, abs=1e-3)


def test_unknown_desk_function_args_are_na_not_crash(app):
    sa = _sheet_app(app)
    assert _set_and_eval(sa, "=YTM()") == "#N/A"
    assert _set_and_eval(sa, "=CDS_SPREAD()") == "#N/A"
    assert _set_and_eval(sa, "=PD()") == "#N/A"
    assert _set_and_eval(sa, "=IV()") == "#N/A"
