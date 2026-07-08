"""Tests de l'import CSV du Tableur (apps/app_sheet.py) — symétrique de
l'export CSV déjà existant : bouton « CSV ↑ » ouvre une boîte de saisie
modale (chemin, Ctrl+V supporté), lit le fichier et le verse dans le
classeur via core/workbook.py::Workbook.import_csv."""
import csv
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

pytest.importorskip("pygame")

import pygame

import main

pygame.font.init()

RECT = pygame.Rect(0, 0, 1000, 640)


@pytest.fixture()
def app():
    a = main.App()
    a.ensure_market()
    a.scenes.go("desktop")
    return a


def _click(rect):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)


def _key(k, unicode="", mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode=unicode, mod=mod)


def _open_sheet(app):
    desk = app.scenes.current
    w = desk._open_sheet_app()
    return w.app_obj


def test_csv_import_button_opens_prompt(app):
    sheet = _open_sheet(app)
    sheet.draw(app.screen, RECT)
    assert sheet._csv_import_rect is not None
    sheet.handle_event(_click(sheet._csv_import_rect), RECT)
    assert sheet.csv_import_prompt is True


def test_csv_import_reads_file_into_active_sheet(app, tmp_path):
    path = tmp_path / "data.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["MVC", "142.5"])
        w.writerow(["NVDA", "98.1"])

    sheet = _open_sheet(app)
    sheet.draw(app.screen, RECT)
    sheet.csv_import_prompt = True
    sheet._csv_import_buf = str(path)
    sheet._confirm_csv_import()

    assert sheet.csv_import_prompt is False
    assert sheet.sheet.get_raw("A1") == "MVC"
    assert sheet.sheet.get_raw("B1") == "142.5"
    assert sheet.sheet.get_raw("A2") == "NVDA"
    assert "Importé" in sheet.msg


def test_csv_import_opens_new_sheet_if_active_not_blank(app, tmp_path):
    path = tmp_path / "data.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["x", "y"])

    sheet = _open_sheet(app)
    sheet.sheet.set("A1", "modèle en cours")
    n_before = len(sheet.workbook.tabs)

    sheet.csv_import_prompt = True
    sheet._csv_import_buf = str(path)
    sheet._confirm_csv_import()

    assert len(sheet.workbook.tabs) == n_before + 1
    assert sheet.sheet.get_raw("A1") == "x"


def test_csv_import_missing_file_shows_error_and_does_not_crash(app):
    sheet = _open_sheet(app)
    sheet.csv_import_prompt = True
    sheet._csv_import_buf = "/nonexistent/path/data.csv"
    sheet._confirm_csv_import()
    assert sheet.csv_import_prompt is False
    assert "chemin inaccessible" in sheet.msg.lower() or "échec" in sheet.msg.lower()
    sheet.draw(app.screen, RECT)   # ne doit pas lever


def test_csv_import_empty_path_shows_message_and_stays_closed(app):
    sheet = _open_sheet(app)
    sheet.csv_import_prompt = True
    sheet._csv_import_buf = "   "
    sheet._confirm_csv_import()
    assert sheet.csv_import_prompt is False
    assert sheet.msg == "Chemin vide."


def test_csv_import_prompt_pastes_via_ctrl_v(app, monkeypatch):
    from core import clipboard
    monkeypatch.setattr(clipboard, "paste", lambda: "/tmp/pasted.csv")

    sheet = _open_sheet(app)
    sheet.csv_import_prompt = True
    sheet._csv_import_buf = ""
    sheet.handle_event(_key(pygame.K_v, unicode="v", mod=pygame.KMOD_CTRL), RECT)
    assert sheet._csv_import_buf == "/tmp/pasted.csv"


def test_csv_import_prompt_escape_cancels(app):
    sheet = _open_sheet(app)
    sheet.csv_import_prompt = True
    sheet.handle_event(_key(pygame.K_ESCAPE), RECT)
    assert sheet.csv_import_prompt is False


def test_csv_import_prompt_is_modal(app):
    """Tant que la boîte est ouverte, les autres raccourcis du tableur
    (ex. Ctrl+Z) ne doivent pas s'exécuter."""
    sheet = _open_sheet(app)
    sheet.csv_import_prompt = True
    consumed = sheet.handle_event(_key(pygame.K_z, unicode="z", mod=pygame.KMOD_CTRL), RECT)
    assert consumed is True


def test_csv_import_draws_without_crash(app):
    sheet = _open_sheet(app)
    sheet.csv_import_prompt = True
    sheet._csv_import_buf = "some/path.csv"
    sheet.draw(app.screen, RECT)   # boîte modale rendue sans exception
