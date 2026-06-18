"""Tests des états financiers (core/financials.py).

On verrouille la COHÉRENCE : réconciliation du compte de résultat, équilibre du
bilan, recoupement de la dette nette, monotonie de l'historique, déterminisme.
"""
import pytest

from core import financials as F
from core.market import Market


def _market():
    return Market(seed=2024)


def test_income_statement_reconciles():
    m = _market()
    for tk in [c["ticker"] for c in m.companies[:30]]:
        inc = F.income_statement(m, tk)
        # marge brute = CA - COGS
        assert inc["gross_profit"] == pytest.approx(inc["revenue"] - inc["cogs"], rel=1e-9)
        # EBITDA = marge brute - SG&A - R&D
        assert inc["ebitda"] == pytest.approx(inc["gross_profit"] - inc["sga"] - inc["rnd"], rel=1e-9)
        # EBIT = EBITDA - D&A
        assert inc["ebit"] == pytest.approx(inc["ebitda"] - inc["da"], rel=1e-9)
        # EBT = EBIT - intérêts
        assert inc["ebt"] == pytest.approx(inc["ebit"] - inc["interest"], rel=1e-9)
        # impôt = EBT - résultat net (réconciliation exacte)
        assert inc["tax"] == pytest.approx(inc["ebt"] - inc["net_income"], rel=1e-9)


def test_net_income_matches_market_metrics():
    """Le résultat net du compte de résultat == celui de la fiche (revenue×net_margin)."""
    m = _market()
    tk = m.companies[0]["ticker"]
    inc = F.income_statement(m, tk)
    mt = m.metrics(tk)
    assert inc["net_income"] == pytest.approx(mt["net_income"], rel=1e-9)
    assert inc["eps"] == pytest.approx(mt["eps"], rel=1e-9)


def test_balance_sheet_balances():
    m = _market()
    for tk in [c["ticker"] for c in m.companies[:40]]:
        for offset in (0, 1, 2):
            bs = F.balance_sheet(m, tk, offset)
            # Actif = Passif + Capitaux propres (par construction)
            assert bs["total_assets"] == pytest.approx(bs["total_liab"] + bs["equity"], rel=1e-9)
            # actifs courants = cash + créances + stocks
            assert bs["current_assets"] == pytest.approx(
                bs["cash"] + bs["receivables"] + bs["inventory"], rel=1e-9)


def test_net_debt_reconciles_with_company():
    m = _market()
    tk = m.companies[3]["ticker"]
    c = m.companies[3]
    bs = F.balance_sheet(m, tk, 0)
    # dette - cash == net_debt de la société (exercice N)
    assert bs["net_debt"] == pytest.approx(c["net_debt"], rel=1e-6, abs=1e-6)


def test_history_is_monotonic_for_growing_firms():
    m = _market()
    # une société à croissance positive : CA N > N-1 > N-2
    tk = next(c["ticker"] for c in m.companies if F.annual_growth(m, c["ticker"]) > 0.01)
    revs = [F.income_statement(m, tk, k)["revenue"] for k in (0, 1, 2)]
    assert revs[0] > revs[1] > revs[2]


def test_statements_block_and_years():
    m = _market()
    tk = m.companies[0]["ticker"]
    block = F.statements(m, tk, base_year=2025, n_years=3)
    assert [b["year"] for b in block] == [2025, 2024, 2023]
    assert all("income" in b and "balance" in b for b in block)


def test_deterministic():
    a, b = Market(seed=7), Market(seed=7)
    tk = a.companies[0]["ticker"]
    assert F.income_statement(a, tk)["net_income"] == F.income_statement(b, tk)["net_income"]
    assert F.balance_sheet(a, tk)["equity"] == F.balance_sheet(b, tk)["equity"]


def test_fiscal_year_rolls_forward():
    from core.game_state import PlayerState
    p = PlayerState()
    p.day = 1
    assert F.fiscal_year(p, 2025) == 2025
    p.day = 400          # > 1 an de jeu
    assert F.fiscal_year(p, 2025) == 2026


def test_equity_positive_for_most_firms():
    m = _market()
    eqs = [F.balance_sheet(m, c["ticker"], 0)["equity"] for c in m.companies]
    # la grande majorité des sociétés ont des capitaux propres positifs
    assert sum(1 for e in eqs if e > 0) / len(eqs) > 0.9
