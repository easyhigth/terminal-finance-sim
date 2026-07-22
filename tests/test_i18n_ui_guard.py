"""
test_i18n_ui_guard.py — Garde anti-régression de la localisation UI.

Verrouille le travail de l'audit i18n (scenes/ apps/ ui/) : le mode anglais ne
doit plus afficher de français dans le CHROME de l'interface. On ne peut pas
exiger ZÉRO littéral accentué, car certaines chaînes sont légitimement en
français (clés de logique, côtés FR de tuples bilingues `(fr, en)`, libellés de
données) — cf. scripts/i18n_ui_audit.py qui sur-signale volontairement.

Stratégie : un BASELINE figé (tests/i18n_ui_baseline.json) liste, par fichier,
les littéraux FR non enveloppés ACCEPTÉS aujourd'hui. Le test échoue dès qu'un
NOUVEAU littéral apparaît → toute nouvelle chaîne UI doit être enveloppée dans
`_L(fr, en)`/`t(...)`, ou (si c'est une vraie clé de données) ajoutée
explicitement au baseline via :

    python scripts/i18n_ui_audit.py            # inspecter
    python -m tests.test_i18n_ui_guard --update-baseline   # régénérer

Le baseline est indépendant des numéros de ligne (indexé par contenu), donc il
ne casse pas quand le code se déplace.
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import i18n_ui_audit as audit_mod  # noqa: E402

_BASELINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "i18n_ui_baseline.json")


def _current():
    """{chemin: set(chaînes)} des littéraux FR non localisés actuels."""
    data = audit_mod.audit(base_dir=_ROOT)
    return {path: {s for _ln, s in hits} for path, hits in data.items()}


def _load_baseline():
    with open(_BASELINE_PATH, encoding="utf-8") as f:
        return {k: set(v) for k, v in json.load(f).items()}


def test_no_new_untranslated_ui_strings():
    current = _current()
    baseline = _load_baseline()
    new = {}
    for path, strings in current.items():
        extra = strings - baseline.get(path, set())
        if extra:
            new[path] = sorted(extra)
    assert not new, (
        "Nouveaux littéraux FR non localisés détectés dans le chrome UI.\n"
        "Enveloppez-les dans _L(fr, en)/t(...), ou (si c'est une clé de données) "
        "régénérez le baseline : python -m tests.test_i18n_ui_guard --update-baseline\n\n"
        + "\n".join(f"  {p}:\n    " + "\n    ".join(ss) for p, ss in sorted(new.items()))
    )


def _update_baseline():
    data = audit_mod.audit(base_dir=_ROOT)
    baseline = {path: sorted({s for _ln, s in hits}) for path, hits in data.items()}
    with open(_BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=1, sort_keys=True)
    n = sum(len(v) for v in baseline.values())
    print(f"baseline régénéré : {len(baseline)} fichiers, {n} chaînes")


if __name__ == "__main__":
    if "--update-baseline" in sys.argv:
        _update_baseline()
    else:
        test_no_new_untranslated_ui_strings()
        print("OK — aucun nouveau littéral FR non localisé.")
