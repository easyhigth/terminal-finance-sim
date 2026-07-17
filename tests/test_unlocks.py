"""Tests du déblocage progressif des fonctionnalités selon le grade (core/unlocks.py)."""
from core import unlocks
from core.game_state import PlayerState


def _player(grade=0):
    p = PlayerState()
    p.grade_index = grade
    return p


def test_feature_locked_below_required_grade():
    p = _player(grade=0)
    assert not unlocks.unlocked(p, "trade")


def test_feature_unlocked_at_required_grade():
    p = _player(grade=unlocks.required_grade("trade"))
    assert unlocks.unlocked(p, "trade")


def test_unknown_feature_defaults_to_unlocked():
    p = _player(grade=0)
    assert unlocks.unlocked(p, "inconnu")


def test_cmd_unlocked_follows_mapped_feature():
    p = _player(grade=0)
    assert not unlocks.cmd_unlocked(p, "BUY")
    p.grade_index = unlocks.required_grade("trade")
    assert unlocks.cmd_unlocked(p, "BUY")


def test_cmd_unlocked_true_for_unmapped_command():
    p = _player(grade=0)
    assert unlocks.cmd_unlocked(p, "INCONNU")


def test_every_label_has_a_matching_unlock_entry():
    assert set(unlocks.LABELS) == set(unlocks.UNLOCKS)


def test_next_unlock_returns_lowest_pending_grade():
    p = _player(grade=0)
    label, grade = unlocks.next_unlock(p)
    pending = [g for g in unlocks.UNLOCKS.values() if g > p.grade_index]
    assert grade == min(pending)
    assert label == unlocks.feature_label(
        next(f for f, g in unlocks.UNLOCKS.items() if g == grade)
    )


def test_next_unlock_none_when_everything_open():
    p = _player(grade=max(unlocks.UNLOCKS.values()))
    assert unlocks.next_unlock(p) is None


def test_track_affinity_locks_mismatched_module_until_top_grade():
    p = _player(grade=6)
    p.track = "Quant"
    # "ma" est affilié à M&A : un Quant reste verrouillé jusqu'au grade max
    assert not unlocks.unlocked(p, "ma")
    assert unlocks.effective_required_grade(p, "ma") == unlocks.TRACK_LOCK_GRADE
    assert unlocks.track_lock_note(p, "ma") is not None
    p.grade_index = unlocks.TRACK_LOCK_GRADE
    assert unlocks.unlocked(p, "ma")


def test_track_affinity_allows_matching_track_at_base_grade():
    p = _player(grade=unlocks.required_grade("ma"))
    p.track = "M&A"
    assert unlocks.unlocked(p, "ma")
    assert unlocks.track_lock_note(p, "ma") is None


def test_track_affinity_does_not_lock_general_track():
    p = _player(grade=unlocks.required_grade("hedge"))
    p.track = "General"
    assert unlocks.unlocked(p, "hedge")
    assert unlocks.track_lock_note(p, "hedge") is None


def test_track_affinity_ignores_veteran_headstart():
    p = _player(grade=unlocks.TRACK_LOCK_GRADE - 1)
    p.track = "Risk"
    p.flags["veteran"] = True
    # "options" est affilié à Quant : le headstart vétéran ne contourne pas le verrou de voie
    assert not unlocks.unlocked(p, "options")


def test_intern_has_only_the_bare_basics():
    """Le stagiaire (grade 0) n'a QUE les basiques : rien d'analytique, pas de
    graphes, pas de watchlist/alertes, pas de VaR/quant/ALM ni de boîte à
    outils. Ces outils n'ont aucun sens tant qu'on ne peut ni investir ni
    détenir de position — ils se découvrent à mesure qu'ils deviennent
    utilisables (progression plus digeste)."""
    p = _player(grade=0)
    for feature in ("analyst", "charts", "risk", "quant", "alm", "tools",
                    "trade", "deals", "track", "ipo", "calendar"):
        assert not unlocks.unlocked(p, feature), feature
    for cmd in ("WATCHLIST", "ALERT", "COMPARE", "RESEARCH", "BUY"):
        assert not unlocks.cmd_unlocked(p, cmd), cmd


def test_analyst_and_charts_unlock_at_grade_one():
    """Grade 1 (Junior Analyst) : on devient un analyste qui investit — les
    outils d'analyse, les graphes et le trading arrivent ensemble."""
    p = _player(grade=1)
    for feature in ("analyst", "charts", "trade", "deals", "track"):
        assert unlocks.unlocked(p, feature), feature
    # la mesure de risque et la boîte à outils quant restent pour le grade 2
    for feature in ("risk", "quant", "tools"):
        assert not unlocks.unlocked(p, feature), feature


def test_risk_and_quant_tools_unlock_at_grade_two():
    p = _player(grade=2)
    for feature in ("risk", "quant", "tools", "calendar", "ipo"):
        assert unlocks.unlocked(p, feature), feature


def test_every_grade_unlocks_something():
    """CHAQUE promotion (grades 1 à 11) apporte au moins une fonctionnalité —
    l'équipe au grade Managing Director, la fondation de sa firme à Partner."""
    from core import config
    grades_with_unlock = set(unlocks.UNLOCKS.values())
    for g in range(1, len(config.GRADES)):
        assert g in grades_with_unlock, f"le grade {g} ne débloque rien"


def test_founding_declared_at_top_grade_and_no_headstart():
    """"founding" (fonder sa firme) est déclaré au grade max, aligné sur la
    mécanique réelle (core/founding.can_found exige le grade max) — et le
    raccourci vétéran ne le descend PAS (sinon l'UI montrerait débloqué ce
    que le module refuse)."""
    from core import config
    top = len(config.GRADES) - 1
    assert unlocks.required_grade("founding") == top
    p = _player(grade=top - 1)
    p.flags["veteran"] = True
    assert not unlocks.unlocked(p, "founding")
    p.grade_index = top
    assert unlocks.unlocked(p, "founding")


def test_veteran_still_gets_a_bare_intern():
    """Le raccourci vétéran accélère la suite mais ne saute JAMAIS le stade
    Intern : au grade 0, aucune fonctionnalité gated n'est ouverte, même pour
    un profil vétéran."""
    p = _player(grade=0)
    p.flags["veteran"] = True
    for feature in unlocks.UNLOCKS:
        assert not unlocks.unlocked(p, feature), feature
    # mais le vétéran accélère bien dès le grade 1 (headstart appliqué au-dessus)
    p.grade_index = 1
    assert unlocks.unlocked(p, "risk")     # risk (grade 2) ramené à 1 pour un vétéran
