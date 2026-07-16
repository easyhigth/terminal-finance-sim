"""Compatibilité des sauvegardes ANCIENNES : des fixtures JSON committées
(tests/fixtures/save_v0_*.json) figent le format d'anciennes versions du jeu.
Chaque fixture doit se charger sans lever, reconstruire son marché depuis
(market_seed, market_step) — le save ne stocke jamais les prix — et pouvoir
avancer plusieurs pas de jeu complets.

Règle d'or : on n'ÉDITE jamais une fixture existante pour faire passer un
test — si un changement de format casse ces tests, c'est le chargement
(`GameState.from_dict`) qui doit devenir tolérant, pas la fixture. Quand le
format évolue volontairement, on AJOUTE une nouvelle fixture de la nouvelle
version, on ne réécrit pas l'histoire."""
import json
import os

import pytest

from core.game_state import GameState
from core.market import Market

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
FIXTURES = sorted(fn for fn in os.listdir(FIXTURE_DIR)
                  if fn.startswith("save_") and fn.endswith(".json"))


def _load(fn):
    with open(os.path.join(FIXTURE_DIR, fn), "r", encoding="utf-8") as f:
        return GameState.from_dict(json.load(f))


def _rebuild_market(p):
    m = Market(seed=p.market_seed)
    while m.step_count < p.market_step:
        m.step()
    return m


def test_fixture_list_is_not_empty():
    assert FIXTURES, "aucune fixture de sauvegarde — le filet de compat a disparu"


@pytest.mark.parametrize("fn", FIXTURES)
def test_old_save_loads_without_error(fn):
    gs = _load(fn)
    p = gs.player
    # les champs présents dans la fixture sont repris tels quels
    assert p.cash > 0
    assert p.market_seed == 1234
    # les champs ABSENTS (ajoutés par des versions ultérieures) retombent
    # sur les défauts au lieu de lever
    assert isinstance(p.trs_positions, list)
    assert isinstance(p.arb_positions, list)
    assert isinstance(p.repo_positions, list)
    assert isinstance(p.flags, dict)


@pytest.mark.parametrize("fn", FIXTURES)
def test_old_save_market_rebuilds_deterministically(fn):
    gs = _load(fn)
    m = _rebuild_market(gs.player)
    assert m.step_count == gs.player.market_step
    # le roster est déterministe : les tickers du portefeuille existent encore
    for tk in gs.player.portfolio:
        assert tk in m.ticker_idx, tk


@pytest.mark.parametrize("fn", FIXTURES)
def test_old_save_can_play_several_steps(fn):
    gs = _load(fn)
    p = gs.player
    m = _rebuild_market(p)
    for _ in range(5):
        m.step()
        p.market_step = m.step_count
        summary = gs.advance_step(market=m)
        assert "net" in summary
    assert not p.game_over
    # l'historique de valeur nette a bien été alimenté
    assert len(p.cash_history) >= 5


def test_old_save_without_onboarding_key_marks_it_done():
    """Une sauvegarde antérieure au parcours d'intégration ne doit pas se
    voir imposer le tutoriel après coup."""
    gs = _load("save_v0_minimal.json")
    assert gs.player.onboarding_done is True


def test_old_save_roundtrips_through_current_format():
    """Charger une vieille save puis la resauver au format courant doit
    produire un dict complet rechargeable (migration implicite)."""
    gs = _load("save_v0_midgame.json")
    d = gs.to_dict()
    gs2 = GameState.from_dict(d)
    assert gs2.player.cash == gs.player.cash
    assert gs2.player.portfolio == gs.player.portfolio
    assert gs2.player.conditional_orders == gs.player.conditional_orders
