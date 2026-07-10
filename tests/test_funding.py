"""Tests du desk de FINANCEMENT : repo (haircut/carry/appel de marge),
prêt-emprunt de titres (frais des shorts, revenu de prêt) et marché
monétaire (dépôts à terme, sweep) — y compris le câblage advance_step et
l'agrégation net_worth."""
import pytest

from core import bonds as B
from core import money_market as MM
from core import portfolio as pf
from core import repo as REPO
from core import seclending as SL
from core.game_state import GameState, PlayerState
from core.market import Market
from core.portfolio_margin import net_worth


@pytest.fixture()
def market():
    m = Market(seed=29)
    for _ in range(40):
        m.step()
    return m


@pytest.fixture()
def player():
    p = PlayerState()
    p.grade_index = 9
    p.cash = 2_000_000.0
    return p


def _sov(market, longest=True):
    quotes = sorted(B.sovereign_quotes(market), key=lambda q: q["years"])
    return quotes[-1 if longest else 0]


# ==================================================================== repo
def test_repo_quote_leverage_and_carry(market):
    q = _sov(market)
    dv = REPO.quote(market, q["id"], 100)
    assert dv is not None
    assert dv["margin"] == pytest.approx(dv["value"] * dv["haircut"])
    assert dv["borrowed"] == pytest.approx(dv["value"] - dv["margin"])
    assert dv["value"] / dv["margin"] > 5              # haircut 3 % → levier > 5×
    # carry de l'equity : (YTM×V − repo×emprunt)/marge
    expected = (dv["ytm"] * dv["value"] - dv["rate"] * dv["borrowed"]) / dv["margin"]
    assert dv["equity_carry"] == pytest.approx(expected)


def test_repo_open_debits_margin_only_and_counts_in_net_worth(market, player):
    q = _sov(market)
    cash0 = player.cash
    nw0 = net_worth(player, market)
    r = REPO.open_repo(player, market, q["id"], 100)
    assert r["ok"]
    dv = r["quote"]
    assert player.cash == pytest.approx(cash0 - dv["margin"])
    # le patrimoine ne bouge pas à l'ouverture (cash → equity de la pension)
    assert net_worth(player, market) == pytest.approx(nw0, rel=1e-6)


def test_repo_accrue_coupons_minus_interest(market, player):
    q = _sov(market)
    REPO.open_repo(player, market, q["id"], 100)
    flux = REPO.accrue(player, market, 5)
    pos = player.repo_positions[0]
    b = B._BY_ID[q["id"]]
    coupon = B.FACE * (b["coupon"] - B._RATING_LOSS.get(b["rating"], 0.0)) \
        * 100 * (5 / 365.0)
    interest = pos["borrowed"] * REPO.repo_rate(market) * (5 / 365.0)
    assert flux == pytest.approx(coupon - interest)


def test_repo_margin_call_forced_liquidation(market, player):
    q = _sov(market)
    REPO.open_repo(player, market, q["id"], 100)
    pos = player.repo_positions[0]
    # on gonfle artificiellement l'emprunt : equity sous la maintenance
    pos["borrowed"] = REPO.position_state(market, pos)["value"] * 0.999
    events = REPO.mark_and_call(player, market)
    assert len(events) == 1
    assert not player.repo_positions                   # liquidée de force


def test_repo_haircut_widens_with_stress(market):
    q = _sov(market)
    market.last_stress_level = 0.0
    h_calm = REPO.haircut(market, q["kind"])
    rate_calm = REPO.repo_rate(market)
    market.last_stress_level = 1.0
    assert REPO.haircut(market, q["kind"]) > h_calm    # 2008 : le haircut monte
    assert REPO.repo_rate(market) > rate_calm
    market.last_stress_level = 0.0


def test_repo_close_returns_equity(market, player):
    q = _sov(market)
    r = REPO.open_repo(player, market, q["id"], 50)
    cash_after_open = player.cash
    res = REPO.close_repo(player, market, r["position"]["id"])
    assert res["ok"]
    assert player.cash == pytest.approx(cash_after_open + res["proceeds"])
    assert not player.repo_positions


# ================================================================= lending
def test_short_pays_borrow_fee_long_earns_when_lending(market, player):
    tks = [c["ticker"] for c in market.top_companies(n=2)]
    pf.buy(player, market, tks[0], 100)
    pf.short(player, market, tks[1], 50)
    flux_off = SL.accrue(player, market, 5)
    assert flux_off < 0                                # le short paie, rien ne prête
    player.flags["sec_lending"] = True
    flux_on = SL.accrue(player, market, 5)
    assert flux_on > flux_off                          # le prêt des longs compense


def test_small_caps_are_hard_to_borrow(market):
    big = market.top_companies(n=1)[0]["ticker"]
    caps = [(c["ticker"], market.metrics(c["ticker"])["mktcap"])
            for c in market.companies]
    small = min(caps, key=lambda x: x[1])[0]
    assert SL.borrow_fee_rate(market, small) > SL.borrow_fee_rate(market, big)


def test_lender_gets_split_of_borrow_fee(market):
    tk = market.top_companies(n=1)[0]["ticker"]
    assert SL.lending_rate(market, tk) == pytest.approx(
        SL.borrow_fee_rate(market, tk) * SL.LENDER_SPLIT)


# ============================================================ money market
def test_term_deposit_locks_and_matures_with_interest(market, player):
    r = MM.open_deposit(player, market, 300_000.0, 18)
    assert r["ok"]
    assert player.cash == pytest.approx(1_700_000.0)
    assert net_worth(player, market) == pytest.approx(2_000_000.0, rel=1e-9)
    for _ in range(18):
        market.step()
    results = MM.mature_due(player, market)
    assert len(results) == 1 and results[0]["interest"] > 0
    assert player.cash > 2_000_000.0 - 1e-6
    assert not player.mm_deposits


def test_term_premium_orders_deposit_rates(market):
    rates = [MM.deposit_rate(market, t) for t in MM.TERM_STEPS]
    assert rates == sorted(rates)                      # plus long = mieux payé
    assert MM.sweep_rate(market) < rates[0]            # le liquide paie moins


def test_sweep_accrues_only_above_buffer_and_when_enabled(market, player):
    assert MM.sweep_accrue(player, market, 5) == 0.0   # désactivé
    player.flags["mm_sweep"] = True
    got = MM.sweep_accrue(player, market, 5)
    idle = player.cash - MM.SWEEP_BUFFER
    assert got == pytest.approx(idle * MM.sweep_rate(market) * (5 / 365.0))
    player.cash = MM.SWEEP_BUFFER / 2
    assert MM.sweep_accrue(player, market, 5) == 0.0   # sous le coussin


def test_advance_step_wires_funding_flows(market, player):
    q = _sov(market)
    REPO.open_repo(player, market, q["id"], 100)
    player.flags["mm_sweep"] = True
    expected = (REPO.accrue(player, market, 5)
                + MM.sweep_accrue(player, market, 5))
    gs = GameState()
    gs.player = player
    cash0 = player.cash
    gs.advance_step(market=market)
    assert player.cash >= cash0 + expected * 0.5       # + salaire et autres flux


def test_save_load_roundtrip_keeps_funding_positions(market, player, tmp_path):
    q = _sov(market)
    REPO.open_repo(player, market, q["id"], 30)
    MM.open_deposit(player, market, 100_000.0, 6)
    gs = GameState()
    gs.player = player
    path = tmp_path / "save.json"
    gs.export_to(str(path))
    gs2 = GameState.import_from(str(path))
    assert gs2 is not None
    assert len(gs2.player.repo_positions) == 1
    assert len(gs2.player.mm_deposits) == 1
    assert gs2.player.repo_positions[0]["bond_id"] == q["id"]
