"""Tests du module M&A (core/ma.py) : catalogue, valorisation, acquisition
(financement cash+dette), axes d'amélioration, évolution trimestrielle
(croissance, service de la dette, incidents, détresse/défaut) et sortie (exit).
"""
import pytest

from core.game_state import PlayerState
from core import ma as M
from data.ma_targets import all_targets, TARGETS_BY_TICKER


def _player(grade_index=4, cash=2_000_000.0, day=1, quarter=1):
    p = PlayerState()
    p.grade_index = grade_index
    p.cash = cash
    p.day = day
    p.quarter = quarter
    return p


# --------------------------------------------------------------- catalogue
def test_catalog_has_fifty_unique_targets():
    targets = all_targets()
    assert len(targets) == 50
    tickers = {t["ticker"] for t in targets}
    assert len(tickers) == 50


def test_catalog_deterministic_across_imports():
    import importlib
    from data import ma_targets as mt
    importlib.reload(mt)
    assert [t["ticker"] for t in mt.all_targets()] == [t["ticker"] for t in all_targets()]


# --------------------------------------------------------------- valorisation
def test_valuation_blends_comps_and_dcf():
    t = all_targets()[0]
    v = M.valuation(t)
    assert v["fair_ev"] == pytest.approx(0.5 * v["comps_ev"] + 0.5 * v["dcf_ev"], rel=1e-9)
    assert v["equity_value"] == pytest.approx(max(0.0, v["fair_ev"] - t["net_debt"]), rel=1e-9)
    assert v["ebitda"] == pytest.approx(t["revenue"] * t["ebitda_margin"], rel=1e-9)


def test_ask_price_includes_control_premium():
    t = all_targets()[0]
    v = M.valuation(t)
    assert M.ask_price(t) == pytest.approx(v["fair_ev"] * (1 + M.CONTROL_PREMIUM), rel=1e-9)


# --------------------------------------------------------------- acquisition
def test_acquire_deducts_equity_cash_and_creates_instance():
    target = all_targets()[0]
    price = M.ask_price(target)
    p = _player(cash=price)  # assez pour n'importe quel niveau de dette
    cash_before = p.cash
    res = M.acquire(p, target["ticker"], debt_pct=0.6)
    assert res["ok"]
    terms = res["terms"]
    assert p.cash == pytest.approx(cash_before - terms["equity_cash"], rel=1e-9)
    inst = p.ma_owned[target["ticker"]]
    assert inst["debt_balance"] == pytest.approx(terms["debt_amount"], rel=1e-9)
    assert inst["equity_invested"] == pytest.approx(terms["equity_cash"], rel=1e-9)


def test_acquire_rejects_insufficient_cash():
    target = all_targets()[1]
    p = _player(cash=1.0)
    res = M.acquire(p, target["ticker"], debt_pct=0.6)
    assert not res["ok"]
    assert target["ticker"] not in (p.ma_owned or {})


def test_acquire_rejects_unknown_or_already_taken_ticker():
    p = _player(cash=10_000_000.0)
    res = M.acquire(p, "NOPE999", debt_pct=0.5)
    assert not res["ok"]
    target = all_targets()[2]
    res1 = M.acquire(p, target["ticker"], debt_pct=0.5)
    assert res1["ok"]
    res2 = M.acquire(p, target["ticker"], debt_pct=0.5)
    assert not res2["ok"]


def test_available_targets_excludes_owned_and_history():
    target = all_targets()[3]
    p = _player(cash=10_000_000.0)
    M.acquire(p, target["ticker"], debt_pct=0.5)
    assert target["ticker"] not in {t["ticker"] for t in M.available_targets(p)}
    M.exit_company(p, target["ticker"])
    assert target["ticker"] not in {t["ticker"] for t in M.available_targets(p)}


def test_financing_terms_clamped_to_max_debt_pct():
    terms = M.financing_terms(1000.0, debt_pct=0.99)
    assert terms["debt_pct"] == M.MAX_DEBT_PCT
    assert terms["debt_amount"] == pytest.approx(1000.0 * M.MAX_DEBT_PCT, rel=1e-9)
    assert terms["equity_cash"] == pytest.approx(1000.0 * (1 - M.MAX_DEBT_PCT), rel=1e-9)


# --------------------------------------------------------------- axes d'amélioration
def test_apply_action_costs_cash_and_changes_scores():
    target = all_targets()[4]
    p = _player(cash=10_000_000.0, quarter=1)
    M.acquire(p, target["ticker"], debt_pct=0.5)
    inst = p.ma_owned[target["ticker"]]
    mgmt_before = inst["management_score"]
    cash_before = p.cash
    res = M.apply_action(p, target["ticker"], "training")
    assert res["ok"]
    assert inst["management_score"] > mgmt_before
    assert p.cash < cash_before


def test_apply_action_negative_kind_credits_cash():
    target = all_targets()[5]
    p = _player(cash=10_000_000.0, quarter=1)
    M.acquire(p, target["ticker"], debt_pct=0.5)
    inst = p.ma_owned[target["ticker"]]
    morale_before = inst["morale"]
    cash_before = p.cash
    res = M.apply_action(p, target["ticker"], "layoffs")
    assert res["ok"]
    assert inst["morale"] < morale_before
    assert p.cash > cash_before  # licenciements = économie immédiate


def test_one_action_per_quarter_enforced():
    target = all_targets()[6]
    p = _player(cash=10_000_000.0, quarter=1)
    M.acquire(p, target["ticker"], debt_pct=0.5)
    res1 = M.apply_action(p, target["ticker"], "training")
    assert res1["ok"]
    res2 = M.apply_action(p, target["ticker"], "org")
    assert not res2["ok"]
    p.quarter = 2
    res3 = M.apply_action(p, target["ticker"], "org")
    assert res3["ok"]


def test_net_margin_never_exceeds_ebitda_margin_after_action():
    target = all_targets()[7]
    p = _player(cash=10_000_000.0, quarter=1)
    M.acquire(p, target["ticker"], debt_pct=0.5)
    inst = p.ma_owned[target["ticker"]]
    M.apply_action(p, target["ticker"], "capex")
    assert inst["net_margin"] <= inst["ebitda_margin"]


# --------------------------------------------------------------- évolution trimestrielle
def test_evolve_quarter_grows_healthy_company_and_amortizes_debt():
    target = all_targets()[8]
    p = _player(cash=10_000_000.0, day=1, quarter=1)
    M.acquire(p, target["ticker"], debt_pct=0.4)
    inst = p.ma_owned[target["ticker"]]
    # scores déjà au-dessus de la moyenne -> conditions favorables
    inst["management_score"] = 80.0
    inst["morale"] = 80.0
    inst["efficiency"] = 80.0
    debt0 = inst["debt_balance"]
    for q in range(1, 9):
        p.day += 91
        p.quarter = q + 1
        M.evolve_quarter(p)
    inst = p.ma_owned.get(target["ticker"])
    assert inst is not None  # ne doit pas faire défaut dans de bonnes conditions
    assert inst["debt_balance"] < debt0


def test_evolve_quarter_mean_reverts_scores_without_action():
    target = all_targets()[9]
    p = _player(cash=10_000_000.0, day=1, quarter=1)
    M.acquire(p, target["ticker"], debt_pct=0.4)
    inst = p.ma_owned[target["ticker"]]
    inst["management_score"] = 95.0
    p.day += 91
    p.quarter = 2
    M.evolve_quarter(p)
    inst = p.ma_owned[target["ticker"]]
    assert inst["management_score"] < 95.0
    assert inst["management_score"] > M.SCORE_MEAN


def test_evolve_quarter_defaults_when_player_cannot_bail_out():
    target = all_targets()[10]
    p = _player(cash=10_000_000.0, day=1, quarter=1)
    M.acquire(p, target["ticker"], debt_pct=M.MAX_DEBT_PCT)
    inst = p.ma_owned[target["ticker"]]
    # cash-flow nul (revenu nul) + trésorerie joueur nulle -> défaut assuré
    inst["revenue"] = 0.0
    inst["cash_buffer"] = 0.0
    p.cash = 0.0
    p.day += 91
    p.quarter = 2
    events = M.evolve_quarter(p)
    assert target["ticker"] not in p.ma_owned
    assert any("DÉFAUT" in e or "redressement" in e for e in events)
    hist = p.ma_history[-1]
    assert hist["status"] == "perdue"
    assert hist["pnl"] < 0


# --------------------------------------------------------------- sortie (exit)
def test_exit_company_credits_cash_and_logs_history():
    target = all_targets()[11]
    p = _player(cash=10_000_000.0, day=1, quarter=1)
    M.acquire(p, target["ticker"], debt_pct=0.4)
    cash_before = p.cash
    res = M.exit_company(p, target["ticker"])
    assert res["ok"]
    assert p.cash > cash_before
    assert target["ticker"] not in p.ma_owned
    hist = p.ma_history[-1]
    assert hist["status"] == "cédée"
    assert hist["moic"] >= 0


def test_holdings_value_reflects_owned_equity_and_zero_after_exit():
    target = all_targets()[12]
    p = _player(cash=10_000_000.0, day=1, quarter=1)
    M.acquire(p, target["ticker"], debt_pct=0.4)
    assert M.holdings_value(p) > 0.0
    M.exit_company(p, target["ticker"])
    assert M.holdings_value(p) == 0.0


# --------------------------------------------------------------- états financiers
def test_statements_for_produces_five_coherent_years():
    target = all_targets()[13]
    block = M.statements_for(target, base_year=2025, n_years=5)
    assert len(block) == 5
    assert [b["year"] for b in block] == [2025, 2024, 2023, 2022, 2021]
    for b in block:
        inc = b["income"]
        assert inc["tax"] == pytest.approx(inc["ebt"] - inc["net_income"], rel=1e-6)
        bal = b["balance"]
        assert bal["total_assets"] == pytest.approx(bal["total_liab"] + bal["equity"], rel=1e-6)
