"""Tests du lot « dérivés & structure » : CDS (prime Merton, MTM, évènement
de crédit, câblage advance_step), IRS (payeur gagne quand les taux montent,
couverture DV01), convertibles (plancher + option, delta, arb), profondeur
de carnet (impact croissant) et gonflement de vol pré-earnings."""
import pytest

from core import bonds as B
from core import cds as CDS
from core import convertibles as CONV
from core import irs as IRS
from core import liquidity as LIQ
from core import options as OPT
from core.game_state import GameState, PlayerState
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
    from core import credit_risk as CR
    return CR.market_scan(market, n=1)[0]["ticker"]


# ==================================================================== CDS
def test_cds_quote_tracks_merton_spread(market):
    from core import credit_risk as CR
    tk = _risky(market)
    q = CDS.quote(market, tk, 3.0)
    f = CR.merton_credit(market, tk, horizon=3.0)
    assert q["spread_bps"] == pytest.approx(f["spread_bps"] + CDS.MARKET_SPREAD_BPS)


def test_cds_premium_accrues_and_mtm_moves_with_spread(market, player):
    tk = _risky(market)
    r = CDS.buy_protection(player, market, tk, 200_000.0, 3.0)
    assert r["ok"]
    assert CDS.accrue(player, market, 5) < 0           # la prime coûte
    pos = player.cds_positions[0]
    # spread d'entrée artificiellement bas → la protection vaut du MTM positif
    pos["entry_spread_bps"] = 1.0
    assert CDS.mark_to_market(market, pos) > 0


def test_cds_credit_event_pays_out(market, player):
    tk = _risky(market)
    CDS.buy_protection(player, market, tk, 200_000.0, 3.0)
    pos = player.cds_positions[0]
    pos["entry_price"] = market.price_of(tk) * 100.0   # action « effondrée » vs entrée
    cash0 = player.cash
    events = CDS.evaluate_due(player, market)
    assert events and events[0]["kind"] == "credit_event"
    assert player.cash == pytest.approx(cash0 + (1 - CDS.RECOVERY) * 200_000.0)
    assert not player.cds_positions


def test_cds_expires_worthless(market, player):
    tk = _risky(market)
    CDS.buy_protection(player, market, tk, 100_000.0, 1.0)
    player.cds_positions[0]["maturity_step"] = market.step_count
    events = CDS.evaluate_due(player, market)
    assert events and events[0]["kind"] == "expiry" and events[0]["payoff"] == 0.0


# ==================================================================== IRS
def test_payer_swap_gains_when_rates_rise(market, player):
    r = IRS.enter_swap(player, market, "payer", 1_000_000.0, 5.0)
    assert r["ok"]
    pos = player.irs_positions[0]
    assert IRS.mark_to_market(market, pos) == pytest.approx(0.0, abs=1e-9)
    pos["fixed_rate"] -= 0.01                          # taux courant 100 bp au-dessus
    assert IRS.mark_to_market(market, pos) > 0         # le payeur gagne


def test_swap_hedge_neutralizes_book_dv01(market, player):
    quotes = sorted(B.sovereign_quotes(market), key=lambda q: q["years"])
    assert B.buy_bond(player, market, quotes[-1]["id"], 100)["ok"]
    dv01_before = IRS.portfolio_dv01(player, market)
    assert dv01_before > 0
    notional = IRS.hedge_notional(dv01_before, years=5.0)
    IRS.enter_swap(player, market, "payer", notional, 5.0)
    assert abs(IRS.portfolio_dv01(player, market)) < dv01_before * 0.05


def test_swap_accrual_signed_and_expiry(market, player):
    IRS.enter_swap(player, market, "payer", 1_000_000.0, 2.0)
    pos = player.irs_positions[0]
    pos["fixed_rate"] = 0.0                            # variable > fixe : payeur reçoit
    assert IRS.accrue(player, market, 5) > 0
    pos["maturity_step"] = market.step_count
    IRS.accrue(player, market, 5)
    assert not player.irs_positions                    # dénoué à l'échéance


# =========================================================== convertibles
def test_convertible_price_is_floor_plus_option(market):
    tk = market.top_companies(n=1)[0]["ticker"]
    q = CONV.quote(market, tk)
    assert q["price"] == pytest.approx(q["bond_floor"] + q["option_value"])
    assert q["price"] > q["bond_floor"]                # l'option vaut > 0
    assert 0 < q["delta"] < q["ratio"]                 # entre obligation et action


def test_convertible_buy_sell_roundtrip_and_coupons(market, player):
    tk = market.top_companies(n=1)[0]["ticker"]
    r = CONV.buy(player, market, tk, 20)
    assert r["ok"]
    assert CONV.accrue(player, market, 5) > 0          # coupons courus
    assert net_worth(player, market) == pytest.approx(3_000_000.0, rel=0.01)
    res = CONV.sell(player, market, player.convertibles[0]["id"])
    assert res["ok"] and not player.convertibles


def test_convertible_arb_plan_shorts_delta(market, player):
    tk = market.top_companies(n=1)[0]["ticker"]
    CONV.buy(player, market, tk, 50)
    plan = CONV.arb_plan(market, player.convertibles[0])
    assert plan is not None and plan["ticker"] == tk
    q = CONV.position_quote(market, player.convertibles[0])
    assert plan["shares"] == round(q["delta"] * 50)


# ============================================================== profondeur
def test_depth_ladder_costs_grow_with_size(market):
    tk = market.top_companies(n=1)[0]["ticker"]
    ladder = LIQ.depth_ladder(market, tk)
    assert ladder is not None and len(ladder["rows"]) == 5
    costs = [r["cost_bps"] for r in ladder["rows"]]
    assert costs == sorted(costs)                      # impact non-linéaire
    for r in ladder["rows"]:
        assert r["bid"] < ladder["mid"] < r["ask"]     # spread des deux côtés


# ============================================================ vol earnings
def test_earnings_vol_bump_and_crush(market, monkeypatch):
    tk = market.top_companies(n=1)[0]["ticker"]
    base_metrics = market.metrics(tk)

    def fake_metrics(t, steps):
        return {**base_metrics, "steps_to_earnings": steps}
    monkeypatch.setattr(market, "metrics",
                        lambda t: fake_metrics(t, 0))
    m0 = OPT.earnings_vol_mult(market, tk)
    monkeypatch.setattr(market, "metrics",
                        lambda t: fake_metrics(t, 2))
    m2 = OPT.earnings_vol_mult(market, tk)
    monkeypatch.setattr(market, "metrics",
                        lambda t: fake_metrics(t, 10))
    m10 = OPT.earnings_vol_mult(market, tk)
    assert m0 == pytest.approx(1.0 + OPT.EARNINGS_VOL_BUMP)   # veille : max
    assert 1.0 < m2 < m0                                       # approche : monte
    assert m10 == 1.0                                          # loin : rien
    # le crush : la prime d'un straddle la veille > la prime loin des résultats
    monkeypatch.setattr(market, "metrics", lambda t: fake_metrics(t, 0))
    hot = OPT.quote(PlayerState(), market, tk, "call", 1.0, 0.25)["premium"]
    monkeypatch.setattr(market, "metrics", lambda t: fake_metrics(t, 10))
    cold = OPT.quote(PlayerState(), market, tk, "call", 1.0, 0.25)["premium"]
    assert hot > cold


# ================================================================= câblage
def test_advance_step_wires_deriv_flows(market, player):
    tk = _risky(market)
    CDS.buy_protection(player, market, tk, 200_000.0, 3.0)
    IRS.enter_swap(player, market, "payer", 500_000.0, 5.0)
    CONV.buy(player, market, market.top_companies(n=1)[0]["ticker"], 10)
    gs = GameState()
    gs.player = player
    gs.advance_step(market=market)                     # aucun crash, flux réglés
    assert len(player.cds_positions) == 1
    assert len(player.irs_positions) == 1


def test_net_worth_includes_new_asset_classes(market, player):
    nw0 = net_worth(player, market)
    CONV.buy(player, market, market.top_companies(n=1)[0]["ticker"], 10)
    assert net_worth(player, market) == pytest.approx(nw0, rel=0.01)  # cash→titre
    IRS.enter_swap(player, market, "payer", 500_000.0, 5.0)
    player.irs_positions[0]["fixed_rate"] -= 0.01
    assert net_worth(player, market) > nw0 * 0.999     # MTM du swap compté