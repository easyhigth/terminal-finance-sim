"""
i18n_report.py — Rapport de couverture de la couche anglaise (data/*_en.py).

Affiche, banque par banque, les clés FR sans traduction EN et les clés EN
orphelines (périmées). Le verrou CI correspondant est
tests/test_i18n_data_coverage.py (couverture actuellement complète — ce
script sert à diagnostiquer rapidement QUOI traduire quand ce test casse
après un ajout de contenu FR).

    python scripts/i18n_report.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.dilemmas as dilemmas_mod  # noqa: E402
import data.dilemmas_en as dilemmas_en_mod  # noqa: E402
import data.glossary_data as glossary_mod  # noqa: E402
import data.glossary_en as glossary_en_mod  # noqa: E402
import data.lessons as lessons_mod  # noqa: E402
import data.lessons_en as lessons_en_mod  # noqa: E402
import data.question_bank as qbank_mod  # noqa: E402
import data.question_bank_en as qbank_en_mod  # noqa: E402


def pairs():
    return {
        "glossaire": (set(glossary_mod.GLOSSARY), set(glossary_en_mod.GLOSSARY_EN)),
        "leçons": ({item["id"] for item in lessons_mod.LESSONS},
                   set(lessons_en_mod.LESSONS_EN)),
        "questions": ({item["id"] for item in qbank_mod.QUESTIONS},
                      set(qbank_en_mod.QUESTIONS_EN)),
        "dilemmes": ({d["id"] for d in dilemmas_mod.DILEMMAS},
                     set(dilemmas_en_mod.DILEMMAS_EN)),
    }


def run():
    problems = 0
    for name, (fr, en) in pairs().items():
        missing = sorted(fr - en)
        stale = sorted(en - fr)
        cov = len(fr & en) / max(1, len(fr))
        print(f"== {name} : {cov:.0%} ({len(fr & en)}/{len(fr)})")
        if missing:
            print(f"   FR sans mirror EN ({len(missing)}) : {', '.join(missing[:20])}"
                  + (" ..." if len(missing) > 20 else ""))
        if stale:
            print(f"   EN orphelines ({len(stale)}) : {', '.join(stale[:20])}")
        if not missing and not stale:
            print("   complet")
        problems += len(missing) + len(stale)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(run())
