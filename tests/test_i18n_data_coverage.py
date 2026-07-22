"""
tests/test_i18n_data_coverage.py — Audit de couverture EN des données de
contenu (verrou de non-régression, cf. CLAUDE.md « i18n ») : le CHROME est
bilingue FR/EN partout ; le contenu finance PROFOND reste FR par défaut,
sauf pour les jeux de données qui affichent explicitement une couche EN
dédiée (glossaire, leçons, banque de questions, dilemmes, scénarios,
certifications, raccourcis). Pour CEUX-LÀ, une entrée manquante ou
désynchronisée dans le pendant `*_en.py` ferait fuiter du texte FR (ou une
absence de contenu) en mode anglais sans qu'aucun test ne le voie venir —
ce fichier verrouille la PARITÉ STRUCTURELLE (mêmes identifiants des deux
côtés), pas la qualité de la traduction elle-même.

Fichiers de contenu narratif profond DÉLIBÉRÉMENT FR-only (déjà documenté
dans leur propre docstring, cf. `data/story_arcs.py`) ou purement
structurels/référentiels (tickers, coordonnées géographiques — rien à
traduire) : `data/companies.py`, `data/ma_targets.py`,
`data/worldmap_geo.py`, `data/story_arcs.py`. `data/tutorials.py` est un
gap CONNU (pas de couche EN, scenes/scene_tutorials.py ne bascule pas sur
la langue) — répertorié explicitement ci-dessous plutôt que silencieusement
ignoré, en attendant une traduction dédiée (hors scope de cet audit
structurel).
"""
import os

import core.certifications as certifications_mod
import core.dilemmas as dilemmas_mod
import core.scenarios as scenarios_mod
import data.certifications_en as certifications_en_mod
import data.dilemmas_en as dilemmas_en_mod
import data.glossary_data as glossary_mod
import data.glossary_en as glossary_en_mod
import data.lessons as lessons_mod
import data.lessons_en as lessons_en_mod
import data.question_bank as qbank_mod
import data.question_bank_en as qbank_en_mod
import data.scenarios_en as scenarios_en_mod
import data.shortcuts_data as shortcuts_mod
import data.shortcuts_data_en as shortcuts_en_mod
import data.story_arcs as story_arcs_mod
import data.story_arcs_en as story_arcs_en_mod

# Gaps connus et acceptés : contenu narratif profond FR-only pas encore traduit
# (data/tutorials.py — scene_tutorials.py ignore la langue courante).
KNOWN_FR_ONLY = {"data/tutorials.py"}


def test_glossary_en_has_exactly_the_same_terms_as_french():
    fr_terms = set(glossary_mod.GLOSSARY)
    en_terms = set(glossary_en_mod.GLOSSARY_EN)
    missing = fr_terms - en_terms
    extra = en_terms - fr_terms
    assert not missing, f"Termes FR sans traduction EN : {sorted(missing)}"
    assert not extra, f"Termes EN orphelins (plus dans la version FR) : {sorted(extra)}"


def test_lessons_en_covers_every_lesson_id():
    fr_ids = {lesson["id"] for lesson in lessons_mod.LESSONS}
    en_ids = set(lessons_en_mod.LESSONS_EN)
    assert fr_ids == en_ids


def test_question_bank_en_covers_every_question_id_in_the_same_order():
    fr_ids = [q["id"] for q in qbank_mod.QUESTIONS]
    en_ids = list(qbank_en_mod.QUESTIONS_EN)
    assert set(fr_ids) == set(en_ids)
    assert len(fr_ids) == len(set(fr_ids)), "Identifiants de questions FR dupliqués"


def test_dilemmas_en_covers_every_dilemma_id():
    fr_ids = {d["id"] for d in dilemmas_mod.DILEMMAS}
    en_ids = set(dilemmas_en_mod.DILEMMAS_EN)
    assert fr_ids == en_ids


def test_dilemma_en_options_align_by_index_with_french():
    """La traduction EN d'un dilemme doit proposer le MÊME NOMBRE d'options,
    dans le même ordre (core.dilemmas.localized() les recompose par index) —
    sinon un choix cliqué en anglais applique l'effet d'un autre choix."""
    for d in dilemmas_mod.DILEMMAS:
        en = dilemmas_en_mod.DILEMMAS_EN[d["id"]]
        assert len(en["options"]) == len(d["options"]), (
            f"Dilemme {d['id']!r} : {len(d['options'])} options FR vs "
            f"{len(en['options'])} en EN")


def test_scenarios_en_covers_every_scenario_id():
    fr_ids = {s["id"] for s in scenarios_mod.SCENARIOS}
    en_ids = set(scenarios_en_mod.SCENARIOS_EN)
    assert fr_ids == en_ids


def test_certifications_en_covers_every_program_id():
    assert set(certifications_mod.PROGRAMS) == set(certifications_en_mod.PROGRAMS_EN)


def test_shortcuts_sections_match_in_count_and_shape():
    fr, en = shortcuts_mod.SECTIONS, shortcuts_en_mod.SECTIONS_EN
    assert len(fr) == len(en), "Nombre de sections différent entre FR et EN"
    for (fr_title, fr_items), (en_title, en_items) in zip(fr, en):
        assert len(fr_items) == len(en_items), (
            f"Section {fr_title!r}/{en_title!r} : {len(fr_items)} entrées FR "
            f"vs {len(en_items)} en EN")


def test_story_arcs_en_covers_every_arc_with_matching_stage_counts():
    """Chaque arc narratif doit avoir un pendant EN (data/story_arcs_en) avec
    le MÊME nombre de messages, dans le même ordre — sinon un stage livré en
    anglais retomberait en français (ou déborderait de l'index)."""
    en = story_arcs_en_mod.STAGES_EN
    fr_ids = {a["id"] for a in story_arcs_mod.ARCS}
    assert fr_ids == set(en), (
        f"IDs FR sans mirror EN : {sorted(fr_ids - set(en))} ; "
        f"EN orphelins : {sorted(set(en) - fr_ids)}")
    for arc in story_arcs_mod.ARCS:
        assert len(arc["stages"]) == len(en[arc["id"]]), (
            f"Arc {arc['id']!r} : {len(arc['stages'])} stages FR vs "
            f"{len(en[arc['id']])} en EN")


def test_known_fr_only_files_are_still_the_expected_set():
    """Verrou anti-oubli dans les deux sens : si un de ces fichiers gagne
    un jour une couche EN, ce test le signale (retirer l'entrée de
    KNOWN_FR_ONLY) plutôt que de laisser l'exception traîner sans raison ;
    s'il en gagne un nouveau sans traduction, l'ajouter ici en connaissance
    de cause plutôt que de le découvrir en jouant en anglais."""
    for path in KNOWN_FR_ONLY:
        assert os.path.exists(path), f"{path} n'existe plus — retirer de KNOWN_FR_ONLY"
    en_pendant = {
        "data/tutorials.py": "data/tutorials_en.py",
    }
    for fr_path, en_path in en_pendant.items():
        assert not os.path.exists(en_path), (
            f"{en_path} existe maintenant : retirer {fr_path} de KNOWN_FR_ONLY "
            "et ajouter un vrai test de parité pour ce fichier")
