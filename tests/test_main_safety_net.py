"""Tests du filet de sécurité anti-crash (main.py::App._safe_call).

Une exception imprévue dans handle_event/update/draw (ex. la régression du
popup d'indice — widgets._hover_sync manquant) ne doit plus fermer toute la
partie : elle est journalisée (core/crashlog.py) et notifiée au joueur, mais
la boucle principale continue.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main
from core import crashlog

pygame.font.init()


@pytest.fixture()
def app(tmp_path, monkeypatch):
    # journal de plantage isolé dans un dossier temporaire : ne pollue pas
    # (et ne dépend pas de) le vrai dossier de sauvegarde de l'utilisateur.
    monkeypatch.setattr(crashlog, "_PATH", str(tmp_path / "crash.log"))
    a = main.App()
    a.ensure_market()
    return a


def test_safe_call_swallows_exception_and_keeps_running(app):
    def boom():
        raise RuntimeError("boom")

    app._safe_call(boom, "test")
    assert app.running is True   # ne ferme pas la partie


def test_safe_call_records_crash_to_log(app):
    def boom():
        raise ValueError("historique insuffisant simulé")

    app._safe_call(boom, "draw")
    assert os.path.exists(crashlog.path())
    with open(crashlog.path(), encoding="utf-8") as f:
        content = f.read()
    assert "ValueError" in content
    assert "historique insuffisant simulé" in content
    assert "[draw]" in content


def test_safe_call_notifies_once_then_throttles(app):
    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        raise RuntimeError("répété")

    before = len(app.notes.toasts)
    app._safe_call(boom, "update")
    app._safe_call(boom, "update")   # immédiatement après : pas de 2e toast
    assert calls["n"] == 2           # la fonction est bien appelée à chaque fois...
    # ... mais la notification est limitée (anti-spam) : un seul toast récent
    after = len(app.notes.toasts)
    assert after - before <= 1


def test_safe_call_does_not_propagate_when_notify_itself_fails(app, monkeypatch):
    """Même si notify() lève (ex. état de partie incohérent), _safe_call ne
    doit jamais elle-même faire remonter d'exception — c'est tout le sens du
    filet de sécurité."""
    def broken_notify(*a, **k):
        raise RuntimeError("notify cassé")
    monkeypatch.setattr(app, "notify", broken_notify)

    def boom():
        raise RuntimeError("original")

    app._safe_call(boom, "draw")   # ne doit pas lever
    assert app.running is True


def test_run_loop_survives_a_crashing_draw(app, monkeypatch):
    """Bout en bout : une scène dont draw() lève ne doit pas arrêter run(),
    seulement être absorbée frame après frame."""
    calls = {"n": 0}
    orig_draw = app.pages.draw

    def crashing_draw(surf):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise AttributeError("simulate widgets._hover_sync-like bug")
        app.running = False   # sort proprement de la boucle après 3 frames
        return orig_draw(surf)

    monkeypatch.setattr(app.pages, "draw", crashing_draw)
    monkeypatch.setattr(pygame.event, "get", lambda: [])
    # run() appelle pygame.quit()/sys.exit(0) en sortie normale de boucle —
    # attendu (ce n'est pas ce que ce test vérifie), mais un VRAI pygame.quit()
    # invaliderait les Font mis en cache (ui/fonts.py) pour tous les tests
    # suivants de la même session pytest (cf. test_scene_smoke.py) : neutralisé
    # ici, seule la survie aux 2 crashs nous intéresse.
    monkeypatch.setattr(pygame, "quit", lambda: None)
    with pytest.raises(SystemExit):
        app.run()
    assert calls["n"] == 3   # les 2 échecs n'ont pas empêché la 3e frame
