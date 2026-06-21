"""
Vérifie que data/shortcuts_data.py (et sa couche EN) reste synchronisé avec
les vrais raccourcis CTRL+lettre / CTRL+MAJ+lettre câblés dans
scenes/scene_terminal.py (RAIL_SHORTCUTS, MORE_SHORTCUTS) et le raccourci
global Ctrl+K (palette, core/scene_manager.py). Sans ce test, la doc peut
dériver silencieusement du code (cf. le TAB de la Boutique qui ne faisait
rien malgré sa documentation, avant correction).
"""
import re

from data.shortcuts_data import SECTIONS
from data.shortcuts_data_en import SECTIONS_EN
from scenes.scene_terminal import MORE_SHORTCUTS, RAIL_SHORTCUTS

CTRL_SECTION_TITLES = {
    "Raccourcis directs CTRL+lettre (terminal)",
    "Direct CTRL+letter shortcuts (terminal)",
}

# Ctrl+K (palette de navigation) est câblé globalement dans
# core/scene_manager.py, pas dans RAIL_SHORTCUTS — mais documenté avec les
# autres raccourcis Ctrl+lettre du rail.
PALETTE_LETTER = "K"


def _section_rows(sections, title):
    for sec_title, rows in sections:
        if sec_title == title:
            return rows
    raise AssertionError(f"Section {title!r} introuvable")


def _ctrl_rows(sections):
    for title in CTRL_SECTION_TITLES:
        try:
            return _section_rows(sections, title)
        except AssertionError:
            continue
    raise AssertionError("Section des raccourcis CTRL+lettre introuvable")


def _documented_rail_letters(rows):
    letters = set()
    for keys, _desc in rows:
        if keys.startswith("CTRL+") and "MAJ" not in keys and "SHIFT" not in keys:
            letters |= set(re.findall(r"\b([A-Z])\b", keys))
    return letters


def _documented_more_letters(rows):
    for keys, desc in rows:
        if "MAJ" in keys or "SHIFT" in keys:
            return set(re.findall(r"\+([A-Z])\b", desc))
    raise AssertionError("Ligne CTRL+MAJ/SHIFT+lettre introuvable")


def _real_rail_letters():
    return {chr(k).upper() for k in RAIL_SHORTCUTS} | {PALETTE_LETTER}


def _real_more_letters():
    return {chr(k).upper() for k in MORE_SHORTCUTS}


def test_rail_shortcuts_documented_fr():
    assert _documented_rail_letters(_ctrl_rows(SECTIONS)) == _real_rail_letters()


def test_rail_shortcuts_documented_en():
    assert _documented_rail_letters(_ctrl_rows(SECTIONS_EN)) == _real_rail_letters()


def test_more_shortcuts_documented_fr():
    assert _documented_more_letters(_ctrl_rows(SECTIONS)) == _real_more_letters()


def test_more_shortcuts_documented_en():
    assert _documented_more_letters(_ctrl_rows(SECTIONS_EN)) == _real_more_letters()
