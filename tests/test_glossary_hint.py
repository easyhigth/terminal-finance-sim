"""
tests/test_glossary_hint.py — Lexique contextuel en un clic (ui/glossary_hint.py).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

pytest.importorskip("pygame")
pygame.init()
pygame.font.init()

from ui.glossary_hint import GlossaryHint


def _click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def test_label_registers_clickable_rect_for_known_term():
    surf = pygame.Surface((400, 200))
    g = GlossaryHint()
    g.begin_frame()
    g.label(surf, (10, 10), "Bêta", term="Beta")
    assert len(g._rects) == 1
    assert g._rects[0][1] == "Beta"


def test_label_does_not_register_unknown_term():
    surf = pygame.Surface((400, 200))
    g = GlossaryHint()
    g.begin_frame()
    g.label(surf, (10, 10), "Un libellé quelconque")
    assert g._rects == []


def test_label_defaults_term_to_text():
    surf = pygame.Surface((400, 200))
    g = GlossaryHint()
    g.begin_frame()
    g.label(surf, (10, 10), "VaR")   # "VaR" est une clé du glossaire
    assert g._rects and g._rects[0][1] == "VaR"


def test_click_on_registered_term_opens_it():
    surf = pygame.Surface((400, 200))
    g = GlossaryHint()
    g.begin_frame()
    rect = g.label(surf, (10, 10), "Bêta", term="Beta")
    consumed = g.handle_event(_click(rect.center))
    assert consumed is True
    assert g.active_term == "Beta"


def test_click_elsewhere_closes_active_popup():
    surf = pygame.Surface((400, 200))
    g = GlossaryHint()
    g.begin_frame()
    rect = g.label(surf, (10, 10), "Bêta", term="Beta")
    g.handle_event(_click(rect.center))
    assert g.active_term == "Beta"
    consumed = g.handle_event(_click((390, 190)))
    assert consumed is True
    assert g.active_term is None


def test_click_on_empty_space_without_active_term_is_not_consumed():
    g = GlossaryHint()
    g.begin_frame()
    consumed = g.handle_event(_click((5, 5)))
    assert consumed is False


def test_escape_closes_active_popup():
    surf = pygame.Surface((400, 200))
    g = GlossaryHint()
    g.begin_frame()
    rect = g.label(surf, (10, 10), "Bêta", term="Beta")
    g.handle_event(_click(rect.center))
    esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    consumed = g.handle_event(esc)
    assert consumed is True
    assert g.active_term is None


def test_escape_without_active_term_is_not_consumed():
    g = GlossaryHint()
    esc = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    assert g.handle_event(esc) is False


def test_draw_popup_noop_when_no_active_term():
    surf = pygame.Surface((400, 200))
    g = GlossaryHint()
    g.draw_popup(surf)   # ne doit pas lever


def test_draw_popup_draws_definition_for_known_term():
    surf = pygame.Surface((400, 200))
    g = GlossaryHint()
    g.active_term = "Beta"
    g.active_pos = (100, 100)
    g.draw_popup(surf)   # ne doit pas lever


def test_begin_frame_clears_stale_rects():
    surf = pygame.Surface((400, 200))
    g = GlossaryHint()
    g.begin_frame()
    g.label(surf, (10, 10), "Bêta", term="Beta")
    assert g._rects
    g.begin_frame()
    assert g._rects == []
