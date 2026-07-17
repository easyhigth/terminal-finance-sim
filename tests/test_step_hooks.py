"""Tests de core/step_hooks.py : le registre ORDONNÉ des systèmes joués à
chaque pas de marché (extrait de GameState.advance_step). L'ordre des hooks
est un invariant de gameplay — ces tests le verrouillent, ainsi que la forme
du contexte/du résumé que le terminal consomme."""
from core import step_hooks
from core.game_state import GameState
from core.market import Market


def _names():
    return [name for name, _fn in step_hooks.STEP_HOOKS]


def test_hook_names_are_unique():
    names = _names()
    assert len(names) == len(set(names))


def test_conditional_orders_run_before_margin_check():
    """Un ordre voulu par le joueur passe AVANT une liquidation forcée."""
    names = _names()
    assert names.index("conditional_orders") < names.index("financing_and_margin")


def test_net_worth_computed_after_all_settlements():
    """La valeur nette du pas (historique, faillite) voit l'état FINAL."""
    names = _names()
    idx_nw = names.index("net_worth")
    for name in names:
        if name in ("net_worth", "hist_scenario", "portfolio_news"):
            continue
        assert names.index(name) < idx_nw, name


def test_carry_income_credited_before_margin_financing():
    """Les revenus de portage tombent en cash avant le calcul de marge."""
    names = _names()
    idx_margin = names.index("financing_and_margin")
    for name in ("equity_dividends", "bond_coupons", "fx_carry", "funding_desk"):
        assert names.index(name) < idx_margin, name


def test_new_context_has_all_summary_keys():
    ctx = step_hooks.new_context()
    for key in ("dividends", "financing", "margin_call", "structured_due",
                "securitised_due", "hedges_due", "options_due", "ipos_settled",
                "fx_due", "macro_resolved", "swaps_expired",
                "conditional_orders_executed", "nw"):
        assert key in ctx


def test_run_fills_context_on_fresh_game():
    m = Market(seed=42)
    for _ in range(3):
        m.step()
    gs = GameState()
    gs.player.cash = 500_000.0
    ctx = step_hooks.run(gs.player, m)
    assert ctx["nw"] > 0
    assert ctx["dividends"] >= 0.0


def test_advance_step_summary_shape_unchanged():
    """Le dict-résumé consommé par le terminal garde exactement ses clés."""
    m = Market(seed=7)
    for _ in range(2):
        m.step()
    gs = GameState()
    gs.player.cash = 500_000.0
    summary = gs.advance_step(market=m)
    for key in ("events", "expired", "new_deals", "net", "dividends",
                "financing", "margin_call", "structured_due", "securitised_due",
                "hedges_due", "options_due", "ipos_settled", "fx_due",
                "macro_resolved", "swaps_expired", "conditional_orders_executed",
                "quarter_changed", "quarter_report", "ma_events", "review_offer",
                "game_over", "rep_log"):
        assert key in summary, key


def test_advance_step_without_market_still_works():
    gs = GameState()
    gs.player.cash = 100_000.0
    summary = gs.advance_step(market=None)
    assert summary["game_over"] is False
    assert summary["dividends"] == 0.0
