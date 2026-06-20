"""Tests de l'ADN de la firme de départ (core/firms.py) et de son application
dans le portefeuille (levier/marge/secteurs), les obligations, les deals et
les mandats.
"""
import pytest

from core import deals, firms, mandates
from core import portfolio as pf
from core.game_state import PlayerState
from core.market import Market


def _player(firm=None, grade=8):
    p = PlayerState()
    if firm:
        p.firm = firm
    p.grade_index = grade
    p.cash = 1_000_000.0
    return p


# --------------------------------------------------------------- perks de base
def test_all_firms_have_name_tagline_desc():
    for f in firms.FIRMS:
        assert f["name"]
        assert f["tagline"]
        assert f["desc"]


def test_get_unknown_returns_none():
    assert firms.get("nope") is None


def test_unknown_player_firm_falls_back_to_neutral():
    p = _player(firm=None)
    assert firms.perk(p, "deal_reward_mult") == 1.0
    assert firms.perk(p, "max_leverage_add") == 0.0
    assert firms.perk(p, "deal_success_bonus") == 0.0
    assert firms.excluded_sectors(p) == []


def test_apply_sets_firm_and_scales_starting_cash():
    p = PlayerState()
    p.cash = 100_000.0
    p.cash_history = [100_000.0]
    firms.apply(p, "banque_universelle")
    assert p.firm == "banque_universelle"
    mult = firms.get("banque_universelle")["perks"]["starting_cash_mult"]
    assert p.cash == pytest.approx(100_000.0 * mult)
    assert p.cash_history[-1] == pytest.approx(p.cash)


def test_apply_unknown_id_falls_back_to_first_firm():
    p = PlayerState()
    p.cash = 50_000.0
    f = firms.apply(p, "does_not_exist")
    assert f["id"] == firms.FIRMS[0]["id"]
    assert p.firm == firms.FIRMS[0]["id"]


# --------------------------------------------------------------- ESG : secteurs exclus
def test_esg_firm_excludes_energie_and_materiaux():
    p = _player(firm="maison_esg")
    assert not firms.sector_allowed(p, "Energie")
    assert not firms.sector_allowed(p, "Materiaux")
    assert firms.sector_allowed(p, "Tech")


def test_non_esg_firm_has_no_sector_exclusion():
    p = _player(firm="hedge_fund")
    assert firms.sector_allowed(p, "Energie")


def test_buy_blocked_in_excluded_sector_for_esg():
    m = Market(seed=1)
    # trouve un ticker du secteur Energie
    tk = next(c["ticker"] for c in m.companies if c["sector"] == "Energie")
    m.price[m.ticker_idx[tk]] = 50.0
    p = _player(firm="maison_esg")
    res = pf.buy(p, m, tk, 10)
    assert res["ok"] is False
    assert res["reason"] == "sector_excluded"


def test_buy_allowed_in_excluded_sector_for_non_esg():
    m = Market(seed=1)
    tk = next(c["ticker"] for c in m.companies if c["sector"] == "Energie")
    m.price[m.ticker_idx[tk]] = 50.0
    p = _player(firm="hedge_fund")
    res = pf.buy(p, m, tk, 10)
    assert res["ok"] is True


# --------------------------------------------------------------- Levier / marge
def test_hedge_fund_has_higher_max_leverage_than_universal_bank():
    ph = _player(firm="hedge_fund")
    pb = _player(firm="banque_universelle")
    assert pf._max_leverage(ph) > pf._max_leverage(pb)


def test_hedge_fund_stricter_maintenance_margin():
    ph = _player(firm="hedge_fund")
    p0 = _player(firm=None)
    assert pf._maint_margin(ph) > pf._maint_margin(p0)


def test_universal_bank_cheaper_margin_financing():
    m = Market(seed=1)
    tk = m.companies[0]["ticker"]
    m.price[m.ticker_idx[tk]] = 100.0
    p0 = _player(firm=None, grade=8); p0.cash = 10_000.0
    pb = _player(firm="banque_universelle", grade=8); pb.cash = 10_000.0
    pf.buy(p0, m, tk, 250)
    pf.buy(pb, m, tk, 250)
    f0 = pf.accrue_financing(p0, m, days=5)["interest"]
    fb = pf.accrue_financing(pb, m, days=5)["interest"]
    assert fb < f0


# --------------------------------------------------------------- deals : boutique M&A
def test_boutique_ma_richer_deal_reward():
    mult = firms.perk(_player(firm="boutique_ma"), "deal_reward_mult")
    assert mult > 1.0


def test_desk_obligataire_fewer_deals():
    mult = firms.perk(_player(firm="desk_obligataire"), "deal_gen_prob_mult")
    assert mult < 1.0


def test_deal_success_probability_uses_firm_bonus():
    deal = {"kind": "General", "difficulty": 3}
    p0 = _player(firm=None)
    ph = _player(firm="hedge_fund")
    assert deals.success_probability(ph, deal) > deals.success_probability(p0, deal)


# --------------------------------------------------------------- mandats : gestionnaire d'actifs
def test_asset_manager_better_mandate_terms():
    p = _player(firm="asset_manager")
    assert firms.perk(p, "mandate_offer_mult") > 1.0
    assert firms.perk(p, "mandate_reward_mult") > 1.0
    assert mandates.MIN_GRADE >= 0  # sanity: module importable/used in suite


# --------------------------------------------------------------- bêta / obligations
def test_hedge_fund_higher_beta_exposure_mult():
    assert firms.perk(_player(firm="hedge_fund"), "beta_exposure_mult") > 1.0


def test_desk_obligataire_lower_beta_exposure_mult():
    assert firms.perk(_player(firm="desk_obligataire"), "beta_exposure_mult") < 1.0


def test_desk_obligataire_cheaper_bond_commission():
    from core import bonds
    m = Market(seed=1)
    bid = bonds.BONDS[0]["id"]
    p0 = _player(firm=None); p0.cash = 1_000_000.0
    pd = _player(firm="desk_obligataire"); pd.cash = 1_000_000.0
    r0 = bonds.buy_bond(p0, m, bid, 10)
    rd = bonds.buy_bond(pd, m, bid, 10)
    assert rd["fee"] < r0["fee"]
