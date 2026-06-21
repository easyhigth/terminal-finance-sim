import logging
import os

import pytest

from core import applog


@pytest.fixture
def _restore_env():
    old = os.environ.get("FINSIM_DEBUG")
    yield
    if old is None:
        os.environ.pop("FINSIM_DEBUG", None)
    else:
        os.environ["FINSIM_DEBUG"] = old


def test_debug_enabled_recognises_falsy_strings(_restore_env):
    for val in ("", "0", "false", "False", "no", "NO"):
        os.environ["FINSIM_DEBUG"] = val
        assert applog._debug_enabled() is False


def test_debug_enabled_recognises_truthy_strings(_restore_env):
    for val in ("1", "true", "yes", "anything"):
        os.environ["FINSIM_DEBUG"] = val
        assert applog._debug_enabled() is True


def test_debug_enabled_missing_var_is_false(_restore_env):
    os.environ.pop("FINSIM_DEBUG", None)
    assert applog._debug_enabled() is False


def test_logger_name_and_no_propagation():
    assert applog.logger.name == "finsim"
    assert applog.logger.propagate is False


def test_logger_disabled_by_default_uses_null_handler():
    if applog.DEBUG:
        pytest.skip("FINSIM_DEBUG actif dans cet environnement de test")
    assert applog.logger.level == logging.WARNING
    assert any(isinstance(h, logging.NullHandler) for h in applog.logger.handlers)
