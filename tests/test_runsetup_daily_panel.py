"""Tests du panneau « Défi du jour » de l'écran de réglages de partie
(scenes/scene_runsetup.py) : classement du jour (runs locaux + amis importés,
core/hall_of_fame.combined_daily_ranking) visible AVANT de jouer, et import
d'un code d'ami directement depuis cet écran."""
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
from core.game_state import PlayerState

pygame.font.init()


@pytest.fixture(autouse=True)
def _isolated_hof_files(tmp_path, monkeypatch):
    monkeypatch.setattr(hof, "_PATH", str(tmp_path / "hall_of_fame.json"))
    monkeypatch.setattr(hof, "_DAILY_PATH", str(tmp_path / "hall_of_fame_daily.json"))
    monkeypatch.setattr(hof, "_FRIENDS_PATH", str(tmp_path / "hall_of_fame_friends.json"))


def _click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def _scene():
    a = main.App()
    a.scenes.go("runsetup", continent="Europe")
    return a, a.scenes.current


def _friend_code(name="Ada", score=77.0):
    p = PlayerState()
    p.name = name
    difficulty.mark_daily(p, datetime.date.today())
    return cs.encode_entry(hof.make_entry(p, score))


def test_daily_checkbox_shows_ranking_panel():
    a, scene = _scene()
    scene.draw(a.screen)
    assert scene._daily_panel_rect is None      # case décochée : pas de panneau
    scene.handle_event(_click(scene._daily_rect.center))
    assert scene.daily is True
    scene.draw(a.screen)
    assert scene._daily_panel_rect is not None
    assert scene._daily_import_rect is not None


def test_panel_lists_local_and_friend_scores():
    # un run local + un score d'ami importé pour AUJOURD'HUI
    p_local = PlayerState()
    p_local.name = "Moi"
    difficulty.mark_daily(p_local, datetime.date.today())
    hof.record(p_local, 50.0)
    hof.import_friend_code(_friend_code("Ada", 90.0))

    a, scene = _scene()
    scene.daily = True
    scene._refresh_daily_ranking()
    assert [r["name"] for r in scene._daily_ranking] == ["Ada", "Moi"]
    assert scene._daily_ranking[0].get("friend") is True
    scene.draw(a.screen)   # rendu du classement sans exception


def test_import_button_opens_prompt_and_import_refreshes_ranking(monkeypatch):
    code = _friend_code("Ada", 88.0)
    from core import clipboard
    monkeypatch.setattr(clipboard, "paste", lambda: code)

    a, scene = _scene()
    scene.handle_event(_click(scene._daily_rect.center)) if scene._daily_rect else None
    scene.daily = True
    scene.draw(a.screen)
    scene.handle_event(_click(scene._daily_import_rect.center))
    assert scene.code_prompt is True
    scene.draw(a.screen)   # boîte modale sans exception

    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v,
                                           unicode="v", mod=pygame.KMOD_CTRL))
    assert scene.code_buf == code
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="", mod=0))
    assert scene.code_prompt is False
    assert any(r["name"] == "Ada" for r in scene._daily_ranking)


def test_click_inside_panel_does_not_fall_through_to_archetypes():
    a, scene = _scene()
    scene.daily = True
    scene.draw(a.screen)
    arch_before = scene.arch_idx
    # clic dans le panneau (hors bouton importer) : absorbé
    panel = scene._daily_panel_rect
    scene.handle_event(_click((panel.centerx, panel.y + 40)))
    assert scene.arch_idx == arch_before
    assert scene.code_prompt is False


def test_escape_cancels_prompt_without_leaving_screen():
    a, scene = _scene()
    scene.daily = True
    scene.code_prompt = True
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="", mod=0))
    assert scene.code_prompt is False
    assert a.scenes.current_name == "runsetup"


def test_empty_ranking_draws_placeholder():
    a, scene = _scene()
    scene.daily = True
    scene._refresh_daily_ranking()
    assert scene._daily_ranking == []
    scene.draw(a.screen)   # placeholder sans exception
