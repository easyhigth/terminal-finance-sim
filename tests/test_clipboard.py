"""Tests de core/clipboard.py (lecture/écriture presse-papiers best-effort)
et de son branchement Ctrl+V dans les champs de saisie texte du jeu."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

from core import clipboard

pygame.font.init()


def test_is_paste_shortcut_detects_ctrl_v():
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v, mod=pygame.KMOD_CTRL, unicode="v")
    assert clipboard.is_paste_shortcut(ev)


def test_is_paste_shortcut_detects_cmd_v():
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v, mod=pygame.KMOD_META, unicode="v")
    assert clipboard.is_paste_shortcut(ev)


def test_is_paste_shortcut_rejects_plain_v():
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v, mod=0, unicode="v")
    assert not clipboard.is_paste_shortcut(ev)


def test_is_paste_shortcut_rejects_other_keys():
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c, mod=pygame.KMOD_CTRL, unicode="c")
    assert not clipboard.is_paste_shortcut(ev)


def test_paste_never_raises_without_clipboard_backend(monkeypatch):
    # simule l'indisponibilité totale de pygame.scrap (headless sans X11...)
    import pygame.scrap as scrap
    monkeypatch.setattr(scrap, "get_init", lambda: (_ for _ in ()).throw(RuntimeError("no display")))
    assert clipboard.paste() == ""


def test_copy_never_raises_without_clipboard_backend(monkeypatch):
    import pygame.scrap as scrap
    monkeypatch.setattr(scrap, "get_init", lambda: (_ for _ in ()).throw(RuntimeError("no display")))
    clipboard.copy("hello")  # ne doit pas lever


def test_copy_then_paste_roundtrip_when_backend_available():
    try:
        import pygame.scrap as scrap
        if not scrap.get_init():
            scrap.init()
    except Exception:
        pytest.skip("pygame.scrap indisponible dans cet environnement")
    clipboard.copy("FSC1:abc123")
    result = clipboard.paste()
    if result == "":
        # driver vidéo factice (SDL_VIDEODRIVER=dummy) : le backend s'initialise
        # mais n'a pas de presse-papiers système réel derrière — pas un bug de
        # clipboard.py, juste l'environnement headless/CI.
        pytest.skip("pas de presse-papiers système réel dans cet environnement headless")
    assert result == "FSC1:abc123"
