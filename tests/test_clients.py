"""Tests du carnet de clients récurrents (core/clients.py) : confiance,
capital croissant, référencements, perte définitive, intégration mandats."""
import random

from core import clients
from core.game_state import PlayerState


def _player():
    p = PlayerState()
    p.grade_index = 5
    return p


def test_book_seeds_three_clients():
    p = _player()
    clients.ensure_book(p, random.Random(1))
    assert len(p.clients) == clients.BOOK_SEED_SIZE
    assert all(c["trust"] == clients.TRUST_START for c in p.clients)
    assert len({c["name"] for c in p.clients}) == clients.BOOK_SEED_SIZE


def test_attach_client_overrides_offer_and_scales_capital():
    p = _player()
    rng = random.Random(2)
    clients.ensure_book(p, rng)
    # force le retour d'un client connu (rng.random() < RETURNING_PROB)
    offer = {"client": "Jetable", "client_profile": "x",
             "capital": 100_000.0, "reward_cash": 2_000.0}
    for _ in range(30):
        c = clients.attach_client(p, dict(offer), rng)
        if c is not None:
            break
    assert c is not None
    o2 = dict(offer)
    rng2 = random.Random(3)
    while clients.attach_client(p, o2, rng2) is None:
        o2 = dict(offer)
    assert o2["client"] in {x["name"] for x in p.clients}
    assert o2["from_book"] is True
    assert o2["capital"] != offer["capital"] or o2["reward_cash"] != offer["reward_cash"]


def test_success_grows_trust_and_capital():
    p = _player()
    clients.ensure_book(p, random.Random(1))
    c = p.clients[0]
    before_mult = c["capital_mult"]
    clients.record_outcome(p, c["name"], ok=True, rng=random.Random(1))
    assert c["trust"] == clients.TRUST_START + clients.TRUST_WIN
    assert c["capital_mult"] > before_mult


def test_referral_when_trust_crosses_threshold():
    p = _player()
    clients.ensure_book(p, random.Random(1))
    c = p.clients[0]
    c["trust"] = clients.TRUST_REFERRAL - 5
    events = clients.record_outcome(p, c["name"], ok=True, rng=random.Random(1))
    kinds = {e["kind"] for e in events}
    assert "referral" in kinds
    assert len(p.clients) == clients.BOOK_SEED_SIZE + 1
    assert any(x.get("referred_by") == c["name"] for x in p.clients)


def test_two_failures_lose_the_client_forever():
    p = _player()
    clients.ensure_book(p, random.Random(1))
    c = p.clients[0]
    clients.record_outcome(p, c["name"], ok=False)
    assert not c["lost"]
    events = clients.record_outcome(p, c["name"], ok=False)
    assert c["lost"] is True
    assert any(e["kind"] == "lost" for e in events)
    # un client perdu ne revient jamais dans les offres
    assert c not in clients.active_clients(p)
    # et son issue n'est plus comptabilisée
    assert clients.record_outcome(p, c["name"], ok=True) == []


def test_mandate_offer_can_come_from_book():
    from core import mandates
    p = _player()
    p.grade_index = 8   # mandats dès le grade 7 (mandates.MIN_GRADE)
    rng = random.Random(9)
    got_book_offer = False
    for _ in range(60):
        p.mandate_offers = []
        p.mandates = []
        offer = mandates.maybe_offer(p, rng=rng)
        if offer and offer.get("from_book"):
            got_book_offer = True
            assert offer["client"] in {c["name"] for c in p.clients}
            break
    assert got_book_offer


def test_serialisation_roundtrip():
    from core.game_state import GameState
    gs = GameState()
    clients.ensure_book(gs.player, random.Random(4))
    d = gs.to_dict()
    gs2 = GameState.from_dict(d)
    assert gs2.player.clients == gs.player.clients
