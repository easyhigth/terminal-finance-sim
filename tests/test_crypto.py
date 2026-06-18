"""Tests des crypto-actifs et de la contagion de depeg (core/crypto.py)."""
from core import crypto, market


def _mk(seed=1):
    m = market.Market(seed=seed)
    m.sync_to(market.WARMUP_STEPS)
    return m


def test_stable_ids_and_contagion_group_are_disjoint():
    assert crypto.STABLE_IDS & crypto.CONTAGION_GROUP == set()
    assert "USDX" in crypto.STABLE_IDS
    assert "CBDC" not in crypto.CONTAGION_GROUP
    assert {"BITC", "ETHR", "SOLR", "DOGY"} == crypto.CONTAGION_GROUP


def test_cbdc_spot_always_pegged():
    m = _mk()
    for step in (0, 10, 500):
        m.step_count = step
        assert crypto.spot(m, "CBDC") == 1.0


def test_contagion_risk_zero_outside_group():
    m = _mk()
    assert crypto.contagion_risk(m, "USDX") == 0.0
    assert crypto.contagion_risk(m, "CBDC") == 0.0


def test_contagion_risk_in_bounds_for_group_members():
    m = _mk()
    for step in range(0, 200, 20):
        m.step_count = step
        for cid in crypto.CONTAGION_GROUP:
            r = crypto.contagion_risk(m, cid)
            assert 0.0 <= r <= 1.0


def test_contagion_risk_is_deterministic_for_same_seed_and_step():
    m1 = _mk(seed=99)
    m2 = _mk(seed=99)
    m1.step_count = 150
    m2.step_count = 150
    for cid in crypto.CONTAGION_GROUP:
        assert crypto.contagion_risk(m1, cid) == crypto.contagion_risk(m2, cid)


def test_contagion_risk_differs_across_seeds_eventually():
    # pas une garantie stricte, mais avec assez de seeds on doit voir une différence
    risks = set()
    for seed in range(20):
        m = _mk(seed=seed)
        m.step_count = 100
        risks.add(crypto.contagion_risk(m, "BITC"))
    assert len(risks) > 1


def test_active_depegs_only_lists_stable_ids():
    m = _mk()
    for step in range(0, 300, 10):
        m.step_count = step
        for sid in crypto.active_depegs(m):
            assert sid in crypto.STABLE_IDS


def test_name_returns_label_for_known_id_and_id_for_unknown():
    assert crypto.name("BITC") == "Bitcorn"
    assert crypto.name("NOPE") == "NOPE"


def test_buy_and_sell_roundtrip_updates_cash_and_holdings():
    from core.game_state import PlayerState
    m = _mk()
    p = PlayerState(continent="Europe")
    p.cash = 1_000_000.0
    r = crypto.buy(p, m, "BITC", 1.0)
    assert r["ok"] is True
    assert "BITC" in p.crypto
    r2 = crypto.sell(p, m, "BITC", 1.0)
    assert r2["ok"] is True
    assert "BITC" not in p.crypto
