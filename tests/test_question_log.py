"""
test_question_log.py — Le registre des questions déjà vues garantit qu'on ne
repose JAMAIS une question (missions ET examens), et que les examens n'utilisent
jamais une question déjà rencontrée en mission.
"""
import random

from core import exam, missions, question_log
from core.game_state import PlayerState
from data import question_bank


def _fresh_player(grade=1, track="General"):
    p = PlayerState()
    p.grade_index = grade
    p.track = track
    return p


# --------------------------------------------------------------------------- #
# Identité et registre
# --------------------------------------------------------------------------- #
def test_identity_bank_vs_generated():
    bank = {"id": "q42", "q": "Que mesure le ROE ?", "choices": ["a"], "answer": 0}
    assert question_log.identity(bank) == "b:q42"
    converted = {"kind": "mcq", "prompt": "Que mesure le ROE ?", "src_id": "q42"}
    assert question_log.identity(converted) == "b:q42"   # même identité après conversion
    gen = {"kind": "fill", "prompt": "Calculez la duration modifiée."}
    assert question_log.identity(gen).startswith("g:")
    assert question_log.identity({}) is None


def test_normalization_stable_across_accents_and_case():
    a = question_log.identity({"prompt": "Duration modifiée d'une OBLIGATION"})
    b = question_log.identity({"prompt": "duration  modifiee  d'une obligation"})
    assert a == b


def test_mark_seen_dedupes_and_caps():
    p = _fresh_player()
    question_log.mark_seen(p, [{"prompt": "A"}, {"prompt": "A"}, {"prompt": "B"}])
    assert len(p.seen_questions) == 2
    # cap FIFO
    big = [{"prompt": f"Q{i}"} for i in range(question_log.MAX + 50)]
    question_log.mark_seen(p, big)
    assert len(p.seen_questions) == question_log.MAX


# --------------------------------------------------------------------------- #
# Banque de missions : éviter les déjà-vues, recycler seulement si épuisé
# --------------------------------------------------------------------------- #
def test_for_grade_avoids_seen_when_possible():
    rng = random.Random(1)
    pool = question_bank.available_pool(2, "General", "fr")
    assert len(pool) > 6
    seen = {"b:" + pool[0]["id"], "b:" + pool[1]["id"]}
    picked = question_bank.for_grade(2, "General", 5, rng=rng, avoid=seen)
    got = {"b:" + q["id"] for q in picked}
    assert got.isdisjoint(seen)          # aucune des questions évitées n'est ressortie
    assert len(picked) == 5


def test_for_grade_recycles_when_pool_exhausted():
    rng = random.Random(2)
    pool = question_bank.available_pool(0, "General", "fr")
    # on marque TOUT le pool comme vu : la révision doit quand même rendre des questions
    seen = {"b:" + q["id"] for q in pool}
    picked = question_bank.for_grade(0, "General", 3, rng=rng, avoid=seen)
    assert len(picked) == 3              # tolérance de répétition en révision


# --------------------------------------------------------------------------- #
# Examens : jamais une question déjà vue (mission ou examen précédent)
# --------------------------------------------------------------------------- #
def test_exam_excludes_seen_identities():
    rng = random.Random(3)
    first = exam.generate(2, rng=random.Random(3), n=12)
    avoid = {question_log.identity(it) for it in first}
    avoid.discard(None)
    second = exam.generate(2, rng=rng, n=12, avoid=avoid)
    ids = {question_log.identity(it) for it in second}
    assert ids.isdisjoint(avoid)         # aucun recouvrement avec le 1er examen


def test_exam_never_reuses_mission_bank_question():
    # une question de banque servie en mission ne doit jamais réapparaître en examen
    p = _fresh_player(grade=2)
    m = missions.generate(2, market=None, rng=random.Random(4), player=p)
    bank_items = [it for it in m["items"] if it.get("src_id")]
    assert bank_items
    question_log.mark_seen(p, bank_items)
    seen = question_log.seen_set(p)
    ex = exam.generate(2, rng=random.Random(5), n=15, avoid=seen)
    ex_ids = {question_log.identity(it) for it in ex}
    for it in bank_items:
        assert question_log.identity(it) not in ex_ids


# --------------------------------------------------------------------------- #
# Missions : les questions de banque évitent le déjà-vu
# --------------------------------------------------------------------------- #
def test_mission_bank_items_carry_src_id_and_avoid_seen():
    p = _fresh_player(grade=1)
    m1 = missions.generate(1, market=None, rng=random.Random(6), player=p)
    b1 = [it for it in m1["items"] if it.get("src_id")]
    assert b1                                   # les items de banque portent bien src_id
    question_log.mark_seen(p, b1)
    seen1 = {it["src_id"] for it in b1}
    m2 = missions.generate(1, market=None, rng=random.Random(6), player=p)
    b2_ids = {it["src_id"] for it in m2["items"] if it.get("src_id")}
    # au grade 1 le pool est assez large : la 2e mission ne repioche pas les mêmes
    assert b2_ids.isdisjoint(seen1)


def test_backward_compat_no_player_unchanged():
    # appel historique sans player : comportement inchangé, pas de crash
    m = missions.generate(1, market=None, rng=random.Random(7))
    assert m["items"]
    # generate d'examen sans avoid : inchangé
    assert exam.generate(1, rng=random.Random(7), n=10)
