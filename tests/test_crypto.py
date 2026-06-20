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


# --------------------------------------------------------- exécution réaliste
def test_fill_price_costs_more_under_market_stress():
    """Pour un même ordre crypto, un marché en plein stress (last_stress_level
    proche de 1.0) doit coûter plus cher à l'exécution qu'un marché calme
    (item 9/15 : le coût d'exécution varie avec le régime de marché)."""
    m = _mk()
    m.last_stress_level = 0.0
    calm = crypto.fill_price(m, "BITC", 1.0, "buy")
    m.last_stress_level = 1.0
    stressed = crypto.fill_price(m, "BITC", 1.0, "buy")
    assert stressed > calm > 0


def test_fill_price_more_expensive_for_illiquid_altcoin_than_major():
    """Une petite crypto spéculative (DOGY, tier Illiquide) doit coûter plus cher
    à l'exécution qu'un Bitcorn (BITC, tier Peu liquide), pour un même ordre
    notionnel équivalent — la profondeur de marché diffère par actif."""
    m = _mk()
    bitc_mid = crypto.spot(m, "BITC")
    dogy_mid = crypto.spot(m, "DOGY")
    bitc_fill = crypto.fill_price(m, "BITC", 1.0, "buy")
    dogy_fill = crypto.fill_price(m, "DOGY", 1_000_000.0, "buy")
    bitc_cost_frac = bitc_fill / bitc_mid - 1
    dogy_cost_frac = dogy_fill / dogy_mid - 1
    assert dogy_cost_frac > bitc_cost_frac
    assert crypto.quote(m, "BITC")["liquidity"] == "Peu liquide"
    assert crypto.quote(m, "DOGY")["liquidity"] == "Illiquide"


def test_cbdc_fill_price_has_no_spread_or_impact():
    """La CBDC est un dépôt garanti banque centrale, pas un actif de marché : son
    prix d'exécution doit rester exactement au pair, quelle que soit la taille
    de l'ordre ou le stress de marché."""
    m = _mk()
    m.last_stress_level = 1.0
    assert crypto.fill_price(m, "CBDC", 10 ** 9, "buy") == 1.0
    assert crypto.fill_price(m, "CBDC", 10 ** 9, "sell") == 1.0


def test_fill_price_deterministic_for_same_market_state():
    """Même état de marché (même seed, même step, même stress) -> même prix
    d'exécution, à chaque appel (aucun aléa non reproductible introduit)."""
    m = _mk()
    m.last_stress_level = 0.5
    a = crypto.fill_price(m, "ETHR", 2.0, "sell")
    b = crypto.fill_price(m, "ETHR", 2.0, "sell")
    assert a == b
