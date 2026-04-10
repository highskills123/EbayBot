"""Tests for ebay_bot.config."""

import os
import pytest

from ebay_bot.config import Config, _require


# ---------------------------------------------------------------------------
# _require helper
# ---------------------------------------------------------------------------


def test_require_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("SOME_VAR", "hello")
    assert _require("SOME_VAR") == "hello"


def test_require_raises_when_missing(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)
    with pytest.raises(EnvironmentError, match="MISSING_VAR"):
        _require("MISSING_VAR")


def test_require_raises_when_empty(monkeypatch):
    monkeypatch.setenv("EMPTY_VAR", "")
    with pytest.raises(EnvironmentError, match="EMPTY_VAR"):
        _require("EMPTY_VAR")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def _set_required_env(monkeypatch):
    monkeypatch.setenv("EBAY_APP_ID", "app123")
    monkeypatch.setenv("EBAY_DEV_ID", "dev123")
    monkeypatch.setenv("EBAY_CERT_ID", "cert123")
    monkeypatch.setenv("EBAY_USER_TOKEN", "token123")


def test_config_defaults(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("EBAY_SANDBOX", raising=False)
    monkeypatch.delenv("BOT_POLL_INTERVAL", raising=False)
    monkeypatch.delenv("LOW_STOCK_THRESHOLD", raising=False)

    cfg = Config()
    assert cfg.app_id == "app123"
    assert cfg.sandbox is True
    assert cfg.poll_interval == 300
    assert cfg.low_stock_threshold == 5


def test_config_sandbox_false(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("EBAY_SANDBOX", "false")
    cfg = Config()
    assert cfg.sandbox is False


def test_config_sandbox_numeric(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("EBAY_SANDBOX", "1")
    cfg = Config()
    assert cfg.sandbox is True


def test_config_custom_poll_interval(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("BOT_POLL_INTERVAL", "60")
    cfg = Config()
    assert cfg.poll_interval == 60


def test_config_missing_required_raises(monkeypatch):
    monkeypatch.delenv("EBAY_APP_ID", raising=False)
    monkeypatch.delenv("EBAY_DEV_ID", raising=False)
    monkeypatch.delenv("EBAY_CERT_ID", raising=False)
    monkeypatch.delenv("EBAY_USER_TOKEN", raising=False)
    with pytest.raises(EnvironmentError):
        Config()
