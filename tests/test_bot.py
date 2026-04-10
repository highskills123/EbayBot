"""Tests for EbayBot (bot.py) – uses mocking so no real API calls are made."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from ebay_bot.api import EbayAPIError
from ebay_bot.bot import EbayBot
from ebay_bot.config import Config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_config(monkeypatch):
    """Return a Config with all required env vars set."""
    monkeypatch.setenv("EBAY_APP_ID", "app")
    monkeypatch.setenv("EBAY_DEV_ID", "dev")
    monkeypatch.setenv("EBAY_CERT_ID", "cert")
    monkeypatch.setenv("EBAY_USER_TOKEN", "token")
    monkeypatch.setenv("EBAY_SANDBOX", "True")
    monkeypatch.setenv("BOT_POLL_INTERVAL", "60")
    monkeypatch.setenv("LOW_STOCK_THRESHOLD", "3")
    return Config()


@pytest.fixture()
def bot(mock_config):
    """Return an EbayBot with its internal EbayAPI mocked out."""
    with patch("ebay_bot.bot.EbayAPI") as MockAPI:
        instance = MockAPI.return_value
        b = EbayBot(config=mock_config)
        b._api = instance
        yield b


# ---------------------------------------------------------------------------
# print_summary
# ---------------------------------------------------------------------------


def test_print_summary_returns_dict(bot):
    bot._api.get_seller_summary.return_value = {
        "ActiveListingCount": "5",
        "QuantitySold": "2",
    }
    result = bot.print_summary()
    assert result["ActiveListingCount"] == "5"


def test_print_summary_handles_api_error(bot):
    bot._api.get_seller_summary.side_effect = EbayAPIError("network error")
    result = bot.print_summary()
    assert result == {}


# ---------------------------------------------------------------------------
# check_orders
# ---------------------------------------------------------------------------


def test_check_orders_returns_orders(bot):
    sample_order = {"OrderID": "123", "OrderStatus": "Active", "Total": {"_": "19.99"}}
    bot._api.get_orders.return_value = [sample_order]
    orders = bot.check_orders()
    assert len(orders) == 1
    assert orders[0]["OrderID"] == "123"


def test_check_orders_empty(bot):
    bot._api.get_orders.return_value = []
    orders = bot.check_orders()
    assert orders == []


def test_check_orders_handles_api_error(bot):
    bot._api.get_orders.side_effect = EbayAPIError("timeout")
    orders = bot.check_orders()
    assert orders == []


# ---------------------------------------------------------------------------
# check_inventory
# ---------------------------------------------------------------------------


def _make_listing(item_id, title, quantity):
    return {"ItemID": item_id, "Title": title, "QuantityAvailable": str(quantity)}


def test_check_inventory_flags_low_stock(bot):
    # threshold is 3 (from mock_config)
    bot._api.get_active_listings.return_value = [
        _make_listing("1", "Widget A", 2),
        _make_listing("2", "Widget B", 10),
    ]
    low = bot.check_inventory()
    assert len(low) == 1
    assert low[0]["ItemID"] == "1"


def test_check_inventory_no_low_stock(bot):
    bot._api.get_active_listings.return_value = [
        _make_listing("1", "Widget A", 5),
        _make_listing("2", "Widget B", 10),
    ]
    low = bot.check_inventory()
    assert low == []


def test_check_inventory_at_threshold_not_flagged(bot):
    # threshold is 3; quantity exactly at threshold should NOT be flagged
    bot._api.get_active_listings.return_value = [
        _make_listing("1", "Widget A", 3),
    ]
    low = bot.check_inventory()
    assert low == []


def test_check_inventory_handles_api_error(bot):
    bot._api.get_active_listings.side_effect = EbayAPIError("not found")
    low = bot.check_inventory()
    assert low == []


# ---------------------------------------------------------------------------
# relist_ended_items
# ---------------------------------------------------------------------------


def _make_unsold_response(*item_ids):
    """Build a minimal fake ebaysdk response for GetMyeBaySelling/UnsoldList."""
    items = [SimpleNamespace(ItemID=iid) for iid in item_ids]
    item_array = SimpleNamespace(Item=items if len(items) != 1 else items[0])
    unsold_list = SimpleNamespace(ItemArray=item_array)
    reply = SimpleNamespace(UnsoldList=unsold_list)
    return SimpleNamespace(reply=reply)


def test_relist_ended_items_relists_all(bot):
    bot._api._trading = MagicMock()
    bot._api._trading.execute.return_value = _make_unsold_response("A1", "A2")
    bot._api.relist_item.side_effect = lambda iid: f"NEW-{iid}"

    new_ids = bot.relist_ended_items()
    assert new_ids == ["NEW-A1", "NEW-A2"]


def test_relist_ended_items_no_unsold(bot):
    bot._api._trading = MagicMock()
    reply = SimpleNamespace(UnsoldList=None)
    bot._api._trading.execute.return_value = SimpleNamespace(reply=reply)

    new_ids = bot.relist_ended_items()
    assert new_ids == []


def test_relist_ended_items_handles_execute_error(bot):
    bot._api._trading = MagicMock()
    bot._api._trading.execute.side_effect = Exception("connection reset")

    new_ids = bot.relist_ended_items()
    assert new_ids == []
