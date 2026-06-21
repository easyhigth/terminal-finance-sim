import os

import pytest

from core import i18n


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(i18n, "_SETTINGS", os.path.join(str(tmp_path), "settings.json"))
    monkeypatch.setattr(i18n, "_LANG", "fr")
    yield
    monkeypatch.setattr(i18n, "_LANG", "fr")


def test_get_lang_default_is_fr():
    assert i18n.get_lang() == "fr"


def test_set_lang_persists_to_disk():
    i18n.set_lang("en")
    assert i18n.get_lang() == "en"
    assert os.path.isfile(i18n._SETTINGS)
    i18n._LANG = "fr"
    i18n._load()
    assert i18n.get_lang() == "en"


def test_set_lang_invalid_value_falls_back_to_fr():
    i18n.set_lang("de")
    assert i18n.get_lang() == "fr"


def test_toggle_lang_switches_back_and_forth():
    assert i18n.toggle_lang() == "en"
    assert i18n.toggle_lang() == "fr"


def test_t_returns_translation_for_active_lang():
    i18n.set_lang("en")
    assert i18n.t("menu.new") == "NEW CAREER"
    i18n.set_lang("fr")
    assert i18n.t("menu.new") == "NOUVELLE CARRIÈRE"


def test_t_falls_back_to_raw_key_when_unknown():
    assert i18n.t("totally.unknown.key") == "totally.unknown.key"


def test_t_formats_kwargs():
    i18n.set_lang("fr")
    out = i18n.t("academy.progress", n=2, m=5)
    assert out == "2/5 leçons lues · cliquez une leçon pour l'étudier"


def test_load_missing_settings_file_defaults_to_fr():
    i18n._load()
    assert i18n.get_lang() == "fr"
