"""
i18n_ui_audit.py — Audit de localisation de l'INTERFACE (chrome UI).

Complète scripts/i18n_report.py (qui couvre les banques de CONTENU
data/*_en.py) : celui-ci scanne scenes/ apps/ ui/ par AST et signale les
littéraux de chaîne CONTENANT DES ACCENTS français qui ne sont PAS enveloppés
dans un appel de localisation (_L(fr, en) / t(...)). Ce sont les candidats à
traduire pour que le mode anglais n'affiche plus de français.

    python scripts/i18n_ui_audit.py            # rapport par fichier
    python scripts/i18n_ui_audit.py | wc -l    # ampleur

Faux positifs possibles : chaînes qui servent AUSSI de clé de logique (ex.
libellés de classe d'actif) — à traiter en séparant clé et libellé, pas en
enveloppant aveuglément. Le compte n'est donc qu'une borne HAUTE.
"""
import ast
import os
import sys

ROOTS = ["scenes", "apps", "ui"]
LOC_FUNCS = {"_L", "_l", "t", "tr", "L", "_"}
ACCENTS = set("àâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ")
# fonctions dont un argument str est AFFICHÉ à l'écran (chrome UI)
DISPLAY_HINTS = ("draw_text", "notify", "Button", "draw_badge", "tooltip",
                 "draw_tooltip", "title", "draw_button", "label", "toast",
                 "draw_panel", "set_caption", "header")


def is_french(s):
    return any(c in ACCENTS for c in s)


def collect_localized_ids(tree):
    """id() de tous les Constant str situés dans un appel _L(...)/t(...)."""
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name in LOC_FUNCS:
                for arg in ast.walk(node):
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        ids.add(id(arg))
    return ids


def docstring_ids(tree):
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                ids.add(id(body[0].value))
    return ids


def scan(path):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    localized = collect_localized_ids(tree)
    docs = docstring_ids(tree)
    hits = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if id(node) in localized or id(node) in docs:
            continue
        s = node.value
        if not is_french(s) or len(s.strip()) < 4:
            continue
        hits.append((node.lineno, s[:70]))
    return hits


def audit(roots=ROOTS, base_dir="."):
    """Scanne les racines et retourne {chemin_relatif: [(lineno, extrait), ...]}.
    Réutilisé par le test anti-régression tests/test_i18n_ui_guard.py."""
    result = {}
    for root in roots:
        root_path = os.path.join(base_dir, root)
        for dirpath, _dirs, files in os.walk(root_path):
            if "__pycache__" in dirpath:
                continue
            for fn in sorted(files):
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(dirpath, fn)
                hits = scan(p)
                if hits:
                    rel = os.path.relpath(p, base_dir)
                    result[rel] = hits
    return result


def main():
    total = 0
    for p, hits in audit().items():
        print(f"\n### {p}  ({len(hits)})")
        for ln, s in hits:
            print(f"  {ln}: {s}")
        total += len(hits)
    print(f"\n=== TOTAL littéraux FR non localisés : {total} ===", file=sys.stderr)


if __name__ == "__main__":
    main()
