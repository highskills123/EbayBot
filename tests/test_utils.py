"""Tests for ebay_bot.utils."""

import logging
from ebay_bot.utils import get_logger, format_price, utcnow


def test_get_logger_returns_logger():
    logger = get_logger("test.logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.logger"


def test_get_logger_idempotent():
    """Calling get_logger twice should not add duplicate handlers."""
    logger1 = get_logger("idempotent.test")
    logger2 = get_logger("idempotent.test")
    assert logger1 is logger2
    assert len(logger1.handlers) == 1


def test_format_price_default_currency():
    assert format_price(9.99) == "$9.99 USD"


def test_format_price_custom_currency():
    assert format_price(12.5, "GBP") == "$12.50 GBP"


def test_format_price_zero():
    assert format_price(0.0) == "$0.00 USD"


def test_utcnow_is_timezone_aware():
    import datetime

    now = utcnow()
    assert now.tzinfo is not None
    assert now.tzinfo == datetime.timezone.utc
