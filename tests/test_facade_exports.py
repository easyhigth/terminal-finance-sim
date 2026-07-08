"""Garde-fou permanent contre la classe de bug corrigée dans
scenes/scene_terminal_windows.py / ui/widgets.py (PR « Corrige le crash au
clic sur un indice du terminal ») : `ui/widgets.py` réexporte les helpers de
graphes de `ui/chart_widgets.py` (`from ui.chart_widgets import (...)`), mais
un symbole (`_hover_sync`) avait été oublié de cette liste — invisible à la
compilation, il ne se manifestait qu'à l'exécution (AttributeError) dès
qu'un graphe affichait un historique réel, fermant toute la partie (aucun
`try/except` autour de la boucle principale à l'époque, cf. main.py::App._safe_call
depuis lors).

Ce test rejoue, en PERMANENT, l'audit statique (analyse AST — pas de simple
recherche texte, pour ignorer commentaires/docstrings) qui avait révélé le
symbole manquant : pour chaque façade connue (`ui.widgets` vers
`ui.chart_widgets`, `core.portfolio` vers `core.portfolio_margin`/
`core.portfolio_views`), toute expression `<alias>.<nom>` réellement présente
dans le code du projet doit résoudre sur le VRAI module importé.
"""
import ast
import os

import pytest

pytest.importorskip("pygame")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SKIP_DIRS = {".git", "__pycache__", "dist", "build", ".venv", "node_modules"}

# alias de code -> module réellement visé (cf. grep des imports dans le
# projet : `from ui import widgets`, `from core import portfolio as pf/PF/pf_mod`).
_FACADES = {
    "widgets": "ui.widgets",
    "pf": "core.portfolio",
    "pf_mod": "core.portfolio",
    "PF": "core.portfolio",
}


def _iter_py_files():
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fn in files:
            if fn.endswith(".py"):
                yield os.path.join(root, fn)


def _collect_attribute_usages():
    """{alias: {nom_attribut: [chemins de fichiers]}} — uniquement de VRAIES
    expressions `alias.nom` (nœuds AST Attribute sur un Name), donc aucun
    faux positif venant d'un commentaire ou d'une docstring mentionnant par
    ex. « ui/widgets.py » ou « core.portfolio.xxx » en exemple."""
    usages = {alias: {} for alias in _FACADES}
    for path in _iter_py_files():
        try:
            src = open(path, encoding="utf-8").read()
            tree = ast.parse(src, filename=path)
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id in _FACADES):
                usages[node.value.id].setdefault(node.attr, []).append(path)
    return usages


@pytest.mark.parametrize("alias,module_name", sorted(_FACADES.items()))
def test_facade_attribute_usages_resolve_on_real_module(alias, module_name):
    import importlib
    module = importlib.import_module(module_name)
    usages = _collect_attribute_usages()[alias]
    missing = {name: files for name, files in usages.items() if not hasattr(module, name)}
    assert not missing, (
        f"{len(missing)} symbole(s) '{alias}.<x>' utilisé(s) dans le code mais "
        f"absent(s) de {module_name} (façade de réexport incomplète — cf. le "
        f"crash widgets._hover_sync) : "
        + ", ".join(f"{alias}.{n} <- {sorted(set(fs))}" for n, fs in sorted(missing.items()))
    )
