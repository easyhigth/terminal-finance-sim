"""Tests PAR PROPRIÉTÉS (Hypothesis) des invariants financiers du moteur.

La suite classique teste des cas choisis ; ici on laisse Hypothesis chercher
les cas que personne n'imagine. Les invariants verrouillés :

  1. DÉTERMINISME : (seed, n pas) reconstruit un marché bit-à-bit identique —
     c'est LE contrat des sauvegardes (qui ne stockent jamais les prix).
  2. PAS DE CRÉATION D'ARGENT : un aller-retour achat/vente immédiat ne peut
     jamais être profitable (commissions + spread + impact de marché).
  3. COMPTABILITÉ : après toute séquence de trades, la valeur nette égale
     cash + valorisation des positions, et les compteurs de frais montent.
  4. SÉRIALISABILITÉ : quoi qu'il arrive dans une partie, to_dict() reste
     JSON-sérialisable et rechargeable (une save ne doit jamais devenir
     impossible à écrire).

Ces tests sont skippés proprement si hypothesis n'est pas installé (dep de
test uniquement — la CI l'installe, cf. .github/workflows/tests.yml).
"""
import json

import numpy as np
import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st

from core import portfolio as pf  # noqa: E402
from core.game_state import GameState  # noqa: E402
from core.market import Market  # noqa: E402

# CI : garder la charge raisonnable — chaque exemple avance un vrai marché.
_SETTINGS = dict(max_examples=20, deadline=None)


def _market(seed, steps):
    m = Market(seed=seed)
    for _ in range(steps):
        m.step()
    return m


# ------------------------------------------------------------ déterminisme
@settings(**_SETTINGS)
@given(seed=st.integers(min_value=1, max_value=2_000_000_000),
       steps=st.integers(min_value=1, max_value=30))
def test_market_rebuild_is_bit_identical(seed, steps):
    """(seed, n) rejoué deux fois donne exactement les mêmes prix, indices et
    taux — sans quoi les sauvegardes dériveraient au rechargement."""
    a = _market(seed, steps)
    b = _market(seed, steps)
    assert np.array_equal(a.price, b.price)
    for name in a.index_hist:
        assert a.index_hist[name] == b.index_hist[name]
    assert a.macro_hist == b.macro_hist


# ------------------------------------------------- pas de création d'argent
@settings(**_SETTINGS)
@given(seed=st.integers(min_value=1, max_value=1_000_000),
       steps=st.integers(min_value=2, max_value=15),
       comp_idx=st.integers(min_value=0, max_value=319),
       qty=st.integers(min_value=1, max_value=500))
def test_immediate_roundtrip_never_profits(seed, steps, comp_idx, qty):
    """Acheter puis tout revendre sans que le marché bouge coûte toujours de
    l'argent (2 commissions + spread + impact) — jamais l'inverse."""
    m = _market(seed, steps)
    gs = GameState()
    p = gs.player
    p.grade_index = 8
    p.cash = 50_000_000.0
    tk = m.companies[comp_idx]["ticker"]
    start = p.cash
    r1 = pf.buy(p, m, tk, qty)
    if not r1.get("ok"):
        return  # ordre refusé (levier/liquidité) : rien à vérifier
    r2 = pf.sell(p, m, tk, qty)
    assert r2.get("ok")
    assert p.cash < start
    assert p.total_fees_paid >= r1["fee"] + r2["fee"] - 1e-9
    assert tk not in p.portfolio  # la position est intégralement soldée


# ------------------------------------------------------------- comptabilité
@settings(**_SETTINGS)
@given(seed=st.integers(min_value=1, max_value=1_000_000),
       ops=st.lists(st.tuples(st.integers(min_value=0, max_value=319),
                              st.integers(min_value=1, max_value=200),
                              st.booleans()),
                    min_size=1, max_size=8))
def test_net_worth_equals_cash_plus_positions(seed, ops):
    """Après une séquence arbitraire d'achats/ventes, la valeur nette égale
    cash + somme(actions × prix courant), et aucune position fantôme (0
    action) ne traîne dans le portefeuille."""
    m = _market(seed, 5)
    gs = GameState()
    p = gs.player
    p.grade_index = 8
    p.cash = 50_000_000.0
    for comp_idx, qty, is_sell in ops:
        tk = m.companies[comp_idx]["ticker"]
        if is_sell and tk in p.portfolio:
            pf.sell(p, m, tk, min(qty, p.portfolio[tk]["shares"]))
        else:
            pf.buy(p, m, tk, qty)
    equity_value = sum(pos["shares"] * m.price_of(tk)
                       for tk, pos in p.portfolio.items())
    assert pf.net_worth(p, m) == pytest.approx(p.cash + equity_value, rel=1e-6)
    assert all(pos["shares"] for pos in p.portfolio.values())


# ---------------------------------------------------------- sérialisabilité
@settings(**_SETTINGS)
@given(seed=st.integers(min_value=1, max_value=1_000_000),
       steps=st.integers(min_value=1, max_value=10),
       comp_idx=st.integers(min_value=0, max_value=319),
       qty=st.integers(min_value=1, max_value=100))
def test_game_state_stays_json_serialisable(seed, steps, comp_idx, qty):
    """Quoi qu'il arrive (trades + pas de jeu complets), to_dict() doit rester
    JSON-sérialisable et rechargeable — sinon la sauvegarde devient impossible
    au pire moment."""
    m = _market(seed, 2)
    gs = GameState()
    p = gs.player
    p.grade_index = 5
    p.cash = 2_000_000.0
    pf.buy(p, m, m.companies[comp_idx]["ticker"], qty)
    for _ in range(steps):
        m.step()
        gs.advance_step(market=m)
    blob = json.dumps(gs.to_dict())
    reloaded = GameState.from_dict(json.loads(blob))
    assert reloaded.player.cash == pytest.approx(p.cash)
    assert reloaded.player.portfolio == p.portfolio
