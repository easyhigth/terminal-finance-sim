"""Tests de l'UI de partage du score de Défi du jour sur l'écran de fin de
partie (scenes/scene_gameover.py — boutons EXPORTER/IMPORTER, cf.
core/challenge_share.py)."""
import datetime
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from core import challenge_share as cs
from core import difficulty
from core import hall_of_fame as hof

pygame.font.init()


@pytest.fixture(autouse=True)
def _isolated_hof_files(tmp_path, monkeypatch):
    monkeypatch.setattr(hof, "_PATH", str(tmp_path / "hall_of_fame.json"))
    monkeypatch.setattr(hof, "_DAILY_PATH", str(tmp_path / "hall_of_fame_daily.json"))
    monkeypatch.setattr(hof, "_FRIENDS_PATH", str(tmp_path / "hall_of_fame_friends.json"))


def _click(x, y, button=1):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=(x, y))


def _daily_app():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.cash = -10.0            # faillite
    p.game_over = True
    p.game_over_reason = "Test"
    difficulty.mark_daily(p, datetime.date(2026, 7, 8))
    return a


def test_export_button_generates_code_and_copies(app_placeholder=None):
    a = _daily_app()
    a.scenes.go("gameover")
    scene = a.scenes.current
    scene.draw(a.screen)
    assert scene._export_rect is not None
    scene.handle_event(_click(scene._export_rect.centerx, scene._export_rect.centery))
    assert scene._export_code is not None
    assert scene._export_code.startswith("FSC1:")
    decoded = cs.decode_entry(scene._export_code)
    assert decoded["daily_date"] == "2026-07-08"


def test_import_button_opens_prompt_and_imports_code(monkeypatch):
    # génère un code "d'ami" via une AUTRE partie
    a1 = _daily_app()
    a1.gs.player.name = "Ada"
    entry = hof.make_entry(a1.gs.player, 88.0)
    code = cs.encode_entry(entry)

    a2 = _daily_app()
    a2.scenes.go("gameover")
    scene = a2.scenes.current
    scene.draw(a2.screen)
    assert scene._import_rect is not None
    scene.handle_event(_click(scene._import_rect.centerx, scene._import_rect.centery))
    assert scene.code_prompt is True

    for ch in code:
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord(ch.lower()) if ch.isalpha() else 0,
                                              unicode=ch, mod=0))
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="", mod=0))
    assert scene.code_prompt is False
    assert any(r["name"] == "Ada" for r in scene.hof_daily_top)
    assert any(r.get("friend") for r in scene.hof_daily_top)


def test_import_prompt_pastes_code_via_ctrl_v(monkeypatch):
    a1 = _daily_app()
    a1.gs.player.name = "Ada"
    code = cs.encode_entry(hof.make_entry(a1.gs.player, 88.0))

    from core import clipboard
    monkeypatch.setattr(clipboard, "paste", lambda: code)

    a2 = _daily_app()
    a2.scenes.go("gameover")
    scene = a2.scenes.current
    scene.draw(a2.screen)
    scene.handle_event(_click(scene._import_rect.centerx, scene._import_rect.centery))
    assert scene.code_prompt is True

    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v,
                                           unicode="v", mod=pygame.KMOD_CTRL))
    assert scene.code_buf == code
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="", mod=0))
    assert scene.code_prompt is False
    assert any(r["name"] == "Ada" for r in scene.hof_daily_top)


def test_import_invalid_code_shows_error_and_does_not_crash():
    a = _daily_app()
    a.scenes.go("gameover")
    scene = a.scenes.current
    scene.draw(a.screen)
    scene.code_prompt = True
    scene.code_buf = "n'importe quoi"
    scene._confirm_code_prompt()
    assert scene.code_prompt is False   # se referme même en cas d'échec
    scene.draw(a.screen)   # ne doit pas lever


def test_escape_cancels_code_prompt_without_going_to_menu():
    a = _daily_app()
    a.scenes.go("gameover")
    scene = a.scenes.current
    scene.draw(a.screen)
    scene.code_prompt = True
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="", mod=0))
    assert scene.code_prompt is False
    assert a.scenes.current_name == "gameover"   # pas de sortie vers le menu


def test_import_notifies_when_player_beats_friend():
    a1 = _daily_app()
    a1.gs.player.name = "Ada"
    entry = hof.make_entry(a1.gs.player, 1.0)   # score d'ami très faible
    code = cs.encode_entry(entry)

    a2 = _daily_app()
    a2.scenes.go("gameover")
    scene = a2.scenes.current
    scene.draw(a2.screen)   # calcule scene.score
    scene.code_buf = code
    scene._confirm_code_prompt()
    assert any("Vous le devancez" in t["text"] for t in a2.notes.toasts)


def test_import_notifies_when_friend_beats_player(monkeypatch):
    a1 = _daily_app()
    a1.gs.player.name = "Ada"
    entry = hof.make_entry(a1.gs.player, 1_000_000.0)   # score d'ami très élevé
    code = cs.encode_entry(entry)

    a2 = _daily_app()
    a2.scenes.go("gameover")
    scene = a2.scenes.current
    scene.draw(a2.screen)
    scene.code_buf = code
    scene._confirm_code_prompt()
    assert any("Ada vous devance" in t["text"] for t in a2.notes.toasts)


def test_import_no_comparison_for_non_daily_run():
    """Un run classique n'affiche pas le classement du défi (bouton importer
    absent) : si import_friend_code est appelé quand même (ex. programmatique-
    ment), aucune comparaison ne doit être tentée (self._daily_date est None)."""
    a1 = _daily_app()
    a1.gs.player.name = "Ada"
    code = cs.encode_entry(hof.make_entry(a1.gs.player, 50.0))

    a2 = main.App()
    a2.ensure_market()
    a2.gs.player.cash = -10.0
    a2.gs.player.game_over = True
    a2.gs.player.game_over_reason = "Test"
    a2.scenes.go("gameover")
    scene = a2.scenes.current
    scene.draw(a2.screen)
    assert scene._daily_date is None
    scene.code_buf = code
    scene._confirm_code_prompt()
    assert not any("devance" in t["text"] for t in a2.notes.toasts)


def test_non_daily_run_shows_no_export_import_buttons():
    a = main.App()
    a.ensure_market()
    p = a.gs.player
    p.cash = -10.0
    p.game_over = True
    p.game_over_reason = "Test"
    a.scenes.go("gameover")
    scene = a.scenes.current
    scene.draw(a.screen)
    assert scene._export_rect is None
    assert scene._import_rect is None
