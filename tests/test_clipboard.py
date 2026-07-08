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


# ------------------------------------------------- Ctrl+V dans les champs de saisie
def _paste_event():
    return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v,
                              mod=pygame.KMOD_CTRL, unicode="\x16")


def _app():
    import main
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.grade_index = 9
    p.cash = 5_000_000.0
    p.flags["intro_guide_done"] = True
    p.flags["desktop_seeded"] = True
    from core import desktop_onboarding, desktop_tutorial
    desktop_onboarding.mark_seen()
    desktop_tutorial.skip()
    return a


def test_terminal_command_line_pastes(monkeypatch):
    monkeypatch.setattr(clipboard, "paste", lambda: "BUY MVC 10")
    a = _app()
    a.scenes.go("terminal")
    term = a.scenes.current
    term.draw(a.screen)
    term.handle_event(_paste_event())
    assert term.cmd == "BUY MVC 10"


def test_terminal_paste_flattens_newlines(monkeypatch):
    monkeypatch.setattr(clipboard, "paste", lambda: "BUY\nMVC\r\n10")
    a = _app()
    a.scenes.go("terminal")
    term = a.scenes.current
    term.draw(a.screen)
    term.handle_event(_paste_event())
    assert "\n" not in term.cmd and "\r" not in term.cmd


def test_sheet_formula_bar_pastes_while_editing(monkeypatch):
    monkeypatch.setattr(clipboard, "paste", lambda: 'PRICE("MVC")')
    a = _app()
    a.scenes.go("desktop")
    desk = a.scenes.current
    w = desk._open_sheet_app()
    sheet = w.app_obj
    rect = pygame.Rect(0, 0, 900, 600)
    sheet.editing = True
    sheet.edit_buf = "="
    sheet.handle_event(_paste_event(), rect)
    assert sheet.edit_buf == '=PRICE("MVC")'


def test_research_search_pastes(monkeypatch):
    monkeypatch.setattr(clipboard, "paste", lambda: "MVC")
    a = _app()
    a.scenes.go("desktop")
    desk = a.scenes.current
    w = desk._launch("research")
    rect = pygame.Rect(0, 0, 800, 500)
    w.app_obj.handle_event(_paste_event(), rect)
    assert w.app_obj.search == "MVC"


def test_book_key_box_pastes(monkeypatch):
    monkeypatch.setattr(clipboard, "paste", lambda: "MVC")
    a = _app()
    a.scenes.go("desktop")
    desk = a.scenes.current
    w = desk._launch("book")
    w.app_obj.text_focus = "key"
    rect = pygame.Rect(0, 0, 980, 600)
    w.app_obj.handle_event(_paste_event(), rect)
    assert w.app_obj.trade_key == "MVC"


def test_inbox_search_pastes(monkeypatch):
    monkeypatch.setattr(clipboard, "paste", lambda: "manager")
    a = _app()
    a.scenes.go("desktop")
    desk = a.scenes.current
    w = desk._launch("inbox")
    rect = pygame.Rect(0, 0, 800, 500)
    w.app_obj.handle_event(_paste_event(), rect)
    assert w.app_obj.search == "manager"


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
