"""Tests des scénarios HISTORIQUES (core/histscenarios.py) : preset appliqué
au setup, crise scriptée déclenchée au pas prévu par le hook de pas dédié,
verdict rendu au pas de fin — le tout déterministe (graine fixe du preset)."""
from core import histscenarios as hist
from core.game_state import GameState
from core.market import WARMUP_STEPS, Market


def test_presets_are_well_formed():
    assert hist.HIST_SCENARIOS
    from core import scenarios
    known_crises = {s["id"] for s in scenarios.SCENARIOS}
    for s in hist.HIST_SCENARIOS:
        assert s["crisis_id"] in known_crises, s["id"]
        assert 0 < s["trigger_step"] < s["end_step"]
        assert 0.0 < s["nw_ratio_min"] <= 1.0
        assert s["seed"] > 0 and s["cash"] > 0
        assert hist.label(s) and hist.story(s)


def test_apply_configures_the_run():
    gs = GameState()
    p = gs.player
    assert hist.apply(p, "h2008") is True
    s = hist.get("h2008")
    assert p.market_seed == s["seed"]
    assert p.cash == s["cash"]
    assert p.grade_index == s["grade_index"]
    assert p.flags["hist_scenario"] == {"id": "h2008", "fired": False,
                                        "start_nw": None, "result": None}
    assert p.onboarding_done is True


def test_apply_unknown_id_is_a_noop():
    gs = GameState()
    assert hist.apply(gs.player, "nope") is False
    assert "hist_scenario" not in gs.player.flags


def test_crisis_fires_then_verdict_lands():
    """Boucle de jeu complète sur le scénario 2023 : la crise part au pas
    prévu, le verdict tombe au pas de fin, le journal en garde trace."""
    gs = GameState()
    p = gs.player
    hist.apply(p, "h2023")
    s = hist.get("h2023")
    m = Market(seed=p.market_seed)
    while m.step_count < WARMUP_STEPS:
        m.step()
    p.market_step = m.step_count

    fired_at = verdict_at = None
    for rel in range(1, s["end_step"] + 3):
        m.step()
        gs.advance_step(market=m)
        p.market_step = m.step_count
        st = p.flags.get("hist_scenario", {})
        if fired_at is None and st.get("fired"):
            fired_at = rel
        if verdict_at is None and st.get("result") is not None:
            verdict_at = rel
            break
    assert fired_at is not None and fired_at >= s["trigger_step"]
    assert verdict_at is not None and verdict_at >= s["end_step"]
    result = p.flags["hist_scenario"]["result"]
    assert set(result) == {"success", "ratio"}
    assert any("Défi historique" in e["text"] for e in p.journal)
    # le verdict est rendu UNE fois : rejouer des pas ne le change plus
    snapshot = dict(result)
    m.step()
    gs.advance_step(market=m)
    assert p.flags["hist_scenario"]["result"] == snapshot


def test_scenario_is_deterministic():
    """Deux runs du même preset (sans action joueur) donnent le même ratio."""
    ratios = []
    for _ in range(2):
        gs = GameState()
        p = gs.player
        hist.apply(p, "hdotcom")
        s = hist.get("hdotcom")
        m = Market(seed=p.market_seed)
        while m.step_count < WARMUP_STEPS:
            m.step()
        import random
        random.seed(7)   # events/deals tirent dans le random global
        for _rel in range(s["end_step"] + 2):
            m.step()
            gs.advance_step(market=m)
            if p.flags["hist_scenario"]["result"] is not None:
                break
        ratios.append(p.flags["hist_scenario"]["result"]["ratio"])
    assert ratios[0] == ratios[1]
