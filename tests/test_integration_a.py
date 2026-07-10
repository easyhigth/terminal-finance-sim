"""Tests du lot « intégration A » : pédagogie des nouveaux desks (leçons/
glossaire/questions), limites de VaR imposées par la firme (avertissement →
réputation → réduction forcée) et l'instantané « P&L Explain » posé par
advance_step (+ l'app qui le lit)."""
import pytest

from core import risklimits as RL
from core.game_state import GameState, PlayerState
from core.market import Market
from data.glossary_data import GLOSSARY
from data.lessons import LESSONS
from data.lessons_en import LESSONS_EN
from data.question_bank import QUESTIONS


# ============================================================== contenu
def test_lessons_have_full_en_coverage():
    ids = [x["id"] for x in LESSONS]
    assert len(ids) == len(set(ids))
    missing = [i for i in ids if i not in LESSONS_EN]
    assert missing == []


def test_new_desk_lessons_present():
    ids = {x["id"] for x in LESSONS}
    for expected in ("repo", "cds", "merton_credit", "irs", "convertible",
                     "kelly", "garch", "regimes", "brinson", "component_var",
                     "kupiec", "gamma_scalping", "fx_carry", "immunization",
                     "cointegration", "vol_surface"):
        assert expected in ids


def test_glossary_has_new_terms():
    for expected in ("Repo", "CDS", "IRS", "TWAP", "Critère de Kelly", "GARCH"):
        assert expected in GLOSSARY


def test_question_bank_adv_ids_unique_and_answerable():
    ids = [q["id"] for q in QUESTIONS]
    assert len(ids) == len(set(ids))
    adv = [q for q in QUESTIONS if q["id"].startswith("adv")]
    assert len(adv) == 20
    for q in adv:
        assert "answer" in q or "correct" in q or "choices" in q


# ======================================================= limites de VaR
@pytest.fixture()
def market():
    m = Market(seed=17)
    for _ in range(40):
        m.step()
    return m


@pytest.fixture()
def player():
    p = PlayerState()
    p.cash = 5_000_000.0
    p.grade_index = 0
    return p


def test_firm_var_no_breach_on_empty_book(player, market):
    chk = RL.firm_var_check(player, market)
    assert chk["breach"] is False
    assert chk["var"] == 0.0


def test_firm_var_limit_grows_with_grade(player, market):
    lim0 = RL.firm_var_limit(player)
    player.grade_index = 9
    lim9 = RL.firm_var_limit(player)
    assert lim9 > lim0


def _load_up(player, market, mult=40):
    """Empile assez de positions risquées pour dépasser la limite de VaR du
    grade 0 (très basse, 0.06 M)."""
    from core import portfolio as pf
    for c in market.top_companies(n=8):
        price = market.price_of(c["ticker"])
        if not price:
            continue
        qty = max(1, int((player.cash * 0.9 / 8) / price))
        pf.buy(player, market, c["ticker"], qty * mult // 40 if mult != 40 else qty)


def test_firm_var_enforce_escalates_warn_then_rep_then_cut(player, market):
    from core import portfolio as pf
    player.cash = 50_000_000.0
    for c in market.top_companies(n=5):
        price = market.price_of(c["ticker"])
        if not price:
            continue
        pf.buy(player, market, c["ticker"], int(2_000_000 / price))
    chk = RL.firm_var_check(player, market)
    assert chk["breach"], "le book doit dépasser la limite du grade 0 pour ce test"

    ev1 = RL.firm_var_enforce(player, market)
    assert ev1["level"] == "warn"
    assert player.flags["firm_var_streak"] == 1

    ev2 = RL.firm_var_enforce(player, market)
    assert ev2["level"] == "warn"
    ev3 = RL.firm_var_enforce(player, market)
    assert ev3["level"] == "rep"
    assert player.flags["firm_var_streak"] == 3

    ev4 = RL.firm_var_enforce(player, market)
    assert ev4["level"] == "rep"
    ev5 = RL.firm_var_enforce(player, market)
    assert ev5["level"] == "cut"
    assert ev5["cut_qty"] > 0
    assert player.flags["firm_var_streak"] == 0


def test_firm_var_streak_resets_when_no_breach(player, market):
    player.flags["firm_var_streak"] = 3
    ev = RL.firm_var_enforce(player, market)
    assert ev is None
    assert player.flags["firm_var_streak"] == 0


# =========================================================== P&L Explain
def test_advance_step_writes_pnl_explain_snapshot(player, market):
    gs = GameState()
    gs.player = player
    gs.advance_step(market=market)
    snap = player.flags.get("pnl_explain")
    assert snap is not None
    for key in ("step", "day", "nw", "nw_prev", "passive", "net"):
        assert key in snap


def test_pnl_explain_nw_prev_chains_across_steps(player, market):
    gs = GameState()
    gs.player = player
    gs.advance_step(market=market)
    nw1 = player.flags["pnl_explain"]["nw"]
    market.step()
    gs.advance_step(market=market)
    snap2 = player.flags["pnl_explain"]
    assert snap2["nw_prev"] == pytest.approx(nw1)


def test_pnl_explain_app_draws_without_data_and_with_data(player, market):
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from apps.app_pnlexplain import PnlExplainApp

    class _FakeApp:
        def __init__(self, gs, market):
            self.gs = gs
            self._market = market

        def ensure_market(self):
            return self._market

    gs = GameState()
    gs.player = player
    app = PnlExplainApp.__new__(PnlExplainApp)
    app.app = _FakeApp(gs, market)
    app.on_open()
    surf = pygame.Surface((940, 580))
    rect = surf.get_rect()
    app.draw(surf, rect)  # sans snapshot : ne doit pas planter

    from core import portfolio as pf
    c = market.top_companies(n=1)[0]
    price = market.price_of(c["ticker"])
    pf.buy(player, market, c["ticker"], max(1, int(100_000 / price)))
    gs.advance_step(market=market)
    app.draw(surf, rect)  # avec snapshot + position action : ne doit pas planter
