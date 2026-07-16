"""Tests du module TRS (Total Return Swaps) — logique pure.

Patron parallèle à tests/test_credit_derivs.py : un marché seedé avancé de 60
pas, un joueur grade 9 (déblocage creditdesk), un nom « risqué » via
credit_risk.market_scan. Couvre la cote (spread croissant avec la PD), la
symétrie receiver/payer au MTM, les flux courus (financement + dividende),
l'évènement de crédit symétrique, l'échéance et la sortie anticipée.
"""
import pytest

from core import credit_risk as CR
from core import trs as TRS
from core.game_state import PlayerState
from core.market import Market
from core.portfolio_margin import net_worth


@pytest.fixture()
def market():
    m = Market(seed=31)
    for _ in range(60):
        m.step()
    return m


@pytest.fixture()
def player():
    p = PlayerState()
    p.grade_index = 9
    p.cash = 3_000_000.0
    return p


def _risky(market):
    return CR.market_scan(market, n=1)[0]["ticker"]


def _solid(market):
    return CR.market_scan(market, n=12)[-1]["ticker"]


# ================================================================== quote
def test_quote_funding_spread_increases_with_pd(market):
    rk, sd = _risky(market), _solid(market)
    qrk = TRS.quote(market, rk, 3.0)
    qsd = TRS.quote(market, sd, 3.0)
    assert qrk and qsd
    assert qrk["funding_bps"] > qsd["funding_bps"]      # nom risqué se finance plus cher
    assert qrk["ref_rate"] == qsd["ref_rate"]           # même taux directeur macro


def test_quote_rejects_unanalyzable(market):
    assert TRS.quote(market, "ZZZ_NOPE", 3.0) is None


# ============================================================ MTM symétrie
def test_receiver_mtm_positive_when_price_rises(market, player):
    tk = _solid(market)
    r = TRS.open_trs(player, market, tk, 200_000.0, 3.0, "receiver")
    assert r["ok"]
    pos = player.trs_positions[0]
    pos["entry_price"] = market.price_of(tk) * 0.5      # le cours a « doublé »
    assert TRS.mark_to_market(market, pos) > 0


def test_payer_mtm_is_opposite_of_receiver(market, player):
    tk = _solid(market)
    TRS.open_trs(player, market, tk, 200_000.0, 3.0, "receiver")
    rec = player.trs_positions[0]
    rec["entry_price"] = market.price_of(tk) * 0.5
    mrec = TRS.mark_to_market(market, rec)
    # même trade côté payer
    TRS.open_trs(player, market, tk, 200_000.0, 3.0, "payer")
    pay = player.trs_positions[-1]
    pay["entry_price"] = market.price_of(tk) * 0.5
    assert TRS.mark_to_market(market, pay) == pytest.approx(-mrec, abs=1e-6)


# ================================================================ accrue
def test_receiver_pays_financing_payer_receives(market, player):
    tk = _solid(market)
    TRS.open_trs(player, market, tk, 200_000.0, 3.0, "receiver")
    TRS.open_trs(player, market, tk, 200_000.0, 3.0, "payer")
    pos_rec, pos_pay = player.trs_positions
    # forçons un financement élevé pour dominer le (faible) dividende du solide
    pos_rec["funding_bps"] = pos_pay["funding_bps"] = 5000.0
    rate = pos_rec["ref_rate"] + 5000.0 / 1e4
    financing = 200_000.0 * rate * (5 / 365.0)
    mt = market.metrics(tk)
    div = 200_000.0 * (mt["div_yield"] if mt else 0.0) * (5 / 365.0)
    # receiver net = dividende − financement (< 0) ; payer net = financement − dividende (> 0)
    assert div - financing < 0
    assert financing - div > 0
    TRS.accrue(player, market, 5)
    assert pos_rec["accrued_financing"] > 0       # receiver accumule le coût de portage
    assert pos_pay["accrued_financing"] < 0       # payer accumule un gain de financement


def test_accrual_updates_accrued_financing_for_mtm(market, player):
    tk = _solid(market)
    TRS.open_trs(player, market, tk, 200_000.0, 3.0, "receiver")
    pos = player.trs_positions[0]
    pos["funding_bps"] = 5000.0
    assert pos["accrued_financing"] == 0.0
    TRS.accrue(player, market, 5)
    assert pos["accrued_financing"] > 0                 # le financement couru s'accumule
    # le MTM receiver est amputé du financement couru
    pos["entry_price"] = market.price_of(tk)            # pas de gain de prix
    assert TRS.mark_to_market(market, pos) < 0          # = -accrued_financing


# ======================================================== credit event
def test_credit_event_receiver_loses_payer_gains(market, player):
    tk = _risky(market)
    TRS.open_trs(player, market, tk, 200_000.0, 3.0, "receiver")
    TRS.open_trs(player, market, tk, 200_000.0, 3.0, "payer")
    for p in player.trs_positions:
        p["entry_price"] = market.price_of(tk) * 100.0   # action « effondrée »
    cash0 = player.cash
    events = TRS.evaluate_due(player, market)
    kinds = {e["side"]: e["kind"] for e in events}
    assert kinds == {"receiver": "credit_event", "payer": "credit_event"}
    # receiver absorbe la perte, payer gagne symétriquement → somme nulle
    delta = player.cash - cash0
    assert delta == pytest.approx(0.0, abs=1e-6)
    assert not player.trs_positions


# ============================================================ échéance
def test_maturity_settles_mtm_and_closes(market, player):
    tk = _solid(market)
    TRS.open_trs(player, market, tk, 200_000.0, 1.0, "receiver")
    pos = player.trs_positions[0]
    pos["entry_price"] = market.price_of(tk) * 0.5      # cours doublé → MTM positif
    pos["maturity_step"] = market.step_count            # échéance maintenant
    expected = TRS.mark_to_market(market, pos)
    cash0 = player.cash
    events = TRS.evaluate_due(player, market)
    assert events and events[0]["kind"] == "expiry"
    assert events[0]["payoff"] == pytest.approx(expected)
    assert player.cash == pytest.approx(cash0 + expected)
    assert not player.trs_positions


# ========================================================== close early
def test_close_early_pays_mtm(market, player):
    tk = _solid(market)
    r = TRS.open_trs(player, market, tk, 200_000.0, 3.0, "receiver")
    pid = r["position"]["id"]
    player.trs_positions[0]["entry_price"] = market.price_of(tk) * 0.5
    expected = TRS.mark_to_market(market, player.trs_positions[0])
    cash0 = player.cash
    res = TRS.close(player, market, pid)
    assert res["ok"] and res["mtm"] == pytest.approx(expected)
    assert player.cash == pytest.approx(cash0 + expected)
    assert not player.trs_positions


def test_close_unknown_returns_notfound(player, market):
    assert TRS.close(player, market, 999)["ok"] is False


# =============================================================== net_worth
def test_holdings_value_included_in_net_worth(market, player):
    tk = _solid(market)
    nw0 = net_worth(player, market)
    TRS.open_trs(player, market, tk, 200_000.0, 3.0, "receiver")
    pos = player.trs_positions[0]
    pos["entry_price"] = market.price_of(tk) * 0.5      # cours doublé
    nw1 = net_worth(player, market)
    assert nw1 - nw0 == pytest.approx(TRS.holdings_value(player, market))
    # dénouement → le MTM est réglé en cash, la position disparaît du net_worth
    pos["maturity_step"] = market.step_count
    TRS.evaluate_due(player, market)
    assert not player.trs_positions
    # après règlement, le cash porte le MTM ; net_worth reflète le cash (≈ nw0 + mtm)
    assert net_worth(player, market) == pytest.approx(nw0 + (nw1 - nw0))
